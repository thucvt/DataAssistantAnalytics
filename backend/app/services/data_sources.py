"""Truy xuất dữ liệu thô từ các nguồn đã kết nối.

Hỗ trợ: Meta Ads (Facebook), Shopee, TikTok Ads, Google Ads Manager.
LangChain Tools (agent.py) và Analytics router đều gọi vào đây.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services import config_service, oauth_service
from app.services.integrations import facebook
from app.services.integrations import tiktok as tiktok_client
from app.services.integrations import google_ads as google_client
from app.services.integrations.shopee import ShopeeClient


def get_meta_ads_cost(db: Session, user_id: int, since: str, until: str) -> list[dict]:
    """Chi phí Ads Meta theo ngày [{date, spend}]."""
    token = oauth_service.get_access_token(db, user_id, "facebook")
    if not token:
        raise ValueError("Chưa kết nối Facebook. Vào Data Sources để kết nối.")
    conn = oauth_service.get_connection(db, user_id, "facebook")
    extra = oauth_service.get_extra(conn) if conn else {}
    ad_account_id = extra.get("ad_account_id") or config_service.get_config(db, "FACEBOOK_AD_ACCOUNT_ID")
    if not ad_account_id:
        raise ValueError("Chưa cấu hình FACEBOOK_AD_ACCOUNT_ID.")
    return facebook.fetch_ad_spend(token, ad_account_id, since, until)


def get_shopee_revenue(db: Session, user_id: int, since: str, until: str) -> list[dict]:
    """Doanh thu Shopee theo ngày [{date, revenue}]."""
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


def get_tiktok_ads_cost(db: Session, user_id: int, since: str, until: str) -> list[dict]:
    """Chi phí TikTok Ads theo ngày [{date, spend}]."""
    token = oauth_service.get_access_token(db, user_id, "tiktok")
    if not token:
        raise ValueError("Chưa kết nối TikTok. Vào Data Sources để kết nối.")
    conn = oauth_service.get_connection(db, user_id, "tiktok")
    extra = oauth_service.get_extra(conn) if conn else {}
    advertiser_id = (
        extra.get("advertiser_id")
        or config_service.get_config(db, "TIKTOK_ADVERTISER_ID")
    )
    if not advertiser_id:
        raise ValueError("Chưa cấu hình TIKTOK_ADVERTISER_ID.")
    return tiktok_client.fetch_ad_spend(token, advertiser_id, since, until)


def get_google_ads_cost(db: Session, user_id: int, since: str, until: str) -> list[dict]:
    """Chi phí Google Ads theo ngày [{date, spend}]."""
    from app.core.config import get_settings
    from app.core.security import decrypt_secret

    token = oauth_service.get_access_token(db, user_id, "google")
    if not token:
        raise ValueError("Chưa kết nối Google Ads. Vào Data Sources để kết nối.")
    conn = oauth_service.get_connection(db, user_id, "google")
    extra = oauth_service.get_extra(conn) if conn else {}

    customer_id = extra.get("customer_id") or config_service.get_config(db, "GOOGLE_ADS_CUSTOMER_ID")
    developer_token = config_service.get_config(db, "GOOGLE_ADS_DEVELOPER_TOKEN")
    login_customer_id = config_service.get_config(db, "GOOGLE_ADS_LOGIN_CUSTOMER_ID")

    if not customer_id:
        raise ValueError("Chưa cấu hình GOOGLE_ADS_CUSTOMER_ID.")
    if not developer_token:
        raise ValueError("Chưa cấu hình GOOGLE_ADS_DEVELOPER_TOKEN.")

    # Thử refresh token nếu cần
    refresh_token_enc = conn.refresh_token if conn else ""
    if refresh_token_enc:
        secret = get_settings().SECRET_KEY
        refresh_tok = decrypt_secret(refresh_token_enc, secret)
        try:
            token = google_client.refresh_access_token(db, refresh_tok)
        except Exception:
            pass  # giữ nguyên token cũ nếu refresh lỗi

    return google_client.fetch_ad_spend(
        token, customer_id, since, until, developer_token, login_customer_id
    )
