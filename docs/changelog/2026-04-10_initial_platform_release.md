# 2026-04-10 — Initial Platform Release (v1.0.0)

**Version:** 1.0.0  
**Type:** Feature  
**Scope:** Infrastructure, Backend, Frontend, Documentation

---

## Summary

Initial release of the NeuralAPI AI Platform — a full-stack multi-tenant platform with LLM gateway, RAG pipeline, agent builder, usage analytics, and billing.

---

## Added

### Infrastructure
* `docker-compose.yml` — 8 services: postgres+pgvector, redis, ray, vllm, prometheus, grafana, backend, frontend
* `.env.example` — all required environment variables
* `monitoring/prometheus.yml` — Prometheus scrape config

### Backend (FastAPI)
* `main.py` — FastAPI app with CORS, Prometheus metrics middleware, all routers
* `models.py` — 9 SQLAlchemy models: `Team`, `User`, `ApiKey`, `UsageLog`, `Agent`, `AgentMessage`, `Collection`, `Document`, `DocumentChunk`, `Subscription`, `Webhook`
* `auth.py` — JWT (HS256, 60-min), bcrypt, SHA-256 API key hashing, Redis sliding-window rate limiter
* `metrics.py` — Prometheus counters: `api_request_total`, `api_request_latency_seconds`, `llm_tokens_total`, `embedding_requests_total`, `rag_search_latency_seconds`
* `config.py` — pydantic-settings env config
* `database.py` — SQLAlchemy engine + `get_db()` dependency
* `alembic/versions/0001_initial.py` — all tables + enums + pgvector IVFFlat index (cosine, 100 lists)

### API Routes
* `POST /auth/register` — team + user creation, returns JWT
* `POST /auth/login` — bcrypt verify, returns JWT
* `GET /auth/me` — current user profile
* `GET /v1/keys` — list team API keys
* `POST /v1/keys` — create API key
* `DELETE /v1/keys/{id}` — revoke API key
* `GET /v1/models` — list available LLM models
* `POST /v1/chat/completions` — OpenAI-compatible chat with SSE streaming
* `POST /v1/embeddings` — vector embedding generation
* `POST /v1/convert/markdown` — file-to-markdown
* `POST /v1/memchat/completions` — chat with persistent memory
* `GET /v1/messages` — conversation history
* `GET/POST /v1/collections` — RAG collection CRUD
* `GET/DELETE /v1/collections/{id}` — get / delete collection
* `POST /v1/collections/{id}/search` — pgvector cosine semantic search
* `POST /v1/documents` — file upload + RQ enqueue
* `GET/DELETE /v1/documents/{id}` — status / delete document
* `GET /v1/usage/summary` — analytics (daily, by-service, quota)
* `GET /v1/usage/logs` — paginated request log
* `GET /v1/billing/quota` — quota per service
* `POST /v1/billing/upgrade` — plan upgrade
* `GET/POST /v1/agents` — agent CRUD
* `GET/PUT/DELETE /v1/agents/{id}` — agent get / update / delete
* `GET/POST /v1/webhooks` — webhook CRUD
* `DELETE /v1/webhooks/{id}` — delete webhook
* `GET /v1/teams/current` — team info + members
* `PATCH /v1/teams/current` — update team name
* `GET /health` — health check
* `GET /metrics` — Prometheus metrics

### Workers
* `workers/document_worker.py` — RQ worker: read file → chunk (512w/64overlap) → embed via vLLM → store `DocumentChunk` + `vector(1536)`

### Ray Serve
* `serve/vllm_deployment.py` — `VLLMDeployment` (autoscale 1–4 replicas) + `EmbeddingDeployment` (sentence-transformers)

### Frontend (Next.js 14)
* `app/globals.css` — dark mode tokens, brand gradient, glassmorphism, animations
* `tailwind.config.ts` — brand colors, Inter + JetBrains Mono fonts
* `lib/api.ts` — typed API client
* `lib/auth-context.tsx` — AuthProvider (JWT, login/register/logout)
* `lib/utils.ts` — `cn()`, `formatNumber()`, `formatBytes()`, `pct()`, `relativeTime()`
* `components/sidebar.tsx` — 11-item sidebar, dark mode toggle, user info
* `components/theme-provider.tsx` — next-themes wrapper

### Pages
* `/login`, `/register`
* `/dashboard` — KPI cards, AreaChart, quota bars, activity feed
* `/keys` — create/revoke API keys
* `/usage` — 4 Recharts (area, bar, line, donut), log table
* `/agents` — agent builder form + card grid
* `/rag` — collections, document upload, semantic search
* `/billing` — quota meters, plan upgrade cards
* `/teams` — members + roles + token usage
* `/webhooks` — create + event-chip selector
* `/docs` — interactive API reference with curl examples
* `/data`, `/stt-tts` — placeholders

### Documentation
* `README.md` — architecture, quick start, service table

---

## Files Changed
- `docker-compose.yml` (new)
- `backend/**` (new — all backend files)
- `frontend/**` (new — all frontend files)
- `monitoring/prometheus.yml` (new)
- `.env.example` (new)
- `README.md` (new)
