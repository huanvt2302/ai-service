# 2026-04-13 — Replace vLLM with Ollama Docker Image
**Version:** 1.1.1
**Type:** Refactor
**Scope:** Infrastructure

---

## Summary
Replaced the problematic vLLM Docker service with the official `ollama/ollama:latest` image to provide a vastly more stable and resource-efficient local LLM fallback on macOS ARM64. Ollama uses the highly optimized `llama.cpp` backend which compiles beautifully for Apple Silicon CPUs without the complex multiprocessing, NUMA node assertions, and OOM issues inherent to vLLM's CPU fallback mode.

The new Ollama container automatically pulls the `qwen2.5:3b` model on startup and aliases it to `qwen3.5-plus` to remain 100% compatible with the existing backend API calls.

---

## Changed
* Replaced `ai_vllm` service with `ai_ollama` running `ollama/ollama:latest` in `docker-compose.yml`
* Updated the default `VLLM_BASE_URL` and `EMBEDDING_BASE_URL` environment variables pointing from `http://vllm:8000` to `http://ollama:11434/v1` (Ollama's native OpenAI-compatible wrapper endpoint)
* Changed volume storage from `hf_cache` to `ollama_data`
* The start profile is now `--profile ollama` instead of `--profile vllm`

---

## Files Changed
- `docker-compose.yml` (modified)
- `docs/changelog/2026-04-13_replace_vllm_with_ollama.md` (new)
