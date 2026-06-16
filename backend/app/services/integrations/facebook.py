"""Facebook Graph API — OAuth 2.0 + lấy chi phí quảng cáo (Meta Ads).

Cấu hình (App ID/Secret/Redirect URI) lưu trong system_configs, set qua Admin Panel:
  FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_REDIRECT_URI
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.services import config_service

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
OAUTH_DIALOG = f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"

DEFAULT_SCOPES = ["ads_read", "read_insights"]


def _cfg(db: Session) -> tuple[str, str, str]:
    return (
        config_service.get_config(db, "FACEBOOK_APP_ID"),
        config_service.get_config(db, "FACEBOOK_APP_SECRET"),
        config_service.get_config(db, "FACEBOOK_REDIRECT_URI"),
    )


def build_authorization_url(db: Session, state: str) -> str:
    """Sinh URL để user bấm vào, đồng ý cấp quyền cho app."""
    app_id, _, redirect_uri = _cfg(db)
    if not app_id or not redirect_uri:
        raise ValueError("Chưa cấu hình FACEBOOK_APP_ID / FACEBOOK_REDIRECT_URI.")
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": ",".join(DEFAULT_SCOPES),
        "response_type": "code",
    }
    return f"{OAUTH_DIALOG}?{urlencode(params)}"


def exchange_code_for_token(db: Session, code: str) -> dict:
    """Đổi authorization code lấy access_token (long-lived nếu có thể)."""
    app_id, app_secret, redirect_uri = _cfg(db)
    params = {
        "client_id": app_id,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    with httpx.Client(timeout=20) as client:
        resp = client.get(f"{GRAPH_BASE}/oauth/access_token", params=params)
        resp.raise_for_status()
        data = resp.json()

        # Đổi sang long-lived token
        short_token = data.get("access_token", "")
        long_params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        }
        long_resp = client.get(f"{GRAPH_BASE}/oauth/access_token", params=long_params)
        if long_resp.status_code == 200:
            data = long_resp.json()
    return data  # {access_token, token_type, expires_in?}


def fetch_ad_spend(access_token: str, ad_account_id: str, since: str, until: str) -> list[dict]:
    """Lấy chi phí Ads theo ngày từ Insights API.

    ad_account_id dạng 'act_123456789'. Trả [{date, spend}].
    """
    acct = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
    params = {
        "access_token": access_token,
        "level": "account",
        "time_increment": 1,
        "fields": "spend",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
    }
    out: list[dict] = []
    url = f"{GRAPH_BASE}/{acct}/insights"
    with httpx.Client(timeout=30) as client:
        while url:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
            for row in payload.get("data", []):
                out.append({
                    "date": row.get("date_start"),
                    "spend": float(row.get("spend", 0) or 0),
                })
            url = payload.get("paging", {}).get("next")
            params = None  # next URL đã chứa sẵn query
    return out
