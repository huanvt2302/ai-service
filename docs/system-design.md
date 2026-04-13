# System Design — NeuralAPI AI Platform

**Version:** 1.0.0  
**Last Updated:** 2026-04-10  
**Status:** Active

---

## 1. Component Responsibilities

### 1.1 Frontend (Next.js 14)

| Responsibility | Implementation |
|---|---|
| Authentication | JWT stored in `localStorage`, injected into every request via `lib/api.ts` |
| Auth guard | `(dashboard)/layout.tsx` — redirects unauthenticated users to `/login` |
| API communication | `lib/api.ts` — typed functions per resource |
| Theme | `next-themes` — dark/light mode persisted in localStorage |
| Charts | `recharts` — AreaChart, BarChart, LineChart, PieChart |
| Routing | App Router with route groups `(dashboard)` for layout nesting |

**Rules:**
- No inline API calls in page components — all calls go through `lib/api.ts`
- No business logic in components — components call API helpers only
- Auth token managed only in `lib/auth-context.tsx`

---

### 1.2 API Gateway (FastAPI)

| Responsibility | File |
|---|---|
| Request routing | `main.py` (includes all routers) |
| Auth validation | `auth.py` — `get_current_user()`, `get_current_team_from_api_key()` |
| Rate limiting | `auth.py` — `check_rate_limit()` using Redis sorted sets |
| Metrics export | `metrics.py` — Prometheus counters/histograms |
| Usage logging | `routes/gateway.py` — `log_usage()` called after every LLM request |
| Configuration | `config.py` — pydantic-settings, reads from `.env` |
| DB sessions | `database.py` — `get_db()` FastAPI dependency |

**Rules:**
- Business logic belongs in service functions, not route handlers
- Route handlers should be thin (validate → call service → return response)
- All DB access goes through SQLAlchemy session from `get_db()`
- Never store raw API keys — always store SHA-256 hash

---

### 1.3 Database (PostgreSQL + pgvector)

| Table | Owner | Access Pattern |
|---|---|---|
| `teams` | `routes/teams.py` | Read by team_id; rarely written |
| `users` | `routes/auth.py` | Read by email/id; written on register |
| `api_keys` | `routes/keys.py` | Scanned by key_hash on every API call |
| `usage_logs` | `routes/usage.py` | Append-only; read for analytics |
| `agents` | `routes/agents.py` | CRUD by team_id |
| `agent_messages` | `routes/gateway.py` | Append on each chat turn |
| `collections` | `routes/rag.py` | CRUD by team_id |
| `documents` | `routes/rag.py` | CRUD; status updated by worker |
| `document_chunks` | `workers/` | Insert by worker; read for vector search |
| `subscriptions` | `routes/billing.py` | Read/write on quota check |
| `webhooks` | `routes/webhooks.py` | CRUD |

**Indexing strategy:**
- `api_keys.key_hash` — unique index (hot path for every API call)
- `usage_logs.created_at` — B-Tree index (time-range queries)
- `users.email` — unique index
- `document_chunks.embedding` — IVFFlat (cosine, 100 lists)
- `agent_messages.contact_id` — B-Tree index

---

### 1.4 Redis

Two independent usage patterns:

**Rate Limiting** (sorted sets):
```
Key:   rate:{api_key_id}
Type:  Sorted Set
Score: Unix timestamp (float)
Value: Unix timestamp (string)
TTL:   window_seconds + 5

Algorithm:
  ZREMRANGEBYSCORE key 0 (now - window)   # remove old entries
  ZADD key now now                         # add current
  ZCARD key                                # count
  → allow if count ≤ limit
```

**Task Queue** (RQ):
```
Queue name:  document_queue
Job:         workers.document_worker.process_document(document_id)
Timeout:     300s
Retry:       default RQ retry (3x with backoff)
```

---

### 1.5 RQ Worker

Single worker process subscribing to `document_queue`.

Pipeline per document:
```
1. SELECT document WHERE id = $1
2. UPDATE document SET status = 'processing'
3. Read file from disk (doc.file_path)
4. Split into chunks (512 words, 64-word overlap)
5. POST /v1/embeddings  [batch if multiple chunks]
6. INSERT document_chunks (chunk_index, content, embedding)
7. UPDATE document SET status='done', chunk_count=N
   (or status='error', error_message=... on failure)
```

**Failure handling:** On exception, document status → `error`, message stored. Worker does not crash — moves to next job.

---

### 1.6 Ray Serve

Two named deployments started via `backend/serve/vllm_deployment.py`:

| Deployment | route_prefix | Backing | Replicas |
|---|---|---|---|
| `vllm` | `/v1` | vLLM OpenAI server at `:8000` | 1–4 (autoscale) |
| `embeddings` | `/embeddings` | sentence-transformers in-process | 1 (fixed) |

Autoscaling trigger: `target_num_ongoing_requests_per_replica = 10`

---

## 2. Scaling Strategy

### Horizontal Scaling

| Component | Strategy |
|---|---|
| FastAPI | Add more `backend` containers behind a load balancer |
| RQ Workers | Add more `worker` containers — all share the same Redis queue |
| Ray Serve replicas | Autoscale via Ray — increase `max_replicas` in `serve_config.yaml` |
| PostgreSQL | Read replicas for analytics queries (`/v1/usage/*`) |
| Redis | Redis Sentinel or Cluster for HA |

### Vertical Scaling Limits

| Component | Bottleneck | Mitigation |
|---|---|---|
| vLLM | GPU VRAM | Quantization (AWQ/GPTQ), tensor parallelism |
| pgvector | IVFFlat memory | Increase `lists`, use HNSW for larger datasets |
| PostgreSQL | connection count | PgBouncer connection pooling |

---

## 3. Caching Layer

| Cache Target | Location | TTL | Invalidation |
|---|---|---|---|
| Model list | Redis (planned) | 5 min | On model server restart |
| Team subscription | Redis (planned) | 30s | On billing update |
| JWT decode | In-process (jose) | Token expiry | — |
| API key lookup | In-process (planned LRU) | 60s | On revoke |

> **Current state:** Caching is not yet implemented for DB lookups. It is planned for v1.1. The hot-path `api_keys.key_hash` lookup hits the DB on every call. An LRU cache (128 entries, 60s TTL) is the recommended next step.

---

## 4. Rate Limiting Design

```
Algorithm:   Sliding Window (Redis sorted set)
Granularity: Per API key
Default:     100 requests / 60 seconds
Storage:     rate:{api_key_id} sorted set

Flow:
  1. Remove timestamps older than (now - window)
  2. Add current timestamp
  3. Count entries in window
  4. If count > limit → HTTP 429, do NOT call LLM
  5. If allowed → proceed (rate limit does NOT consume tokens)
```

Custom limits per key (planned v1.2): Store limit in `api_keys.rate_limit` column.

---

## 5. Multi-Tenant Design

Every resource is scoped to `team_id`:

```sql
-- All data access is team-scoped:
SELECT * FROM api_keys WHERE team_id = $1
SELECT * FROM usage_logs WHERE team_id = $1
SELECT * FROM agents WHERE team_id = $1
SELECT * FROM collections WHERE team_id = $1
SELECT * FROM subscriptions WHERE team_id = $1
```

**Isolation guarantees:**
- JWT payload contains `team_id` — no cross-team lookup possible via JWT auth
- API key carries `team_id` — all usage logged to that team
- All route handlers filter by `current_user.team_id` or `api_key.team_id`
- Agent memory (`agent_messages`) scoped by `agent_id` which is scoped to `team_id`
- RAG collections scoped to `team_id` — cross-team search is not possible

**No row-level security (RLS)** is used at DB level currently — isolation is enforced in application code. Adding PostgreSQL RLS is recommended for v2.0.

---

## 6. Failure Handling

### 6.1 vLLM Unavailable

Gateway catches `httpx.ConnectError` and returns a **stub response**:
```json
{
  "id": "chatcmpl-stub",
  "choices": [{"message": {"role": "assistant", "content": "[stub mode]"}}]
}
```
Usage is still logged (10 input / 20 output tokens). This allows UI development without a running LLM.

### 6.2 Redis Unavailable

`enqueue_document_processing()` catches connection errors and falls back to **synchronous processing** in the request thread. This degrades performance (slow upload response) but does not break the feature.

Rate limiting: if Redis is unavailable, `check_rate_limit()` returns `True` (allow all). This is a fail-open design — change to fail-closed for stricter security.

### 6.3 Database Unavailable

SQLAlchemy connection pool raises immediately. FastAPI returns HTTP 500 via the global exception handler. No retry is built in at the application level — PostgreSQL HA (Patroni/replication) handles this at infra level.

### 6.4 Worker Job Failure

RQ marks the job as `failed`. Document status → `error`. The worker continues processing other jobs. Failed jobs visible in RQ dashboard (planned: expose at `/admin/jobs`).

### 6.5 JWT Expiry

Gateway returns HTTP 401. Frontend clears `localStorage` token and redirects to `/login`. No refresh token is implemented (v1.2 roadmap).
