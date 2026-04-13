# 2026-04-13 — Fix JSON Decode Error

**Version:** 1.0.X  
**Type:** Fix  
**Scope:** Backend

---

## Summary
Fixed a `JSONDecodeError` caused by unescaped control characters in JSON payloads arriving at the LLM Gateway and vLLM proxy deployments. Migrated `await request.json()` to lenient parsing using `json.loads(..., strict=False)`, mitigating crashes on strings containing invalid control characters (e.g., `\n`, `\t` inside string literals).

---

## Added
* `get_safe_json` helper in gateway to safely decode bodies with `strict=False`.
* Explicit string payload handling with fallback errors to prevent 500 crashes and bubble 400 errors gracefully instead.

## Changed
* Changed `json` extraction in `gateway.py` (`chat_completions`, `embeddings`, `memchat_completions`) to handle invalid bytes gracefully.
* Changed body decoding logic in `vllm_deployment.py` to prevent crashes when receiving non-compliant user input.

## Fixed
* `json.decoder.JSONDecodeError` during `request.json()` processing.

## Removed
* None

---

## Files Changed
- `backend/routes/gateway.py` (modified)
- `backend/serve/vllm_deployment.py` (modified)
