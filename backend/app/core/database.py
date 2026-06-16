"""Khởi tạo SQLAlchemy engine/session từ DATABASE_URL.

Hỗ trợ SQLite (fallback mặc định), PostgreSQL và MySQL. Engine được tạo lười
(lazy) để Installer có thể test kết nối với một URL bất kỳ trước khi commit.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _normalize_db_url(url: str) -> str:
    """Render provides postgres:// — convert to postgresql+psycopg:// for psycopg3."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def build_engine(database_url: str) -> Engine:
    """Tạo engine cho một DATABASE_URL. Tách riêng để Installer test connection."""
    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        # SQLite + FastAPI threadpool cần tắt check_same_thread; đảm bảo thư mục tồn tại
        connect_args = {"check_same_thread": False}
        db_path = database_url.replace("sqlite:///", "")
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    else:
        database_url = _normalize_db_url(database_url)
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


def init_engine() -> Engine:
    """Khởi tạo engine toàn cục từ settings hiện tại."""
    global _engine, _SessionLocal
    settings = get_settings()
    _engine = build_engine(settings.DATABASE_URL)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        init_engine()
    assert _engine is not None
    return _engine


def get_db():
    """FastAPI dependency: yield một session, đảm bảo đóng sau request."""
    if _SessionLocal is None:
        init_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
