# Data Assistant Analytics — On-Premise AI Analytics Platform

Nền tảng phân tích dữ liệu bằng AI, đóng gói On-Premise. Khách hàng tự host trên 1 server
(Ubuntu/CentOS) và chạy 1 lệnh duy nhất.

## Kiến trúc

| Service    | Mô tả                                              | Port |
|------------|----------------------------------------------------|------|
| `backend`  | FastAPI — Web Installer + Main App (LLM, OAuth...)  | 8080 |
| `frontend` | Vue 3 + Vite — Admin Dashboard                      | 5173 |
| `postgres` | PostgreSQL (tùy chọn, profile `with-postgres`)      | 5432 |

> Mặc định backend dùng **SQLite fallback** (`backend/data/app.db`) nếu khách không nhập
> thông tin DB ngoài. Có thể bật Postgres đóng gói sẵn bằng profile.

## Cài đặt (Quick start)

```bash
# 1. Khởi động (chỉ backend + frontend, dùng SQLite)
docker compose up -d

# 2. Mở trình duyệt tới http://<server-ip>:8080
#    -> Web Installer (tone đen-vàng) hiện ra ở lần chạy đầu
#    -> Điền 4 bước: License -> Database -> Super Admin -> LLM API Key
#    -> Hệ thống ghi .env, tạo DB, rồi tự restart sang Main App
```

Bật Postgres đóng gói sẵn:

```bash
docker compose --profile with-postgres up -d
```

## Luồng Installer

Khi backend khởi động mà chưa có cấu hình (`INSTALLED != true` trong `.env`):
1. Toàn bộ traffic `/` được route về Web Installer tĩnh.
2. Khách điền cấu hình → API `/api/installer/finalize` ghi `.env` (có `SECRET_KEY`
   sinh ngẫu nhiên để mã hóa API key trong DB), tạo bảng, tạo Super Admin.
3. Backend tự thoát tiến trình → Docker `restart: unless-stopped` bật lại container,
   lần này đọc thấy `INSTALLED=true` → boot **Main App** thay vì Installer.

## Lộ trình

- [x] **Phase 1** — Core structure, docker-compose, Web Installer
- [ ] Phase 2 — Auth (JWT) + LLM Router (LiteLLM) + Token Tracking
- [ ] Phase 3 — OAuth Data Sources (Facebook, Shopee)
- [ ] Phase 4 — LangChain Tools + Function Calling + Pandas/Excel export

## Cấu trúc thư mục

```
backend/
  app/
    core/        # config, database, security (encryption), state
    models/      # SQLAlchemy models (user, system_config, ...)
    routers/     # installer, main_app, (auth, llm... ở phase sau)
    services/    # business logic (installer_service, ...)
    static/      # installer UI tĩnh (HTML/CSS/JS, tone đen-vàng)
  data/          # SQLite db + .env runtime (mount volume)
frontend/        # Vue 3 + Vite admin dashboard
```
