"""Bảng giá token (USD trên 1 token) để ước tính chi phí AI.

Giá tham khảo, có thể chỉnh trong Admin Panel sau. Đơn vị: USD / 1 token
(= giá-per-1M / 1_000_000). Dùng cho cột estimated_cost trong llm_usage_logs.
"""
from __future__ import annotations

# (prompt_per_1m, completion_per_1m) theo USD
_PRICE_PER_1M: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    # Anthropic
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    # Google
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
}

_DEFAULT = (1.0, 3.0)  # fallback cho model lạ


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p_in, p_out = _PRICE_PER_1M.get(model, _DEFAULT)
    cost = (prompt_tokens / 1_000_000) * p_in + (completion_tokens / 1_000_000) * p_out
    return round(cost, 6)
