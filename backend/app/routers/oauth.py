"""Router OAuth 2.0 cho các nguồn dữ liệu (Facebook Graph, Shopee Open Platform).

Luồng: client gọi `/authorize` (đã đăng nhập) -> nhận URL -> user đồng ý ->
provider redirect về `/callback?code=...&state=...` -> đổi token -> lưu DB.

`state` là một JWT ngắn hạn chứa user_id để callback (không có Authorization
header) vẫn biết token thuộc về ai.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, decode_token, get_current_user, require_superadmin
from app.core.database import get_db
from app.models import User
from app.schemas.oauth import AuthUrlOut, ConnectionOut, OAuthConfigItem
from app.services import config_service, oauth_service
from app.services.integrations import facebook
from app.services.integrations.shopee import ShopeeClient

router = APIRouter(prefix="/api/oauth", tags=["oauth"])

# Các config key được phép set qua endpoint config (tránh ghi đè key tùy ý)
ALLOWED_CONFIG_KEYS = {
    "FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET", "FACEBOOK_REDIRECT_URI",
    "SHOPEE_PARTNER_ID", "SHOPEE_PARTNER_KEY", "SHOPEE_REDIRECT_URI",
}
SECRET_CONFIG_KEYS = {"FACEBOOK_APP_SECRET", "SHOPEE_PARTNER_KEY"}


def _make_state(user_id: int, provider: str) -> str:
    return create_access_token(user_id, extra={"oauth_provider": provider, "scope": "oauth_state"})


def _read_state(state: str, provider: str) -> int:
    try:
        payload = decode_token(state)
        if payload.get("scope") != "oauth_state" or payload.get("oauth_provider") != provider:
            raise ValueError
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=400, detail="state không hợp lệ hoặc đã hết hạn.")


def _ok_page(provider: str) -> HTMLResponse:
    return HTMLResponse(
        f"<html><body style='font-family:sans-serif;background:#0a0a0b;color:#e8c766;"
        f"text-align:center;padding:60px'><h2>✓ Đã kết nối {provider} thành công</h2>"
        f"<p style='color:#9a9aa2'>Bạn có thể đóng cửa sổ này.</p></body></html>"
    )


# ---------- Cấu hình credentials (Super Admin) ----------
@router.put("/config")
def set_config(
    item: OAuthConfigItem,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    if item.key not in ALLOWED_CONFIG_KEYS:
        raise HTTPException(status_code=400, detail="Config key không được phép.")
    is_secret = item.key in SECRET_CONFIG_KEYS
    config_service.set_config(db, item.key, item.value, is_secret=is_secret)
    return {"ok": True}


@router.get("/connections", response_model=list[ConnectionOut])
def list_connections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    out = []
    for provider in ("facebook", "shopee"):
        conn = oauth_service.get_connection(db, user.id, provider)
        out.append(ConnectionOut(
            provider=provider,
            connected=bool(conn and conn.access_token),
            expires_at=conn.expires_at.isoformat() if conn and conn.expires_at else None,
        ))
    return out


# ---------- Facebook ----------
@router.get("/facebook/authorize", response_model=AuthUrlOut)
def fb_authorize(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    url = facebook.build_authorization_url(db, state=_make_state(user.id, "facebook"))
    return AuthUrlOut(authorization_url=url)


@router.get("/facebook/callback")
def fb_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    user_id = _read_state(state, "facebook")
    try:
        token_data = facebook.exchange_code_for_token(db, code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lỗi đổi token Facebook: {exc}")

    expires_at = None
    if token_data.get("expires_in"):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(token_data["expires_in"]))
    oauth_service.save_connection(
        db, user_id=user_id, provider="facebook",
        access_token=token_data.get("access_token", ""), expires_at=expires_at,
    )
    return _ok_page("Facebook")


# ---------- Shopee ----------
@router.get("/shopee/authorize", response_model=AuthUrlOut)
def shopee_authorize(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    client = ShopeeClient.from_db(db)
    # state (JWT chứa user_id) được nhúng vào redirect URI để callback xác định user
    url = client.build_authorization_url(state=_make_state(user.id, "shopee"))
    return AuthUrlOut(authorization_url=url)


@router.get("/shopee/callback")
def shopee_callback(
    code: str = Query(...),
    shop_id: int = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    user_id = _read_state(state, "shopee")
    client = ShopeeClient.from_db(db)
    try:
        token_data = client.get_access_token(code, shop_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lỗi đổi token Shopee: {exc}")

    expires_at = None
    if token_data.get("expire_in"):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(token_data["expire_in"]))
    oauth_service.save_connection(
        db, user_id=user_id, provider="shopee",
        access_token=token_data.get("access_token", ""),
        refresh_token=token_data.get("refresh_token", ""),
        expires_at=expires_at, extra={"shop_id": shop_id},
    )
    return _ok_page("Shopee")
