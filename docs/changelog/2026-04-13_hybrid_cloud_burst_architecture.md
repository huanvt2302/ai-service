# 2026-04-13 — Hybrid Local-First + GCP Cloud Burst Architecture

**Version:** 1.1.0  
**Type:** Infrastructure  
**Scope:** Infrastructure

---

## Summary

Implemented a hybrid deployment architecture that runs the AI platform on a 3-machine local Docker Swarm cluster as the primary compute tier, and automatically bursts to Google Cloud Run (serverless, min=0, max=20 instances) when the aggregate cluster CPU exceeds a configurable threshold (default 70%). This eliminates cloud costs when local resources are sufficient, while providing unlimited elastic capacity for peak loads.

Two new services orchestrate the burst logic:

- **Hybrid Router** (`hybrid-router/`) — A FastAPI transparent reverse proxy that sits in front of the backend. It caches average cluster CPU from Prometheus every 10 seconds and routes requests to the local Swarm backend when CPU is below the threshold, or to GCP Cloud Run when bursting. Includes a circuit breaker that forces cloud routing after 3 consecutive local errors.

- **Burst Controller** (`burst-controller/`) — A Python daemon that monitors Prometheus and calls `gcloud run services update --min-instances=N` to pre-warm Cloud Run instances before traffic arrives (triggers when CPU is high for 30s), then scales back to 0 when CPU is low for 60s.

---

## Added

* `hybrid-router/main.py` — FastAPI reverse proxy with CPU-based routing, circuit breaker, Prometheus metrics emission, and `/router/status` + `/router/reset` endpoints
* `hybrid-router/requirements.txt` — fastapi, uvicorn, httpx, prometheus-client
* `hybrid-router/Dockerfile` — Minimal Python 3.11-slim image
* `burst-controller/controller.py` — Async CPU-monitoring daemon with hysteresis-based scale up/down logic
* `burst-controller/requirements.txt` — httpx only (gcloud installed in image)
* `burst-controller/Dockerfile` — Includes gcloud CLI installation
* `docker-compose.swarm.yml` — Full Docker Swarm stack converting docker-compose.yml to Swarm mode with placement constraints, resource limits, node-exporter in global mode, and the two new services
* `scripts/setup-swarm.sh` — Comprehensive Swarm cluster setup script (manager init, worker join, GPU labeling, image build/push, stack deploy)
* `scripts/burst-gcp.sh` — Full GCP infrastructure setup + Cloud Run deployment script (APIs, Artifact Registry, IAM, Cloud SQL, Memorystore, GCS, Secret Manager, Cloud Run deploy)

## Changed

* `.gitignore` — Comprehensive ignore rules for Python, Node.js/Next.js (.next/), AI artifacts (HuggingFace weights, model files), uploads, and editor files
* `.env.example` — Added Hybrid Cloud Burst section with all new env vars (MACHINE IPs, BURST_THRESHOLD, CLOUD_BACKEND_URL, GCP_PROJECT, etc.)
* `monitoring/prometheus.yml` — Added node-exporter scrape targets for all 3 Swarm nodes, hybrid-router self-metrics, vLLM metrics; reduced scrape_interval to 10s for faster burst detection; removed Ray Serve target

## Removed

* Ray Serve dependency from deployment topology (replaced by Cloud Run autoscaling + Docker Swarm replica scaling)
* `RAY_ADDRESS` env var from `.env.example`
* ray scrape job from prometheus.yml

---

## Files Changed

- `hybrid-router/main.py` (new)
- `hybrid-router/requirements.txt` (new)
- `hybrid-router/Dockerfile` (new)
- `burst-controller/controller.py` (new)
- `burst-controller/requirements.txt` (new)
- `burst-controller/Dockerfile` (new)
- `docker-compose.swarm.yml` (new)
- `scripts/setup-swarm.sh` (new)
- `scripts/burst-gcp.sh` (new)
- `.gitignore` (modified)
- `.env.example` (modified)
- `monitoring/prometheus.yml` (modified)
