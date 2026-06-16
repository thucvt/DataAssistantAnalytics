from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LLMUsageLog(Base, TimestampMixin):
    """Log token mỗi lần gọi LLM — phục vụ dashboard chi phí AI (Phase 2).

    Bảng được tạo sẵn từ Phase 1 để schema ổn định; logic ghi log nằm ở
    callback của AIManager (Phase 2).
    """

    __tablename__ = "llm_usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    model_name: Mapped[str] = mapped_column(String(128))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
