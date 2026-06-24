"""Embedding provider factory.

Returns a LangChain ``Embeddings`` instance selected by configuration so the
rest of the code is provider-agnostic. Supports OpenAI, Google Gemini and a
fully local, zero-cost option via Sentence-Transformers.

``api_key`` lets a caller override the configured provider key per request
(bring-your-own-key). When omitted, the key from the environment is used. The
local Sentence-Transformers model is cached (it is expensive to load); the
API-based clients are cheap to construct per call.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import get_settings


@lru_cache
def _local_embeddings(model_name: str) -> Embeddings:
    """Cached Sentence-Transformers embeddings (no API key needed)."""
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=model_name)


def get_embeddings(api_key: str | None = None) -> Embeddings:
    """Build the configured embedding client, optionally with a per-request key."""
    settings = get_settings()

    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        # OpenAI caps a single embeddings request at 300k tokens. Our chunks are
        # ~chunk_size tokens each, so cap how many we send per request to stay
        # safely under that limit; otherwise large documents fail with a 400.
        batch = max(1, 250_000 // max(settings.chunk_size, 1))
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=api_key or settings.openai_api_key,
            chunk_size=batch,
        )

    if settings.embedding_provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=api_key or settings.google_api_key,
        )

    if settings.embedding_provider == "sentence-transformers":
        try:
            import langchain_huggingface  # noqa: F401
        except ImportError as exc:  # optional heavy dependency
            raise ImportError(
                "EMBEDDING_PROVIDER=sentence-transformers requires the optional "
                "local embedding stack. Install it with "
                "`pip install -r requirements-local.txt` or rebuild the image "
                "with INSTALL_LOCAL_EMBEDDINGS=true."
            ) from exc

        return _local_embeddings(settings.embedding_model)

    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
