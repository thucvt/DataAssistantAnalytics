"""Cấu hình ứng dụng.

Đọc từ file `.env` runtime (mặc định `/app/data/.env`, override bằng biến môi
trường `ENV_FILE`). File này do Web Installer ghi ra sau khi khách điền cấu hình.
"""
from __future__ import annotations

import os  # noqa: E402 — phải import trước pydantic để đọc PORT
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Đường dẫn file .env runtime. Cho phép override để dễ test / chạy local.
# Trên Vercel, ENV_FILE trỏ về /dev/null (không tồn tại file .env — dùng env vars)
ENV_FILE = os.getenv("ENV_FILE", "/app/data/.env")
_env_file_exists = Path(ENV_FILE).exists()
DATA_DIR = Path(ENV_FILE).parent if ENV_FILE != "/dev/null" else Path("/tmp")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE if _env_file_exists else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Trạng thái cài đặt — quyết định boot Installer hay Main App
    INSTALLED: bool = False

    # Khóa bí mật sinh ngẫu nhiên lúc cài, dùng mã hóa API key trong DB (Fernet)
    SECRET_KEY: str = ""

    # Kết nối DB. Mặc định SQLite fallback trong thư mục data.
    DATABASE_URL: str = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"

    # License key của bản phần mềm đã bán
    LICENSE_KEY: str = ""

    # Cấu hình app
    APP_NAME: str = "Data Assistant Analytics"
    APP_PORT: int = int(os.getenv("PORT", os.getenv("APP_PORT", "8080")))
    DEBUG: bool = False

    # ── Facebook / Meta Ads ─────────────────────────────────────────────────
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""
    FACEBOOK_REDIRECT_URI: str = ""
    FACEBOOK_AD_ACCOUNT_ID: str = ""   # act_xxxxxxxxx

    # ── Shopee Open Platform ────────────────────────────────────────────────
    SHOPEE_PARTNER_ID: str = ""
    SHOPEE_PARTNER_KEY: str = ""
    SHOPEE_REDIRECT_URI: str = ""

    # ── TikTok Business API ─────────────────────────────────────────────────
    TIKTOK_APP_ID: str = ""
    TIKTOK_APP_SECRET: str = ""
    TIKTOK_REDIRECT_URI: str = ""
    TIKTOK_ADVERTISER_ID: str = ""

    # ── Google Ads Manager ──────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    GOOGLE_ADS_CUSTOMER_ID: str = ""
    GOOGLE_ADS_DEVELOPER_TOKEN: str = ""
    GOOGLE_ADS_LOGIN_CUSTOMER_ID: str = ""   # MCC account (tuỳ chọn)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Xóa cache để đọc lại .env (dùng sau khi Installer ghi file)."""
    get_settings.cache_clear()
    return get_settings()
