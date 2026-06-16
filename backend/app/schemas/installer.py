from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class LicensePayload(BaseModel):
    license_key: str = Field(min_length=4)


class DatabasePayload(BaseModel):
    """Cấu hình DB. `engine='sqlite'` => dùng SQLite fallback, bỏ qua các field khác."""

    engine: Literal["sqlite", "postgresql", "mysql"] = "sqlite"
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    def to_url(self, sqlite_path: str) -> str:
        if self.engine == "sqlite":
            return f"sqlite:///{sqlite_path}"
        if self.engine == "postgresql":
            return (
                f"postgresql+psycopg://{self.username}:{self.password}"
                f"@{self.host}:{self.port or 5432}/{self.database}"
            )
        # mysql
        return (
            f"mysql+pymysql://{self.username}:{self.password}"
            f"@{self.host}:{self.port or 3306}/{self.database}"
        )


class AdminPayload(BaseModel):
    email: EmailStr
    full_name: str = ""
    password: str = Field(min_length=8)


class LLMPayload(BaseModel):
    provider: Literal["openai", "anthropic", "gemini"]
    api_key: str = Field(min_length=8)
    default_model: str = ""


class FinalizePayload(BaseModel):
    license: LicensePayload
    database: DatabasePayload
    admin: AdminPayload
    llm: LLMPayload


class StatusResponse(BaseModel):
    installed: bool
    app_name: str


class SimpleResult(BaseModel):
    ok: bool
    message: str = ""
