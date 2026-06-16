"""Shopee Open Platform API client.

Chữ ký số (signature) theo tài liệu Shopee v2, dùng HMAC-SHA256:

- API public (chưa có token):
    base_string = partner_id + path + timestamp
- API shop (cần token):
    base_string = partner_id + path + timestamp + access_token + shop_id
  sign = HEX( HMAC_SHA256(partner_key, base_string) )

Cấu hình đọc từ env vars (Settings):
  SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY, SHOPEE_REDIRECT_URI
"""
from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

HOST = "https://partner.shopeemobile.com"


def make_signature(partner_key: str, base_string: str) -> str:
    """HMAC-SHA256 hex digest — tách riêng để unit test xác định."""
    return hmac.new(
        partner_key.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class ShopeeClient:
    def __init__(self, partner_id: str, partner_key: str, redirect_uri: str = ""):
        self.partner_id = str(partner_id)
        self.partner_key = partner_key
        self.redirect_uri = redirect_uri

    @classmethod
    def from_settings(cls) -> "ShopeeClient":
        s = get_settings()
        if not s.SHOPEE_PARTNER_ID or not s.SHOPEE_PARTNER_KEY:
            raise ValueError("Chưa cấu hình SHOPEE_PARTNER_ID / SHOPEE_PARTNER_KEY trong .env")
        return cls(s.SHOPEE_PARTNER_ID, s.SHOPEE_PARTNER_KEY, s.SHOPEE_REDIRECT_URI)

    # ----- Public (chưa có token) -----
    def _sign_public(self, path: str, timestamp: int) -> str:
        base = f"{self.partner_id}{path}{timestamp}"
        return make_signature(self.partner_key, base)

    def build_authorization_url(self, state: str = "") -> str:
        """URL để chủ shop bấm vào và ủy quyền cho app.

        Shopee chỉ append `code` & `shop_id` vào redirect, không có tham số state
        riêng. Vì vậy ta nhúng `state` ngay vào query của redirect URI để callback
        biết kết nối thuộc user nào.
        """
        path = "/api/v2/shop/auth_partner"
        ts = int(time.time())
        sign = self._sign_public(path, ts)
        redirect = self.redirect_uri
        if state:
            sep = "&" if "?" in redirect else "?"
            redirect = f"{redirect}{sep}{urlencode({'state': state})}"
        params = {
            "partner_id": self.partner_id,
            "timestamp": ts,
            "sign": sign,
            "redirect": redirect,
        }
        return f"{HOST}{path}?{urlencode(params)}"

    def get_access_token(self, code: str, shop_id: int) -> dict:
        """Đổi code lấy access_token cho shop."""
        path = "/api/v2/auth/token/get"
        ts = int(time.time())
        sign = self._sign_public(path, ts)
        url = f"{HOST}{path}"
        params = {"partner_id": self.partner_id, "timestamp": ts, "sign": sign}
        body = {"code": code, "shop_id": int(shop_id), "partner_id": int(self.partner_id)}
        with httpx.Client(timeout=20) as client:
            resp = client.post(url, params=params, json=body)
            resp.raise_for_status()
            return resp.json()  # {access_token, refresh_token, expire_in, ...}

    # ----- Shop API (cần token) -----
    def _sign_shop(self, path: str, timestamp: int, access_token: str, shop_id: int) -> str:
        base = f"{self.partner_id}{path}{timestamp}{access_token}{shop_id}"
        return make_signature(self.partner_key, base)

    def signed_get(self, path: str, access_token: str, shop_id: int, extra: dict | None = None):
        ts = int(time.time())
        sign = self._sign_shop(path, ts, access_token, shop_id)
        params = {
            "partner_id": self.partner_id,
            "timestamp": ts,
            "sign": sign,
            "access_token": access_token,
            "shop_id": int(shop_id),
        }
        if extra:
            params.update(extra)
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{HOST}{path}", params=params)
            resp.raise_for_status()
            return resp.json()

    def fetch_revenue(
        self, access_token: str, shop_id: int, time_from: int, time_to: int
    ) -> list[dict]:
        """Lấy doanh thu theo đơn trong khoảng [time_from, time_to] (unix seconds).

        Dùng order.get_order_list (theo create_time) + escrow để tính doanh thu.
        Trả về [{date(YYYY-MM-DD), revenue}] đã gộp theo ngày.
        """
        from collections import defaultdict
        from datetime import datetime, timezone

        path = "/api/v2/order/get_order_list"
        daily: dict[str, float] = defaultdict(float)
        cursor = ""
        while True:
            data = self.signed_get(
                path, access_token, shop_id,
                extra={
                    "time_range_field": "create_time",
                    "time_from": time_from,
                    "time_to": time_to,
                    "page_size": 100,
                    "cursor": cursor,
                    "response_optional_fields": "order_status,total_amount,create_time",
                },
            )
            resp = data.get("response", {})
            for o in resp.get("order_list", []):
                ts = o.get("create_time")
                amount = float(o.get("total_amount", 0) or 0)
                if ts:
                    day = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                    daily[day] += amount
            if resp.get("more") and resp.get("next_cursor"):
                cursor = resp["next_cursor"]
            else:
                break
        return [{"date": d, "revenue": round(v, 2)} for d, v in sorted(daily.items())]
