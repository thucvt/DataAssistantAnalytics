"""Lưu/đọc kết nối OAuth của user. Token được mã hóa trước khi ghi DB."""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models import OAuthConnection


def save_connection(
    db: Session,
    *,
    user_id: int,
    provider: str,
    access_token: str,
    refresh_token: str = "",
    expires_at: datetime | None = None,
    extra: dict | None = None,
) -> OAuthConnection:
    secret = get_settings().SECRET_KEY
    conn = (
        db.query(OAuthConnection)
        .filter(OAuthConnection.user_id == user_id, OAuthConnection.provider == provider)
        .first()
    )
    if not conn:
        conn = OAuthConnection(user_id=user_id, provider=provider)
        db.add(conn)
    conn.access_token = encrypt_secret(access_token, secret)
    conn.refresh_token = encrypt_secret(refresh_token, secret) if refresh_token else ""
    conn.expires_at = expires_at
    conn.extra = json.dumps(extra or {})
    db.commit()
    db.refresh(conn)
    return conn


def get_connection(db: Session, user_id: int, provider: str) -> OAuthConnection | None:
    return (
        db.query(OAuthConnection)
        .filter(OAuthConnection.user_id == user_id, OAuthConnection.provider == provider)
        .first()
    )


def get_access_token(db: Session, user_id: int, provider: str) -> str:
    conn = get_connection(db, user_id, provider)
    if not conn:
        return ""
    return decrypt_secret(conn.access_token, get_settings().SECRET_KEY)


def get_extra(conn: OAuthConnection) -> dict:
    try:
        return json.loads(conn.extra or "{}")
    except json.JSONDecodeError:
        return {}
