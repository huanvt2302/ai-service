# Setup Guide — Hybrid Local Swarm + GCP Cloud Burst

> Hướng dẫn này giả định bạn có **3 máy Linux** (Ubuntu 22.04+) cùng mạng LAN và 1 tài khoản Google Cloud.

---

## 📋 Checklist trước khi bắt đầu

### Yêu cầu phần cứng

| Máy | Role | CPU | RAM | GPU (tuỳ chọn) |
|---|---|---|---|---|
| **Machine 1** | Swarm Manager | 4 cores | 8 GB | Không cần |
| **Machine 2** | Swarm Worker | 4 cores | 16 GB | GTX 1080+ / RTX 3090 |
| **Machine 3** | Swarm Worker | 4 cores | 16 GB | GTX 1080+ / RTX 3090 |

> Không có GPU → vLLM vẫn chạy ở CPU mode (chậm hơn). Xem ghi chú ở bước 2.4.

### Cài Docker trên cả 3 máy

```bash
# Chạy trên MỖI máy
sudo apt-get update && sudo apt-get install -y docker.io curl git
sudo systemctl enable docker && sudo systemctl start docker
sudo usermod -aG docker $USER && newgrp docker
docker --version   # phải >= 24
```

### Mở firewall giữa 3 máy

```bash
# Chạy trên cả 3 máy
sudo ufw allow 2377/tcp   # Swarm management
sudo ufw allow 7946/tcp   # Node communication
sudo ufw allow 7946/udp
sudo ufw allow 4789/udp   # Overlay network
sudo ufw allow 9100/tcp   # node-exporter (Prometheus scrape)
sudo ufw allow 80/tcp     # Hybrid Router (public entry point)
```

---

## PHASE 1 — Chuẩn bị source code

### 1.1 Clone repo lên Machine 1

```bash
git clone https://github.com/huanvt2302/ai-service.git
cd ai-service
```

### 1.2 Tạo file `.env`

```bash
cp .env.example .env
nano .env
```

Fill in các giá trị bắt buộc:

```env
# ── Core (BẮT BUỘC) ──────────────────────────────────────────────────────
# Tạo bằng: openssl rand -hex 32
JWT_SECRET=<random-hex-32>
NEXTAUTH_SECRET=<random-hex-32>
DB_PASSWORD=<strong-password>
HF_TOKEN=hf_xxxx              # Lấy tại: huggingface.co/settings/tokens

# ── IPs thực của 3 máy ────────────────────────────────────────────────────
MACHINE1_IP=192.168.1.10
MACHINE2_IP=192.168.1.11
MACHINE3_IP=192.168.1.12

# ── Local Docker Registry (chạy trên Machine 1, port 5000) ───────────────
REGISTRY=192.168.1.10:5000
TAG=latest

# ── Burst settings (mặc định OK cho lần đầu) ─────────────────────────────
BURST_THRESHOLD=70            # burst sang cloud khi CPU > 70%
SCALE_DOWN_THRESHOLD=40       # về local khi CPU < 40%
CLOUD_BACKEND_URL=            # để trống, điền sau Phase 4
```

> **Tạo secret ngẫu nhiên:**
> ```bash
> openssl rand -hex 32
> ```

### 1.3 Cập nhật Prometheus với IP thực

Mở `monitoring/prometheus.yml`, sửa phần `node-exporter`:

```yaml
- job_name: "node-exporter"
  static_configs:
    - targets:
        - "192.168.1.10:9100"   # Machine 1 thực
        - "192.168.1.11:9100"   # Machine 2 thực
        - "192.168.1.12:9100"   # Machine 3 thực
```

---

## PHASE 2 — Khởi tạo Docker Swarm

### 2.1 Init Manager (Machine 1)

```bash
cd ~/ai-service
bash scripts/setup-swarm.sh manager
```

Output sẽ in ra join token — **copy lại**:

```
══════════════════════════════════════════════════
  🎉 Manager node ready!

  Run this command on WORKER machines:

    docker swarm join --token SWMTKN-1-xxxx 192.168.1.10:2377
══════════════════════════════════════════════════
```

### 2.2 Join Worker (Machine 2 và Machine 3)

SSH vào từng máy rồi chạy:

```bash
# Thay TOKEN và IP thực của Machine 1
bash scripts/setup-swarm.sh worker SWMTKN-1-xxxx 192.168.1.10
```

### 2.3 Verify cluster (Machine 1)

```bash
docker node ls
```

Kết quả mong đợi:
```
ID            HOSTNAME   STATUS  AVAILABILITY  MANAGER STATUS
abc123 *      machine1   Ready   Active        Leader
def456        machine2   Ready   Active
ghi789        machine3   Ready   Active
```

### 2.4 Label GPU nodes

```bash
# Machine 1 — thay hostname thực của machine 2 và 3
bash scripts/setup-swarm.sh label-gpu machine2
bash scripts/setup-swarm.sh label-gpu machine3

# Verify
docker node inspect machine2 --pretty | grep gpu
# → Labels: gpu=true
```

> **Không có GPU?** Sửa `docker-compose.swarm.yml`:
> ```yaml
> vllm:
>   command: >
>     --model Qwen/Qwen2.5-3B-Instruct
>     --served-model-name qwen3.5-plus
>     --host 0.0.0.0 --port 8000
>     --device cpu --dtype float32   # ← thêm 2 flag này
>   deploy:
>     placement:
>       constraints:
>         - node.role == worker
>         # Xóa dòng: - node.labels.gpu == "true"
> ```

---

## PHASE 3 — Build và Deploy Stack

### 3.1 Build tất cả Docker images (Machine 1)

```bash
bash scripts/setup-swarm.sh build

# Lần đầu: ~10-20 phút (download base images)
# Output:
#   Building backend → 192.168.1.10:5000/backend:latest ✓
#   Building frontend → 192.168.1.10:5000/frontend:latest ✓
#   Building hybrid-router → 192.168.1.10:5000/hybrid-router:latest ✓
#   Building burst-controller → 192.168.1.10:5000/burst-controller:latest ✓
```

### 3.2 Deploy toàn bộ stack

```bash
bash scripts/setup-swarm.sh deploy

# Verify
docker service ls
```

Kết quả mong đợi:

```
NAME                          REPLICAS   IMAGE
ai-platform_backend           4/4        ...backend:latest
ai-platform_frontend          2/2        ...frontend:latest
ai-platform_hybrid-router     1/1        ...hybrid-router:latest
ai-platform_burst-controller  1/1        ...burst-controller:latest
ai-platform_vllm              2/2        vllm/vllm-openai:latest
ai-platform_worker            4/4        ...backend:latest
ai-platform_postgres          1/1        pgvector/pgvector:pg16
ai-platform_redis             1/1        redis:7-alpine
ai-platform_node-exporter     3/3        prom/node-exporter:latest  ← global mode
ai-platform_prometheus        1/1        prom/prometheus:latest
ai-platform_grafana           1/1        grafana/grafana:latest
```

### 3.3 Chạy DB migrations

```bash
docker exec $(docker ps -q -f name=ai-platform_backend) \
  alembic upgrade head
```

### 3.4 Kiểm tra hệ thống

```bash
# Router status
curl http://192.168.1.10/router/status
# {"mode":"local","local_cpu_percent":12.3,"is_bursting":false,"cloud_configured":false}

# Backend API
curl http://192.168.1.10/health
# {"status":"ok"}

# Frontend (trình duyệt)
open http://192.168.1.10:3000
```

> ✅ **Tới đây hệ thống đã chạy hoàn toàn trên local!**
> Phase 4 (Cloud Burst) là tùy chọn — thêm khi cần overflow.

---

## PHASE 4 — GCP Cloud Burst (Tùy chọn)

> Bỏ qua nếu chỉ muốn chạy local. Thực hiện Phase 4 khi traffic vượt quá khả năng 3 máy.

### 4.1 Cài gcloud CLI trên Machine 1

```bash
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
  gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg

echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] \
  https://packages.cloud.google.com/apt cloud-sdk main" | \
  sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list

sudo apt-get update && sudo apt-get install -y google-cloud-cli

# Đăng nhập
gcloud auth login
```

### 4.2 Thêm GCP config vào `.env`

```env
GCP_PROJECT=your-project-id    # tạo tại console.cloud.google.com
GCP_REGION=asia-southeast1     # Singapore — gần VN nhất
GCP_REGION_GPU=us-central1     # GPU hiện available tại đây
BURST_MIN_INSTANCES=2
CLOUD_RUN_SERVICES=ai-backend,ai-vllm
```

### 4.3 Chạy GCP setup (một lần duy nhất)

```bash
bash scripts/burst-gcp.sh all
```

Script tự động (~15-20 phút):

```
✓ Enable GCP APIs
✓ Tạo Artifact Registry
✓ Tạo Service Account (roles: run.admin, sql.client, storage.objectAdmin)
✓ Tạo Cloud SQL PostgreSQL 16 + pgvector
✓ Tạo Memorystore Redis 7
✓ Tạo GCS buckets (uploads, hf-cache)
✓ Lưu secrets → Secret Manager
✓ Build & push images → Artifact Registry
✓ Deploy ai-backend → Cloud Run (min=0, max=20)
✓ Deploy ai-vllm GPU → Cloud Run (min=0, max=20, NVIDIA L4)
```

Output cuối:

```
✅ Cloud Run deployment complete!

Backend URL: https://ai-backend-abc123-as.a.run.app

👉 Add to your local .env:
   CLOUD_BACKEND_URL=https://ai-backend-abc123-as.a.run.app
```

### 4.4 Kích hoạt Hybrid Burst Routing

```bash
CLOUD_URL=https://ai-backend-abc123-as.a.run.app

# Update Hybrid Router
docker service update \
  --env-add CLOUD_BACKEND_URL=$CLOUD_URL \
  ai-platform_hybrid-router

# Verify
curl http://192.168.1.10/router/status
# {"mode":"local","cloud_configured":true,...}
```

---

## PHASE 5 — Test burst hoạt động

```bash
# Terminal 1: theo dõi realtime
watch -n 2 'curl -s http://192.168.1.10/router/status | python3 -m json.tool'

# Terminal 2: giả lập CPU cao
sudo apt-get install -y stress
stress --cpu 8 --timeout 60

# Sau ~30 giây, Terminal 1 sẽ đổi:
# "mode": "cloud"
# "is_bursting": true
# "local_cpu_percent": 85.2
```

Xem Burst Controller logs:

```bash
docker service logs -f ai-platform_burst-controller

# [WARNING] CPU HIGH 82.3% → BURST UP
# OK: service=ai-backend min-instances=2
# OK: service=ai-vllm min-instances=2

# (Sau khi CPU giảm ~60 giây)
# [INFO] CPU LOW 22.1% → SCALE DOWN
# OK: service=ai-backend min-instances=0   ← $0 cost
```

---

## 🔄 Vận hành thường ngày

### Deploy code mới (rolling update, zero downtime)

```bash
cd ~/ai-service
git pull

# Rebuild service cần update (ví dụ: backend)
docker build -t $REGISTRY/backend:latest ./backend
docker push $REGISTRY/backend:latest

# Rolling update
docker service update \
  --image $REGISTRY/backend:latest \
  ai-platform_backend
```

### Xem logs

```bash
docker service logs -f ai-platform_backend
docker service logs -f ai-platform_hybrid-router
docker service logs -f ai-platform_burst-controller
```

### Thay đổi burst threshold

```bash
# Burst sớm hơn (60% thay vì 70%)
docker service update --env-add BURST_THRESHOLD=60 ai-platform_hybrid-router
docker service update --env-add BURST_THRESHOLD=60 ai-platform_burst-controller
```

### Scale replicas thủ công

```bash
docker service scale ai-platform_backend=8
docker service scale ai-platform_worker=8
```

### Kiểm tra trạng thái stack

```bash
bash scripts/setup-swarm.sh verify
docker stack ps ai-platform
bash scripts/burst-gcp.sh status   # Cloud Run services
```

---

## 📊 Endpoints tham chiếu

| URL | Mô tả |
|---|---|
| `http://MACHINE1_IP:3000` | Frontend UI |
| `http://MACHINE1_IP/router/status` | Routing mode + CPU % realtime |
| `http://MACHINE1_IP/router/reset` | Reset circuit breaker (POST) |
| `http://MACHINE1_IP:8080/docs` | FastAPI Swagger UI |
| `http://MACHINE1_IP:9090` | Prometheus |
| `http://MACHINE1_IP:3001` | Grafana (admin / admin) |

---

## 🆘 Troubleshooting

| Vấn đề | Lệnh debug |
|---|---|
| Service không start | `docker service ps ai-platform_backend --no-trunc` |
| Node unreachable | `sudo ufw status` — port 2377/7946/4789 phải ALLOW |
| CPU metric lỗi | `curl http://MACHINE1:9100/metrics | grep node_cpu` |
| Burst không trigger | `docker service logs ai-platform_burst-controller` |
| Toàn traffic đi cloud | `curl -X POST http://MACHINE1/router/reset` (reset circuit breaker) |
| Cloud Run lỗi | `bash scripts/burst-gcp.sh status` |
| vLLM không load model | Kiểm tra `HF_TOKEN` trong `.env` + disk space |

---

## 📎 Tài liệu liên quan

- [Architecture Overview](./architecture.md) — Sơ đồ kiến trúc đầy đủ
- [System Design](./system-design.md) — Quy tắc component + chiến lược scaling
- [API Spec](./api-spec.md) — Tất cả endpoints
- [Changelog](./changelog.md) — Lịch sử thay đổi

---

> **Lần đầu setup:** ~1-2 giờ (bao gồm cả Phase 4 GCP)
> **Update sau này:** ~5 phút
