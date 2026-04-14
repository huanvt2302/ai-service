# 2026-04-13 — Code Review Fix Batch

**Version:** 1.0.1  
**Type:** Fix / Security / Refactor  
**Scope:** Backend

---

## Summary

Resolved all P0–P2 issues identified in the code review. Key changes include:
security guard on `/v1/billing/upgrade` (admin/owner only), a lifespan-managed
`httpx.AsyncClient` shared across gateway routes to avoid per-request TCP
handshakes, sentence-aware text chunking in the document worker for better
embedding quality, and a production-ready webhook dispatch utility with
HMAC-SHA256 signing. All previously noted P0/P1 fixes (double `/v1` URL bug,
team_id scope checks in RAG, stub ConnectError log with fake tokens, module-level
logger, `pool_recycle`) were confirmed already applied in prior sessions.

---

## Added

* `dispatch_webhook_event()` in `routes/webhooks.py` — fires signed (`X-NeuralAPI-Signature: sha256=…`) POST requests to all active team webhooks subscribed to a given event; best-effort, logs failures without raising
* `_sign_payload()` helper in `routes/webhooks.py` — HMAC-SHA256 signing (GitHub-style)
* Lifespan-managed `httpx.AsyncClient` on `app.state.http_client` in `main.py` — created at startup with keep-alive pool, closed on shutdown

## Changed

* `routes/billing.py` — `POST /v1/billing/upgrade` now returns 403 for users whose role is `member`; only `owner` or `admin` may change the team plan
* `routes/gateway.py` — `chat_completions`, `embeddings`, and `memchat_completions` now pull `request.app.state.http_client` instead of spawning a new `httpx.AsyncClient` per request
* `workers/document_worker.py` — `_chunk_text()` replaced word-split chunking with sentence-aware chunking (regex on `[.!?]` boundaries, char-based overlap); default chunk_size 512 words → 1500 chars, overlap 64 words → 200 chars

## Fixed

* *(Confirmed already applied)* Double `/v1` bug in `rag.py` and `document_worker.py` — uses `_build_llm_url()`
* *(Confirmed already applied)* `get_document` / `delete_document` scoped to `team_id` via JOIN on Collection
* *(Confirmed already applied)* stub `ConnectError` `log_usage` logs 503 + 0 tokens instead of fake 200 + 30 tokens
* *(Confirmed already applied)* `pool_recycle=3600` in `database.py`
* *(Confirmed already applied)* Module-level `logger` across all backend modules

---

## Files Changed

- `backend/main.py` (modified) — add `httpx` import; create/close shared AsyncClient in lifespan
- `backend/routes/billing.py` (modified) — import `UserRole`; add 403 guard in `upgrade_plan`
- `backend/routes/gateway.py` (modified) — remove per-request `httpx.AsyncClient()`; use `app.state.http_client`
- `backend/routes/webhooks.py` (modified) — add `dispatch_webhook_event()`, `_sign_payload()`, module-level imports/logger
- `backend/workers/document_worker.py` (modified) — replace word-based `_chunk_text()` with sentence-aware implementation
