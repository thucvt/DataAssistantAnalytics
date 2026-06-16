"""Router AI: cấu hình LLM (AI Settings), chat, và báo cáo chi phí token.

- AI Settings (chọn provider/model, thêm/xóa API key): yêu cầu Super Admin.
- Chat: mọi user đã đăng nhập.
- Usage: báo cáo chi phí cho Dashboard.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_superadmin
from app.core.database import get_db
from app.models import User
from app.schemas.llm import (
    AISettingsOut,
    ChatRequest,
    ChatResponse,
    SetAPIKey,
    UpdateAISettings,
)
from app.services import config_service, usage_service
from app.services.ai_manager import AIManager
from app.services.config_service import DEFAULT_MODELS, PROVIDER_KEY_NAME

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/settings", response_model=AISettingsOut)
def get_settings(db: Session = Depends(get_db), _: User = Depends(require_superadmin)):
    return config_service.list_provider_status(db)


@router.put("/settings", response_model=AISettingsOut)
def update_settings(
    payload: UpdateAISettings,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    model = payload.model or DEFAULT_MODELS[payload.provider]
    config_service.set_config(db, "LLM_PROVIDER", payload.provider,
                              description="Nhà cung cấp LLM mặc định")
    config_service.set_config(db, "LLM_DEFAULT_MODEL", model,
                              description="Model LLM mặc định")
    return config_service.list_provider_status(db)


@router.put("/keys", response_model=AISettingsOut)
def set_key(
    payload: SetAPIKey,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    config_service.set_api_key(db, payload.provider, payload.api_key)
    return config_service.list_provider_status(db)


@router.delete("/keys/{provider}", response_model=AISettingsOut)
def delete_key(
    provider: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    key_name = PROVIDER_KEY_NAME.get(provider)
    if not key_name:
        raise HTTPException(status_code=400, detail="Provider không hợp lệ.")
    config_service.delete_config(db, key_name)
    return config_service.list_provider_status(db)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        manager = AIManager(db, user_id=user.id)
        result = manager.chat([m.model_dump() for m in payload.messages])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lỗi gọi LLM: {exc}")
    return ChatResponse(**result.__dict__)


@router.get("/usage")
def usage(
    days: int = 30,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return usage_service.summary(db, days=days)
