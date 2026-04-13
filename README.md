# NeuralAPI — Multi-Tenant AI Platform

> **Hybrid Local-First + GCP Cloud Burst** — Runs on your own machines. Automatically scales to Google Cloud Run when local resources are overwhelmed.

---

## ✨ What is this?

A production-ready, **multi-tenant AI platform** modeled after the OpenAI Console. It provides LLM API access, RAG pipelines, AI Agents, usage analytics, and billing — all behind a FastAPI gateway.

**Deployment modes:**

| Mode | Description |
|---|---|
| 🖥️ **Local single node** | `docker compose up` — development, quick start |
| 🐝 **Local Swarm cluster** | 3-machine Docker Swarm — production primary |
| ☁️ **Hybrid burst** | Swarm + GCP Cloud Run — auto-scales to cloud when CPU > 70% |

---

## 🏗️ Architecture

```
                        INTERNET / CLIENTS
                               │
                               ▼
                    ┌─────────────────────┐
                    │    HYBRID ROUTER     │  ← Routes LOCAL or CLOUD
                    │   (CPU-based, auto)  │    based on Prometheus metrics
                    └──────┬──────────┬───┘
                           │          │
               CPU < 70%   │          │  CPU ≥ 70%
                           ▼          ▼
              LOCAL SWARM CLUSTER     GCP CLOUD RUN
              (3 machines)            (min=0, max=20, serverless)
              ┌────────────────┐      ┌──────────────────────────┐
              │ backend  ×4    │      │ ai-backend   (Cloud Run) │
              │ vllm (GPU) ×2  │      │ ai-vllm GPU  (Cloud Run) │
              │ rq-worker ×4   │      └──────────────────────────┘
              │ postgres       │
              │ redis          │        ┌────────────────────────┐
              │ prometheus     │   ←──  │  BURST CONTROLLER      │
              │ grafana        │        │  gcloud auto-scaler    │
              └────────────────┘        └────────────────────────┘
```

**Key component:** When local CPU stays above 70% for 30 seconds, the **Burst Controller** calls `gcloud run services update --min-instances=2` to pre-warm Cloud Run, and the **Hybrid Router** automatically starts directing new traffic there. When CPU drops below 40% for 60 seconds, Cloud Run scales back to zero — **$0 cloud cost when idle**.

---

## 🚀 Quick Start

### Option 1 — Single Node (development)

```bash
cp .env.example .env
# Fill in JWT_SECRET, HF_TOKEN (required)

docker compose up
```

| Service | URL |
|---|---|
| Frontend UI | http://localhost:3000 |
| Backend API | http://localhost:8080/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin/admin) |

### Option 2 — Local development (no Docker)

```bash
# Start infra
docker compose up postgres redis -d

# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # fill in values
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Frontend
cd ../frontend
npm install
npm run dev   # → http://localhost:3000
```

### Option 3 — 3-Machine Docker Swarm (production)

```bash
# Machine 1 (Manager) — init cluster
bash scripts/setup-swarm.sh manager

# Machine 2 & 3 (Workers) — join with token from step above
bash scripts/setup-swarm.sh worker <TOKEN> <MACHINE1_IP>

# Machine 1 — label GPU nodes, build images, deploy
bash scripts/setup-swarm.sh label-gpu <machine2-hostname>
bash scripts/setup-swarm.sh label-gpu <machine3-hostname>
bash scripts/setup-swarm.sh build
bash scripts/setup-swarm.sh deploy

# Check status
docker service ls
curl http://machine1/router/status
```

### Option 4 — Enable GCP Cloud Burst

```bash
# Prerequisites: gcloud CLI installed, authenticated, GCP_PROJECT set in .env

# Full GCP setup (one-time)
bash scripts/burst-gcp.sh all

# The script outputs the Cloud Run URL — set it in your Swarm:
docker service update \
  --env-add CLOUD_BACKEND_URL=https://ai-backend-xxx-as.a.run.app \
  ai-platform_hybrid-router
```

---

## 📦 Services

### Local Swarm Stack (`docker-compose.swarm.yml`)

| Service | Port | Role | Placement |
|---|---|---|---|
| `hybrid-router` | 80 | CPU-based request router (local ↔ cloud) | Manager |
| `burst-controller` | — | GCP Cloud Run auto-scaler daemon | Manager |
| `backend` | 8080 | FastAPI API gateway | Workers ×4 |
| `worker` | — | RQ document ingestion | Workers ×4 |
| `vllm` | 8000 | LLM inference (qwen3.5-plus) | GPU Workers ×2 |
| `frontend` | 3000 | Next.js UI | Workers |
| `postgres` | 5432 | PostgreSQL + pgvector | Manager |
| `redis` | 6379 | Rate limit + task queue | Manager |
| `node-exporter` | 9100 | Host CPU metrics (all nodes) | Global |
| `prometheus` | 9090 | Metrics collection | Manager |
| `grafana` | 3001 | Dashboards | Manager |

### GCP Cloud Run (Burst Layer)

| Service | Instances | Role |
|---|---|---|
| `ai-backend` | min=0, max=20 | Overflow API gateway |
| `ai-vllm` | min=0, max=20 | Overflow LLM inference (NVIDIA L4 GPU) |

---

## 🔧 API (OpenAI Compatible)

```bash
# Chat completion
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.5-plus","messages":[{"role":"user","content":"Hello"}]}'

# Embeddings
curl -X POST http://localhost:8080/v1/embeddings \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello world","model":"text-embedding-3-small"}'
```

### Hybrid Router Status

```bash
# Check real-time routing mode and CPU %
curl http://machine1/router/status
# {
#   "mode": "local",           ← "cloud" when bursting
#   "local_cpu_percent": 42.1,
#   "is_bursting": false,
#   "circuit_open": false,
#   "cloud_configured": true
# }

# Reset circuit breaker manually
curl -X POST http://machine1/router/reset
```

---

## ⚙️ Configuration

Copy `.env.example` → `.env` and fill in required values.

### Core

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET` | ✅ | JWT signing key — change in production |
| `HF_TOKEN` | ✅ | HuggingFace token for vLLM model download |
| `DB_PASSWORD` | ✅ (Swarm) | PostgreSQL password for Swarm deployment |
| `NEXTAUTH_SECRET` | ✅ | NextAuth session secret |

### Hybrid Cloud Burst

| Variable | Default | Description |
|---|---|---|
| `BURST_THRESHOLD` | `70` | CPU % that triggers cloud routing |
| `SCALE_DOWN_THRESHOLD` | `40` | CPU % to return to local-only routing |
| `CLOUD_BACKEND_URL` | _(empty)_ | Cloud Run backend URL — leave empty to disable cloud |
| `GCP_PROJECT` | — | GCP project ID |
| `GCP_REGION` | `asia-southeast1` | GCP region for Cloud Run |
| `BURST_MIN_INSTANCES` | `2` | Cloud Run min-instances when bursting |
| `MACHINE1_IP` | — | Manager node IP (for node-exporter targets) |
| `MACHINE2_IP` | — | Worker node 2 IP |
| `MACHINE3_IP` | — | Worker node 3 IP |

---

## 📊 Feature Modules

| Module | Path | Description |
|---|---|---|
| Dashboard | `/dashboard` | KPIs, charts, activity feed |
| API Keys | `/keys` | Create/revoke API keys (sk-xxx) |
| Usage | `/usage` | Token analytics with charts |
| AI Agents | `/agents` | Build custom AI agents with memory |
| RAG | `/rag` | Collections + document upload + vector search |
| Billing | `/billing` | Quota meters + plan management |
| Teams | `/teams` | Multi-tenant workspace |
| Webhooks | `/webhooks` | Event notifications |
| API Docs | `/docs` | Interactive Swagger UI |

---

## 🗄️ Database

PostgreSQL 16 + pgvector. 11 tables:

```
teams          users          api_keys
usage_logs     agents         agent_messages
collections    documents      document_chunks   ← vector(1536) embeddings
subscriptions  webhooks
```

Run migrations:

```bash
cd backend && alembic upgrade head
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, Tailwind CSS, Recharts, next-themes |
| **Backend** | FastAPI, SQLAlchemy, Alembic, pyjwt, passlib |
| **LLM Serving** | vLLM (qwen3.5-plus), OpenAI-compatible API |
| **Hybrid Routing** | Custom FastAPI proxy + Prometheus CPU metrics |
| **Cloud Burst** | GCP Cloud Run (GPU), gcloud CLI |
| **Orchestration** | Docker Swarm (local cluster) |
| **Database** | PostgreSQL 16 + pgvector (IVFFlat cosine search) |
| **Queue** | Redis + RQ (document ingestion workers) |
| **Auth** | JWT HS256 + bcrypt + API key SHA-256 |
| **Monitoring** | Prometheus + Grafana + node-exporter |

---

## 📁 Project Structure

```
ai-service/
├── backend/                  # FastAPI gateway
│   ├── routes/               # API route handlers
│   ├── workers/              # RQ background workers
│   ├── serve/                # vLLM deployment (legacy, ref only)
│   ├── models.py             # SQLAlchemy models
│   └── Dockerfile
├── frontend/                 # Next.js 14 dashboard
├── hybrid-router/            # CPU-based local↔cloud proxy
│   ├── main.py
│   └── Dockerfile
├── burst-controller/         # GCP Cloud Run auto-scaler
│   ├── controller.py
│   └── Dockerfile
├── monitoring/
│   └── prometheus.yml        # Scrape configs (node-exporter on all nodes)
├── scripts/
│   ├── setup-swarm.sh        # Swarm cluster bootstrap
│   └── burst-gcp.sh          # GCP infrastructure + Cloud Run deploy
├── docs/
│   ├── architecture.md       # Full system architecture
│   ├── system-design.md      # Component responsibilities + scaling
│   ├── api-spec.md           # API reference
│   └── changelog/            # Per-task changelog files
├── docker-compose.yml        # Single-node dev stack
├── docker-compose.swarm.yml  # 3-machine production Swarm stack
└── .env.example              # All configuration options documented
```

---

## 📖 Documentation

| Doc | Description |
|---|---|
| [Architecture](./docs/architecture.md) | High-level diagrams, service inventory, hybrid topology |
| [System Design](./docs/system-design.md) | Component rules, scaling strategy, failure handling |
| [Setup Guide](./docs/setup-server.md) | Step-by-step server setup (Swarm + GCP Cloud Burst) |
| [API Spec](./docs/api-spec.md) | All endpoints with request/response examples |
| [Changelog](./docs/changelog.md) | Per-task change history |
| [Roadmap](./docs/roadmap.md) | Planned features by version |
