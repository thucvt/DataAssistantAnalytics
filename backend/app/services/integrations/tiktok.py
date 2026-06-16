"""TikTok Business API — OAuth 2.0 + lấy chi phí quảng cáo.

Tài liệu: https://business-api.tiktok.com/portal/docs
Cấu hình trong system_configs:
  TIKTOK_APP_ID, TIKTOK_APP_SECRET, TIKTOK_REDIRECT_URI
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.services import config_service

AUTH_BASE = "https://business-api.tiktok.com/portal/auth"
API_BASE = "https://business-api.tiktok.com/open_api/v1.3"
TOKEN_URL = f"{API_BASE}/oauth2/access_token/"


def _cfg(db: Session) -> tuple[str, str, str]:
    return (
        config_service.get_config(db, "TIKTOK_APP_ID"),
        config_service.get_config(db, "TIKTOK_APP_SECRET"),
        config_service.get_config(db, "TIKTOK_REDIRECT_URI"),
    )


def build_authorization_url(db: Session, state: str) -> str:
    app_id, _, redirect_uri = _cfg(db)
    if not app_id or not redirect_uri:
        raise ValueError("Chưa cấu hình TIKTOK_APP_ID / TIKTOK_REDIRECT_URI.")
    params = {
        "app_id": app_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "rid": state[:8],
    }
    return f"{AUTH_BASE}?{urlencode(params)}"


def exchange_code_for_token(db: Session, auth_code: str) -> dict:
    """Đổi auth_code lấy access_token."""
    app_id, app_secret, _ = _cfg(db)
    with httpx.Client(timeout=20) as client:
        resp = client.post(
            TOKEN_URL,
            json={"app_id": app_id, "secret": app_secret, "auth_code": auth_code},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        # TikTok trả {code:0, data:{access_token, advertiser_ids, ...}}
        if data.get("code") != 0:
            raise ValueError(f"TikTok lỗi: {data.get('message')}")
        return data.get("data", {})


def fetch_ad_spend(
    access_token: str, advertiser_id: str, start_date: str, end_date: str
) -> list[dict]:
    """Lấy chi phí Ads theo ngày (YYYY-MM-DD) từ TikTok Ads Manager.

    Trả về [{date, spend}].
    """
    url = f"{API_BASE}/report/integrated/get/"
    headers = {"Access-Token": access_token}
    params = {
        "advertiser_id": advertiser_id,
        "report_type": "BASIC",
        "data_level": "AUCTION_ADVERTISER",
        "dimensions": '["stat_time_day"]',
        "metrics": '["spend"]',
        "start_date": start_date,
        "end_date": end_date,
        "page_size": 1000,
    }
    out: list[dict] = []
    with httpx.Client(timeout=30) as client:
        page = 1
        while True:
            params["page"] = page
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise ValueError(f"TikTok Ads lỗi: {data.get('message')}")
            rows = data.get("data", {}).get("list", [])
            for row in rows:
                day = row.get("dimensions", {}).get("stat_time_day", "")[:10]
                spend = float(row.get("metrics", {}).get("spend", 0) or 0)
                out.append({"date": day, "spend": spend})
            page_info = data.get("data", {}).get("page_info", {})
            if page >= page_info.get("total_page", 1):
                break
            page += 1
    return out
