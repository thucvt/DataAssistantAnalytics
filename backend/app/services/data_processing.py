"""Xử lý & hợp nhất dữ liệu từ nhiều nguồn bằng Pandas, xuất JSON/Excel.

- merge_by_date: gộp chi phí Ads (Meta) và doanh thu (Shopee) theo ngày.
- to_chart_payload: cấu trúc JSON sẵn sàng vẽ biểu đồ (labels + datasets).
- export_excel: xuất file .xlsx (openpyxl) vào EXPORT_DIR, trả đường dẫn.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pandas as pd

EXPORT_DIR = Path("/tmp/exports")


def merge_by_date(meta_spend: list[dict], shopee_revenue: list[dict]) -> pd.DataFrame:
    """Gộp [{date, spend}] và [{date, revenue}] theo cột date (outer join).

    Trả DataFrame cột: date, spend, revenue, profit, roas (revenue/spend).
    """
    df_spend = pd.DataFrame(meta_spend or [], columns=["date", "spend"])
    df_rev = pd.DataFrame(shopee_revenue or [], columns=["date", "revenue"])

    df = pd.merge(df_spend, df_rev, on="date", how="outer")
    df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0.0)
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0.0)
    df = df.sort_values("date").reset_index(drop=True)

    df["profit"] = (df["revenue"] - df["spend"]).round(2)
    df["roas"] = df.apply(
        lambda r: round(r["revenue"] / r["spend"], 2) if r["spend"] else 0.0, axis=1
    )
    return df


def to_chart_payload(df: pd.DataFrame) -> dict:
    """Chuẩn hóa DataFrame thành JSON cho frontend vẽ chart."""
    return {
        "labels": df["date"].astype(str).tolist(),
        "datasets": [
            {"label": "Chi phí Ads (Meta)", "data": df["spend"].tolist()},
            {"label": "Doanh thu (Shopee)", "data": df["revenue"].tolist()},
            {"label": "Lợi nhuận", "data": df["profit"].tolist()},
        ],
        "summary": {
            "total_spend": round(float(df["spend"].sum()), 2),
            "total_revenue": round(float(df["revenue"].sum()), 2),
            "total_profit": round(float(df["profit"].sum()), 2),
            "avg_roas": round(float(df["roas"].replace(0, pd.NA).mean() or 0), 2),
        },
    }


def export_excel(df: pd.DataFrame, filename: str | None = None) -> Path:
    """Xuất DataFrame ra .xlsx trong EXPORT_DIR. Trả về đường dẫn file."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    name = filename or f"report_{uuid.uuid4().hex[:12]}.xlsx"
    if not name.endswith(".xlsx"):
        name += ".xlsx"
    path = EXPORT_DIR / name

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        out = df.rename(columns={
            "date": "Ngày", "spend": "Chi phí Ads", "revenue": "Doanh thu",
            "profit": "Lợi nhuận", "roas": "ROAS",
        })
        out.to_excel(writer, index=False, sheet_name="Báo cáo")
        ws = writer.sheets["Báo cáo"]
        for col in ws.columns:
            width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
            ws.column_dimensions[col[0].column_letter].width = width + 4
    return path
