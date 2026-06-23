"""Embedding provider factory.

Returns a LangChain ``Embeddings`` instance selected by configuration so the
rest of the code is provider-agnostic. Supports the paid OpenAI models and a
fully local, zero-cost option via Sentence-Transformers.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import get_settings


@lru_cache
def get_embeddings() -> Embeddings:
    """Build (and cache) the configured embedding client."""
    settings = get_settings()

    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

    if settings.embedding_provider == "sentence-transformers":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=settings.embedding_model)

    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
