# Hướng dẫn Deploy

## A. On-Premise (cách đúng — production)

Chạy trên 1 server Ubuntu/CentOS có Docker:

```bash
git clone <repo-url>
cd DataAssistantAnalytics
docker compose up -d
# Mở http://<server-ip>:8080 → Web Installer
# License key tạm: 123456
```

---

## B. Vercel (demo/staging) — 2 bước

Vercel là **serverless** nên không có Installer UI, Docker hay SQLite. Cần cấu hình
thủ công bằng environment variables trong Vercel Dashboard.

### B1. Database: Tạo Neon PostgreSQL (miễn phí)

1. Vào **[neon.tech](https://neon.tech)** → Sign up → New Project
2. Tạo xong, copy **Connection String** dạng:
   `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

### B2. Deploy Backend (FastAPI)

```bash
cd backend
npx vercel          # lần đầu: login + chọn project
# hoặc
npx vercel --prod   # deploy production
```

Sau khi deploy, vào **Vercel Dashboard → Project → Settings → Environment Variables**
và thêm các biến sau:

| Key | Giá trị | Ghi chú |
|-----|---------|---------|
| `INSTALLED` | `true` | Bỏ qua Installer |
| `SECRET_KEY` | *(random 48 chars)* | Chạy: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | `postgresql://...` | Connection string từ Neon |
| `VERCEL_DEPLOYMENT` | `1` | Bật chế độ serverless |

Redeploy sau khi thêm env vars.

Tạo bảng DB + Super Admin lần đầu — chạy script này 1 lần:
```bash
cd backend
python scripts/init_vercel_db.py \
  --database-url "postgresql://..." \
  --secret-key "your-secret-key" \
  --admin-email "admin@company.com" \
  --admin-password "yourpassword" \
  --llm-provider "openai" \
  --llm-api-key "sk-..."
```

### B3. Deploy Frontend (Vue 3)

```bash
cd frontend
# Đặt URL backend Vercel vào .env.production
echo "VITE_API_BASE=https://your-backend.vercel.app" > .env.production
npx vercel --prod
```

---

## Environment Variables tham khảo đầy đủ

```
INSTALLED=true
SECRET_KEY=<random_48_chars>
DATABASE_URL=postgresql+psycopg://user:pass@host/db?sslmode=require
VERCEL_DEPLOYMENT=1
APP_NAME=Data Assistant Analytics
DEBUG=false
```
