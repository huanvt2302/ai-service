# 2026-04-13 — Replace Ollama with llama.cpp Server

**Version:** 1.1.1  
**Type:** Refactor  
**Scope:** Infrastructure

---

## Summary

Replaced the Ollama Docker service with the official **llama.cpp server** (`ghcr.io/ggerganov/llama.cpp:server`) for local LLM inference. llama.cpp natively supports GGUF model format, is lighter than Ollama, runs efficiently on macOS ARM64 CPU without any native dependencies, and exposes a fully OpenAI-compatible REST API (`/v1/chat/completions`, `/v1/embeddings`, `/v1/models`) — so no backend code changes were required. A new `model-downloader` init container automatically fetches the GGUF model from HuggingFace on first start and caches it in the `models_data` Docker volume.

---

## Added

* `model-downloader` init service — pulls `Qwen2.5-3B-Instruct-Q4_K_M.gguf` from `Qwen/Qwen2.5-3B-Instruct-GGUF` via `huggingface_hub` on first start; skips if model file already exists
* `llama-cpp` service — `ghcr.io/ggerganov/llama.cpp:server`, serves GGUF model with OpenAI-compatible API on port 8080 (mapped to host port 11434 for drop-in compatibility)
* `models_data` Docker volume — persistent storage for GGUF model files
* New env vars: `LLAMA_CPP_MODEL`, `LLAMA_CPP_CTX_SIZE`, `LLAMA_CPP_THREADS`
* Healthcheck on `llama-cpp` service (`GET /health`)

## Changed

* `VLLM_BASE_URL` default: `http://ollama:11434/v1` → `http://llama-cpp:8080/v1`
* `EMBEDDING_BASE_URL` default: same update as above
* `.env.example` — LLM section updated from `vLLM/Ollama` fields to `llama.cpp` fields
* `docs/architecture.md` — Service inventory, LLM serving section, and single-node diagram updated

## Removed

* `ollama` service (image: `ollama/ollama:latest`, profile `ollama`)
* `ollama_data` Docker volume
* Ollama-specific env vars (`VLLM_MODEL`, `VLLM_SERVED_NAME`, `VLLM_MAX_LEN`) from `.env.example`

---

## Files Changed

- `docker-compose.yml` (modified)
- `.env.example` (modified)
- `docs/architecture.md` (modified)
- `docs/changelog/2026-04-13_replace_ollama_with_llamacpp.md` (new)
- `docs/changelog.md` (modified)
