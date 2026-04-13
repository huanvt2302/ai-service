# Architecture — NeuralAPI AI Platform

**Version:** 1.1.0  
**Last Updated:** 2026-04-13  
**Status:** Active

---

## 1. High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT TIER                                         │
│                                                                                │
│   Browser / SDK / External App                                                 │
│   ┌───────────────────────────────────┐  ┌──────────────────────────────────┐ │
│   │   Next.js 14 Console UI           │  │  External API Consumer           │ │
│   │   (App Router, dark mode,         │  │  (uses x-api-key header)         │ │
│   │    Recharts, shadcn-style UI)      │  │                                  │ │
│   └──────────────┬────────────────────┘  └──────────────┬───────────────────┘ │
└──────────────────┼─────────────────────────────────────┼────────────────────-─┘
                   │ JWT Bearer                           │ x-api-key
                   ▼                                      ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY TIER                                      │
│                                                                                │
│   FastAPI (Python 3.11)   port 8080                                            │
│   ┌────────────────────────────────────────────────────────────────────────┐   │
│   │  Middleware Stack (top → bottom)                                       │   │
│   │  1. CORS Middleware                                                    │   │
│   │  2. Prometheus MetricsMiddleware  (records latency, token counts)      │   │
│   │  3. JWT / API-Key Auth            (validates on every request)         │   │
│   │  4. Rate Limit Check              (Redis sliding window per api_key)   │   │
│   │  5. Quota Enforcement             (blocks if tokens_used ≥ quota)      │   │
│   │  6. Usage Logger                  (writes usage_logs row on response)  │   │
│   └────────────┬───────────────────────────────────────────────────────────┘   │
│                │                                                                │
│   ┌────────────▼─────────────────────────────────────────────────────────────┐ │
│   │  Route Modules                                                           │ │
│   │  /auth  /v1/keys  /v1/chat  /v1/embeddings  /v1/collections             │ │
│   │  /v1/documents  /v1/agents  /v1/usage  /v1/billing  /v1/webhooks        │ │
│   │  /v1/teams  /v1/memchat  /v1/messages  /v1/convert  /metrics /health    │ │
│   └──────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────┘
                   │                           │                   │
      ┌────────────▼───────────┐  ┌───────────▼──────┐  ┌────────▼─────────────┐
      │  DATA TIER              │  │  QUEUE TIER       │  │  MONITORING TIER     │
      │                         │  │                   │  │                      │
      │  PostgreSQL 16          │  │  Redis 7          │  │  Prometheus (9090)   │
      │   + pgvector extension  │  │  ┌─────────────┐ │  │  Grafana     (3001)  │
      │                         │  │  │ Rate-limit  │ │  │                      │
      │  Tables:                │  │  │ sorted sets │ │  │  Scraped from:       │
      │  - teams                │  │  └─────────────┘ │  │  - backend /metrics  │
      │  - users                │  │  ┌─────────────┐ │  │  - ray /metrics      │
      │  - api_keys             │  │  │ RQ task     │ │  │  - redis exporter    │
      │  - usage_logs           │  │  │ queue       │ │  │                      │
      │  - agents               │  │  └──────┬──────┘ │  └──────────────────────┘
      │  - agent_messages       │  └─────────┼────────┘
      │  - collections          │            │
      │  - documents            │  ┌─────────▼────────────────────────────────┐
      │  - document_chunks      │  │  WORKER TIER                             │
      │    (vector(1536))       │  │                                          │
      │  - subscriptions        │  │  RQ Worker Process                       │
      │  - webhooks             │  │  ┌───────────────────────────────────┐   │
      └─────────────────────────┘  │  │ document_worker.py                │   │
                                   │  │ 1. Read uploaded file             │   │
                                   │  │ 2. Chunk text (512w, 64 overlap)  │   │
                                   │  │ 3. Call vLLM /v1/embeddings       │   │
                                   │  │ 4. Store DocumentChunk + vector   │   │
                                   │  │ 5. Update Document.status = done  │   │
                                   │  └───────────────────────────────────┘   │
                                   └──────────────────────────────────────────┘
                                                    │
                                   ┌────────────────▼─────────────────────────┐
                                   │  LLM SERVING TIER                        │
                                   │                                          │
                                   │  Ray Serve (port 8001 / 8265 dashboard)  │
                                   │  ┌──────────────────────────────────┐    │
                                   │  │ VLLMDeployment                   │    │
                                   │  │  - wraps vLLM OpenAI server      │    │
                                   │  │  - autoscales: 1 → 4 replicas    │    │
                                   │  │  - target: 10 req/replica        │    │
                                   │  └──────────────────────────────────┘    │
                                   │  ┌──────────────────────────────────┐    │
                                   │  │ EmbeddingDeployment              │    │
                                   │  │  - sentence-transformers         │    │
                                   │  │  - dim: 384 / 1536 depending     │    │
                                   │  │    on configured model           │    │
                                   │  └──────────────────────────────────┘    │
                                   │                                          │
                                   │  llama.cpp Server (port 8080, host :11434)       │
                                   │   image: ghcr.io/ggerganov/llama.cpp:server       │
                                   │   model: Qwen2.5-3B-Instruct-Q4_K_M.gguf         │
                                   │   served as: qwen3.5-plus (CPU / macOS ARM64)     │
                                   └──────────────────────────────────────────────────┘
```

---

## 2. Services Inventory

### Local Cluster Services (Docker Swarm)

| Service | Language | Port | Role | Placement |
|---|---|---|---|---|
| `hybrid-router` | Python / FastAPI | 80 | CPU-based request router (local ↔ cloud) | Manager |
| `burst-controller` | Python / asyncio | — | GCP Cloud Run auto-scaler daemon | Manager |
| `frontend` | Next.js 14 / TypeScript | 3000 | Console UI | Workers |
| `backend` | Python / FastAPI | 8080 | API Gateway + business logic | Workers (×4) |
| `worker` | Python / RQ | — | Document ingestion background jobs | Workers (×4) |
| `model-downloader` | Python / huggingface_hub | — | Init container: download GGUF model on first start | Workers |
| `llama-cpp` | ghcr.io/ggerganov/llama.cpp | 11434→8080 | LLM serving — OpenAI-compatible (llama.cpp server) | Workers |
| `postgres` | pgvector/pgvector:pg16 | 5432 | Relational DB + vector store | Manager |
| `redis` | redis:7-alpine | 6379 | Rate limiting + task queue + cache | Manager |
| `node-exporter` | prom/node-exporter | 9100 | Host CPU/memory metrics (global) | All Nodes |
| `prometheus` | prom/prometheus | 9090 | Metrics collection | Manager |
| `grafana` | grafana/grafana | 3001 | Metrics visualization | Manager |

### GCP Cloud Run Services (Burst Layer)

| Service | Runtime | min→max | Role |
|---|---|---|---|
| `ai-backend` | Python / FastAPI | 0→20 | Overflow API Gateway when local CPU ≥ threshold |
| `ai-vllm` | vllm-openai / NVIDIA L4 | 0→20 | Overflow LLM inference when local CPU ≥ threshold |

---

## 3. Data Flow

### 3a. Chat Completion Flow

```
Client
  │
  │  POST /v1/chat/completions
  │  x-api-key: sk-xxx
  │
  ▼
FastAPI Gateway
  │
  ├─► [1] Validate x-api-key (SHA-256 lookup in api_keys table)
  ├─► [2] Redis rate limit check (sliding window, key=api_key.id)
  ├─► [3] Quota check (subscriptions.tokens_used < token_quota)
  │
  ├─► [4] HTTP/SSE proxy to vLLM   (VLLM_BASE_URL/v1/chat/completions)
  │        │
  │        ▼
  │       vLLM → generates tokens
  │        │
  │        └─► SSE chunks streamed back (if stream=true)
  │
  └─► [5] On response:
          - Write usage_logs row (input_tokens, output_tokens, latency_ms)
          - Increment subscriptions.tokens_used
          - Update api_keys.last_used_at
          - Emit Prometheus counters
```

### 3b. RAG Document Ingestion Flow

```
Client
  │  POST /v1/documents  (multipart: collection_id + file)
  ▼
FastAPI (routes/rag.py)
  │
  ├─► Validate JWT
  ├─► Validate collection ownership  (collection.team_id == user.team_id)
  ├─► Save file to disk  (/uploads/{uuid}.ext)
  ├─► Create Document row  (status=pending)
  └─► Enqueue RQ job  → redis queue "document_queue"

                ▼ (async)
RQ Worker (workers/document_worker.py)
  │
  ├─► Read file → extract text
  ├─► Chunk text (512 words, 64-word overlap)
  ├─► POST /v1/embeddings to vLLM  (batch)
  ├─► INSERT DocumentChunk rows  (content + embedding vector)
  ├─► UPDATE Document (status=done, chunk_count=N)
  └─► (on error) UPDATE Document (status=error, error_message=...)
```

### 3c. Auth Flow

```
[Register]                          [API Key Auth]
POST /auth/register                 x-api-key: sk-xxx
  → create Team                       → hash key (SHA-256)
  → create Subscription               → lookup api_keys.key_hash
  → create User (role=owner)          → check status=active
  → return JWT                        → check expiry
                                      → Redis rate limit
[Login]                               → return ApiKey object
POST /auth/login
  → bcrypt verify
  → return JWT

[Dashboard routes]
Authorization: Bearer <JWT>
  → jose.decode(JWT, secret)
  → lookup users.id = sub
  → attach user to request
```

---

## 4. Auth Layer

- **JWT**: HS256, 60-minute expiry, payload: `{sub: user_id, team_id, email}`
- **API Keys**: `sk-<urlsafe_b64>`, stored as SHA-256 hash, prefix shown in UI
- **Rate Limiting**: Redis sorted-set sliding window (default: 100 req/60s per key)
- **Quota**: Checked per request against `subscriptions.token_quota`

---

## 5. RAG Pipeline

```
Upload → Save → Chunk(512w/64overlap) → Embed(vLLM) → pgvector(IVFFlat)
                                                              │
Search:  Query → Embed → cosine_distance ORDER BY → top-k chunks returned
```

Vector index: `IVFFlat` with 100 lists on `embedding` column.  
Dimension: `vector(1536)` (configurable via `DEFAULT_EMBEDDING_MODEL`).

---

## 6. LLM Serving Layer

```
┌─────────────────────────────────────────────────────────┐
│  Ray Serve Cluster                                       │
│                                                          │
│  VLLMDeployment (route_prefix=/v1)                       │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│   │ Replica1 │  │ Replica2 │  │ Replica3 │  ... (max 4) │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│        └─────────────┴─────────────┘                     │
│                       │ proxies to                        │
│              vLLM Server (:8000)                          │
│              model: qwen3.5-plus                          │
└─────────────────────────────────────────────────────────┘
```

**Autoscaling policy**:  
- `min_replicas: 1`, `max_replicas: 4`  
- Scales up when `ongoing_requests_per_replica > 10`

---

## 7. Usage Tracking

Every routed request triggers `log_usage()` which:
1. Inserts a `usage_logs` row with `service`, `model`, `input_tokens`, `output_tokens`, `latency_ms`, `status_code`
2. Increments `subscriptions.tokens_used`
3. Emits `TOKEN_USAGE` Prometheus counter with labels `(model, type, team_id)`

Quota blocking happens **before** the LLM call. Usage recording happens **after**.

---

## 8. Billing

- Subscriptions are per-team, created at registration (plan=free)
- Quotas tracked: `token_quota`, `stt_quota`, `tts_quota`, `coding_quota`
- Plan upgrade via `POST /v1/billing/upgrade` — updates limits in-place (no Stripe yet)
- `billing_period_start` / `next_billing_date` tracked per subscription

---

## 9. Deployment Topology — Single Node (docker-compose)

For **local development** only. Use `docker-compose.yml` with `docker compose up`.

```
                    ┌── docker-compose network: ai_platform_net ──┐
  :3000 ◄── frontend                                               │
  :8080 ◄── backend ──► postgres:5432                              │
                    └─► redis:6379                                  │
  worker ──────────────► redis:6379 ◄── RQ jobs                    │
                         postgres:5432                              │
  llama-cpp ◄─ backend ──► :8080 (host :11434, alias qwen3.5-plus)   │
  model-downloader ──────► models_data volume (init, runs once)       │
  prometheus ──────────► backend:8080/metrics                      │
  grafana ─────────────► prometheus:9090                           │
                    └────────────────────────────────────────-─────┘
```

---

## 10. Hybrid Deployment Topology — Local Swarm + GCP Cloud Burst

For **production**. Uses `docker-compose.swarm.yml` with Docker Swarm across 3 machines.
Overflow traffic automatically routes to GCP Cloud Run when local CPU ≥ threshold.

```
╔══════════════════════════════════════════════════════════════════════╗
║                    INTERNET / CLIENTS                                 ║
╚════════════════════╤═════════════════════════════════════════════════╝
                     │ :80
                     ▼
╔══════════════════════════════════════════════════════════════════════╗
║         HYBRID ROUTER  (Machine 1 — Swarm Manager)                   ║
║                                                                       ║
║  ┌───────────────────────────────────────────────────────────────┐   ║
║  │ FastAPI Reverse Proxy                                         │   ║
║  │                                                               │   ║
║  │  Every 10s: avg_cpu = Prometheus query across 3 nodes        │   ║
║  │                                                               │   ║
║  │  avg_cpu < 70%  →  proxy → LOCAL backend (Swarm VIP :8080)  │   ║
║  │  avg_cpu ≥ 70%  →  proxy → CLOUD (GCP Cloud Run URL)        │   ║
║  │  3 local errors →  circuit-breaker → CLOUD                  │   ║
║  └───────────────────────────────────────────────────────────────┘   ║
╚══════════════╤══════════════════════════════════════╤════════════════╝
               │ LOCAL PATH (CPU < 70%)               │ BURST PATH (CPU ≥ 70%)
               ▼                                      ▼
╔══════════════════════════════╗   ╔════════════════════════════════════╗
║  LOCAL SWARM CLUSTER          ║   ║  GCP CLOUD RUN (Burst Layer)       ║
║                               ║   ║                                    ║
║  Machine 1 (Manager):         ║   ║  ai-backend                        ║
║  ├ postgres (primary)         ║   ║  min=0  max=20  CPU=2  RAM=2Gi    ║
║  ├ redis                      ║   ║                                    ║
║  ├ prometheus                 ║   ║  ai-vllm (NVIDIA L4 GPU)           ║
║  └ grafana                    ║   ║  min=0  max=20  CPU=4  RAM=16Gi   ║
║                               ║   ║                                    ║
║  Machine 2 (GPU Worker):      ║   ║  Shared Cloud SQL (pgvector)       ║
║  ├ backend ×2                 ║   ║  Shared Memorystore Redis          ║
║  ├ vllm (GPU)                 ║   ║  GCS file uploads                  ║
║  └ node-exporter              ║   ╚════════════════════════════════════╝
║                               ║              ▲
║  Machine 3 (GPU Worker):      ║              │ gcloud run services update
║  ├ backend ×2                 ║   ╔══════════╧═════════════════════════╗
║  ├ vllm (GPU)                 ║   ║  BURST CONTROLLER (Machine 1)      ║
║  ├ rq-worker ×4               ║   ║                                    ║
║  └ node-exporter              ║   ║  Poll Prometheus CPU every 10s    ║
║                               ║   ║  CPU > 70% for 30s → scale UP     ║
║  [node-exporter global:       ║   ║    min-instances = 2               ║
║   all machines → :9100]       ║   ║  CPU < 40% for 60s → scale DOWN   ║
╚══════════════════════════════╝   ║    min-instances = 0               ║
                                   ╚════════════════════════════════════╝
```

### Burst Decision Logic

```
CPU Timeline:

  30% ──────────────────┐                        ┌──────────── 30%
                        │ rises                  │ falls
  70% ─────────────────-┼──────────────────────--┼──────────── 70% (BURST_THRESHOLD)
                        │ [30s confirm]           │
                        └──────────── 85% ───────┘
                               BURSTING

Actions:
  CPU > 70% for 30s  →  BurstController: set min-instances=2
                      →  HybridRouter: new requests → Cloud Run
  CPU < 40% for 60s  →  BurstController: set min-instances=0
                      →  HybridRouter: new requests → Local
```

### Key Files

| File | Purpose |
|---|---|
| `docker-compose.swarm.yml` | Swarm stack (production) |
| `docker-compose.yml` | Single-node dev stack |
| `hybrid-router/main.py` | Routing logic + circuit breaker |
| `burst-controller/controller.py` | GCP Cloud Run auto-scaler |
| `scripts/setup-swarm.sh` | Cluster bootstrap script |
| `scripts/burst-gcp.sh` | GCP infrastructure + Cloud Run deploy |
| `monitoring/prometheus.yml` | Scrape configs (node-exporter on all nodes) |
