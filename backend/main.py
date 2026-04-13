"""Main FastAPI application — AI Platform Gateway"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import get_settings
from metrics import MetricsMiddleware, metrics_endpoint
from routes import auth, keys, usage, gateway, rag, agents, billing, webhooks, teams

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create upload directory
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield


app = FastAPI(
    title="AI Platform API",
    version="1.0.0",
    description="Multi-tenant AI Platform — OpenAI-compatible gateway with RAG, agents, and analytics",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(MetricsMiddleware)

# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(keys.router)
app.include_router(usage.router)
app.include_router(gateway.router)
app.include_router(rag.router)
app.include_router(agents.router)
app.include_router(billing.router)
app.include_router(webhooks.router)
app.include_router(teams.router)


# ── Health + Metrics ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-platform-api"}


@app.get("/metrics")
async def metrics():
    return await metrics_endpoint()


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )
