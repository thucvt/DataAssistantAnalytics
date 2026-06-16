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
