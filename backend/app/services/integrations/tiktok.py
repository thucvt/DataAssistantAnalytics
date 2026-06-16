"""TikTok Business API v1.3 — OAuth 2.0 + lấy chi phí quảng cáo.

Cấu hình đọc từ env vars (Settings):
  TIKTOK_APP_ID, TIKTOK_APP_SECRET, TIKTOK_REDIRECT_URI
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

AUTH_BASE = "https://business-api.tiktok.com/portal/auth"
API_BASE = "https://business-api.tiktok.com/open_api/v1.3"
TOKEN_URL = f"{API_BASE}/oauth2/access_token/"


def _cfg() -> tuple[str, str, str]:
    s = get_settings()
    return s.TIKTOK_APP_ID, s.TIKTOK_APP_SECRET, s.TIKTOK_REDIRECT_URI


def build_authorization_url(state: str) -> str:
    app_id, _, redirect_uri = _cfg()
    if not app_id or not redirect_uri:
        raise ValueError("Chưa cấu hình TIKTOK_APP_ID / TIKTOK_REDIRECT_URI trong .env")
    params = {
        "app_id": app_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "rid": state[:8],
    }
    return f"{AUTH_BASE}?{urlencode(params)}"


def exchange_code_for_token(auth_code: str) -> dict:
    """Đổi auth_code lấy access_token."""
    app_id, app_secret, _ = _cfg()
    with httpx.Client(timeout=20) as client:
        resp = client.post(
            TOKEN_URL,
            json={"app_id": app_id, "secret": app_secret, "auth_code": auth_code},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise ValueError(f"TikTok lỗi: {data.get('message')}")
        return data.get("data", {})


def verify_token(access_token: str, advertiser_id: str) -> dict:
    """Xác minh token bằng cách lấy thông tin advertiser. Trả {name}."""
    url = f"{API_BASE}/advertiser/info/"
    with httpx.Client(timeout=10) as client:
        resp = client.get(url, params={"advertiser_ids": f'["{advertiser_id}"]'},
                          headers={"Access-Token": access_token})
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise ValueError(data.get("message", "Token không hợp lệ"))
        lst = data.get("data", {}).get("list", [])
        name = lst[0].get("advertiser_name", f"Advertiser {advertiser_id}") if lst else advertiser_id
        return {"name": name}


def fetch_ad_spend(
    access_token: str, advertiser_id: str, start_date: str, end_date: str
) -> list[dict]:
    """Lấy chi phí Ads theo ngày. Trả [{date, spend}]."""
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
            for row in data.get("data", {}).get("list", []):
                day = row.get("dimensions", {}).get("stat_time_day", "")[:10]
                spend = float(row.get("metrics", {}).get("spend", 0) or 0)
                out.append({"date": day, "spend": spend})
            page_info = data.get("data", {}).get("page_info", {})
            if page >= page_info.get("total_page", 1):
                break
            page += 1
    return out
