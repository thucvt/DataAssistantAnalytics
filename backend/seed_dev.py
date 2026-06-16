# -*- coding: utf-8 -*-
"""Seed database dev de test nhanh."""
import os, sys
os.environ["INSTALLED"]    = "true"
os.environ["SECRET_KEY"]   = "dev-secret-key-32-chars-minimum!!"
os.environ["DATABASE_URL"] = "sqlite:///./dev_test.db"
os.environ["ENV_FILE"]     = "nul"
os.environ["PYTHONUTF8"]   = "1"

from app.core.database import build_engine
from app.core.security import hash_password
from app.models import Base, User
from sqlalchemy.orm import Session

engine = build_engine("sqlite:///./dev_test.db")
Base.metadata.create_all(engine)

with Session(engine) as db:
    if not db.query(User).filter_by(email="admin@example.com").first():
        db.add(User(
            email="admin@example.com",
            full_name="Dev Admin",
            hashed_password=hash_password("admin123"),
            is_superadmin=True,
            is_active=True,
        ))
        db.commit()
        print("OK - Tao user: admin@example.com / admin123")
    else:
        print("OK - User da ton tai: admin@example.com / admin123")

print("OK - Database dev san sang: dev_test.db")
