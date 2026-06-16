"""Logic cài đặt hệ thống.

Nhận cấu hình từ Web Installer, test kết nối DB, ghi file `.env` runtime, tạo
bảng, tạo Super Admin và lưu API key (đã mã hóa) vào `system_configs`.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.config import ENV_FILE, DATA_DIR, reload_settings
from app.core.database import build_engine
from app.core.security import (
    encrypt_secret,
    generate_secret_key,
    hash_password,
)
from app.models import Base, SystemConfig, User
from app.schemas.installer import FinalizePayload

SQLITE_PATH = (DATA_DIR / "app.db").as_posix()

# Map provider -> model mặc định nếu khách không chỉ định
DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
    "gemini": "gemini-1.5-pro",
}

# Tên config key cho API key của từng provider
PROVIDER_KEY_NAME = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def test_database_connection(database_url: str) -> tuple[bool, str]:
    """Thử kết nối DB với URL cho trước. Trả về (ok, message)."""
    try:
        engine = build_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True, "Kết nối Database thành công."
    except Exception as exc:  # noqa: BLE001 - cần báo nguyên nhân cho UI
        return False, f"Không kết nối được Database: {exc}"


# Key tạm thời dùng để qua bước cài đặt. Hệ thống License thật (kích hoạt sau khi
# cài, mở khóa tính năng trong Admin Panel) sẽ được bổ sung sau — xem [[license-plan]].
TEMP_LICENSE_KEY = "123456"


def validate_license(license_key: str) -> tuple[bool, str]:
    """Kiểm tra license key (TẠM THỜI).

    Hiện chỉ chấp nhận key tạm `123456` để hoàn tất cài đặt. Cơ chế bản quyền thật
    (ký số / kích hoạt sau cài) sẽ thay hàm này ở bản thương mại.
    """
    key = (license_key or "").strip()
    if key != TEMP_LICENSE_KEY:
        return False, "License key không đúng. Nhập key tạm: 123456"
    return True, "License hợp lệ."


def _write_env_file(values: dict[str, str]) -> None:
    """Ghi file .env runtime một cách atomic (ghi tmp rồi đổi tên)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in values.items()]
    content = "\n".join(lines) + "\n"
    tmp = Path(ENV_FILE).with_suffix(".env.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, ENV_FILE)


def finalize_installation(payload: FinalizePayload) -> tuple[bool, str]:
    """Thực thi toàn bộ quá trình cài đặt. Idempotent-ish: tạo bảng nếu chưa có."""

    # 1. Validate license
    ok, msg = validate_license(payload.license.license_key)
    if not ok:
        return False, msg

    # 2. Resolve DATABASE_URL + test kết nối
    database_url = payload.database.to_url(SQLITE_PATH)
    ok, msg = test_database_connection(database_url)
    if not ok:
        return False, msg

    # 3. Sinh SECRET_KEY và mã hóa API key
    secret_key = generate_secret_key()
    provider = payload.llm.provider
    default_model = payload.llm.default_model or DEFAULT_MODELS[provider]
    encrypted_api_key = encrypt_secret(payload.llm.api_key, secret_key)

    # 4. Tạo bảng + seed dữ liệu trong DB đích
    engine = build_engine(database_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        # Super Admin (chỉ tạo nếu chưa tồn tại email này)
        existing = db.query(User).filter(User.email == payload.admin.email).first()
        if not existing:
            db.add(
                User(
                    email=payload.admin.email,
                    full_name=payload.admin.full_name,
                    hashed_password=hash_password(payload.admin.password),
                    is_active=True,
                    is_superadmin=True,
                )
            )

        # Lưu cấu hình LLM vào system_configs
        _upsert_config(db, "LLM_PROVIDER", provider, is_secret=False,
                       description="Nhà cung cấp LLM mặc định")
        _upsert_config(db, "LLM_DEFAULT_MODEL", default_model, is_secret=False,
                       description="Model LLM mặc định")
        _upsert_config(db, PROVIDER_KEY_NAME[provider], encrypted_api_key,
                       is_secret=True, description=f"API key cho {provider} (đã mã hóa)")

        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return False, f"Lỗi khi khởi tạo dữ liệu: {exc}"
    finally:
        db.close()
        engine.dispose()

    # 5. Ghi .env runtime (đánh dấu INSTALLED=true)
    _write_env_file(
        {
            "INSTALLED": "true",
            "SECRET_KEY": secret_key,
            "DATABASE_URL": database_url,
            "LICENSE_KEY": payload.license.license_key.strip(),
            "APP_PORT": os.getenv("APP_PORT", "8080"),
        }
    )

    # 6. Reload settings để lần kiểm tra tiếp theo thấy INSTALLED=true
    reload_settings()
    return True, "Cài đặt hoàn tất."


def _upsert_config(db, key: str, value: str, *, is_secret: bool, description: str) -> None:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = value
        row.is_secret = is_secret
        row.description = description
    else:
        db.add(SystemConfig(key=key, value=value, is_secret=is_secret,
                            description=description))
