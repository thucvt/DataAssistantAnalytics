"""LangChain Agent với tools: Meta Ads, Shopee, TikTok Ads, Google Ads, Báo cáo tổng hợp."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.ai_manager import AIManager
from app.services.data_processing import merge_by_date, to_chart_payload
from app.services import data_sources


def _default_dates() -> tuple[str, str]:
    until = datetime.now(timezone.utc).date()
    since = until - timedelta(days=29)
    return str(since), str(until)


# ── Input schemas ──────────────────────────────────────────────────────────────

class DateRange(BaseModel):
    since: str = Field(default="", description="Ngày bắt đầu YYYY-MM-DD (bỏ trống = 30 ngày qua)")
    until: str = Field(default="", description="Ngày kết thúc YYYY-MM-DD (bỏ trống = hôm nay)")


# ── Tool builder ───────────────────────────────────────────────────────────────

def build_tools(db: Session, user_id: int, ai: AIManager) -> list:
    def _dates(since: str, until: str) -> tuple[str, str]:
        s, u = _default_dates()
        return since or s, until or u

    def meta_ads_cost(since: str = "", until: str = "") -> str:
        s, u = _dates(since, until)
        try:
            data = data_sources.get_meta_ads_cost(db, user_id, s, u)
        except ValueError as e:
            return str(e)
        if not data:
            return f"Không có dữ liệu chi phí Meta Ads từ {s} đến {u}."
        total = sum(r["spend"] for r in data)
        rows = "\n".join(f"  {r['date']}: ${r['spend']:,.2f}" for r in data[:10])
        suffix = f"\n  ... (+{len(data)-10} ngày nữa)" if len(data) > 10 else ""
        return f"Chi phí Meta Ads từ {s} đến {u} (tổng: ${total:,.2f} USD):\n{rows}{suffix}"

    def shopee_revenue(since: str = "", until: str = "") -> str:
        s, u = _dates(since, until)
        try:
            data = data_sources.get_shopee_revenue(db, user_id, s, u)
        except ValueError as e:
            return str(e)
        if not data:
            return f"Không có dữ liệu doanh thu Shopee từ {s} đến {u}."
        total = sum(r["revenue"] for r in data)
        rows = "\n".join(f"  {r['date']}: {r['revenue']:,.0f} VND" for r in data[:10])
        suffix = f"\n  ... (+{len(data)-10} ngày nữa)" if len(data) > 10 else ""
        return f"Doanh thu Shopee từ {s} đến {u} (tổng: {total:,.0f} VND):\n{rows}{suffix}"

    def tiktok_ads_cost(since: str = "", until: str = "") -> str:
        s, u = _dates(since, until)
        try:
            data = data_sources.get_tiktok_ads_cost(db, user_id, s, u)
        except ValueError as e:
            return str(e)
        if not data:
            return f"Không có dữ liệu chi phí TikTok Ads từ {s} đến {u}."
        total = sum(r["spend"] for r in data)
        rows = "\n".join(f"  {r['date']}: ${r['spend']:,.2f}" for r in data[:10])
        suffix = f"\n  ... (+{len(data)-10} ngày nữa)" if len(data) > 10 else ""
        return f"Chi phí TikTok Ads từ {s} đến {u} (tổng: ${total:,.2f} USD):\n{rows}{suffix}"

    def google_ads_cost(since: str = "", until: str = "") -> str:
        s, u = _dates(since, until)
        try:
            data = data_sources.get_google_ads_cost(db, user_id, s, u)
        except ValueError as e:
            return str(e)
        if not data:
            return f"Không có dữ liệu chi phí Google Ads từ {s} đến {u}."
        total = sum(r["spend"] for r in data)
        rows = "\n".join(f"  {r['date']}: ${r['spend']:,.2f}" for r in data[:10])
        suffix = f"\n  ... (+{len(data)-10} ngày nữa)" if len(data) > 10 else ""
        return f"Chi phí Google Ads từ {s} đến {u} (tổng: ${total:,.2f} USD):\n{rows}{suffix}"

    def merged_report(since: str = "", until: str = "") -> str:
        s, u = _dates(since, until)
        # Gom tất cả nguồn ads (bỏ qua nguồn chưa kết nối)
        all_spend: list[dict] = []
        for getter, label in [
            (data_sources.get_meta_ads_cost, "Meta"),
            (data_sources.get_tiktok_ads_cost, "TikTok"),
            (data_sources.get_google_ads_cost, "Google"),
        ]:
            try:
                rows = getter(db, user_id, s, u)
                all_spend.extend(rows)
            except ValueError:
                pass

        # Merge spend by date
        from collections import defaultdict
        spend_by_date: dict[str, float] = defaultdict(float)
        for r in all_spend:
            spend_by_date[r["date"]] += r["spend"]
        ads_merged = [{"date": d, "spend": v} for d, v in sorted(spend_by_date.items())]

        try:
            shopee = data_sources.get_shopee_revenue(db, user_id, s, u)
        except ValueError:
            shopee = []

        df = merge_by_date(ads_merged, shopee)
        payload = to_chart_payload(df)
        sm = payload["summary"]
        return (
            f"Báo cáo tổng hợp {s} → {u} (gộp Meta+TikTok+Google Ads):\n"
            f"  Tổng chi phí Ads: ${sm['total_spend']:,.2f}\n"
            f"  Doanh thu (Shopee): {sm['total_revenue']:,.0f}\n"
            f"  Lợi nhuận: {sm['total_profit']:,.0f}\n"
            f"  ROAS trung bình: {sm['avg_roas']:.2f}x"
        )

    return [
        StructuredTool(name="meta_ads_cost",   description="Lấy chi phí quảng cáo Meta Ads (Facebook/Instagram) theo ngày.", func=meta_ads_cost,   args_schema=DateRange),
        StructuredTool(name="shopee_revenue",  description="Lấy doanh thu bán hàng Shopee theo ngày.",                       func=shopee_revenue,  args_schema=DateRange),
        StructuredTool(name="tiktok_ads_cost", description="Lấy chi phí quảng cáo TikTok Ads theo ngày.",                   func=tiktok_ads_cost, args_schema=DateRange),
        StructuredTool(name="google_ads_cost", description="Lấy chi phí quảng cáo Google Ads Manager theo ngày.",           func=google_ads_cost, args_schema=DateRange),
        StructuredTool(name="merged_report",   description="Báo cáo tổng hợp gộp tất cả nguồn Ads + Shopee (lợi nhuận, ROAS).", func=merged_report, args_schema=DateRange),
    ]


SYSTEM_PROMPT = """Bạn là trợ lý phân tích kinh doanh thông minh, chuyên về dữ liệu bán hàng
và quảng cáo đa kênh. Bạn có thể truy cập dữ liệu từ Meta Ads, Shopee, TikTok Ads
và Google Ads Manager thông qua các công cụ.

Hãy phân tích và đưa ra nhận xét có giá trị, không chỉ liệt kê số liệu. Trả lời bằng
tiếng Việt. Khi cần số liệu, gọi tool phù hợp trước khi trả lời. Với câu hỏi về tổng
chi phí nhiều kênh, dùng merged_report."""


def create_agent_executor(db: Session, user_id: int, ai: AIManager) -> AgentExecutor:
    tools = build_tools(db, user_id, ai)
    llm = ai.get_langchain_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=6)


def run_agent(db: Session, user_id: int, question: str) -> dict:
    """Chạy agent và trả {answer, steps}."""
    ai = AIManager(db, user_id=user_id)
    executor = create_agent_executor(db, user_id, ai)
    result = executor.invoke({"input": question})
    return {
        "answer": result.get("output", ""),
        "steps": len(result.get("intermediate_steps", [])),
    }
