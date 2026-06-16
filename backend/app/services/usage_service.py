"""Tổng hợp dữ liệu token/chi phí cho Dashboard "Chi phí AI"."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import LLMUsageLog


def summary(db: Session, days: int = 30) -> dict:
    """Tổng quan + chuỗi theo ngày + phân bổ theo model trong N ngày gần nhất."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(LLMUsageLog).filter(LLMUsageLog.created_at >= since)

    totals = q.with_entities(
        func.coalesce(func.sum(LLMUsageLog.prompt_tokens), 0),
        func.coalesce(func.sum(LLMUsageLog.completion_tokens), 0),
        func.coalesce(func.sum(LLMUsageLog.total_tokens), 0),
        func.coalesce(func.sum(LLMUsageLog.estimated_cost), 0.0),
        func.count(LLMUsageLog.id),
    ).one()

    # Chuỗi theo ngày (cho biểu đồ đường/cột)
    day_expr = func.date(LLMUsageLog.created_at)
    by_day_rows = (
        q.with_entities(
            day_expr.label("day"),
            func.sum(LLMUsageLog.total_tokens),
            func.sum(LLMUsageLog.estimated_cost),
        )
        .group_by(day_expr)
        .order_by(day_expr)
        .all()
    )

    # Phân bổ theo model (cho biểu đồ tròn)
    by_model_rows = (
        q.with_entities(
            LLMUsageLog.model_name,
            func.sum(LLMUsageLog.total_tokens),
            func.sum(LLMUsageLog.estimated_cost),
            func.count(LLMUsageLog.id),
        )
        .group_by(LLMUsageLog.model_name)
        .all()
    )

    return {
        "range_days": days,
        "totals": {
            "prompt_tokens": int(totals[0]),
            "completion_tokens": int(totals[1]),
            "total_tokens": int(totals[2]),
            "estimated_cost": round(float(totals[3]), 6),
            "requests": int(totals[4]),
        },
        "by_day": [
            {"date": str(r[0]), "total_tokens": int(r[1] or 0), "cost": round(float(r[2] or 0), 6)}
            for r in by_day_rows
        ],
        "by_model": [
            {
                "model": r[0],
                "total_tokens": int(r[1] or 0),
                "cost": round(float(r[2] or 0), 6),
                "requests": int(r[3]),
            }
            for r in by_model_rows
        ],
    }
