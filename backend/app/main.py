"""FastAPI app factory.

Tùy trạng thái cài đặt mà dựng app khác nhau:
- CHƯA cài: mount router Installer + serve giao diện Installer tĩnh ở `/`.
- ĐÃ cài : mount router Main App + healthcheck.

run.py đọc trạng thái lúc khởi động để chọn app phù hợp. Sau khi Installer chạy
xong, tiến trình tự thoát và Docker restart -> lần boot sau sẽ vào nhánh Main App.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import init_engine
from app.core.state import is_installed

STATIC_DIR = Path(__file__).parent / "static"
INSTALLER_DIR = STATIC_DIR / "installer"


def _add_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # On-Premise nội bộ; siết lại ở Phase 2 nếu cần
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_installer_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=f"{s.APP_NAME} — Installer", docs_url="/api/docs")
    _add_cors(app)

    from app.routers import installer

    app.include_router(installer.router)

    # Serve assets tĩnh của installer (css/js/ảnh nếu có)
    if INSTALLER_DIR.exists():
        app.mount(
            "/installer-assets",
            StaticFiles(directory=INSTALLER_DIR),
            name="installer-assets",
        )

    @app.get("/", include_in_schema=False)
    def installer_index() -> FileResponse:
        return FileResponse(INSTALLER_DIR / "index.html")

    return app


def create_main_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.APP_NAME, docs_url="/api/docs")
    _add_cors(app)

    # Kết nối DB thật của hệ thống
    init_engine()

    from app.routers import analytics, auth, llm, main_app, oauth

    app.include_router(main_app.router)
    app.include_router(auth.router)
    app.include_router(llm.router)
    app.include_router(oauth.router)
    app.include_router(analytics.router)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {"app": s.APP_NAME, "status": "running"}

    return app


def create_app() -> FastAPI:
    return create_main_app() if is_installed() else create_installer_app()
