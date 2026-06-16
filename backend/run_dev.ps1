# Chạy backend cục bộ để test — bypass Installer, dùng SQLite
$env:INSTALLED        = "true"
$env:SECRET_KEY       = "dev-secret-key-32-chars-minimum!!"
$env:DATABASE_URL     = "sqlite:///./dev_test.db"
$env:ENV_FILE         = "nul"          # Windows: không đọc file .env
$env:APP_PORT         = "8080"

# Điền App ID/Secret nếu muốn gia hạn token 60 ngày (tuỳ chọn)
# $env:FACEBOOK_APP_ID     = ""
# $env:FACEBOOK_APP_SECRET  = ""

Write-Host "Backend dev dang chay tai http://localhost:8080" -ForegroundColor Green
Write-Host "API docs: http://localhost:8080/api/docs" -ForegroundColor Cyan
Write-Host "Ctrl+C de dung" -ForegroundColor Yellow

python run.py
