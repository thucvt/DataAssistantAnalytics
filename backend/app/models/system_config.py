from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemConfig(Base, TimestampMixin):
    """Lưu cấu hình hệ thống dạng key/value.

    Dùng cho API keys của LLM/OAuth. Khi `is_secret=True`, `value` được mã hóa
    bằng Fernet (xem core/security.py) trước khi ghi DB.
    """

    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(String(255), default="")
