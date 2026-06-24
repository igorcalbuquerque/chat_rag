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
    "models/text-embedding-004": 768,
    "text-embedding-004": 768,
}

DEFAULT_DIMENSION = 384

# LLM providers the visitor can pick from in the frontend.
SUPPORTED_LLM_PROVIDERS = ("openai", "anthropic", "gemini", "ollama")
# Providers that authenticate with an API key (vs local Ollama / Sentence-T.).
KEY_PROVIDERS = ("openai", "anthropic", "gemini")

# OAuth login providers offered when AUTH_ENABLED is on.
AUTH_PROVIDERS = ("google", "github")
# user_id used when auth is disabled (local dev): everything is scoped to it,
# so the same data-isolation code path runs with or without login.
PUBLIC_USER_ID = "public"


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Providers ---
    llm_provider: Literal["openai", "anthropic", "ollama", "gemini"] = "ollama"
    embedding_provider: Literal[
        "openai", "sentence-transformers", "gemini"
    ] = "sentence-transformers"

    # --- Model names ---
    llm_model: str = "llama3"
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- API keys / endpoints ---
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379"
    redis_index_name: str = "docs"
    redis_key_prefix: str = "doc:"

    # --- RAG / chunking ---
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    # HNSW search breadth at query time. Higher = better recall (finds the true
    # nearest neighbours even in large/skewed indexes), at a small latency cost.
    ef_runtime: int = 128
    history_size: int = 6  # past messages kept per session for context

    # --- Generation ---
    llm_temperature: float = 0.0
    max_tokens: int = 1024

    # --- OCR (optional, for scanned PDFs) ---
    ocr_language: str = "por+eng"
    ocr_dpi: int = 200

    # --- Authentication (optional; OFF for local dev, ON in production) ---
    # When false, the app is open and all data is scoped to PUBLIC_USER_ID.
    # When true, visitors must log in via Google/GitHub and each user only
    # sees their own documents and conversations.
    auth_enabled: bool = False
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    github_oauth_client_id: str | None = None
    github_oauth_client_secret: str | None = None
    # Signs both the OAuth handshake session cookie and the issued bearer token.
    # MUST be overridden with a strong random value in production.
    session_secret: str = "dev-insecure-secret-change-me"
    # Where the OAuth callback redirects the browser back to after login.
    frontend_url: str = "/"
    # Public base URL of this backend (e.g. https://chat-rag-api.onrender.com).
    # Used to build the OAuth redirect URI so it exactly matches what is
    # registered in the provider console (avoids http/https proxy mismatches).
    # When unset, the URL is derived from the incoming request.
    backend_url: str | None = None
    # Lifetime of an issued login token.
    token_ttl_seconds: int = 60 * 60 * 8

    @property
    def embedding_dimension(self) -> int:
        """Vector dimension for the configured embedding model."""
        return EMBEDDING_DIMENSIONS.get(self.embedding_model, DEFAULT_DIMENSION)


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
