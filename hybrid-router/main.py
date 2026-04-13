"""
Hybrid Router — Local-First AI Request Router
=============================================

Routing logic (evaluated per-request, with 10s CPU cache):

  1. Query Prometheus for avg CPU across all cluster nodes
  2. if local_cpu < BURST_THRESHOLD  →  proxy to LOCAL backend (Swarm VIP)
  3. if local_cpu >= BURST_THRESHOLD →  proxy to CLOUD_BACKEND_URL (GCP Cloud Run)
  4. Circuit breaker: 3 consecutive local errors → force cloud until reset

Environment variables:
  PROMETHEUS_URL      Prometheus base URL          (default: http://prometheus:9090)
  LOCAL_BACKEND_URL   Local FastAPI Swarm VIP       (default: http://backend:8080)
  CLOUD_BACKEND_URL   GCP Cloud Run URL             (default: "" = cloud disabled)
  BURST_THRESHOLD     CPU % to trigger burst        (default: 70)
  CPU_CACHE_TTL       Seconds to cache CPU value    (default: 10)
  CIRCUIT_BREAKER_MAX Errors before circuit opens   (default: 3)

Endpoints:
  ALL /* (proxy)       — Transparent reverse proxy
  GET /router/status   — Current routing status (CPU, mode, errors)
  GET /router/metrics  — Prometheus-format metrics for this router
  POST /router/reset   — Reset circuit breaker manually
"""

import asyncio
import time
import os
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# ── Configuration ──────────────────────────────────────────────────────────────

PROMETHEUS_URL      = os.getenv("PROMETHEUS_URL",      "http://prometheus:9090")
LOCAL_BACKEND_URL   = os.getenv("LOCAL_BACKEND_URL",   "http://backend:8080")
CLOUD_BACKEND_URL   = os.getenv("CLOUD_BACKEND_URL",   "").rstrip("/")
BURST_THRESHOLD     = float(os.getenv("BURST_THRESHOLD",     "70"))
CPU_CACHE_TTL       = float(os.getenv("CPU_CACHE_TTL",       "10"))
CIRCUIT_BREAKER_MAX = int(os.getenv("CIRCUIT_BREAKER_MAX",   "3"))

# ── Prometheus metrics emitted by this router ──────────────────────────────────

ROUTER_REQUESTS   = Counter("hybrid_router_requests_total",
                             "Total requests proxied", ["target"])
ROUTER_ERRORS     = Counter("hybrid_router_errors_total",
                             "Total proxy errors",     ["target"])
LOCAL_CPU_GAUGE   = Gauge("hybrid_router_local_cpu_percent",
                           "Current avg CPU % across local cluster")
IS_BURSTING_GAUGE = Gauge("hybrid_router_is_bursting",
                           "1 when routing to cloud, 0 when routing to local")

# ── App ────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
log = logging.getLogger("hybrid-router")

app = FastAPI(
    title="Hybrid Router",
    description="Local-first reverse proxy with automatic GCP Cloud Run burst",
    version="1.0.0",
    docs_url="/router/docs",
    redoc_url=None,
)

# ── State ──────────────────────────────────────────────────────────────────────

class RouterState:
    """Thread-safe (asyncio) state for routing decisions."""

    def __init__(self):
        self._cpu_value: float    = 0.0
        self._cpu_ts:    float    = 0.0
        self._cpu_lock:  asyncio.Lock = asyncio.Lock()

        self.local_errors:  int   = 0
        self.circuit_open:  bool  = False   # True = force cloud
        self.last_burst_at: Optional[float] = None

    # ── CPU Fetching ───────────────────────────────────────────────────────────

    async def get_cpu(self) -> float:
        """Return cached avg CPU %. Re-fetches from Prometheus when TTL expires."""
        now = time.monotonic()
        if now - self._cpu_ts < CPU_CACHE_TTL:
            return self._cpu_value

        async with self._cpu_lock:
            # Double-check after acquiring lock
            if now - self._cpu_ts < CPU_CACHE_TTL:
                return self._cpu_value

            value = await self._fetch_cpu_from_prometheus()
            self._cpu_value = value
            self._cpu_ts    = now
            LOCAL_CPU_GAUGE.set(value)
            return value

    async def _fetch_cpu_from_prometheus(self) -> float:
        """
        PromQL query: average idle → convert to used.
        Returns 0.0 on any error (fail-open: prefer local).
        """
        # Works with node_exporter on every Swarm node
        promql = (
            '100 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100'
        )
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    f"{PROMETHEUS_URL}/api/v1/query",
                    params={"query": promql},
                )
                data = resp.json()
                raw  = data["data"]["result"][0]["value"][1]
                return float(raw)
        except Exception as exc:
            log.warning("Cannot fetch CPU from Prometheus (%s) — defaulting to 0%%", exc)
            return 0.0

    # ── Routing Decision ───────────────────────────────────────────────────────

    async def should_use_cloud(self) -> bool:
        """Return True if this request should go to Cloud Run."""
        if not CLOUD_BACKEND_URL:
            return False

        # Circuit breaker: too many local errors
        if self.circuit_open:
            return True

        cpu = await self.get_cpu()
        is_bursting = cpu >= BURST_THRESHOLD
        IS_BURSTING_GAUGE.set(1 if is_bursting else 0)
        return is_bursting

    # ── Circuit Breaker ────────────────────────────────────────────────────────

    def record_local_success(self):
        if self.local_errors > 0:
            log.info("Local backend recovered — resetting circuit breaker")
        self.local_errors = 0
        self.circuit_open = False

    def record_local_error(self):
        self.local_errors += 1
        log.warning("Local backend error #%d (max=%d)", self.local_errors, CIRCUIT_BREAKER_MAX)
        if self.local_errors >= CIRCUIT_BREAKER_MAX:
            if not self.circuit_open:
                log.error("Circuit breaker OPEN — forcing cloud routing")
            self.circuit_open = True

    def reset_circuit(self):
        self.local_errors = 0
        self.circuit_open = False
        log.info("Circuit breaker manually reset")


state = RouterState()

# ── Proxy Helpers ──────────────────────────────────────────────────────────────

# Headers we must not forward upstream
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
}


def _filter_headers(headers: dict) -> dict:
    return {k: v for k, v in headers.items() if k.lower() not in _HOP_BY_HOP}


async def _proxy_request(target_url: str, request: Request) -> Response:
    body    = await request.body()
    headers = _filter_headers(dict(request.headers))

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        upstream = await client.request(
            method  = request.method,
            url     = target_url,
            content = body,
            headers = headers,
            params  = dict(request.query_params),
        )

    # Stream-safe: for SSE / large responses
    response_headers = dict(upstream.headers)
    response_headers.pop("content-encoding", None)  # already decoded by httpx
    response_headers.pop("transfer-encoding", None)

    return StreamingResponse(
        content     = iter([upstream.content]),
        status_code = upstream.status_code,
        headers     = response_headers,
        media_type  = upstream.headers.get("content-type", "application/octet-stream"),
    )

# ── Routes ─────────────────────────────────────────────────────────────────────


# Exclude internal router endpoints from proxying
_ROUTER_PATHS = {"/router/status", "/router/metrics", "/router/reset", "/router/docs"}


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def proxy(request: Request, path: str) -> Response:
    # Don't intercept our own endpoints
    full_path = "/" + path
    if full_path in _ROUTER_PATHS:
        return Response(status_code=404)

    use_cloud = await state.should_use_cloud()
    target    = CLOUD_BACKEND_URL if use_cloud else LOCAL_BACKEND_URL
    target_label = "cloud" if use_cloud else "local"
    target_url   = f"{target}/{path}"

    ROUTER_REQUESTS.labels(target=target_label).inc()
    if use_cloud:
        log.debug("→ CLOUD  %s %s", request.method, target_url)
    else:
        log.debug("→ LOCAL  %s %s", request.method, target_url)

    try:
        response = await _proxy_request(target_url, request)
        if not use_cloud:
            state.record_local_success()
        return response

    except httpx.ConnectError as exc:
        ROUTER_ERRORS.labels(target=target_label).inc()
        if not use_cloud:
            state.record_local_error()
            # Retry once on cloud if available
            if CLOUD_BACKEND_URL:
                log.warning("Local failed (%s) — retrying on cloud", exc)
                try:
                    cloud_url = f"{CLOUD_BACKEND_URL}/{path}"
                    ROUTER_REQUESTS.labels(target="cloud-fallback").inc()
                    return await _proxy_request(cloud_url, request)
                except Exception as cloud_exc:
                    log.error("Cloud fallback also failed: %s", cloud_exc)
        raise

    except Exception as exc:
        ROUTER_ERRORS.labels(target=target_label).inc()
        if not use_cloud:
            state.record_local_error()
        log.error("Proxy error to %s: %s", target_url, exc)
        raise


@app.get("/router/status", tags=["Router"])
async def router_status():
    """Current routing status — CPU load, burst mode, circuit breaker state."""
    cpu        = await state.get_cpu()
    use_cloud  = await state.should_use_cloud()
    return {
        "mode":                "cloud" if use_cloud else "local",
        "local_cpu_percent":   round(cpu, 1),
        "burst_threshold":     BURST_THRESHOLD,
        "is_bursting":         use_cloud,
        "circuit_open":        state.circuit_open,
        "local_error_count":   state.local_errors,
        "cloud_configured":    bool(CLOUD_BACKEND_URL),
        "local_backend_url":   LOCAL_BACKEND_URL,
        "cloud_backend_url":   CLOUD_BACKEND_URL or None,
    }


@app.get("/router/metrics", tags=["Router"], include_in_schema=False)
async def router_metrics():
    """Prometheus metrics endpoint for the router itself."""
    # Refresh CPU so gauge is current
    await state.get_cpu()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/router/reset", tags=["Router"])
async def reset_circuit():
    """Manually reset the circuit breaker (re-enables local routing)."""
    state.reset_circuit()
    return {"message": "Circuit breaker reset", "local_errors": 0}
