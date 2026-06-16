from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OAuthConnection(Base, TimestampMixin):
    """Kết nối nguồn dữ liệu của 1 user (Facebook, Shopee...).

    access_token / refresh_token được mã hóa Fernet trước khi lưu. `extra` chứa
    JSON metadata theo provider (vd shop_id của Shopee, ad_account_id của Meta).
    """

    __tablename__ = "oauth_connections"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)  # facebook | shopee
    access_token: Mapped[str] = mapped_column(Text, default="")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
