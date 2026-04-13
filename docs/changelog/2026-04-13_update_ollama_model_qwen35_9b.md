# 2026-04-13 — Switch Ollama to Qwen3.5 9B

**Version:** 1.0.0  
**Type:** Infrastructure  
**Scope:** Infrastructure

---

## Summary
Switched the Ollama service from `qwen2.5:latest` to the official `qwen3.5:9b` model (tag = `latest` on ollama.com/library/qwen3.5). Qwen3.5 9B is 6.6GB with a 256K context window, supports Text and Image input, and offers significantly improved reasoning, coding, and multilingual capabilities over the Qwen2.5 family. The backend alias `qwen3.5-plus` is preserved so all downstream code remains unchanged.

---

## Changed
* `docker-compose.yml` — Ollama entrypoint now pulls `qwen3.5:9b` and clones it to the `qwen3.5-plus` alias

---

## Files Changed
- `docker-compose.yml` (modified)
