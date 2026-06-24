"""Chat router: RAG question answering with optional SSE streaming."""

from __future__ import annotations

import json
from typing import Iterator

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.config import SUPPORTED_LLM_PROVIDERS
from app.dependencies import get_current_user
from app.models.schemas import ChatRequest, ChatResponse, Source
from app.services.history import append_message
from app.services.rag_graph import run_rag, stream_rag

router = APIRouter()


def _validate_provider(provider: str | None) -> str | None:
    """Reject an unsupported per-request LLM provider with a clear 400."""
    if provider and provider not in SUPPORTED_LLM_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported LLM provider '{provider}'. "
                f"Supported: {', '.join(SUPPORTED_LLM_PROVIDERS)}."
            ),
        )
    return provider


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_llm_provider: str | None = Header(default=None, alias="X-LLM-Provider"),
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Answer a question using the full RAG pipeline (non-streaming).

    ``X-API-Key`` overrides the provider key and ``X-LLM-Provider`` overrides
    the chat model provider, both per request and both optional. Retrieval and
    history are scoped to the authenticated user.
    """
    provider = _validate_provider(x_llm_provider)
    user_id = user["user_id"]
    result = run_rag(
        request.question,
        request.session_id,
        request.top_k,
        x_api_key,
        provider,
        user_id,
    )

    append_message(request.session_id, "user", request.question, user_id)
    append_message(request.session_id, "assistant", result["answer"], user_id)

    return ChatResponse(
        answer=result["answer"],
        sources=[Source(**s) for s in result["sources"]],
        session_id=request.session_id,
    )


@router.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_llm_provider: str | None = Header(default=None, alias="X-LLM-Provider"),
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the answer token by token via Server-Sent Events.

    Emits ``token`` events while generating and a final ``done`` event with
    the sources and full answer.
    """
    provider = _validate_provider(x_llm_provider)
    user_id = user["user_id"]
    tokens, sources = stream_rag(
        request.question,
        request.session_id,
        request.top_k,
        x_api_key,
        provider,
        user_id,
    )

    def event_stream() -> Iterator[str]:
        collected: list[str] = []
        for token in tokens:
            collected.append(token)
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

        answer = "".join(collected)
        append_message(request.session_id, "user", request.question, user_id)
        append_message(request.session_id, "assistant", answer, user_id)

        payload = {
            "answer": answer,
            "sources": sources,
            "session_id": request.session_id,
        }
        yield f"event: done\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
