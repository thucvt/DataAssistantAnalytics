"""Vercel serverless entrypoint cho FastAPI.

Trên Vercel, không có Installer flow (SIGTERM/restart). Thay vào đó, cấu hình
được đọc từ Vercel environment variables. Xem hướng dẫn tại DEPLOY.md.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Đảm bảo package `app` trong thư mục cha được import đúng
sys.path.insert(0, str(Path(__file__).parent.parent))

# Khi chạy trên Vercel, bypass Installer nếu có env vars đủ dùng
_vercel = os.getenv("VERCEL_DEPLOYMENT") or os.getenv("VERCEL")
if _vercel:
    # Force INSTALLED=true và dùng DATABASE_URL từ env (Neon / Supabase)
    os.environ.setdefault("INSTALLED", "true")

    # SECRET_KEY bắt buộc phải set trong Vercel dashboard
    if not os.getenv("SECRET_KEY"):
        raise RuntimeError(
            "Thiếu biến môi trường SECRET_KEY. "
            "Vào Vercel Dashboard → Settings → Environment Variables để thêm."
        )
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError(
            "Thiếu biến môi trường DATABASE_URL (cần Neon/Supabase PostgreSQL). "
            "Xem DEPLOY.md để hướng dẫn."
        )

    # Override ENV_FILE để Settings đọc từ env thật thay vì file .env
    os.environ["ENV_FILE"] = "/dev/null"

    from app.core.config import reload_settings
    reload_settings()

from app.main import create_app

# Vercel gọi object `app` từ file này
app = create_app()
