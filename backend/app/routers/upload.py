"""Upload router: ingest one or more documents into the vector store."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from app.config import get_settings
from app.dependencies import get_current_user
from app.models.schemas import IngestedFile, UploadResponse
from app.services.documents import delete_document
from app.services.ingestion import (
    TextExtractionError,
    UnsupportedFileType,
    index_prepared,
    prepare_file,
)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload(
    files: list[UploadFile] = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    user: dict = Depends(get_current_user),
) -> UploadResponse:
    """Receive file(s) and trigger the ingestion pipeline for each.

    ``X-API-Key`` (optional) overrides the server's embedding provider key.
    Ingested documents are tagged with the authenticated user's id.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    settings = get_settings()
    if len(files) > settings.max_files_per_request:
        raise HTTPException(
            status_code=413,
            detail=f"Too many files (max {settings.max_files_per_request} per request).",
        )

    user_id = user["user_id"]

    # Phase 1: read + extract + embed every file before touching Redis. Any
    # failure here aborts the whole request, so a partial upload never leaves
    # some files indexed and others not (all-or-nothing).
    prepared = []
    for upload_file in files:
        data = await upload_file.read()
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File '{upload_file.filename}' exceeds the "
                    f"{settings.max_upload_mb} MB limit."
                ),
            )
        try:
            prepared.append(
                prepare_file(upload_file.filename or "unknown", data, x_api_key)
            )
        except UnsupportedFileType as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except TextExtractionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Phase 2: every file prepared cleanly, so index them all.
    ingested = [IngestedFile(**index_prepared(p, user_id)) for p in prepared]

    first = ingested[0]
    return UploadResponse(
        files=ingested,
        file_id=first.file_id,
        chunks_indexed=first.chunks_indexed,
        status="ok",
    )


@router.delete("/documents/{file_id}")
def delete(file_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Remove a document and all of its vectors from Redis (owner only)."""
    deleted = delete_document(file_id, user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"deleted": True}
