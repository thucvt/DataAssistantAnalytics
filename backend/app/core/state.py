"""Xác định trạng thái cài đặt của hệ thống.

`is_installed()` đọc settings (đã load từ .env). Khi chưa cài, app chỉ phục vụ
Web Installer; sau khi cài và restart, app phục vụ Main App.
"""
from __future__ import annotations

from app.core.config import get_settings


def is_installed() -> bool:
    s = get_settings()
    return bool(s.INSTALLED and s.SECRET_KEY and s.DATABASE_URL)
