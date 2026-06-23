"""FastAPI application entry point.

Wires up CORS, the API routers and a startup hook that ensures the Redis
vector index exists before the first request is served.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import HealthResponse
from app.routers import chat, documents, upload
from app.services import redis_client

logger = logging.getLogger("chat_rag")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the Redis vector index on startup (best-effort)."""
    try:
        redis_client.ensure_index()
        logger.info("Redis vector index is ready.")
    except Exception as exc:  # pragma: no cover - startup diagnostics only
        logger.warning("Could not ensure Redis index on startup: %s", exc)
    yield


app = FastAPI(title="Chat com Documentos via RAG", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, tags=["upload"])
app.include_router(documents.router, tags=["documents"])
app.include_router(chat.router, tags=["chat"])


@app.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    """Liveness probe reporting Redis connectivity.

    Returns HTTP 503 when Redis is unreachable so the Docker Compose
    healthcheck marks the API as unhealthy instead of falsely "ok".
    """
    connected = redis_client.ping()
    if not connected:
        response.status_code = 503
    return HealthResponse(
        status="ok" if connected else "error",
        redis="connected" if connected else "disconnected",
    )
