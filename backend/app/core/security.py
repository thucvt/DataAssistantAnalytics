"""Mã hóa secret (API keys) và hash mật khẩu.

- API keys của LLM/OAuth lưu trong DB được mã hóa đối xứng bằng Fernet, khóa lấy
  từ SECRET_KEY (sinh ngẫu nhiên lúc cài đặt).
- Mật khẩu Super Admin được hash bằng bcrypt.
"""
from __future__ import annotations

import base64
import hashlib
import secrets

import bcrypt
from cryptography.fernet import Fernet, InvalidToken


def generate_secret_key() -> str:
    """Sinh SECRET_KEY ngẫu nhiên (url-safe) cho lần cài đặt."""
    return secrets.token_urlsafe(48)


def _fernet(secret_key: str) -> Fernet:
    """Suy ra khóa Fernet 32-byte hợp lệ từ SECRET_KEY tùy ý."""
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str, secret_key: str) -> str:
    if plaintext is None:
        plaintext = ""
    return _fernet(secret_key).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str, secret_key: str) -> str:
    try:
        return _fernet(secret_key).decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def _pw_bytes(password: str) -> bytes:
    # bcrypt chỉ xử lý tối đa 72 bytes; cắt an toàn để tránh lỗi với mật khẩu dài
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(password), hashed.encode("utf-8"))
    except ValueError:
        return False
