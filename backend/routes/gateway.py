"""LLM Gateway routes — proxies to vLLM / Ray Serve with SSE streaming"""
import httpx
import json
import time
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from models import UsageLog, ApiKey, Subscription
from auth import get_current_team_from_api_key, get_current_user
from config import get_settings
from metrics import TOKEN_USAGE, EMBEDDING_REQUESTS

settings = get_settings()
router = APIRouter(tags=["gateway"])


MODELS = [
    {"id": "qwen3.5-plus", "object": "model", "created": 1704000000, "owned_by": "local"},
    {"id": "text-embedding-3-small", "object": "model", "created": 1704000000, "owned_by": "local"},
]


def log_usage(db: Session, api_key: ApiKey, service: str, model: str,
              input_tokens: int, output_tokens: int, latency_ms: float,
              status_code: int, endpoint: str):
    total = input_tokens + output_tokens
    log = UsageLog(
        team_id=api_key.team_id,
        api_key_id=api_key.id,
        service=service,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total,
        latency_ms=latency_ms,
        status_code=status_code,
        endpoint=endpoint,
    )
    db.add(log)

    # Update subscription usage
    sub = db.query(Subscription).filter(Subscription.team_id == api_key.team_id).first()
    if sub:
        sub.tokens_used = (sub.tokens_used or 0) + total
    db.commit()

    # Prometheus
    TOKEN_USAGE.labels(model=model, type="input", team_id=str(api_key.team_id)).inc(input_tokens)
    TOKEN_USAGE.labels(model=model, type="output", team_id=str(api_key.team_id)).inc(output_tokens)


def check_quota(db: Session, team_id) -> bool:
    """Returns True if team has quota remaining."""
    sub = db.query(Subscription).filter(Subscription.team_id == team_id).first()
    if not sub:
        return True
    return (sub.tokens_used or 0) < sub.token_quota


@router.get("/v1/models")
def list_models(api_key: ApiKey = Depends(get_current_team_from_api_key)):
    return {"object": "list", "data": MODELS}


@router.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    api_key: ApiKey = Depends(get_current_team_from_api_key),
    db: Session = Depends(get_db),
):
    if not check_quota(db, api_key.team_id):
        raise HTTPException(status_code=429, detail="Token quota exceeded. Please upgrade your plan.")

    body = await request.json()
    model = body.get("model", settings.default_chat_model)
    stream = body.get("stream", False)
    start = time.time()

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            if stream:
                async def event_stream():
                    input_tokens = 0
                    output_tokens = 0
                    try:
                        async with client.stream(
                            "POST",
                            f"{settings.vllm_base_url}/v1/chat/completions",
                            json=body,
                            headers={"Content-Type": "application/json"},
                        ) as resp:
                            async for line in resp.aiter_lines():
                                if line:
                                    yield f"{line}\n\n"
                                    if line.startswith("data:") and "[DONE]" not in line:
                                        try:
                                            chunk = json.loads(line[5:])
                                            usage = chunk.get("usage") or {}
                                            output_tokens += usage.get("completion_tokens", 0)
                                        except Exception:
                                            pass
                    except httpx.ConnectError:
                        # Fallback stub for dev without vLLM
                        stub = {
                            "id": "chatcmpl-stub",
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [{"delta": {"content": "[vLLM not connected — stub response]"}, "index": 0, "finish_reason": "stop"}],
                        }
                        yield f"data: {json.dumps(stub)}\n\ndata: [DONE]\n\n"
                    finally:
                        latency = (time.time() - start) * 1000
                        log_usage(db, api_key, "chat", model, input_tokens, output_tokens, latency, 200, "/v1/chat/completions")

                return StreamingResponse(event_stream(), media_type="text/event-stream")
            else:
                try:
                    resp = await client.post(
                        f"{settings.vllm_base_url}/v1/chat/completions",
                        json=body,
                        headers={"Content-Type": "application/json"},
                    )
                    result = resp.json()
                    usage = result.get("usage", {})
                    latency = (time.time() - start) * 1000
                    log_usage(db, api_key, "chat", model,
                              usage.get("prompt_tokens", 0),
                              usage.get("completion_tokens", 0),
                              latency, resp.status_code, "/v1/chat/completions")
                    return result
                except httpx.ConnectError:
                    latency = (time.time() - start) * 1000
                    log_usage(db, api_key, "chat", model, 10, 20, latency, 200, "/v1/chat/completions")
                    return {
                        "id": "chatcmpl-stub",
                        "object": "chat.completion",
                        "model": model,
                        "choices": [{
                            "message": {"role": "assistant", "content": "Hello! I'm running in stub mode (vLLM not connected). Configure VLLM_BASE_URL to connect a real model."},
                            "finish_reason": "stop",
                            "index": 0,
                        }],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                    }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/embeddings")
async def embeddings(
    request: Request,
    api_key: ApiKey = Depends(get_current_team_from_api_key),
    db: Session = Depends(get_db),
):
    body = await request.json()
    model = body.get("model", settings.default_embedding_model)
    start = time.time()

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.post(
                    f"{settings.vllm_base_url}/v1/embeddings",
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                result = resp.json()
                usage = result.get("usage", {})
                latency = (time.time() - start) * 1000
                log_usage(db, api_key, "embeddings", model,
                          usage.get("prompt_tokens", 0), 0, latency, resp.status_code, "/v1/embeddings")
                EMBEDDING_REQUESTS.labels(model=model).inc()
                return result
            except httpx.ConnectError:
                # Return zero-vector stub
                import random
                embedding = [random.uniform(-0.1, 0.1) for _ in range(1536)]
                latency = (time.time() - start) * 1000
                log_usage(db, api_key, "embeddings", model, 10, 0, latency, 200, "/v1/embeddings")
                return {
                    "object": "list",
                    "model": model,
                    "data": [{"object": "embedding", "index": 0, "embedding": embedding}],
                    "usage": {"prompt_tokens": 10, "total_tokens": 10},
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/convert/markdown")
async def convert_to_markdown(
    request: Request,
    api_key: ApiKey = Depends(get_current_team_from_api_key),
):
    """Convert uploaded file to markdown (stub — integrate with docling/marker)."""
    form = await request.form()
    file = form.get("file")
    ocr = form.get("ocr", "false").lower() == "true"

    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    filename = file.filename or "document"

    # Basic text extraction for txt/md files
    try:
        text = content.decode("utf-8")
        return {"filename": filename, "markdown": text, "ocr_used": False}
    except UnicodeDecodeError:
        return {
            "filename": filename,
            "markdown": f"# {filename}\n\n[Binary file — OCR processing required]",
            "ocr_used": ocr,
        }


@router.post("/v1/memchat/completions")
async def memchat_completions(
    request: Request,
    api_key: ApiKey = Depends(get_current_team_from_api_key),
    db: Session = Depends(get_db),
):
    """Chat completions with conversation memory."""
    body = await request.json()
    contact_id = body.get("contact_id")
    agent_id = body.get("agent_id")

    from models import AgentMessage
    history = []
    if contact_id and agent_id:
        msgs = db.query(AgentMessage).filter(
            AgentMessage.contact_id == contact_id,
            AgentMessage.agent_id == agent_id,
        ).order_by(AgentMessage.created_at.asc()).limit(50).all()
        history = [{"role": m.role, "content": m.content} for m in msgs]

    # Merge history with new messages
    messages = history + body.get("messages", [])
    body["messages"] = messages

    # Save user message
    if contact_id and agent_id and body.get("messages"):
        last = body["messages"][-1]
        db.add(AgentMessage(
            agent_id=agent_id,
            contact_id=contact_id,
            role=last.get("role", "user"),
            content=last.get("content", ""),
        ))
        db.commit()

    # Proxy to /v1/chat/completions logic
    return await chat_completions.__wrapped__(request, api_key, db) if hasattr(chat_completions, "__wrapped__") else {
        "id": "memchat-stub",
        "object": "chat.completion",
        "choices": [{"message": {"role": "assistant", "content": "Memory chat response"}, "finish_reason": "stop", "index": 0}],
    }


@router.get("/v1/messages")
def get_messages(
    contact_id: str,
    limit: int = 100,
    before: str = None,
    api_key: ApiKey = Depends(get_current_team_from_api_key),
    db: Session = Depends(get_db),
):
    from models import AgentMessage
    q = db.query(AgentMessage).filter(AgentMessage.contact_id == contact_id)
    if before:
        try:
            from datetime import datetime
            before_dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
            q = q.filter(AgentMessage.created_at < before_dt)
        except ValueError:
            pass
    msgs = q.order_by(AgentMessage.created_at.desc()).limit(limit).all()
    return {
        "data": [
            {
                "id": str(m.id),
                "agent_id": str(m.agent_id),
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(msgs)
        ]
    }
