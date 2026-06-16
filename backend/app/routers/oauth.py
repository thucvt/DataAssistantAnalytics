"""Router OAuth 2.0 — Facebook, Shopee, TikTok, Google Ads."""
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
from app.services.integrations import tiktok as tiktok_int
from app.services.integrations import google_ads as google_int
from app.services.integrations.shopee import ShopeeClient

router = APIRouter(prefix="/api/oauth", tags=["oauth"])

ALLOWED_CONFIG_KEYS = {
    # Facebook / Meta
    "FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET", "FACEBOOK_REDIRECT_URI", "FACEBOOK_AD_ACCOUNT_ID",
    # Shopee
    "SHOPEE_PARTNER_ID", "SHOPEE_PARTNER_KEY", "SHOPEE_REDIRECT_URI",
    # TikTok
    "TIKTOK_APP_ID", "TIKTOK_APP_SECRET", "TIKTOK_REDIRECT_URI", "TIKTOK_ADVERTISER_ID",
    # Google Ads
    "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI",
    "GOOGLE_ADS_CUSTOMER_ID", "GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
}

SECRET_CONFIG_KEYS = {
    "FACEBOOK_APP_SECRET", "SHOPEE_PARTNER_KEY",
    "TIKTOK_APP_SECRET", "GOOGLE_CLIENT_SECRET", "GOOGLE_ADS_DEVELOPER_TOKEN",
}

ALL_PROVIDERS = ("facebook", "shopee", "tiktok", "google")


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


# ── Cấu hình credentials ────────────────────────────────────────────────────
@router.put("/config")
def set_config(item: OAuthConfigItem, db: Session = Depends(get_db), _: User = Depends(require_superadmin)):
    if item.key not in ALLOWED_CONFIG_KEYS:
        raise HTTPException(status_code=400, detail="Config key không được phép.")
    config_service.set_config(db, item.key, item.value, is_secret=item.key in SECRET_CONFIG_KEYS)
    return {"ok": True}


@router.get("/connections", response_model=list[ConnectionOut])
def list_connections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [
        ConnectionOut(
            provider=p,
            connected=bool((c := oauth_service.get_connection(db, user.id, p)) and c.access_token),
            expires_at=c.expires_at.isoformat() if (c := oauth_service.get_connection(db, user.id, p)) and c.expires_at else None,
        )
        for p in ALL_PROVIDERS
    ]


# ── Facebook ────────────────────────────────────────────────────────────────
@router.get("/facebook/authorize", response_model=AuthUrlOut)
def fb_authorize(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return AuthUrlOut(authorization_url=facebook.build_authorization_url(db, state=_make_state(user.id, "facebook")))


@router.get("/facebook/callback")
def fb_callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    user_id = _read_state(state, "facebook")
    try:
        data = facebook.exchange_code_for_token(db, code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Facebook: {exc}")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"])) if data.get("expires_in") else None
    oauth_service.save_connection(db, user_id=user_id, provider="facebook", access_token=data.get("access_token", ""), expires_at=expires_at)
    return _ok_page("Facebook / Meta Ads")


# ── Shopee ──────────────────────────────────────────────────────────────────
@router.get("/shopee/authorize", response_model=AuthUrlOut)
def shopee_authorize(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return AuthUrlOut(authorization_url=ShopeeClient.from_db(db).build_authorization_url(state=_make_state(user.id, "shopee")))


@router.get("/shopee/callback")
def shopee_callback(code: str = Query(...), shop_id: int = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    user_id = _read_state(state, "shopee")
    try:
        data = ShopeeClient.from_db(db).get_access_token(code, shop_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Shopee: {exc}")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(data["expire_in"])) if data.get("expire_in") else None
    oauth_service.save_connection(db, user_id=user_id, provider="shopee", access_token=data.get("access_token", ""), refresh_token=data.get("refresh_token", ""), expires_at=expires_at, extra={"shop_id": shop_id})
    return _ok_page("Shopee")


# ── TikTok ──────────────────────────────────────────────────────────────────
@router.get("/tiktok/authorize", response_model=AuthUrlOut)
def tiktok_authorize(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return AuthUrlOut(authorization_url=tiktok_int.build_authorization_url(db, state=_make_state(user.id, "tiktok")))


@router.get("/tiktok/callback")
def tiktok_callback(auth_code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    user_id = _read_state(state, "tiktok")
    try:
        data = tiktok_int.exchange_code_for_token(db, auth_code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi TikTok: {exc}")
    # Lấy advertiser_id đầu tiên (nếu nhiều, user chọn sau trong settings)
    advertiser_ids = data.get("advertiser_ids", [])
    extra = {"advertiser_id": advertiser_ids[0] if advertiser_ids else ""}
    oauth_service.save_connection(db, user_id=user_id, provider="tiktok", access_token=data.get("access_token", ""), extra=extra)
    return _ok_page("TikTok Ads")


# ── Google Ads ───────────────────────────────────────────────────────────────
@router.get("/google/authorize", response_model=AuthUrlOut)
def google_authorize(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return AuthUrlOut(authorization_url=google_int.build_authorization_url(db, state=_make_state(user.id, "google")))


@router.get("/google/callback")
def google_callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    user_id = _read_state(state, "google")
    try:
        data = google_int.exchange_code_for_token(db, code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Google: {exc}")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"])) if data.get("expires_in") else None
    oauth_service.save_connection(db, user_id=user_id, provider="google", access_token=data.get("access_token", ""), refresh_token=data.get("refresh_token", ""), expires_at=expires_at)
    return _ok_page("Google Ads Manager")
