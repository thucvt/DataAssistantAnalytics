"""Entrypoint container.

Đọc trạng thái cài đặt rồi chạy uvicorn với app phù hợp (Installer hoặc Main App).
Khi Installer hoàn tất, tiến trình tự thoát; Docker `restart: unless-stopped` bật
lại container -> lần này boot vào Main App.
"""
from __future__ import annotations

import uvicorn

from app.core.config import get_settings
from app.core.state import is_installed


def main() -> None:
    settings = get_settings()
    mode = "MAIN APP" if is_installed() else "INSTALLER"
    print(f"[boot] {settings.APP_NAME} starting in {mode} mode on port {settings.APP_PORT}")

    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
