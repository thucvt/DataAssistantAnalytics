FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Cài deps trước để tận dụng layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Thư mục data (SQLite + .env runtime). Sẽ được mount volume ở compose.
RUN mkdir -p /app/data /tmp/exports

EXPOSE 8080

# run.py tự quyết định chạy Installer hay Main App dựa trên trạng thái cài đặt
CMD ["python", "run.py"]
