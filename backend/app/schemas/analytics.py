from __future__ import annotations

from pydantic import BaseModel


class DateRange(BaseModel):
    since: str  # YYYY-MM-DD
    until: str  # YYYY-MM-DD


class AgentQuery(BaseModel):
    question: str


class AgentResponse(BaseModel):
    answer: str
    steps: int


class ReportPayload(BaseModel):
    since: str
    until: str


class DownloadResponse(BaseModel):
    filename: str
    download_url: str
