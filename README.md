# NeuralAPI — Full-Stack AI Platform

A multi-tenant AI platform modeled after the OpenAI Console, featuring LLM API access, RAG pipelines, AI Agents, usage analytics, and billing — all powered by a FastAPI gateway, Ray Serve + vLLM, PostgreSQL+pgvector, and Redis.

## Architecture

```
Next.js 14 Frontend (port 3000)
        ↓ HTTP / SSE
FastAPI Gateway (port 8080)   ←→  Redis (rate-limit + task queue)
        ↓                              ↓
PostgreSQL + pgvector          RQ Worker (document ingestion)
        ↓
Ray Serve → vLLM (qwen3.5-plus)
        ↓
Prometheus (port 9090) + Grafana (port 3001)
```

## Quick Start

### Option 1: Full Docker Compose (all services)

```bash
cp .env.example .env
# Edit .env if needed (set HF_TOKEN for model download)

docker compose up
# Access frontend at http://localhost:3000
```

### Option 2: Development (frontend only, no GPU needed)

```bash
# Start infrastructure:
docker compose up postgres redis -d

# Start backend:
cd backend
pip install -r requirements.txt
cp ../.env.example .env
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Start frontend:
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Option 3: With vLLM + Ray Serve

```bash
# Start everything including Ray + vLLM:
docker compose --profile vllm up

# Or start Ray Serve manually (requires GPU or CPU mode):
cd backend
python serve/vllm_deployment.py
```

## Services

| Service | URL | Description |
|---|---|---|
| Frontend | http://localhost:3000 | Next.js dashboard |
| Backend API | http://localhost:8080 | FastAPI gateway |
| API Docs | http://localhost:8080/docs | Swagger UI |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3001 | Dashboards (admin/admin) |
| Ray Dashboard | http://localhost:8265 | Ray cluster UI |

## Environment Variables

See `.env.example` for all configuration options.

Key vars:
- `VLLM_BASE_URL` — URL of the vLLM server (default: http://localhost:8000)
- `JWT_SECRET` — Change in production
- `HF_TOKEN` — HuggingFace token for model download
- `ENABLE_GPU` — Set `true` if GPU available for vLLM

## Feature Modules

| Module | Path | Description |
|---|---|---|
| Dashboard | `/dashboard` | KPIs, charts, activity feed |
| API Keys | `/keys` | Create/revoke API keys |
| Usage | `/usage` | Analytics with Recharts |
| AI Agents | `/agents` | Build custom AI agents |
| RAG | `/rag` | Collections + document upload + vector search |
| Billing | `/billing` | Quota meters + plan upgrade |
| Teams | `/teams` | Multi-tenant workspace |
| Webhooks | `/webhooks` | Event notifications |
| API Docs | `/docs` | Interactive API reference |

## API (OpenAI Compatible)

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

## Ray Serve Deployments

```bash
# Start Ray Serve with vLLM proxy + embedding deployment
python backend/serve/vllm_deployment.py

# Deployments:
# VLLMDeployment  → /v1  (autoscales 1-4 replicas)
# EmbeddingDeployment → /embeddings (sentence-transformers)
```

## Database

PostgreSQL + pgvector with 9 tables:
- `teams`, `users`, `api_keys`
- `usage_logs` (every API call logged)
- `agents`, `agent_messages`
- `collections`, `documents`, `document_chunks` (vectors)
- `subscriptions`, `webhooks`

Run migrations: `cd backend && alembic upgrade head`

## Tech Stack

- **Frontend**: Next.js 14, Tailwind CSS, Recharts, lucide-react, next-themes
- **Backend**: FastAPI, SQLAlchemy, Alembic, pyjwt, passlib
- **LLM**: vLLM (qwen3.5-plus), Ray Serve autoscaling
- **DB**: PostgreSQL 16 + pgvector (cosine similarity search)
- **Queue**: Redis + RQ (document ingestion workers)
- **Auth**: JWT (HS256) + bcrypt + API key (SHA-256 hash)
- **Monitoring**: Prometheus + Grafana
