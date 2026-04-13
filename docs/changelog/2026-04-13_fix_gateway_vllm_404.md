# 2026-04-13 — Fix Gateway vLLM 404 Route Errors

**Version:** 0.2.1  
**Type:** Fix  
**Scope:** Backend

---

## Summary
Resolved a `JSONDecodeError: Extra data: line 1 column 5 (char 4)` occurring in the `gateway` routes. This was traced down to `VLLM_BASE_URL` configs sometimes containing a trailing `/v1`, leading to invalid endpoints (e.g., `/v1/v1/chat/completions`) being queried. Rather than failing with a generic python JSON Decode Error when receiving the resulting `404 page not found` plain text from Ollama or vLLM, the API gateway now handles endpoint formatting gracefully and logs non-200 HTTP responses.

---

## Added
* Added graceful handling of non-200 HTTP statuses in `/v1/chat/completions` (regular and streaming) and `/v1/embeddings` routes before attempting JSON decoding.

## Changed
* Normalized the `settings.vllm_base_url` path construction when executing outbound HTTP POST requests to prevent double `/v1/v1` routes.

## Fixed
* Fixed generic JSON decode errors obscuring backend connection / 404 response errors when interacting with AI inference engines.

## Removed
* None.

---

## Files Changed
- `backend/routes/gateway.py` (modified)
