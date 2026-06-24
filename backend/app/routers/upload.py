"""Upload router: ingest one or more documents into the vector store."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from app.dependencies import get_current_user
from app.models.schemas import IngestedFile, UploadResponse
from app.services.documents import delete_document
from app.services.ingestion import (
    TextExtractionError,
    UnsupportedFileType,
    ingest_file,
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

    user_id = user["user_id"]
    ingested: list[IngestedFile] = []
    for upload_file in files:
        data = await upload_file.read()
        try:
            result = ingest_file(
                upload_file.filename or "unknown", data, x_api_key, user_id
            )
        except UnsupportedFileType as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except TextExtractionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        ingested.append(IngestedFile(**result))

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
