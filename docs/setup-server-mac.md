# Setup Guide — Single Mac Machine (Development)

> Hướng dẫn chạy toàn bộ AI Service trên **1 máy Mac** (M1/M2/M3/Intel) bằng `docker compose`.
> Dùng cho mục đích **phát triển và test** — không cần Swarm hay GCP.

---

## 📋 Yêu cầu

| Yêu cầu | Tối thiểu | Khuyến nghị |
|---|---|---|
| **OS** | macOS 12+ | macOS 14+ (Sonoma) |
| **RAM** | 8 GB | 16 GB+ |
| **Disk** | 20 GB free | 50 GB+ (LLM model ~6GB) |
| **Docker Desktop** | 4.x+ | Latest |

> **⚠️ Inference trên Mac:** Để tận dụng nguyên vẹn sức mạnh của GPU Apple Silicon (Metal), module Inference Server sẽ được chạy bản Native (MLX) ở ngoài và Docker sẽ connect tới.

---

## BƯỚC 1 — Cài Docker Desktop

Nếu chưa có:

```bash
# Kiểm tra đã cài chưa
docker --version

# Nếu chưa có → tải tại:
# https://www.docker.com/products/docker-desktop/
# Hoặc dùng Homebrew:
brew install --cask docker
```

Sau khi cài, **mở Docker Desktop** và tăng resource limit:

```
Docker Desktop → Settings → Resources:
  CPUs:  6+ (recommended)
  Memory: 8 GB+
  Swap:  2 GB
  Disk:  50 GB+
```

> Nhớ click **Apply & Restart** sau khi thay đổi.

---

## BƯỚC 2 — Clone repo và tạo `.env`

```bash
cd ~/Desktop/HuanVo/ai-service   # hoặc đường dẫn tới repo

cp .env.example .env
```

Mở `.env` và điền các giá trị **bắt buộc**:

```bash
# Tạo secret ngẫu nhiên
openssl rand -hex 32
```

```env
# ── BẮT BUỘC ─────────────────────────────────────────────────────────────
JWT_SECRET=<kết quả openssl rand -hex 32>
NEXTAUTH_SECRET=<kết quả openssl rand -hex 32>

# ── HuggingFace (để tải mô hình vLLM) ────────────────────────────────────
HF_TOKEN=hf_xxxx    # Lấy tại: huggingface.co/settings/tokens (miễn phí)

# ── Các giá trị còn lại giữ nguyên default ───────────────────────────────
GRAFANA_PASSWORD=admin
```

> Các giá trị khác (`DATABASE_URL`, `REDIS_URL`, `VLLM_BASE_URL`...) đã có default phù hợp cho local — **không cần thay**.

---

## BƯỚC 3 — Chạy services cơ bản (không có vLLM)

Cách nhanh nhất để kiểm tra hệ thống:

```bash
docker compose up -d
```

Lần đầu sẽ build images (~5-10 phút). Sau đó kiểm tra:

```bash
docker compose ps
```

Phải thấy trạng thái `running` / `healthy`:
```
NAME           STATUS
ai_postgres    running (healthy)
ai_redis       running (healthy)
ai_backend     running
ai_worker      running
ai_frontend    running
ai_prometheus  running
ai_grafana     running
```

Truy cập:

| Service | URL |
|---|---|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8080/docs |
| **Prometheus** | http://localhost:9090 |
| **Grafana** | http://localhost:3001 (admin / admin) |

> **Chat completion sẽ báo lỗi** nếu chưa bật MLX Inference Server. Các chức năng khác (auth, webhooks...) hoạt động bình thường.

---

## BƯỚC 4 — Khởi động MLX Inference Server (Native GPU)

> **Lưu ý:** MLX dùng để thay thế module LLM server trong docker vì DockerVM không pass-through được Apple Neural engine. Chạy script này bên ngoài docker để sử dụng Apple Metal GPU.

```bash
# Mở một terminal MỚI (bên ngoài Docker)
chmod +x scripts/start_mlx.sh
./scripts/start_mlx.sh
```

Theo dõi quá trình tải model (Qwen3.5-4B):
Khi nào thấy báo "Uvicorn running on http://0.0.0.0:9999" là thành công.

Kiểm tra:

```bash
curl http://localhost:8080/v1/models
# {"data":[{"id":"mlx-community/Qwen3.5-4B-Instruct-4bit",...}]}

# Test chat
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"mlx-community/Qwen3.5-4B-Instruct-4bit","messages":[{"role":"user","content":"Xin chào"}]}'
```

---

## BƯỚC 5 — Tạo tài khoản và API key

1. Mở http://localhost:3000
2. Click **Register** → tạo tài khoản
3. Vào **API Keys** → **Create Key** → copy `sk-xxx`
4. Dùng key đó trong header `x-api-key` cho tất cả API calls

---

## 🔄 Các lệnh thường dùng

### Khởi động / tắt

```bash
# Khởi động tất cả database, queue, api
docker compose up -d

# Tắt tất cả (giữ data)
docker compose down

# Tắt và XÓA toàn bộ data (reset hoàn toàn)
docker compose down -v
```

### Xem logs

```bash
docker compose logs -f backend     # FastAPI logs
docker compose logs -f worker      # RQ worker logs
docker compose logs -f             # tất cả logs cùng lúc
```

### Restart 1 service

```bash
docker compose restart backend
docker compose restart frontend
```

### Rebuild sau khi thay code

```bash
# Backend (Python code thay đổi)
docker compose build backend
docker compose up -d backend

# Frontend (Next.js code thay đổi)
docker compose build frontend
docker compose up -d frontend

# Hoặc rebuild tất cả
docker compose up -d --build
```

### Chạy Alembic migration thủ công

```bash
docker exec ai_backend alembic upgrade head

# Hoặc vào shell backend để debug
docker exec -it ai_backend bash
```

### Xem database

```bash
# Kết nối PostgreSQL
docker exec -it ai_postgres psql -U aiplatform -d aiplatform

# Một số query hữu ích
\dt              # liệt kê tables
\d users         # xem cấu trúc bảng users
SELECT * FROM teams LIMIT 5;
SELECT count(*) FROM usage_logs;
```

---

## ⚡ Dev mode (không dùng Docker cho backend)

Nếu muốn **hot-reload nhanh hơn** khi phát triển Python:

```bash
# Bước 1: Chỉ chạy infra bằng Docker
docker compose up -d postgres redis

# Bước 2: Backend chạy native
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp ../.env.example .env
# Sửa DATABASE_URL và REDIS_URL sang localhost:
# DATABASE_URL=postgresql://aiplatform:aiplatform@localhost:5432/aiplatform
# REDIS_URL=redis://localhost:6379

alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
# → reload tự động khi save file Python

# Bước 3: Worker (terminal khác)
rq worker --with-scheduler --url redis://localhost:6379 document_queue

# Bước 4: Frontend
cd ../frontend
npm install
npm run dev   # → http://localhost:3000
```

---

## 🆘 Lỗi thường gặp trên Mac

### `docker: Cannot connect to the Docker daemon`

```bash
# Docker Desktop chưa chạy → mở app Docker Desktop
open /Applications/Docker.app
```

### `port is already allocated` (port bị chiếm)

```bash
# Tìm process đang dùng port
lsof -i :8080    # hoặc 3000, 5432, 6379...
kill -9 <PID>
```

### Backend container crash với `address already in use`

```bash
docker compose down
docker compose up -d
```





### `alembic: command not found` trong container

```bash
docker exec ai_backend pip install alembic
docker exec ai_backend alembic upgrade head
```

### Xóa toàn bộ và bắt đầu lại

```bash
docker compose down -v               # xóa containers + volumes
docker system prune -a --volumes     # xóa tất cả images và cache
docker compose up -d --build         # build lại từ đầu
```

---

## 📊 Services và ports tóm tắt

| Service | Port | URL |
|---|---|---|
| Frontend | 3000 | http://localhost:3000 |
| Backend API | 8080 | http://localhost:8080 |
| Swagger UI | 8080 | http://localhost:8080/docs |
| PostgreSQL | 5432 | `postgresql://aiplatform:aiplatform@localhost:5432/aiplatform` |
| Redis | 6379 | `redis://localhost:6379` |
| MLX Server | 8080 (Mac Host) | http://127.0.0.1:8080/v1 |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3001 | http://localhost:3001 |

---

## 📎 Tài liệu liên quan

- [Setup 3 máy Swarm + GCP](./setup-server.md) — Production deployment
- [Architecture](./architecture.md) — Kiến trúc tổng thể
- [API Spec](./api-spec.md) — Tất cả endpoints
