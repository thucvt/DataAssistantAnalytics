"""API endpoints cho Web Installer.

Chỉ được mount khi hệ thống CHƯA cài đặt. Sau khi `/finalize` thành công, app
sẽ tự thoát tiến trình để Docker restart và boot Main App.
"""
from __future__ import annotations

import asyncio
import os
import signal

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.state import is_installed
from app.schemas.installer import (
    DatabasePayload,
    FinalizePayload,
    LicensePayload,
    SimpleResult,
    StatusResponse,
)
from app.services import installer_service

router = APIRouter(prefix="/api/installer", tags=["installer"])


def _guard_not_installed() -> None:
    if is_installed():
        raise HTTPException(status_code=409, detail="Hệ thống đã được cài đặt.")


@router.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    s = get_settings()
    return StatusResponse(installed=is_installed(), app_name=s.APP_NAME)


@router.post("/license", response_model=SimpleResult)
def check_license(payload: LicensePayload) -> SimpleResult:
    _guard_not_installed()
    ok, msg = installer_service.validate_license(payload.license_key)
    return SimpleResult(ok=ok, message=msg)


@router.post("/test-database", response_model=SimpleResult)
def test_database(payload: DatabasePayload) -> SimpleResult:
    _guard_not_installed()
    url = payload.to_url(installer_service.SQLITE_PATH)
    ok, msg = installer_service.test_database_connection(url)
    return SimpleResult(ok=ok, message=msg)


@router.post("/finalize", response_model=SimpleResult)
async def finalize(payload: FinalizePayload) -> SimpleResult:
    _guard_not_installed()
    ok, msg = installer_service.finalize_installation(payload)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    # Cài xong: lên lịch thoát tiến trình SAU khi trả response, để Docker
    # (restart: unless-stopped) bật lại container và boot Main App.
    asyncio.create_task(_shutdown_after_response())
    return SimpleResult(ok=True, message=msg)


async def _shutdown_after_response() -> None:
    # Chờ một nhịp ngắn để response kịp gửi về client
    await asyncio.sleep(1.5)
    os.kill(os.getpid(), signal.SIGTERM)
