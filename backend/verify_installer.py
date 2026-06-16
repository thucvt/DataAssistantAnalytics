"""Smoke test luồng Installer (Phase 1) — không cần Docker.

Đặt ENV_FILE vào thư mục tạm, dựng app ở chế độ Installer, đi qua 4 bước rồi
finalize, sau đó dựng lại app và xác nhận đã chuyển sang Main App.
"""
import os
import tempfile
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
os.environ["ENV_FILE"] = str(tmp / ".env")
os.environ["APP_PORT"] = "8080"

from fastapi.testclient import TestClient
from app.core.config import reload_settings
from app.core.state import is_installed
import app.main as main_mod


def fresh_client():
    reload_settings()
    # rebuild engine module-global cho DB mới
    import app.core.database as db
    db._engine = None
    db._SessionLocal = None
    return TestClient(main_mod.create_app())


print("== Bước 0: chưa cài ==")
assert not is_installed(), "Phải ở trạng thái chưa cài"
c = fresh_client()

r = c.get("/")
assert r.status_code == 200 and "Installer" not in r.text[:0] and "Data" in r.text, r.status_code
print("  GET / -> trả Installer HTML OK")

r = c.get("/api/installer/status").json()
assert r["installed"] is False, r
print("  status.installed = False OK")

print("== Màn 1: License ==")
r = c.post("/api/installer/license", json={"license_key": "123456"}).json()
assert r["ok"], r
print("  license hợp lệ OK")

print("== Màn 2: test SQLite ==")
r = c.post("/api/installer/test-database", json={"engine": "sqlite"}).json()
assert r["ok"], r
print("  test-database sqlite OK:", r["message"])

print("== Test Postgres giả (phải fail gọn) ==")
r = c.post("/api/installer/test-database", json={
    "engine": "postgresql", "host": "10.255.255.1", "port": 5432,
    "database": "x", "username": "u", "password": "p"}).json()
assert r["ok"] is False, r
print("  postgres sai -> báo lỗi OK")

print("== Finalize ==")
payload = {
    "license": {"license_key": "123456"},
    "database": {"engine": "sqlite"},
    "admin": {"email": "admin@company.com", "full_name": "Admin", "password": "supersecret1"},
    "llm": {"provider": "anthropic", "api_key": "sk-ant-xxxxxxxx", "default_model": ""},
}
r = c.post("/api/installer/finalize", json=payload)
assert r.status_code == 200 and r.json()["ok"], (r.status_code, r.text)
print("  finalize OK:", r.json()["message"])

# .env phải được ghi với INSTALLED=true
env_text = (tmp / ".env").read_text(encoding="utf-8")
assert "INSTALLED=true" in env_text and "SECRET_KEY=" in env_text, env_text
print("  .env đã ghi INSTALLED=true + SECRET_KEY OK")

print("== Bước cuối: rebuild app -> Main App ==")
assert is_installed(), "Phải đã cài sau finalize"
c2 = fresh_client()
r = c2.get("/api/info").json()
assert r["installed"] is True and r["phase"] == 1, r
print("  /api/info ->", r)

# Kiểm tra DB: admin + config đã mã hóa
from app.core.database import get_engine
from app.core.config import get_settings
from app.core.security import decrypt_secret
from sqlalchemy.orm import sessionmaker
from app.models import User, SystemConfig

Session = sessionmaker(bind=get_engine())
db = Session()
admin = db.query(User).filter_by(email="admin@company.com").first()
assert admin and admin.is_superadmin and admin.hashed_password.startswith("$2"), "admin/hash"
print("  Super Admin tạo OK, password đã hash bcrypt")

cfg = db.query(SystemConfig).filter_by(key="ANTHROPIC_API_KEY").first()
assert cfg and cfg.is_secret, "config thiếu"
secret = get_settings().SECRET_KEY
assert cfg.value != "sk-ant-xxxxxxxx", "API key phải được mã hóa trong DB"
assert decrypt_secret(cfg.value, secret) == "sk-ant-xxxxxxxx", "giải mã sai"
print("  API key lưu mã hóa + giải mã đúng OK")

model = db.query(SystemConfig).filter_by(key="LLM_DEFAULT_MODEL").first()
assert model.value == "claude-3-5-sonnet-20241022", model.value
print("  default model auto-fill theo provider OK:", model.value)
db.close()

print("\n✅ TẤT CẢ PASS — Phase 1 Installer hoạt động end-to-end.")
