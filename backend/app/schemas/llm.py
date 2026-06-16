from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AISettingsOut(BaseModel):
    active_provider: str
    active_model: str
    keys_configured: dict[str, bool]


class UpdateAISettings(BaseModel):
    provider: Literal["openai", "anthropic", "gemini"]
    model: str = ""


class SetAPIKey(BaseModel):
    provider: Literal["openai", "anthropic", "gemini"]
    api_key: str = Field(min_length=8)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
