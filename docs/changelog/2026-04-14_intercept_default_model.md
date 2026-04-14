# 2026-04-14 — Update Model Mapping

**Version:** 1.0.0  
**Type:** Fix  
**Scope:** Backend  

---

## Summary
Updated the backend gateway to explicitly map any incoming `default_model` requests to `qwen3.5-plus`. Since some integrations and generic setups naturally send `default_model` or missing model keys, this ensures stability and allows the system to seamlessly route requests to the intended `qwen3.5-plus` LLM engine.

---

## Changed
* Added interception constraint to `chat_completions` and `memchat_completions` routes in `gateway.py` to rewrite `default_model` explicitly to `qwen3.5-plus`.

---

## Files Changed
- `backend/routes/gateway.py` (modified)
