# API Specification — NeuralAPI AI Platform

**Version:** 1.0.0  
**Base URL:** `http://localhost:8080`  
**Last Updated:** 2026-04-10

---

## Authentication

All endpoints require one of:

| Method | Header | Used by |
|---|---|---|
| JWT Bearer | `Authorization: Bearer <jwt_token>` | Dashboard / management routes |
| API Key | `x-api-key: sk-<key>` | External LLM / RAG / gateway routes |

JWT obtained via `POST /auth/login` or `POST /auth/register`.  
API keys created via `POST /v1/keys` (JWT required).

---

## Error Format

All errors return:
```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Code | Meaning |
|---|---|
| 400 | Bad request / validation error |
| 401 | Missing or invalid auth |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (e.g. duplicate email) |
| 413 | File too large |
| 422 | Unprocessable entity (schema validation) |
| 429 | Rate limit exceeded / quota exceeded |
| 500 | Internal server error |

---

## Auth Routes

### POST /auth/register

Create a new user account and team.

**Auth:** None

**Request:**
```json
{
  "email": "user@example.com",
  "password": "min8chars",
  "full_name": "John Doe",
  "team_name": "Acme Corp"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- `409` — Email already registered
- `422` — Password too short (< 8 chars)

---

### POST /auth/login

Authenticate and receive JWT.

**Auth:** None

**Request:**
```json
{
  "email": "user@example.com",
  "password": "min8chars"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:**
- `401` — Invalid credentials

---

### GET /auth/me

Get current user profile.

**Auth:** JWT Bearer

**Response 200:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "owner",
  "team_id": "uuid",
  "team_name": "Acme Corp",
  "avatar_url": null
}
```

---

## API Key Routes

### GET /v1/keys

List all active API keys for the current team.

**Auth:** JWT Bearer

**Response 200:**
```json
[
  {
    "id": "uuid",
    "name": "Production",
    "prefix": "sk-AbCdEf1234",
    "status": "active",
    "created_at": "2026-04-10T10:00:00+00:00",
    "last_used_at": "2026-04-10T11:30:00+00:00",
    "expires_at": null
  }
]
```

---

### POST /v1/keys

Create a new API key.

**Auth:** JWT Bearer

**Request:**
```json
{
  "name": "Production API",
  "expires_in_days": 90
}
```
> `expires_in_days` is optional. Omit for a non-expiring key.

**Response 200:**
```json
{
  "id": "uuid",
  "name": "Production API",
  "prefix": "sk-AbCdEf1234",
  "status": "active",
  "created_at": "2026-04-10T10:00:00+00:00",
  "expires_at": "2026-07-09T10:00:00+00:00",
  "full_key": "sk-AbCdEf1234XyzPqrStuVwx..."
}
```

> ⚠️ `full_key` is returned **only once** at creation time. Store it immediately.

---

### DELETE /v1/keys/{key_id}

Revoke an API key.

**Auth:** JWT Bearer

**Response 200:**
```json
{ "message": "API key revoked" }
```

**Errors:**
- `404` — Key not found or not owned by team

---

## LLM Gateway Routes

### GET /v1/models

List available models.

**Auth:** `x-api-key`

**Response 200:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen3.5-plus",
      "object": "model",
      "created": 1704000000,
      "owned_by": "local"
    },
    {
      "id": "text-embedding-3-small",
      "object": "model",
      "created": 1704000000,
      "owned_by": "local"
    }
  ]
}
```

---

### POST /v1/chat/completions

OpenAI-compatible chat completion. Supports streaming via SSE.

**Auth:** `x-api-key`

**Request:**
```json
{
  "model": "qwen3.5-plus",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user",   "content": "What is RAG?" }
  ],
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false
}
```

**Response 200 (non-streaming):**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "qwen3.5-plus",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "RAG stands for Retrieval-Augmented Generation..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 28,
    "completion_tokens": 42,
    "total_tokens": 70
  }
}
```

**Response 200 (streaming, stream=true):**
```
Content-Type: text/event-stream

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","choices":[{"delta":{"content":"RAG"},"index":0}]}

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","choices":[{"delta":{"content":" stands"},"index":0}]}

data: [DONE]
```

**Errors:**
- `401` — Invalid/missing API key
- `429` — Rate limit exceeded
- `429` — Token quota exceeded (`"detail": "Token quota exceeded. Please upgrade your plan."`)
- `500` — LLM server error

---

### POST /v1/embeddings

Generate vector embeddings for input text.

**Auth:** `x-api-key`

**Request:**
```json
{
  "input": "Hello, world!",
  "model": "text-embedding-3-small"
}
```
> `input` may be a string or an array of strings for batch embedding.

**Response 200:**
```json
{
  "object": "list",
  "model": "text-embedding-3-small",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.0023, -0.0091, ..., 0.0045]
    }
  ],
  "usage": {
    "prompt_tokens": 4,
    "total_tokens": 4
  }
}
```

**Errors:**
- `401` — Invalid API key
- `429` — Rate limit / quota exceeded

---

## RAG — Collections

### GET /v1/collections

List all collections for the current team.

**Auth:** JWT Bearer

**Response 200:**
```json
[
  {
    "id": "uuid",
    "name": "Product Docs",
    "description": "Official product documentation",
    "doc_count": 12,
    "embedding_model": "text-embedding-3-small",
    "created_at": "2026-04-10T10:00:00+00:00"
  }
]
```

---

### POST /v1/collections

Create a new collection.

**Auth:** JWT Bearer

**Request:**
```json
{
  "name": "Product Docs",
  "description": "Official product documentation",
  "embedding_model": "text-embedding-3-small"
}
```

**Response 200:**
```json
{
  "id": "uuid",
  "name": "Product Docs",
  "description": "Official product documentation",
  "doc_count": 0
}
```

**Errors:**
- `422` — Missing required field `name`

---

### GET /v1/collections/{collection_id}

Get collection details with document list.

**Auth:** JWT Bearer

**Response 200:**
```json
{
  "id": "uuid",
  "name": "Product Docs",
  "description": "...",
  "doc_count": 3,
  "embedding_model": "text-embedding-3-small",
  "documents": [
    {
      "id": "uuid",
      "filename": "guide.pdf",
      "file_size": 204800,
      "chunk_count": 42,
      "status": "done",
      "created_at": "2026-04-10T10:00:00+00:00"
    }
  ]
}
```

**Document status values:** `pending` | `processing` | `done` | `error`

---

### DELETE /v1/collections/{collection_id}

Delete a collection and all its documents and chunks.

**Auth:** JWT Bearer

**Response 200:**
```json
{ "message": "Collection deleted" }
```

---

### POST /v1/collections/{collection_id}/search

Semantic search in a collection using pgvector cosine similarity.

**Auth:** JWT Bearer

**Request:**
```json
{
  "query": "How do I reset my password?",
  "top_k": 5
}
```

**Response 200:**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "content": "To reset your password, navigate to Settings → Security...",
      "chunk_index": 3
    }
  ]
}
```

---

## RAG — Documents

### POST /v1/documents

Upload a document for ingestion (multipart/form-data).

**Auth:** JWT Bearer

**Request (multipart/form-data):**
```
collection_id: <uuid>
file: <binary>
```

Max file size: 50 MB (configurable via `MAX_UPLOAD_SIZE_MB`)

**Response 200:**
```json
{
  "id": "uuid",
  "filename": "guide.txt",
  "status": "pending",
  "message": "Document uploaded and queued for processing"
}
```

**Errors:**
- `404` — Collection not found or not owned by team
- `413` — File exceeds maximum size

---

### GET /v1/documents/{doc_id}

Get document processing status.

**Auth:** JWT Bearer

**Response 200:**
```json
{
  "id": "uuid",
  "filename": "guide.txt",
  "file_size": 10240,
  "chunk_count": 8,
  "status": "done",
  "error_message": null,
  "created_at": "2026-04-10T10:00:00+00:00"
}
```

---

### DELETE /v1/documents/{doc_id}

Delete a document and all its chunks.

**Auth:** JWT Bearer

**Response 200:**
```json
{ "message": "Document deleted" }
```

---

## Memory Chat

### POST /v1/memchat/completions

Chat with persistent conversation memory. History is loaded from `agent_messages` and prepended to the request.

**Auth:** `x-api-key`

**Request:**
```json
{
  "agent_id": "uuid",
  "contact_id": "uuid",
  "messages": [
    { "role": "user", "content": "What did I ask earlier?" }
  ],
  "model": "qwen3.5-plus"
}
```

**Response:** Same as `/v1/chat/completions`

---

### GET /v1/messages

Retrieve conversation history.

**Auth:** `x-api-key`

**Query params:**
- `contact_id` (required) — UUID of the contact/session
- `limit` (optional, default: 100)
- `before` (optional) — ISO timestamp for pagination

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "agent_id": "uuid",
      "role": "user",
      "content": "Hello",
      "created_at": "2026-04-10T10:00:00+00:00"
    }
  ]
}
```

---

## File Conversion

### POST /v1/convert/markdown

Convert an uploaded file to Markdown.

**Auth:** `x-api-key`

**Request (multipart/form-data):**
```
file: <binary>
ocr: false
```

**Response 200:**
```json
{
  "filename": "document.txt",
  "markdown": "# Document Title\n\nContent...",
  "ocr_used": false
}
```

---

## Usage Analytics

### GET /v1/usage/summary

**Auth:** JWT Bearer  
**Query:** `?days=30` (1–365)

**Response 200:**
```json
{
  "summary": {
    "total_tokens": 48200,
    "input_tokens": 32100,
    "output_tokens": 16100,
    "total_requests": 142,
    "avg_latency_ms": 312.5,
    "success_rate": 98.6
  },
  "quota": {
    "token_quota": 100000,
    "tokens_used": 48200,
    "stt_quota": 60,
    "stt_used": 0,
    "tts_quota": 60,
    "tts_used": 0,
    "coding_quota": 50000,
    "coding_used": 0
  },
  "daily": [
    { "date": "2026-04-01", "requests": 12, "tokens": 4200, "avg_latency": 280 }
  ],
  "by_service": [
    { "service": "chat", "requests": 130, "tokens": 45000 },
    { "service": "embeddings", "requests": 12, "tokens": 3200 }
  ]
}
```

---

## Billing

### GET /v1/billing/quota

**Auth:** JWT Bearer

**Response 200:**
```json
{
  "plan": "free",
  "price_usd": 0,
  "billing_period_start": "2026-04-01T00:00:00+00:00",
  "next_billing_date": null,
  "quotas": [
    { "name": "Token Usage", "service": "chat", "used": 48200, "limit": 100000, "unit": "tokens" },
    { "name": "STT Minutes", "service": "stt",  "used": 0,     "limit": 60,     "unit": "minutes" },
    { "name": "TTS Minutes", "service": "tts",  "used": 0,     "limit": 60,     "unit": "minutes" },
    { "name": "Coding Tokens", "service": "coding", "used": 0, "limit": 50000,  "unit": "tokens" }
  ]
}
```

### POST /v1/billing/upgrade

**Auth:** JWT Bearer

**Request:**
```json
{ "plan": "pro" }
```

**Plans:** `free` | `pro` | `enterprise`

**Response 200:**
```json
{ "message": "Upgraded to pro", "plan": "pro" }
```

---

## Monitoring

### GET /health

**Auth:** None

**Response 200:**
```json
{ "status": "ok", "service": "ai-platform-api" }
```

### GET /metrics

**Auth:** None  
**Response:** Prometheus text format (for scraping by Prometheus server)
