"""Ray Serve deployment for vLLM (qwen3.5-plus).

Start with:
    ray start --head
    python backend/serve/vllm_deployment.py
"""
import ray
from ray import serve
import httpx
import os

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000")


@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_cpus": 2, "num_gpus": 0},
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 4,
        "target_num_ongoing_requests_per_replica": 10,
    },
)
class VLLMDeployment:
    """Proxy deployment that forwards to the actual vLLM server and handles autoscaling via Ray."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120)
        print(f"[VLLMDeployment] Initialized, proxying to {VLLM_BASE_URL}")

    async def __call__(self, request):
        path = request.url.path
        method = request.method
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)

        url = f"{VLLM_BASE_URL}{path}"

        resp = await self.client.request(
            method=method,
            url=url,
            content=body,
            headers=headers,
        )

        from starlette.responses import Response
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json"),
        )


# ── Embedding Deployment ────────────────────────────────────────────────────

@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_cpus": 1, "num_gpus": 0},
)
class EmbeddingDeployment:
    """Standalone embedding service using sentence-transformers."""

    def __init__(self):
        # Lazy import to avoid GPU dependency at import time
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.dim = self.model.get_sentence_embedding_dimension()
        print(f"[EmbeddingDeployment] Loaded model, dim={self.dim}")

    async def __call__(self, request):
        body = await request.json()
        texts = body.get("input", [])
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(texts, convert_to_list=True)

        from starlette.responses import JSONResponse
        return JSONResponse({
            "object": "list",
            "model": body.get("model", "all-MiniLM-L6-v2"),
            "data": [
                {"object": "embedding", "index": i, "embedding": emb}
                for i, emb in enumerate(embeddings)
            ],
            "usage": {"prompt_tokens": sum(len(t.split()) for t in texts), "total_tokens": sum(len(t.split()) for t in texts)},
        })


# ── Deployment Entrypoint ─────────────────────────────────────────────────────

if __name__ == "__main__":
    ray.init(address="auto", ignore_reinit_error=True)
    serve.start(detached=True, http_options={"host": "0.0.0.0", "port": 8001})

    vllm_app = VLLMDeployment.bind()
    embedding_app = EmbeddingDeployment.bind()

    serve.run(vllm_app, route_prefix="/v1", name="vllm")
    serve.run(embedding_app, route_prefix="/embeddings", name="embeddings")

    print("[RayServe] Deployments started:")
    print("  - VLLMDeployment at /v1")
    print("  - EmbeddingDeployment at /embeddings")

    import time
    while True:
        time.sleep(10)
