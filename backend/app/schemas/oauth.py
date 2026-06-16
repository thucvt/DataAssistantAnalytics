from __future__ import annotations

from pydantic import BaseModel


class OAuthConfigItem(BaseModel):
    key: str
    value: str


class AuthUrlOut(BaseModel):
    authorization_url: str


class ConnectionOut(BaseModel):
    provider: str
    connected: bool
    expires_at: str | None = None
    meta: dict | None = None   # thông tin bổ sung (tên user, ad account...)


class PasteTokenIn(BaseModel):
    access_token: str
    extra: dict = {}           # ad_account_id, advertiser_id, shop_id...


class TokenVerifyOut(BaseModel):
    ok: bool
    name: str = ""             # tên user/account từ API
    expires_at: str | None = None
    long_lived: bool = False   # đã gia hạn lên long-lived chưa
