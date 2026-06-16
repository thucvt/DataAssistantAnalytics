"""Router OAuth 2.0 — Facebook, Shopee, TikTok, Google Ads.

App credentials (App ID / Secret / Redirect URI) đọc từ Settings (env vars).
Người dùng chỉ cần bấm nút Kết nối — không cần nhập credentials trên UI.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, decode_token, get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.oauth import AuthUrlOut, ConnectionOut, PasteTokenIn, TokenVerifyOut
from app.services import oauth_service
from app.services.integrations import facebook
from app.services.integrations import tiktok as tiktok_int
from app.services.integrations import google_ads as google_int
from app.services.integrations.shopee import ShopeeClient

router = APIRouter(prefix="/api/oauth", tags=["oauth"])

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


# ── Danh sách kết nối ────────────────────────────────────────────────────────
@router.get("/connections", response_model=list[ConnectionOut])
def list_connections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = []
    for p in ALL_PROVIDERS:
        c = oauth_service.get_connection(db, user.id, p)
        result.append(ConnectionOut(
            provider=p,
            connected=bool(c and c.access_token),
            expires_at=c.expires_at.isoformat() if c and c.expires_at else None,
        ))
    return result


# ── Facebook paste token ─────────────────────────────────────────────────────
@router.post("/facebook/token", response_model=TokenVerifyOut)
def fb_paste_token(
    body: PasteTokenIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """User dán Access Token từ Graph API Explorer. Tự động gia hạn nếu có App credentials."""
    try:
        info = facebook.verify_token(body.access_token)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Token không hợp lệ: {exc}")

    token, extended = facebook.try_extend_token(body.access_token)

    # Lấy thời hạn sau khi gia hạn
    expires_at_str = info.get("expires_at")
    if extended:
        try:
            new_info = facebook.verify_token(token)
            expires_at_str = new_info.get("expires_at")
        except Exception:
            pass

    expires_at_dt = None
    if expires_at_str:
        from datetime import datetime, timezone
        try:
            expires_at_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        except Exception:
            pass

    # Lưu vào DB — extra chứa ad_account_id nếu user nhập
    oauth_service.save_connection(
        db, user_id=user.id, provider="facebook",
        access_token=token, expires_at=expires_at_dt,
        extra=body.extra or {},
    )
    return TokenVerifyOut(
        ok=True,
        name=info.get("name", ""),
        expires_at=expires_at_str,
        long_lived=extended,
    )


# ── Facebook / Meta Ads OAuth (tuỳ chọn, cần App Review) ────────────────────
@router.get("/facebook/authorize", response_model=AuthUrlOut)
def fb_authorize(user: User = Depends(get_current_user)):
    try:
        return AuthUrlOut(authorization_url=facebook.build_authorization_url(state=_make_state(user.id, "facebook")))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/facebook/callback")
def fb_callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    user_id = _read_state(state, "facebook")
    try:
        data = facebook.exchange_code_for_token(code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Facebook: {exc}")
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"]))
        if data.get("expires_in") else None
    )
    oauth_service.save_connection(
        db, user_id=user_id, provider="facebook",
        access_token=data.get("access_token", ""), expires_at=expires_at,
    )
    return _ok_page("Facebook / Meta Ads")


# ── Shopee ────────────────────────────────────────────────────────────────────
@router.get("/shopee/authorize", response_model=AuthUrlOut)
def shopee_authorize(user: User = Depends(get_current_user)):
    try:
        url = ShopeeClient.from_settings().build_authorization_url(state=_make_state(user.id, "shopee"))
        return AuthUrlOut(authorization_url=url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/shopee/callback")
def shopee_callback(
    code: str = Query(...), shop_id: int = Query(...), state: str = Query(...),
    db: Session = Depends(get_db),
):
    user_id = _read_state(state, "shopee")
    try:
        data = ShopeeClient.from_settings().get_access_token(code, shop_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Shopee: {exc}")
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=int(data["expire_in"]))
        if data.get("expire_in") else None
    )
    oauth_service.save_connection(
        db, user_id=user_id, provider="shopee",
        access_token=data.get("access_token", ""),
        refresh_token=data.get("refresh_token", ""),
        expires_at=expires_at, extra={"shop_id": shop_id},
    )
    return _ok_page("Shopee")


# ── TikTok Ads ────────────────────────────────────────────────────────────────
@router.get("/tiktok/authorize", response_model=AuthUrlOut)
def tiktok_authorize(user: User = Depends(get_current_user)):
    try:
        return AuthUrlOut(authorization_url=tiktok_int.build_authorization_url(state=_make_state(user.id, "tiktok")))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tiktok/callback")
def tiktok_callback(auth_code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    user_id = _read_state(state, "tiktok")
    try:
        data = tiktok_int.exchange_code_for_token(auth_code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi TikTok: {exc}")
    advertiser_ids = data.get("advertiser_ids", [])
    oauth_service.save_connection(
        db, user_id=user_id, provider="tiktok",
        access_token=data.get("access_token", ""),
        extra={"advertiser_id": advertiser_ids[0] if advertiser_ids else ""},
    )
    return _ok_page("TikTok Ads")


# ── Google Ads Manager ────────────────────────────────────────────────────────
@router.get("/google/authorize", response_model=AuthUrlOut)
def google_authorize(user: User = Depends(get_current_user)):
    try:
        return AuthUrlOut(authorization_url=google_int.build_authorization_url(state=_make_state(user.id, "google")))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/google/callback")
def google_callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    user_id = _read_state(state, "google")
    try:
        data = google_int.exchange_code_for_token(code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Google: {exc}")
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"]))
        if data.get("expires_in") else None
    )
    oauth_service.save_connection(
        db, user_id=user_id, provider="google",
        access_token=data.get("access_token", ""),
        refresh_token=data.get("refresh_token", ""),
        expires_at=expires_at,
    )
    return _ok_page("Google Ads Manager")
