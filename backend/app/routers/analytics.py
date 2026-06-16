"""Router Analytics: báo cáo hợp nhất, Agent AI, xuất Excel.

Toàn bộ endpoint yêu cầu đăng nhập. Dữ liệu truy xuất theo user_id (mỗi user
có kết nối OAuth riêng của họ).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.analytics import (
    AgentQuery,
    AgentResponse,
    DownloadResponse,
    ReportPayload,
)
from app.services import data_sources
from app.services.data_processing import export_excel, merge_by_date, to_chart_payload

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/report/chart")
def report_chart(
    payload: ReportPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Trả cấu trúc JSON sẵn sàng cho frontend vẽ biểu đồ."""
    try:
        meta = data_sources.get_meta_ads_cost(db, user.id, payload.since, payload.until)
        shopee = data_sources.get_shopee_revenue(db, user.id, payload.since, payload.until)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lỗi lấy dữ liệu: {exc}")

    df = merge_by_date(meta, shopee)
    return to_chart_payload(df)


@router.post("/report/export", response_model=DownloadResponse)
def report_export(
    payload: ReportPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DownloadResponse:
    """Xuất báo cáo ra file Excel, trả link tải."""
    try:
        meta = data_sources.get_meta_ads_cost(db, user.id, payload.since, payload.until)
        shopee = data_sources.get_shopee_revenue(db, user.id, payload.since, payload.until)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lỗi lấy dữ liệu: {exc}")

    df = merge_by_date(meta, shopee)
    filename = f"report_{payload.since}_{payload.until}.xlsx"
    export_excel(df, filename)
    return DownloadResponse(
        filename=filename,
        download_url=f"/api/analytics/download/{filename}",
    )


@router.get("/download/{filename}")
def download_file(filename: str, user: User = Depends(get_current_user)) -> FileResponse:
    """Serve file Excel đã xuất."""
    from app.services.data_processing import EXPORT_DIR
    import re

    # Chặn path traversal: chỉ chấp nhận tên file đơn giản, không có / \ hay ..
    if "/" in filename or "\\" in filename or ".." in filename or not re.match(r"^[\w\-]+\.xlsx$", filename):
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ.")
    path = EXPORT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại hoặc đã bị xóa.")
    return FileResponse(
        path=str(path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/ask", response_model=AgentResponse)
def ask_agent(
    payload: AgentQuery,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentResponse:
    """Gửi câu hỏi tự nhiên cho AI Agent, agent tự gọi tools cần thiết."""
    from app.services.agent import run_agent

    try:
        result = run_agent(db, user.id, payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lỗi Agent: {exc}")

    return AgentResponse(**result)
