"""Xác thực JWT + dependency kiểm tra quyền.

Token ký bằng SECRET_KEY (sinh lúc cài). Dependency `get_current_user` dùng cho
mọi route cần đăng nhập; `require_superadmin` cho các route quản trị.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models import User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 giờ

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không xác thực được người dùng.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise cred_exc

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise cred_exc
    return user


def require_superadmin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Yêu cầu quyền quản trị (Super Admin).")
    return user
