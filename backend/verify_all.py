"""Smoke test toàn bộ Phase 1-4 (không cần Docker, không cần API key thật).

Dùng TestClient + mock cho LLM và external HTTP.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# --- Thiết lập env trước khi import bất kỳ app module nào ---
tmp = Path(tempfile.mkdtemp())
os.environ["ENV_FILE"] = str(tmp / ".env")
os.environ["APP_PORT"] = "8080"
os.environ.setdefault("PYTHONPATH", str(Path(__file__).parent))

from fastapi.testclient import TestClient
import app.core.database as db_mod
import app.main as main_mod
from app.core.config import reload_settings

PASS = 0
FAIL = 0


def check(cond, label):
    global PASS, FAIL
    if cond:
        print(f"  [OK] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label}", file=sys.stderr)
        FAIL += 1


def fresh_client():
    reload_settings()
    db_mod._engine = None
    db_mod._SessionLocal = None
    return TestClient(main_mod.create_app(), raise_server_exceptions=True)


# ════════════════════════════════════════════════════════
# PHASE 1 — Installer
# ════════════════════════════════════════════════════════
print("━━━ Phase 1: Installer ━━━")
c = fresh_client()
r = c.get("/api/installer/status").json()
check(r["installed"] is False, "chưa cài: installed=False")

r = c.post("/api/installer/license", json={"license_key": "WRONG"}).json()
check(r["ok"] is False, "license sai bị reject")

r = c.post("/api/installer/license", json={"license_key": "123456"}).json()
check(r["ok"] is True, "license '123456' hợp lệ")

r = c.post("/api/installer/test-database", json={"engine": "sqlite"}).json()
check(r["ok"] is True, "test DB sqlite OK")

r = c.post("/api/installer/test-database", json={
    "engine": "postgresql", "host": "10.255.0.1", "port": 5432,
    "database": "x", "username": "u", "password": "p"}).json()
check(r["ok"] is False, "test DB postgres sai -> lỗi")

finalize_payload = {
    "license": {"license_key": "123456"},
    "database": {"engine": "sqlite"},
    "admin": {"email": "admin@test.com", "full_name": "Admin", "password": "adminpass1"},
    "llm": {"provider": "openai", "api_key": "sk-xxxxxxxxxxxxxxxx", "default_model": "gpt-4o"},
}
r = c.post("/api/installer/finalize", json=finalize_payload)
check(r.status_code == 200 and r.json()["ok"], "finalize thành công")

env_text = (tmp / ".env").read_text()
check("INSTALLED=true" in env_text, ".env có INSTALLED=true")
check("SECRET_KEY=" in env_text, ".env có SECRET_KEY")

# ════════════════════════════════════════════════════════
# PHASE 2 — Auth + AI Settings
# ════════════════════════════════════════════════════════
print("\n━━━ Phase 2: Auth + LLM ━━━")
c2 = fresh_client()

r = c2.get("/api/info").json()
check(r["installed"] is True and r["phase"] == 1, "Main App boot sau install")

# Login
r = c2.post("/api/auth/login", json={"email": "admin@test.com", "password": "adminpass1"})
check(r.status_code == 200, "login thành công")
token = r.json().get("access_token", "")
check(bool(token), "nhận access_token JWT")
auth = {"Authorization": f"Bearer {token}"}

# /me
r = c2.get("/api/auth/me", headers=auth)
check(r.status_code == 200 and r.json()["is_superadmin"], "/me trả đúng user superadmin")

# Sai password
r = c2.post("/api/auth/login", json={"email": "admin@test.com", "password": "wrong"})
check(r.status_code == 401, "sai password -> 401")

# AI Settings (super admin)
r = c2.get("/api/ai/settings", headers=auth)
check(r.status_code == 200, "GET /api/ai/settings OK")
s = r.json()
check(s["active_provider"] == "openai", "provider = openai")
check(s["keys_configured"]["openai"] is True, "openai key đã có")

# Đổi provider sang anthropic
r = c2.put("/api/ai/settings", headers=auth, json={"provider": "anthropic", "model": ""})
check(r.status_code == 200, "PUT settings -> anthropic")
check(r.json()["active_provider"] == "anthropic", "provider đã đổi sang anthropic")

r = c2.put("/api/ai/keys", headers=auth, json={"provider": "anthropic", "api_key": "sk-ant-testkey"})
check(r.status_code == 200, "PUT /api/ai/keys anthropic OK")
check(r.json()["keys_configured"]["anthropic"] is True, "anthropic key đã có")

r = c2.delete("/api/ai/keys/anthropic", headers=auth)
check(r.status_code == 200, "DELETE anthropic key OK")
check(r.json()["keys_configured"]["anthropic"] is False, "anthropic key đã xóa")

# Không có token -> 401
r = c2.get("/api/ai/settings")
check(r.status_code == 401, "không có token -> 401")

# AI Usage stats
r = c2.get("/api/ai/usage", headers=auth)
check(r.status_code == 200, "GET /api/ai/usage OK")
u = r.json()
check("totals" in u and "by_day" in u and "by_model" in u, "usage có đủ keys")
check(u["totals"]["requests"] == 0, "chưa gọi LLM nào -> requests=0")

# ════════════════════════════════════════════════════════
# PHASE 2 — Token logging
# ════════════════════════════════════════════════════════
print("\n━━━ Phase 2: Token Tracking ━━━")
from app.core.database import get_engine
from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.services.ai_manager import log_usage
from app.services.pricing import estimate_cost
from sqlalchemy.orm import sessionmaker
from app.models import LLMUsageLog, SystemConfig

engine = get_engine()
Session = sessionmaker(bind=engine)
db = Session()

# Ghi 2 log token trực tiếp
log_usage(db, user_id=1, model="gpt-4o", prompt_tokens=2000, completion_tokens=500)
log_usage(db, user_id=1, model="gpt-4o", prompt_tokens=1000, completion_tokens=200)

r = c2.get("/api/ai/usage?days=30", headers=auth).json()
check(r["totals"]["requests"] == 2, "2 log token ghi OK")
check(r["totals"]["prompt_tokens"] == 3000, "tổng prompt_tokens = 3000")
check(abs(r["totals"]["estimated_cost"]) > 0, "estimated_cost > 0")
check(len(r["by_model"]) == 1 and r["by_model"][0]["model"] == "gpt-4o", "by_model đúng")

# Kiểm tra bảng giá
cost = estimate_cost("gpt-4o", 2000, 500)
expected = round((2000/1_000_000)*2.50 + (500/1_000_000)*10.00, 6)
check(abs(cost - expected) < 1e-7, f"estimate_cost gpt-4o chính xác ({cost:.6f})")

# API key mã hóa
cfg = db.query(SystemConfig).filter_by(key="OPENAI_API_KEY").first()
check(cfg and cfg.is_secret, "OPENAI_API_KEY là secret")
check(cfg.value != "sk-xxxxxxxxxxxxxxxx", "API key đã mã hóa trong DB")
check(decrypt_secret(cfg.value, get_settings().SECRET_KEY) == "sk-xxxxxxxxxxxxxxxx",
      "giải mã API key đúng")
db.close()

# ════════════════════════════════════════════════════════
# PHASE 3 — OAuth
# ════════════════════════════════════════════════════════
print("\n━━━ Phase 3: OAuth ━━━")
from app.services import oauth_service as os_mod
from app.services.integrations.shopee import make_signature
import hashlib, hmac as hmac_mod

# Test chữ ký HMAC-SHA256 Shopee
partner_key = "my_secret_key"
base = "123456/api/v2/shop/auth_partner1700000000"
expected_sig = hmac_mod.new(
    partner_key.encode(), base.encode(), hashlib.sha256
).hexdigest()
check(make_signature(partner_key, base) == expected_sig, "Shopee HMAC-SHA256 chính xác")

# Lưu/đọc OAuth token (mã hóa)
db2 = Session()
conn = os_mod.save_connection(
    db2, user_id=1, provider="facebook",
    access_token="EAAxxxTESTtoken", extra={"ad_account_id": "act_12345"}
)
check(conn.access_token != "EAAxxxTESTtoken", "access_token mã hóa trong DB")
retrieved = os_mod.get_access_token(db2, 1, "facebook")
check(retrieved == "EAAxxxTESTtoken", "giải mã access_token đúng")
extra = os_mod.get_extra(conn)
check(extra.get("ad_account_id") == "act_12345", "extra JSON lưu/đọc đúng")
db2.close()

# Endpoint connections
r = c2.get("/api/oauth/connections", headers=auth).json()
check(any(c["provider"] == "facebook" and c["connected"] for c in r), "facebook connected=True")
check(any(c["provider"] == "shopee" and not c["connected"] for c in r), "shopee connected=False")

# Config OAuth (super admin)
r = c2.put("/api/oauth/config", headers=auth,
           json={"key": "FACEBOOK_APP_ID", "value": "123456789"})
check(r.status_code == 200, "PUT /api/oauth/config FACEBOOK_APP_ID OK")

r = c2.put("/api/oauth/config", headers=auth,
           json={"key": "EVIL_KEY", "value": "x"})
check(r.status_code == 400, "key không được phép -> 400")

# ════════════════════════════════════════════════════════
# PHASE 4 — Data Processing
# ════════════════════════════════════════════════════════
print("\n━━━ Phase 4: Data Processing ━━━")
from app.services.data_processing import export_excel, merge_by_date, to_chart_payload
import pandas as pd

meta = [
    {"date": "2025-01-01", "spend": 100.0},
    {"date": "2025-01-02", "spend": 150.0},
    {"date": "2025-01-03", "spend": 200.0},
]
shopee = [
    {"date": "2025-01-01", "revenue": 500.0},
    {"date": "2025-01-02", "revenue": 800.0},
    # 2025-01-03 không có data Shopee -> outer join
]
df = merge_by_date(meta, shopee)
check(len(df) == 3, "merge_by_date: 3 hàng (outer join)")
check(df.loc[df["date"] == "2025-01-03", "revenue"].iloc[0] == 0.0, "thiếu ngày Shopee -> revenue=0")
check(df.loc[df["date"] == "2025-01-01", "profit"].iloc[0] == 400.0, "profit ngày 1 = 500-100 = 400")
check(df.loc[df["date"] == "2025-01-01", "roas"].iloc[0] == 5.0, "ROAS ngày 1 = 500/100 = 5.0")

chart = to_chart_payload(df)
check("labels" in chart and "datasets" in chart and "summary" in chart, "chart payload cấu trúc đúng")
check(chart["summary"]["total_spend"] == 450.0, "total_spend = 450")
check(chart["summary"]["total_revenue"] == 1300.0, "total_revenue = 1300")
check(chart["summary"]["total_profit"] == 850.0, "total_profit = 850")

# Excel export
path = export_excel(df, "test_report.xlsx")
check(path.exists(), "file Excel đã tạo")
check(path.stat().st_size > 2000, "Excel có dung lượng thực")
df_check = pd.read_excel(path)
check("Ngày" in df_check.columns and "Doanh thu" in df_check.columns, "Excel có cột đúng tên")
check(len(df_check) == 3, "Excel có 3 hàng dữ liệu")
path.unlink()  # dọn tmp

# Download endpoint guard
r = c2.get("/api/analytics/download/..evil..bad.xlsx", headers=auth)
check(r.status_code == 400, "path traversal bị block")

r = c2.get("/api/analytics/download/not_exist.xlsx", headers=auth)
check(r.status_code == 404, "file không tồn tại -> 404")

# ════════════════════════════════════════════════════════
# Tổng kết
# ════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"  PASS: {PASS}  |  FAIL: {FAIL}")
if FAIL == 0:
    print("  ✅ TẤT CẢ PASS — Phase 1-4 hoạt động đầy đủ.")
else:
    print("  ❌ CÓ LỖI. Xem chi tiết bên trên.")
    sys.exit(1)
