"""Entrypoint container."""
from __future__ import annotations

import os
import uvicorn

from app.core.config import get_settings
from app.core.state import is_installed


def _auto_seed() -> None:
    """Khi INSTALLED=true + DB trống, tự tạo tables + admin từ env vars.

    Dùng cho deploy cloud (Render/Railway) không có Installer UI.
    Env vars: ADMIN_EMAIL (default admin@example.com), ADMIN_PASSWORD (default Admin@1234)
    """
    from app.core.database import build_engine
    from app.core.security import hash_password
    from app.models import Base, User
    from sqlalchemy.orm import Session

    s = get_settings()
    engine = build_engine(s.DATABASE_URL)
    Base.metadata.create_all(engine)

    email    = os.getenv("ADMIN_EMAIL",    "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD", "Admin@1234")
    name     = os.getenv("ADMIN_NAME",     "Super Admin")

    with Session(engine) as db:
        if not db.query(User).filter_by(email=email).first():
            db.add(User(
                email=email,
                full_name=name,
                hashed_password=hash_password(password),
                is_superadmin=True,
                is_active=True,
            ))
            db.commit()
            print(f"[boot] Admin seeded: {email}")
        else:
            print(f"[boot] Admin already exists: {email}")


def main() -> None:
    settings = get_settings()
    mode = "MAIN APP" if is_installed() else "INSTALLER"
    print(f"[boot] {settings.APP_NAME} — {mode} — port {settings.APP_PORT}")

    if is_installed():
        _auto_seed()

    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
