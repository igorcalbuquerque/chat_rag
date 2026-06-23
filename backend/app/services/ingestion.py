"""Document ingestion pipeline: parse -> chunk -> embed -> index in Redis.

Supported formats: PDF (via ``pypdf``) and plain text. Each chunk is stored as
a Redis HASH so RediSearch can run KNN vector queries over the embeddings.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.config import get_settings
from app.services.embeddings import get_embeddings
from app.services.redis_client import get_redis


class UnsupportedFileType(ValueError):
    """Raised when an uploaded file has an unsupported extension."""


def _extract_text(filename: str, data: bytes) -> str:
    """Extract raw text from a PDF or TXT payload."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if lower.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    raise UnsupportedFileType(f"Unsupported file type: {filename}")


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks sized by tokens.

    ``CHUNK_SIZE``/``CHUNK_OVERLAP`` are measured in tokens (tiktoken) rather
    than characters, matching how embedding/LLM context budgets are counted.
    """
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    return [c for c in splitter.split_text(text) if c.strip()]


def _to_float32_bytes(vector: list[float]) -> bytes:
    """Serialize an embedding vector to the float32 bytes Redis expects."""
    return np.asarray(vector, dtype=np.float32).tobytes()


def ingest_file(filename: str, data: bytes) -> dict:
    """Run the full ingestion pipeline for a single file.

    Returns a dict with ``file_id``, ``name``, ``chunks_indexed`` and
    ``status`` so the upload endpoint can serialize it directly.
    """
    settings = get_settings()
    text = _extract_text(filename, data)
    chunks = chunk_text(text)

    if not chunks:
        return {
            "file_id": str(uuid.uuid4()),
            "name": filename,
            "chunks_indexed": 0,
            "status": "empty",
        }

    embeddings = get_embeddings().embed_documents(chunks)

    file_id = str(uuid.uuid4())
    uploaded_at = datetime.now(timezone.utc).isoformat()
    client = get_redis()
    pipe = client.pipeline()

    for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        key = f"{settings.redis_key_prefix}{file_id}:chunk:{idx}"
        pipe.hset(
            key,
            mapping={
                "content": chunk,
                "source": filename,
                "file_id": file_id,
                "chunk_index": idx,
                "uploaded_at": uploaded_at,
                "embedding": _to_float32_bytes(vector),
            },
        )
    pipe.execute()

    return {
        "file_id": file_id,
        "name": filename,
        "chunks_indexed": len(chunks),
        "status": "indexed",
    }
