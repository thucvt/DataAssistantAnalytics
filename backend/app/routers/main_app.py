"""Router của Main App (sau khi đã cài đặt).

Phase 1 chỉ có healthcheck + thông tin cơ bản. Phase 2+ sẽ thêm auth, llm,
oauth, analytics... vào đây.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["main"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/info")
def info() -> dict:
    s = get_settings()
    return {
        "app_name": s.APP_NAME,
        "installed": True,
        "phase": 1,
    }
