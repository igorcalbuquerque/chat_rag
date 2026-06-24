"""FastAPI application entry point.

Wires up CORS, the API routers and a startup hook that ensures the Redis
vector index exists before the first request is served.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import (
    AUTH_PROVIDERS,
    DEFAULT_SESSION_SECRET,
    KEY_PROVIDERS,
    SUPPORTED_LLM_PROVIDERS,
    get_settings,
)
from app.models.schemas import ConfigResponse, HealthResponse
from app.routers import auth, chat, documents, upload
from app.services import redis_client

logger = logging.getLogger("chat_rag")
logging.basicConfig(level=logging.INFO)


def _validate_startup_config() -> None:
    """Fail fast on dangerous misconfiguration; warn on risky-but-valid ones."""
    settings = get_settings()
    # A weak signing secret with auth on lets anyone forge login tokens.
    if settings.auth_enabled and settings.session_secret == DEFAULT_SESSION_SECRET:
        raise RuntimeError(
            "SESSION_SECRET is still the insecure default while AUTH_ENABLED=true. "
            "Set SESSION_SECRET to a strong random value before starting in "
            "production (e.g. `python -c 'import secrets; print(secrets.token_urlsafe(32))'`)."
        )
    # An unknown embedding model means the index is sized with DEFAULT_DIMENSION,
    # which may not match the model's real output and break KNN retrieval.
    if not settings.embedding_model_is_known:
        logger.warning(
            "Embedding model %r has no known dimension; the Redis index is sized "
            "with the default %d. Verify it matches the model's real output.",
            settings.embedding_model,
            settings.embedding_dimension,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate config and create the Redis vector index on startup."""
    _validate_startup_config()
    try:
        redis_client.ensure_index()
        logger.info("Redis vector index is ready.")
    except Exception as exc:  # pragma: no cover - startup diagnostics only
        logger.warning("Could not ensure Redis index on startup: %s", exc)
    yield


app = FastAPI(title="Chat com Documentos via RAG", version="1.0.0", lifespan=lifespan)

# The API authenticates with a bearer token (no cross-site cookies), so a
# wildcard origin without credentials is the correct, valid CORS combination.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Needed for the OAuth handshake (Authlib stores state/nonce in the session
# cookie). Harmless when login is disabled: no cookie is set unless written.
app.add_middleware(SessionMiddleware, secret_key=get_settings().session_secret)

app.include_router(auth.router, tags=["auth"])
app.include_router(upload.router, tags=["upload"])
app.include_router(documents.router, tags=["documents"])
app.include_router(chat.router, tags=["chat"])


@app.get("/")
def root() -> dict:
    """Friendly landing payload for the API's primary URL.

    The API has no web UI of its own (the React frontend is a separate service),
    so the root just points to the docs and health probe instead of a bare 404.
    """
    return {
        "service": "Chat com Documentos via RAG — API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


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


@app.get("/config", response_model=ConfigResponse)
def config_info() -> ConfigResponse:
    """Report the configured providers so the UI can guide the API-key field."""
    settings = get_settings()
    key_providers: list[str] = []
    for provider in (settings.llm_provider, settings.embedding_provider):
        if provider in KEY_PROVIDERS and provider not in key_providers:
            key_providers.append(provider)
    return ConfigResponse(
        llm_provider=settings.llm_provider,
        embedding_provider=settings.embedding_provider,
        supported_llm_providers=list(SUPPORTED_LLM_PROVIDERS),
        key_providers=key_providers,
        requires_api_key=bool(key_providers),
        auth_enabled=settings.auth_enabled,
        auth_providers=list(AUTH_PROVIDERS) if settings.auth_enabled else [],
    )
