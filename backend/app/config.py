"""Application configuration loaded from environment variables.

All tunables (LLM/embedding provider, Redis URL, chunking parameters) are
centralized here so the rest of the codebase never reads ``os.environ``
directly. Values are validated by ``pydantic-settings``.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Known embedding dimensions per model. Used to size the Redis vector index.
EMBEDDING_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
}

DEFAULT_DIMENSION = 384


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ----- Providers -----------------------------------------------------
    llm_provider: Literal["openai", "anthropic", "ollama"] = "ollama"
    embedding_provider: Literal["openai", "sentence-transformers"] = (
        "sentence-transformers"
    )

    # ----- Model names ---------------------------------------------------
    llm_model: str = "llama3"
    embedding_model: str = "all-MiniLM-L6-v2"

    # ----- API keys / endpoints -----------------------------------------
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # ----- Redis ---------------------------------------------------------
    redis_url: str = "redis://localhost:6379"
    redis_index_name: str = "docs"
    redis_key_prefix: str = "doc:"

    # ----- RAG / chunking ------------------------------------------------
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    history_size: int = 6  # number of past messages kept per session

    # ----- Generation ----------------------------------------------------
    llm_temperature: float = 0.0
    max_tokens: int = 1024

    @property
    def embedding_dimension(self) -> int:
        """Vector dimension for the configured embedding model."""
        return EMBEDDING_DIMENSIONS.get(self.embedding_model, DEFAULT_DIMENSION)


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
