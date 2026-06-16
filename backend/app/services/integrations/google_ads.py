"""Google Ads Manager — OAuth 2.0 + lấy chi phí quảng cáo (REST API v18, GAQL).

Cấu hình đọc từ env vars (Settings):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
  GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CUSTOMER_ID, GOOGLE_ADS_LOGIN_CUSTOMER_ID
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ADS_REST_BASE = "https://googleads.googleapis.com/v18"

SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _cfg() -> tuple[str, str, str]:
    s = get_settings()
    return s.GOOGLE_CLIENT_ID, s.GOOGLE_CLIENT_SECRET, s.GOOGLE_REDIRECT_URI


def build_authorization_url(state: str) -> str:
    client_id, _, redirect_uri = _cfg()
    if not client_id or not redirect_uri:
        raise ValueError("Chưa cấu hình GOOGLE_CLIENT_ID / GOOGLE_REDIRECT_URI trong .env")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    """Đổi authorization code lấy access_token + refresh_token."""
    client_id, client_secret, redirect_uri = _cfg()
    with httpx.Client(timeout=20) as client:
        resp = client.post(TOKEN_URL, data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        return resp.json()  # {access_token, refresh_token, expires_in, ...}


def refresh_access_token(refresh_token: str) -> str:
    """Làm mới access_token từ refresh_token."""
    client_id, client_secret, _ = _cfg()
    with httpx.Client(timeout=20) as client:
        resp = client.post(TOKEN_URL, data={
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        return resp.json().get("access_token", "")


def fetch_ad_spend(
    access_token: str,
    customer_id: str,
    start_date: str,
    end_date: str,
    developer_token: str,
    login_customer_id: str = "",
) -> list[dict]:
    """Lấy chi phí theo ngày qua GAQL searchStream. Trả [{date, spend}]."""
    cid = customer_id.replace("-", "")
    url = f"{ADS_REST_BASE}/customers/{cid}/googleAds:searchStream"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
        "Content-Type": "application/json",
    }
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id.replace("-", "")
    gaql = (
        "SELECT segments.date, metrics.cost_micros "
        "FROM customer "
        f"WHERE segments.date BETWEEN '{start_date}' AND '{end_date}' "
        "ORDER BY segments.date ASC"
    )
    out: list[dict] = []
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json={"query": gaql}, headers=headers)
        resp.raise_for_status()
        batches = resp.json() if isinstance(resp.json(), list) else [resp.json()]
        for batch in batches:
            for row in batch.get("results", []):
                date = row.get("segments", {}).get("date", "")
                micros = int(row.get("metrics", {}).get("costMicros", 0) or 0)
                out.append({"date": date, "spend": round(micros / 1_000_000, 2)})
    return out
