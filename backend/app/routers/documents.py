"""Documents router: list indexed documents."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.schemas import DocumentInfo
from app.services.documents import list_documents

router = APIRouter()


@router.get("/documents", response_model=list[DocumentInfo])
def get_documents(user: dict = Depends(get_current_user)) -> list[DocumentInfo]:
    """Return metadata for the authenticated user's indexed documents."""
    return [DocumentInfo(**doc) for doc in list_documents(user["user_id"])]
