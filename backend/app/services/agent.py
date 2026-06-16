"""LangChain Agent với 2 Tools: Meta Ads cost + Shopee revenue.

Agent tự quyết định gọi tool nào dựa trên câu hỏi user, sau đó tổng hợp câu
trả lời bằng LLM. Token được log qua callback gọi ai_manager.log_usage.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.ai_manager import AIManager, log_usage
from app.services.data_processing import export_excel, merge_by_date, to_chart_payload
from app.services import data_sources


def _default_dates() -> tuple[str, str]:
    """30 ngày gần nhất."""
    until = datetime.now(timezone.utc).date()
    since = until - timedelta(days=29)
    return str(since), str(until)


# ── Schema đầu vào cho tools ──────────────────────────────────────────────────

class AdsInput(BaseModel):
    since: str = Field(default="", description="Ngày bắt đầu YYYY-MM-DD (bỏ trống = 30 ngày qua)")
    until: str = Field(default="", description="Ngày kết thúc YYYY-MM-DD (bỏ trống = hôm nay)")


class ShopeeInput(BaseModel):
    since: str = Field(default="", description="Ngày bắt đầu YYYY-MM-DD (bỏ trống = 30 ngày qua)")
    until: str = Field(default="", description="Ngày kết thúc YYYY-MM-DD (bỏ trống = hôm nay)")


class MergeInput(BaseModel):
    since: str = Field(default="", description="Ngày bắt đầu YYYY-MM-DD")
    until: str = Field(default="", description="Ngày kết thúc YYYY-MM-DD")


# ── Tạo tool list với context đã bind ─────────────────────────────────────────

def build_tools(db: Session, user_id: int, ai: AIManager) -> list:
    """Trả list LangChain tools đã bind db/user_id."""

    def meta_ads_cost(since: str = "", until: str = "") -> str:
        s, u = since or _default_dates()[0], until or _default_dates()[1]
        data = data_sources.get_meta_ads_cost(db, user_id, s, u)
        if not data:
            return f"Không có dữ liệu chi phí Ads Meta từ {s} đến {u}."
        total = sum(r["spend"] for r in data)
        rows = "\n".join(f"  {r['date']}: ${r['spend']:,.2f}" for r in data[:10])
        suffix = f"\n  ... (+{len(data)-10} ngày nữa)" if len(data) > 10 else ""
        return f"Chi phí Ads Meta từ {s} đến {u} (tổng: ${total:,.2f} USD):\n{rows}{suffix}"

    def shopee_revenue(since: str = "", until: str = "") -> str:
        s, u = since or _default_dates()[0], until or _default_dates()[1]
        data = data_sources.get_shopee_revenue(db, user_id, s, u)
        if not data:
            return f"Không có dữ liệu doanh thu Shopee từ {s} đến {u}."
        total = sum(r["revenue"] for r in data)
        rows = "\n".join(f"  {r['date']}: {r['revenue']:,.0f} VND" for r in data[:10])
        suffix = f"\n  ... (+{len(data)-10} ngày nữa)" if len(data) > 10 else ""
        return f"Doanh thu Shopee từ {s} đến {u} (tổng: {total:,.0f} VND):\n{rows}{suffix}"

    def merged_report(since: str = "", until: str = "") -> str:
        s, u = since or _default_dates()[0], until or _default_dates()[1]
        meta = data_sources.get_meta_ads_cost(db, user_id, s, u)
        shopee = data_sources.get_shopee_revenue(db, user_id, s, u)
        df = merge_by_date(meta, shopee)
        payload = to_chart_payload(df)
        sm = payload["summary"]
        return (
            f"Báo cáo tổng hợp {s} → {u}:\n"
            f"  Chi phí Ads (Meta): ${sm['total_spend']:,.2f}\n"
            f"  Doanh thu (Shopee): {sm['total_revenue']:,.0f}\n"
            f"  Lợi nhuận: {sm['total_profit']:,.0f}\n"
            f"  ROAS trung bình: {sm['avg_roas']:.2f}x"
        )

    return [
        StructuredTool(
            name="meta_ads_cost",
            description="Lấy chi phí quảng cáo Meta Ads (Facebook) theo từng ngày.",
            func=meta_ads_cost,
            args_schema=AdsInput,
        ),
        StructuredTool(
            name="shopee_revenue",
            description="Lấy doanh thu bán hàng Shopee theo từng ngày.",
            func=shopee_revenue,
            args_schema=ShopeeInput,
        ),
        StructuredTool(
            name="merged_report",
            description="Lấy báo cáo tổng hợp (chi phí Ads + doanh thu Shopee + lợi nhuận + ROAS).",
            func=merged_report,
            args_schema=MergeInput,
        ),
    ]


SYSTEM_PROMPT = """Bạn là trợ lý phân tích kinh doanh thông minh chuyên về dữ liệu bán hàng
và quảng cáo. Bạn có quyền truy cập dữ liệu Meta Ads và Shopee thông qua các công cụ.

Hãy phân tích và đưa ra nhận xét có giá trị, không chỉ liệt kê số liệu. Trả lời bằng
tiếng Việt. Khi cần số liệu, hãy gọi tool phù hợp trước khi trả lời."""


def create_agent_executor(db: Session, user_id: int, ai: AIManager) -> AgentExecutor:
    tools = build_tools(db, user_id, ai)
    llm = ai.get_langchain_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=5)


def run_agent(db: Session, user_id: int, question: str) -> dict:
    """Chạy agent và ghi log token. Trả {answer, steps}."""
    ai = AIManager(db, user_id=user_id)
    executor = create_agent_executor(db, user_id, ai)
    result = executor.invoke({"input": question})
    return {
        "answer": result.get("output", ""),
        "steps": len(result.get("intermediate_steps", [])),
    }
