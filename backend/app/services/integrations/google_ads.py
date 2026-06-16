"""Google Ads Manager — OAuth 2.0 + lấy chi phí quảng cáo.

Dùng Google Ads API v18 qua REST (không cần thư viện google-ads nặng).
Tài liệu: https://developers.google.com/google-ads/api/docs/rest/overview

Cấu hình trong system_configs:
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.services import config_service

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
ADS_REST_BASE = "https://googleads.googleapis.com/v18"

SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _cfg(db: Session) -> tuple[str, str, str]:
    return (
        config_service.get_config(db, "GOOGLE_CLIENT_ID"),
        config_service.get_config(db, "GOOGLE_CLIENT_SECRET"),
        config_service.get_config(db, "GOOGLE_REDIRECT_URI"),
    )


def build_authorization_url(db: Session, state: str) -> str:
    client_id, _, redirect_uri = _cfg(db)
    if not client_id or not redirect_uri:
        raise ValueError("Chưa cấu hình GOOGLE_CLIENT_ID / GOOGLE_REDIRECT_URI.")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",   # lấy refresh_token
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(db: Session, code: str) -> dict:
    """Đổi authorization code lấy access_token + refresh_token."""
    client_id, client_secret, redirect_uri = _cfg(db)
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


def refresh_access_token(db: Session, refresh_token: str) -> str:
    """Làm mới access_token từ refresh_token khi hết hạn."""
    client_id, client_secret, _ = _cfg(db)
    with httpx.Client(timeout=20) as client:
        resp = client.post(TOKEN_URL, data={
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        return resp.json().get("access_token", "")


def _gaql_query(customer_id: str, start: str, end: str) -> str:
    """Google Ads Query Language (GAQL) — lấy cost theo ngày."""
    return (
        "SELECT segments.date, metrics.cost_micros "
        "FROM customer "
        f"WHERE segments.date BETWEEN '{start}' AND '{end}' "
        "ORDER BY segments.date ASC"
    )


def fetch_ad_spend(
    access_token: str,
    customer_id: str,
    start_date: str,
    end_date: str,
    developer_token: str,
    login_customer_id: str = "",
) -> list[dict]:
    """Lấy chi phí Ads theo ngày từ Google Ads Manager.

    customer_id: Google Ads customer ID không có dấu gạch (vd '1234567890').
    developer_token: token do Google cấp khi đăng ký Google Ads API.
    Trả về [{date, spend}] (spend tính bằng đơn vị tiền tệ, không phải micros).
    """
    cid = customer_id.replace("-", "")
    url = f"{ADS_REST_BASE}/customers/{cid}/googleAds:searchStream"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
        "Content-Type": "application/json",
    }
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id.replace("-", "")

    body = {"query": _gaql_query(cid, start_date, end_date)}
    out: list[dict] = []
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        # searchStream trả list of batches
        batches = resp.json() if isinstance(resp.json(), list) else [resp.json()]
        for batch in batches:
            for row in batch.get("results", []):
                date = row.get("segments", {}).get("date", "")
                micros = int(row.get("metrics", {}).get("costMicros", 0) or 0)
                out.append({"date": date, "spend": round(micros / 1_000_000, 2)})
    return out
