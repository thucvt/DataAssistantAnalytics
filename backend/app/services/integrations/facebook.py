"""Facebook Graph API v25 — OAuth 2.0 + lấy chi phí Meta Ads.

App credentials (App ID / Secret / Redirect URI) đọc từ env vars qua Settings.
Không cần nhập trên UI — admin khai báo trong docker-compose.yml một lần.
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

GRAPH_VERSION = "v25.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
OAUTH_DIALOG = f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"

# Quyền tối thiểu để đọc Ads Insights
SCOPES = [
    "ads_read",          # Đọc dữ liệu chiến dịch / nhóm / quảng cáo
    "read_insights",     # Đọc Insights API (spend, impressions, clicks...)
    "ads_management",    # Cần để gọi /insights endpoint ở level account
    "business_management",  # Truy cập Business Manager / Ad Account
]


def _cfg() -> tuple[str, str, str]:
    s = get_settings()
    return s.FACEBOOK_APP_ID, s.FACEBOOK_APP_SECRET, s.FACEBOOK_REDIRECT_URI


def build_authorization_url(state: str) -> str:
    app_id, _, redirect_uri = _cfg()
    if not app_id or not redirect_uri:
        raise ValueError("Chưa cấu hình FACEBOOK_APP_ID / FACEBOOK_REDIRECT_URI trong .env")
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": ",".join(SCOPES),
        "response_type": "code",
    }
    return f"{OAUTH_DIALOG}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    """Đổi authorization code lấy long-lived access_token (60 ngày)."""
    app_id, app_secret, redirect_uri = _cfg()
    with httpx.Client(timeout=20) as client:
        # Bước 1: đổi code → short-lived token
        resp = client.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        })
        resp.raise_for_status()
        data = resp.json()

        # Bước 2: đổi short-lived → long-lived (60 ngày)
        long_resp = client.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": data.get("access_token", ""),
        })
        if long_resp.status_code == 200:
            data = long_resp.json()
    return data  # {access_token, token_type, expires_in}


def fetch_ad_accounts(access_token: str) -> list[dict]:
    """Lấy danh sách Ad Accounts thuộc token. Trả [{id, name, currency}]."""
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_BASE}/me/adaccounts", params={
            "access_token": access_token,
            "fields": "account_id,name,currency,account_status",
            "limit": 100,
        })
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "id": f"act_{row['account_id']}",
                "name": row.get("name", ""),
                "currency": row.get("currency", ""),
                "status": row.get("account_status", 1),
            }
            for row in data.get("data", [])
        ]


def verify_token(access_token: str) -> dict:
    """Kiểm tra token còn hợp lệ không. Trả {name, expires_at} hoặc raise."""
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_BASE}/me", params={
            "access_token": access_token,
            "fields": "id,name",
        })
        data = resp.json()
        # Graph API trả lỗi trong body (HTTP 200 hoặc 4xx)
        if "error" in data:
            msg = data["error"].get("message", "Token không hợp lệ")
            code = data["error"].get("code", 0)
            raise ValueError(f"{msg} (code {code})")
        if not resp.is_success:
            resp.raise_for_status()

        # Thử lấy expires_at qua debug_token — dùng App Token nếu có, không thì bỏ qua
        exp = None
        app_id, app_secret, _ = _cfg()
        if app_id and app_secret:
            try:
                app_token = f"{app_id}|{app_secret}"
                dbg = client.get(f"{GRAPH_BASE}/debug_token", params={
                    "input_token": access_token,
                    "access_token": app_token,
                })
                dbg_data = dbg.json().get("data", {})
                exp_ts = dbg_data.get("expires_at") or dbg_data.get("data_access_expires_at")
                if exp_ts and int(exp_ts) > 0:
                    from datetime import datetime, timezone
                    exp = datetime.fromtimestamp(int(exp_ts), tz=timezone.utc).isoformat()
            except Exception:
                pass

        return {"name": data.get("name", ""), "expires_at": exp}


def try_extend_token(short_token: str) -> tuple[str, bool]:
    """Thử gia hạn sang long-lived token (60 ngày). Cần App credentials trong .env.

    Trả (token, extended). Nếu không có App credentials thì trả token gốc, False.
    """
    app_id, app_secret, _ = _cfg()
    if not app_id or not app_secret:
        return short_token, False
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        })
        if resp.status_code == 200 and "access_token" in resp.json():
            return resp.json()["access_token"], True
    return short_token, False


def fetch_ad_spend(access_token: str, ad_account_id: str, since: str, until: str) -> list[dict]:
    """Lấy chi phí theo ngày từ Marketing Insights API.

    ad_account_id: 'act_123456789'. Trả [{date, spend}].
    """
    acct = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
    url = f"{GRAPH_BASE}/{acct}/insights"
    params = {
        "access_token": access_token,
        "level": "account",
        "time_increment": 1,
        "fields": "spend,date_start",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "limit": 500,
    }
    out: list[dict] = []
    with httpx.Client(timeout=30) as client:
        while url:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
            for row in payload.get("data", []):
                out.append({
                    "date": row.get("date_start", ""),
                    "spend": float(row.get("spend", 0) or 0),
                })
            url = payload.get("paging", {}).get("next")
            params = None  # URL tiếp theo đã có sẵn query params
    return out
