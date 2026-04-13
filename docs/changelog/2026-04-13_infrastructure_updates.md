# 2026-04-13 — Infrastructure Updates: Hybrid Cloud Burst & macOS vLLM Support

**Version:** 1.1.0  
**Type:** Infrastructure / Fix  
**Scope:** Infrastructure

---

## Summary
This update introduces a major architectural shift to a Hybrid Local-First + GCP Cloud Burst deployment, alongside a series of critical fixes to ensure the local vLLM AI engine runs stably on macOS ARM64 under Docker Compose (CPU fallback mode). 

---

## Hybrid Local-First + GCP Cloud Burst Architecture

Implemented a hybrid deployment architecture that runs the AI platform on a 3-machine local Docker Swarm cluster as the primary compute tier, and automatically bursts to Google Cloud Run (serverless, min=0, max=20 instances) when the aggregate cluster CPU exceeds a configurable threshold (default 70%). This eliminates cloud costs when local resources are sufficient, while providing unlimited elastic capacity for peak loads.

Two new services orchestrate the burst logic:
- **Hybrid Router** (`hybrid-router/`) — A FastAPI transparent reverse proxy that sits in front of the backend. It routes requests to the local Swarm backend when CPU is below the threshold, or to GCP Cloud Run when bursting.
- **Burst Controller** (`burst-controller/`) — A Python daemon that monitors Prometheus and calls `gcloud run services update --min-instances=N` to pre-warm Cloud Run instances.

### Added (Hybrid Architecture)
* `hybrid-router/main.py`, `requirements.txt`, `Dockerfile` — FastAPI reverse proxy with CPU-based routing and circuit breaker.
* `burst-controller/controller.py`, `requirements.txt`, `Dockerfile` — Async CPU-monitoring daemon for hysteresis-based scaling.
* `docker-compose.swarm.yml` — Full Docker Swarm stack converting docker-compose.yml to Swarm mode.
* `scripts/setup-swarm.sh`, `scripts/burst-gcp.sh` — Setup scripts for local Swarm and GCP infrastructure.

### Changed (Hybrid Architecture)
* `.gitignore` — Ignore rules for Python, Node.js/Next.js, AI artifacts, uploads.
* `.env.example` — Added Hybrid Cloud Burst section.
* `monitoring/prometheus.yml` — Added node-exporter scrape targets, hybrid-router metrics, reduced scrape interval.

### Removed (Hybrid Architecture)
* Ray Serve dependency (replaced by Cloud Run autoscaling + Docker Swarm replica scaling).

---

## macOS ARM64 vLLM Docker Fallback Fixes

Several iterations of debugging were performed to get the vLLM engine running on Apple Silicon (M-series) Macs using Docker Desktop's CPU fallback, bypassing issues with CUDA dependencies and NUMA autobind assertions.

### Fixed
* **Docker GPU Driver:** Removed the `deploy` block reservation for the nvidia GPU in `docker-compose.yml` to fix the `could not select device driver "nvidia"` daemon error on macOS.
* **vLLM Image:** Switched from `vllm/vllm-openai:latest` to `vllm/vllm-openai-cpu:latest-arm64` to prevent loading non-existent PyTorch/Triton CUDA components.
* **CLI Args (Compatibility):** Removed the unsupported `--device cpu` argument and updated the `--model` flag to a positional argument.
* **CLI Args (Memory Constraints):** To prevent Docker Desktop OOM Kill (SIGKILL -9) during KV cache pre-allocation, changed dtype from `float32` to `bfloat16`, reduced `--max-model-len` to `1024`, and constrained `--max-num-seqs 16`.
* **vLLM CPU Autobind Crash:** Resolved `AssertionError: len(logical_cpu_list) >= world_size_across_dp` caused by `libnuma` failing to parse macOS's Docker CPU topology. Set `VLLM_CPU_OMP_THREADS_BIND="all"` to explicitly force a valid `cpustring` for `libnuma`.
* **NUMA Missing Metadata:** Added `VLLM_CPU_SIM_MULTI_NUMA=1` to simulate multi-NUMA topologies, bypassing the strict NUMA node thread-binding assertions.

---

## Files Changed
- `hybrid-router/*` (new)
- `burst-controller/*` (new)
- `docker-compose.swarm.yml` (new)
- `scripts/*` (new)
- `docker-compose.yml` (modified)
- `.gitignore` (modified)
- `.env.example` (modified)
- `monitoring/prometheus.yml` (modified)
