"""Script khởi tạo DB trên Vercel (chạy 1 lần thay cho Installer UI).

Dùng khi deploy lên môi trường serverless (Vercel + Neon):

  python scripts/init_vercel_db.py \\
    --database-url "postgresql+psycopg://..." \\
    --secret-key "..." \\
    --admin-email admin@company.com \\
    --admin-password "..." \\
    --llm-provider openai \\
    --llm-api-key "sk-..."
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import build_engine
from app.core.security import encrypt_secret, hash_password
from app.models import Base, SystemConfig, User
from app.services.config_service import DEFAULT_MODELS, PROVIDER_KEY_NAME
from sqlalchemy.orm import sessionmaker


def main() -> None:
    parser = argparse.ArgumentParser(description="Khởi tạo DB cho Vercel deployment")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--secret-key", required=True)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--admin-name", default="Super Admin")
    parser.add_argument("--llm-provider", required=True, choices=["openai", "anthropic", "gemini"])
    parser.add_argument("--llm-api-key", required=True)
    parser.add_argument("--llm-model", default="")
    args = parser.parse_args()

    print(f"Kết nối DB: {args.database_url[:40]}...")
    engine = build_engine(args.database_url)
    Base.metadata.create_all(engine)
    print("  Đã tạo bảng DB ✓")

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Super Admin
        existing = db.query(User).filter(User.email == args.admin_email).first()
        if existing:
            print(f"  User {args.admin_email} đã tồn tại, bỏ qua.")
        else:
            db.add(User(
                email=args.admin_email, full_name=args.admin_name,
                hashed_password=hash_password(args.admin_password),
                is_active=True, is_superadmin=True,
            ))
            print(f"  Tạo Super Admin {args.admin_email} ✓")

        # LLM config
        model = args.llm_model or DEFAULT_MODELS[args.llm_provider]
        enc_key = encrypt_secret(args.llm_api_key, args.secret_key)

        for key, val, secret in [
            ("LLM_PROVIDER", args.llm_provider, False),
            ("LLM_DEFAULT_MODEL", model, False),
            (PROVIDER_KEY_NAME[args.llm_provider], enc_key, True),
        ]:
            row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if row:
                row.value = val
            else:
                db.add(SystemConfig(key=key, value=val, is_secret=secret))

        db.commit()
        print("  Lưu cấu hình LLM ✓")
    finally:
        db.close()
        engine.dispose()

    print("\n✅ Khởi tạo hoàn tất. Tiếp theo:")
    print("   1. Redeploy backend trên Vercel.")
    print(f"   2. Đăng nhập: POST /api/auth/login với email={args.admin_email}")


if __name__ == "__main__":
    main()
