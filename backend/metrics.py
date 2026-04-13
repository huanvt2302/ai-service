"""Prometheus metrics for the AI Platform."""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# ── Metrics ─────────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "api_request_total",
    "Total API requests",
    ["method", "endpoint", "status_code", "service"],
)

REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "API request latency",
    ["endpoint", "service"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

TOKEN_USAGE = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["model", "type", "team_id"],  # type: input/output
)

ACTIVE_KEYS = Gauge(
    "api_keys_active_total",
    "Number of active API keys",
    ["team_id"],
)

QUEUE_DEPTH = Gauge(
    "document_queue_depth",
    "Number of documents in processing queue",
)

EMBEDDING_REQUESTS = Counter(
    "embedding_requests_total",
    "Total embedding requests",
    ["model"],
)

RAG_SEARCH_LATENCY = Histogram(
    "rag_search_latency_seconds",
    "RAG vector search latency",
    ["collection_id"],
)


# ── Middleware helper ─────────────────────────────────────────────────────

class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")
        start = time.time()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.time() - start
            service = _infer_service(path)
            REQUEST_COUNT.labels(method=method, endpoint=path, status_code=str(status_code), service=service).inc()
            REQUEST_LATENCY.labels(endpoint=path, service=service).observe(duration)


def _infer_service(path: str) -> str:
    if "/chat" in path:
        return "chat"
    elif "/embeddings" in path:
        return "embeddings"
    elif "/rag" in path or "/collections" in path or "/documents" in path:
        return "rag"
    elif "/auth" in path:
        return "auth"
    else:
        return "other"


async def metrics_endpoint():
    from prometheus_client import REGISTRY
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
