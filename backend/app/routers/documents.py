"""Documents router: list indexed documents."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import DocumentInfo
from app.services.documents import list_documents

router = APIRouter()


@router.get("/documents", response_model=list[DocumentInfo])
def get_documents() -> list[DocumentInfo]:
    """Return metadata for every document indexed in the vector store."""
    return [DocumentInfo(**doc) for doc in list_documents()]
