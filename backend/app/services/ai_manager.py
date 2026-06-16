"""AIManager — lớp trừu tượng hóa việc gọi LLM qua LiteLLM.

- Lấy provider/model/API key (đã giải mã) từ Database.
- Chuẩn hóa mọi nhà cung cấp (OpenAI/Claude/Gemini) về một interface chung.
- Sau mỗi lần gọi, đếm token và ghi vào llm_usage_logs (callback token tracking).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import LLMUsageLog
from app.services import config_service
from app.services.pricing import estimate_cost


@dataclass
class ChatResult:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float


def log_usage(
    db: Session,
    *,
    user_id: int | None,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> LLMUsageLog:
    """Ghi 1 dòng log token + chi phí. Tách riêng để test và tái dùng làm callback."""
    total = prompt_tokens + completion_tokens
    cost = estimate_cost(model, prompt_tokens, completion_tokens)
    row = LLMUsageLog(
        user_id=user_id,
        model_name=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        estimated_cost=cost,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _litellm_model_name(provider: str, model: str) -> str:
    """LiteLLM cần prefix provider cho một số hãng (vd gemini)."""
    if provider == "gemini" and not model.startswith("gemini/"):
        return f"gemini/{model}"
    return model


class AIManager:
    def __init__(self, db: Session, user_id: int | None = None):
        self.db = db
        self.user_id = user_id
        self.provider = config_service.get_active_provider(db)
        self.model = config_service.get_active_model(db)
        self.api_key = config_service.get_api_key(db, self.provider)
        if not self.api_key:
            raise ValueError(
                f"Chưa cấu hình API key cho provider '{self.provider}'. "
                "Vào AI Settings để thêm."
            )

    def chat(self, messages: list[dict], **kwargs) -> ChatResult:
        """Gọi LLM với danh sách messages [{role, content}] và ghi log token."""
        import litellm

        model_name = _litellm_model_name(self.provider, self.model)
        resp = litellm.completion(
            model=model_name,
            messages=messages,
            api_key=self.api_key,
            **kwargs,
        )

        choice = resp.choices[0]
        content = choice.message.content or ""
        usage = getattr(resp, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0

        log_usage(
            self.db,
            user_id=self.user_id,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        return ChatResult(
            content=content,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost=estimate_cost(self.model, prompt_tokens, completion_tokens),
        )

    def get_langchain_llm(self):
        """Trả về ChatLiteLLM để dùng với LangChain Agent (Phase 4)."""
        from langchain_community.chat_models import ChatLiteLLM

        return ChatLiteLLM(
            model=_litellm_model_name(self.provider, self.model),
            api_key=self.api_key,
            temperature=0,
        )
