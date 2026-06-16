"""Đọc/ghi cấu hình hệ thống trong bảng system_configs.

Giá trị secret (API key) được mã hóa bằng SECRET_KEY khi ghi và giải mã khi đọc.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models import SystemConfig

# Tên config key cho API key của từng provider
PROVIDER_KEY_NAME = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
    "gemini": "gemini-1.5-pro",
}


def get_config(db: Session, key: str, default: str = "") -> str:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not row:
        return default
    if row.is_secret:
        return decrypt_secret(row.value, get_settings().SECRET_KEY)
    return row.value


def set_config(
    db: Session, key: str, value: str, *, is_secret: bool = False, description: str = ""
) -> SystemConfig:
    stored = encrypt_secret(value, get_settings().SECRET_KEY) if is_secret else value
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = stored
        row.is_secret = is_secret
        if description:
            row.description = description
    else:
        row = SystemConfig(key=key, value=stored, is_secret=is_secret, description=description)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_config(db: Session, key: str) -> bool:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def get_active_provider(db: Session) -> str:
    return get_config(db, "LLM_PROVIDER", "openai")


def get_active_model(db: Session) -> str:
    provider = get_active_provider(db)
    return get_config(db, "LLM_DEFAULT_MODEL", DEFAULT_MODELS.get(provider, "gpt-4o"))


def get_api_key(db: Session, provider: str) -> str:
    return get_config(db, PROVIDER_KEY_NAME.get(provider, ""), "")


def set_api_key(db: Session, provider: str, api_key: str) -> None:
    key_name = PROVIDER_KEY_NAME.get(provider)
    if not key_name:
        raise ValueError(f"Provider không hỗ trợ: {provider}")
    set_config(db, key_name, api_key, is_secret=True,
               description=f"API key cho {provider} (đã mã hóa)")


def list_provider_status(db: Session) -> dict:
    """Trả về trạng thái cấu hình để hiển thị Admin Panel (không lộ key)."""
    return {
        "active_provider": get_active_provider(db),
        "active_model": get_active_model(db),
        "keys_configured": {
            p: bool(get_api_key(db, p)) for p in PROVIDER_KEY_NAME
        },
    }
