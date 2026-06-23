"""Pydantic models for API request/response payloads."""

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Upload / ingestion
# --------------------------------------------------------------------------
class IngestedFile(BaseModel):
    """Result of ingesting a single uploaded file."""

    file_id: str
    name: str
    chunks_indexed: int
    status: str = "indexed"


class UploadResponse(BaseModel):
    """Response for ``POST /upload`` (supports multiple files)."""

    files: list[IngestedFile]
    # Convenience fields for the common single-file upload.
    file_id: str | None = None
    chunks_indexed: int | None = None
    status: str = "ok"


# --------------------------------------------------------------------------
# Documents listing / deletion
# --------------------------------------------------------------------------
class DocumentInfo(BaseModel):
    """Metadata describing an indexed document."""

    file_id: str
    name: str
    uploaded_at: str
    chunks: int


class DeleteResponse(BaseModel):
    deleted: bool


# --------------------------------------------------------------------------
# Chat / RAG
# --------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Payload for ``POST /chat``."""

    question: str = Field(..., min_length=1)
    session_id: str = "default"
    top_k: int | None = None


class Source(BaseModel):
    """A single retrieved chunk used to build the answer."""

    chunk: str
    source: str
    score: float
    chunk_index: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    session_id: str


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    redis: str
