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
