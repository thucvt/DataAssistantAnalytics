"""Lớp truy xuất dữ liệu thô từ các nguồn đã kết nối (Meta Ads, Shopee).

Đây là phần "thực thi" mà LangChain Tools (xem agent.py) gọi tới. Tách khỏi tool
để dễ test và tái dùng cho cả endpoint báo cáo (analytics router).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services import config_service, oauth_service
from app.services.integrations import facebook
from app.services.integrations.shopee import ShopeeClient


def get_meta_ads_cost(db: Session, user_id: int, since: str, until: str) -> list[dict]:
    """Chi phí Ads Meta theo ngày trong [since, until] (YYYY-MM-DD)."""
    token = oauth_service.get_access_token(db, user_id, "facebook")
    if not token:
        raise ValueError("Chưa kết nối Facebook. Vào Data Sources để kết nối.")
    conn = oauth_service.get_connection(db, user_id, "facebook")
    extra = oauth_service.get_extra(conn) if conn else {}
    ad_account_id = extra.get("ad_account_id") or config_service.get_config(
        db, "FACEBOOK_AD_ACCOUNT_ID"
    )
    if not ad_account_id:
        raise ValueError("Chưa cấu hình FACEBOOK_AD_ACCOUNT_ID.")
    return facebook.fetch_ad_spend(token, ad_account_id, since, until)


def get_shopee_revenue(db: Session, user_id: int, since: str, until: str) -> list[dict]:
    """Doanh thu Shopee theo ngày trong [since, until] (YYYY-MM-DD)."""
    token = oauth_service.get_access_token(db, user_id, "shopee")
    conn = oauth_service.get_connection(db, user_id, "shopee")
    if not token or not conn:
        raise ValueError("Chưa kết nối Shopee. Vào Data Sources để kết nối.")
    shop_id = oauth_service.get_extra(conn).get("shop_id")
    if not shop_id:
        raise ValueError("Thiếu shop_id của Shopee.")

    time_from = int(datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    time_to = int(datetime.strptime(until, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, tzinfo=timezone.utc).timestamp())

    client = ShopeeClient.from_db(db)
    return client.fetch_revenue(token, int(shop_id), time_from, time_to)
