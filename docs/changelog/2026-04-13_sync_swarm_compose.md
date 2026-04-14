# 2026-04-13 — Sync docker-compose.swarm.yml with docker-compose.yml Architecture

**Version:** 1.1.2  
**Type:** Infrastructure  
**Scope:** Infrastructure

---

## Summary
Cập nhật `docker-compose.swarm.yml` để đồng bộ với kiến trúc mới trong `docker-compose.yml`. Thay thế service `vllm` (cũ) bằng `model-downloader` + `llama-cpp` (GGUF, OpenAI-compatible), thêm `ray` head node trong Swarm mode, cập nhật tất cả environment variables và volume references. Các thành phần Swarm-specific (hybrid-router, burst-controller, node-exporter, deploy blocks) được giữ nguyên.

---

## Added
* `ray` service — Ray head node pinned to manager node (replicas: 1, 4 CPU / 4G RAM)
* `model-downloader` service — init container pull GGUF từ HuggingFace, placement trên worker `llm == true`, `restart_policy: none`
* `llama-cpp` service — `ghcr.io/ggml-org/llama.cpp:server`, OpenAI-compatible REST API trên port 8080, placement trên worker `llm == true`, limits 6 CPU / 8G RAM
* `models_data` volume — thay thế `hf_cache` và `ollama_data`

## Changed
* `x-common-env` anchor — thêm `RAY_ADDRESS` và `VLLM_BASE_URL=http://llama-cpp:8080/v1`
* `backend` env — `VLLM_BASE_URL` / `EMBEDDING_BASE_URL` trỏ sang `http://llama-cpp:8080/v1`
* `worker` env — `VLLM_BASE_URL` trỏ sang `http://llama-cpp:8080/v1`
* `burst-controller` env — `CLOUD_RUN_SERVICES` đổi từ `ai-backend,ai-vllm` → `ai-backend,ai-llama-cpp`

## Removed
* `vllm` service (`vllm/vllm-openai:latest`)
* `hf_cache` volume

---

## Files Changed
- `docker-compose.swarm.yml` (modified)
