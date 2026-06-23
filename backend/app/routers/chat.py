"""Chat router: RAG question answering with optional SSE streaming."""

from __future__ import annotations

import json
from typing import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse, Source
from app.services.history import append_message
from app.services.rag_graph import run_rag, stream_rag

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Answer a question using the full RAG pipeline (non-streaming)."""
    result = run_rag(request.question, request.session_id, request.top_k)

    append_message(request.session_id, "user", request.question)
    append_message(request.session_id, "assistant", result["answer"])

    return ChatResponse(
        answer=result["answer"],
        sources=[Source(**s) for s in result["sources"]],
        session_id=request.session_id,
    )


@router.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream the answer token by token via Server-Sent Events.

    Emits ``token`` events while generating and a final ``done`` event with
    the sources and full answer.
    """
    tokens, sources = stream_rag(request.question, request.session_id, request.top_k)

    def event_stream() -> Iterator[str]:
        collected: list[str] = []
        for token in tokens:
            collected.append(token)
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

        answer = "".join(collected)
        append_message(request.session_id, "user", request.question)
        append_message(request.session_id, "assistant", answer)

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
