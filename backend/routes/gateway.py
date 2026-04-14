"""LLM Gateway routes — proxies to llama-cpp with SSE streaming"""
import httpx
import json
import time
import logging
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
logger = logging.getLogger(__name__)


MODELS = [
    {"id": "qwen3.5-plus", "object": "model", "created": 1704000000, "owned_by": "local"},
    {"id": "text-embedding-3-small", "object": "model", "created": 1704000000, "owned_by": "local"},
]


# ── URL Builder ───────────────────────────────────────────────────────────────

def _build_llm_url(base_url: str, path: str) -> str:
    """Build a correct LLM endpoint URL avoiding double /v1 when base already ends with /v1.

    Fix: Previously base_url (e.g. 'http://llama-cpp:8080/v1') had /v1 appended again,
    producing '/v1/v1/chat/completions'. Now strips any trailing /v1 suffix before appending.
    """
    # Normalise: strip trailing slash + /v1 suffix if present
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return f"{base}/v1/{path.lstrip('/')}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def log_usage(db: Session, api_key: ApiKey, service: str, model: str,
              input_tokens: int, output_tokens: int, latency_ms: float,
              status_code: int, endpoint: str):
    """Log usage to database and Prometheus metrics.

    Errors in logging don't prevent the response from being returned.
    """
    try:
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

        # Update subscription usage (only on success)
        if 200 <= status_code < 300 and total > 0:
            sub = db.query(Subscription).filter(Subscription.team_id == api_key.team_id).first()
            if sub:
                sub.tokens_used = (sub.tokens_used or 0) + total
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log usage for {service}/{endpoint}: {e}")
        try:
            db.rollback()
        except Exception:
            pass

    # Prometheus metrics should always be updated (best effort)
    try:
        TOKEN_USAGE.labels(model=model, type="input", team_id=str(api_key.team_id)).inc(input_tokens)
        TOKEN_USAGE.labels(model=model, type="output", team_id=str(api_key.team_id)).inc(output_tokens)
    except Exception as e:
        logger.warning(f"Failed to update Prometheus metrics: {e}")


def check_quota(db: Session, team_id) -> bool:
    """Returns True if team has quota remaining.

    If quota check fails, allow the request through (graceful degradation).
    """
    try:
        sub = db.query(Subscription).filter(Subscription.team_id == team_id).first()
        if not sub:
            return True
        return (sub.tokens_used or 0) < sub.token_quota
    except Exception as e:
        logger.error(f"Failed to check quota for team {team_id}: {e}")
        return True


async def get_safe_json(request: Request):
    """Safely parse JSON body, allowing unescaped control characters."""
    try:
        raw_body = await request.body()
        return json.loads(raw_body.decode("utf-8", errors="replace"), strict=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")


# ── Routes ────────────────────────────────────────────────────────────────────

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

    body = await get_safe_json(request)
    model = body.get("model", settings.default_chat_model)
    stream = body.get("stream", False)

    # Inject default system prompt if not present
    messages = body.get("messages", [])
    if not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": settings.default_system_prompt})
        body["messages"] = messages

    start = time.time()

    url = _build_llm_url(settings.llm_base_url, "chat/completions")
    client: httpx.AsyncClient = request.app.state.http_client

    try:
        if stream:
            async def event_stream():
                input_tokens = 0
                output_tokens = 0
                try:
                    try:
                        async with client.stream(
                            "POST",
                            url,
                            json=body,
                            headers={"Content-Type": "application/json"},
                        ) as resp:
                            if resp.status_code != 200:
                                error_body = await resp.aread()
                                logger.error(f"Error response from LLM stream [{resp.status_code}]: {error_body.decode('utf-8', errors='replace')}")
                                error_msg = {
                                    "id": "chatcmpl-error",
                                    "object": "chat.completion.chunk",
                                    "model": model,
                                    "choices": [{"delta": {"content": ""}, "index": 0, "finish_reason": "error"}],
                                    "error": {"message": f"Bad response from AI engine ({resp.status_code})", "type": "server_error"}
                                }
                                yield f"data: {json.dumps(error_msg)}\n\ndata: [DONE]\n\n"
                                return

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
                        # Fix: stub log with 503, 0 tokens — not fake billing data
                        latency = (time.time() - start) * 1000
                        log_usage(db, api_key, "chat", model, 0, 0, latency, 503, "/v1/chat/completions")
                        stub = {
                            "id": "chatcmpl-stub",
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [{"delta": {"content": "[LLM not connected — stub response]"}, "index": 0, "finish_reason": "stop"}],
                        }
                        yield f"data: {json.dumps(stub)}\n\ndata: [DONE]\n\n"
                        return
                    except Exception as e:
                        logger.error(f"Error in chat completion stream: {type(e).__name__}: {e}")
                        error_msg = {
                            "id": "chatcmpl-error",
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [{"delta": {"content": ""}, "index": 0, "finish_reason": "error"}],
                            "error": {"message": "Stream interrupted", "type": "server_error"}
                        }
                        yield f"data: {json.dumps(error_msg)}\n\ndata: [DONE]\n\n"
                    finally:
                        latency = (time.time() - start) * 1000
                        log_usage(db, api_key, "chat", model, input_tokens, output_tokens, latency, 200, "/v1/chat/completions")
                except Exception as e:
                    logger.error(f"Critical error in event_stream generator: {type(e).__name__}: {e}")

            return StreamingResponse(event_stream(), media_type="text/event-stream")
        else:
            try:
                resp = await client.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )

                if resp.status_code != 200:
                    logger.error(f"Error response from LLM [{resp.status_code}]: {resp.text}")
                    latency = (time.time() - start) * 1000
                    log_usage(db, api_key, "chat", model, 0, 0, latency, resp.status_code, "/v1/chat/completions")
                    raise HTTPException(status_code=502, detail=f"Bad response from AI engine ({resp.status_code})")

                try:
                    result = resp.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON response from LLM: {e}. Body: {resp.text}")
                    latency = (time.time() - start) * 1000
                    log_usage(db, api_key, "chat", model, 0, 0, latency, resp.status_code, "/v1/chat/completions")
                    raise HTTPException(status_code=502, detail="Invalid JSON response from AI service")

                usage = result.get("usage", {})
                latency = (time.time() - start) * 1000
                log_usage(db, api_key, "chat", model,
                          usage.get("prompt_tokens", 0),
                          usage.get("completion_tokens", 0),
                          latency, resp.status_code, "/v1/chat/completions")
                return result
            except httpx.ConnectError:
                latency = (time.time() - start) * 1000
                # Fix: log 503 with 0 tokens — previously logged fake 30 tokens with status 200
                log_usage(db, api_key, "chat", model, 0, 0, latency, 503, "/v1/chat/completions")
                return {
                    "id": "chatcmpl-stub",
                    "object": "chat.completion",
                    "model": model,
                    "choices": [{
                        "message": {"role": "assistant", "content": "Hello! I'm running in stub mode (LLM not connected). Configure VLLM_BASE_URL to connect a real model."},
                        "finish_reason": "stop",
                        "index": 0,
                    }],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                }
            except httpx.RequestError as e:
                logger.error(f"HTTP request error in chat_completions: {type(e).__name__}: {e}")
                latency = (time.time() - start) * 1000
                log_usage(db, api_key, "chat", model, 0, 0, latency, 0, "/v1/chat/completions")
                raise HTTPException(status_code=502, detail="Failed to communicate with AI service")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat_completions: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Chat completion service temporarily unavailable. Please try again."
        )

@router.post("/v1/embeddings")
async def embeddings(
    request: Request,
    api_key: ApiKey = Depends(get_current_team_from_api_key),
    db: Session = Depends(get_db),
):
    body = await get_safe_json(request)
    model = body.get("model", settings.default_embedding_model)
    start = time.time()

    url = _build_llm_url(settings.embedding_base_url, "embeddings")
    client: httpx.AsyncClient = request.app.state.http_client

    try:
        try:
                resp = await client.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )

                if resp.status_code != 200:
                    logger.error(f"Error response from LLM embeddings [{resp.status_code}]: {resp.text}")
                    latency = (time.time() - start) * 1000
                    log_usage(db, api_key, "embeddings", model, 0, 0, latency, resp.status_code, "/v1/embeddings")
                    raise HTTPException(status_code=502, detail=f"Bad response from AI engine ({resp.status_code})")

                try:
                    result = resp.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON response from LLM embeddings: {e}. Body: {resp.text}")
                    latency = (time.time() - start) * 1000
                    log_usage(db, api_key, "embeddings", model, 0, 0, latency, resp.status_code, "/v1/embeddings")
                    raise HTTPException(status_code=502, detail="Invalid JSON response from AI service")

                usage = result.get("usage", {})
                latency = (time.time() - start) * 1000
                log_usage(db, api_key, "embeddings", model,
                          usage.get("prompt_tokens", 0), 0, latency, resp.status_code, "/v1/embeddings")
                try:
                    EMBEDDING_REQUESTS.labels(model=model).inc()
                except Exception as e:
                    logger.warning(f"Failed to update embedding metrics: {e}")
                return result
        except httpx.ConnectError:
                # Fix: return stub with 0 tokens and 503 status — not fake billing data
                import random
                embedding = [random.uniform(-0.1, 0.1) for _ in range(1536)]
                latency = (time.time() - start) * 1000
                log_usage(db, api_key, "embeddings", model, 0, 0, latency, 503, "/v1/embeddings")
                return {
                    "object": "list",
                    "model": model,
                    "data": [{"object": "embedding", "index": 0, "embedding": embedding}],
                    "usage": {"prompt_tokens": 0, "total_tokens": 0},
                }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in embeddings: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Embedding service temporarily unavailable. Please try again."
        )


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
    """Chat completions with conversation memory.

    Fix: Previously used chat_completions.__wrapped__ which never existed,
    causing this endpoint to always return a stub response. Now properly
    injects history and calls the LLM directly.
    """
    body = await get_safe_json(request)
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
    new_messages = body.get("messages", [])
    merged_messages = history + new_messages

    # Inject default system prompt if not present
    if not any(m.get("role") == "system" for m in merged_messages):
        merged_messages.insert(0, {"role": "system", "content": settings.default_system_prompt})

    body["messages"] = merged_messages


    # Save last user message to memory before calling LLM
    if contact_id and agent_id and new_messages:
        last = new_messages[-1]
        db.add(AgentMessage(
            agent_id=agent_id,
            contact_id=contact_id,
            role=last.get("role", "user"),
            content=last.get("content", ""),
        ))
        db.commit()

    # Build a fresh Request-like payload and call LLM directly
    model = body.get("model", settings.default_chat_model)
    start = time.time()
    url = _build_llm_url(settings.llm_base_url, "chat/completions")
    client: httpx.AsyncClient = request.app.state.http_client

    try:
        resp = await client.post(url, json=body, headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Bad response from AI engine ({resp.status_code})")
        result = resp.json()

        # Save assistant reply
        if contact_id and agent_id:
            try:
                choices = result.get("choices", [])
                if choices:
                    assistant_content = choices[0].get("message", {}).get("content", "")
                    if assistant_content:
                        db.add(AgentMessage(
                            agent_id=agent_id,
                            contact_id=contact_id,
                            role="assistant",
                            content=assistant_content,
                        ))
                        db.commit()
            except Exception as e:
                logger.warning(f"Failed to save assistant reply to memory: {e}")

        latency = (time.time() - start) * 1000
        usage = result.get("usage", {})
        log_usage(db, api_key, "chat", model,
                  usage.get("prompt_tokens", 0),
                  usage.get("completion_tokens", 0),
                  latency, resp.status_code, "/v1/memchat/completions")
        return result
    except httpx.ConnectError:
        latency = (time.time() - start) * 1000
        log_usage(db, api_key, "chat", model, 0, 0, latency, 503, "/v1/memchat/completions")
        return {
            "id": "memchat-stub",
            "object": "chat.completion",
            "choices": [{"message": {"role": "assistant", "content": "[LLM not connected — stub response]"}, "finish_reason": "stop", "index": 0}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in memchat_completions: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Memory chat service temporarily unavailable.")


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
