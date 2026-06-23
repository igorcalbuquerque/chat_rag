"""Unit tests for the LLM and embedding provider factories.

Provider SDK classes are injected as fake modules via ``sys.modules`` so every
branch is exercised without installing (or calling) the real OpenAI / Anthropic
/ Gemini / Ollama / HuggingFace packages.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from app import config
from app.services import embeddings, llm


def _fake_module(name: str, attr: str):
    """Register a fake provider module exposing ``attr`` as a capturing class."""
    module = types.ModuleType(name)

    class Fake:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    setattr(module, attr, Fake)
    return module, Fake


# --- Embeddings ---
def test_get_embeddings_openai_uses_request_key(monkeypatch):
    module, Fake = _fake_module("langchain_openai", "OpenAIEmbeddings")
    monkeypatch.setitem(sys.modules, "langchain_openai", module)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
    config.get_settings.cache_clear()

    emb = embeddings.get_embeddings(api_key="sk-from-request")
    assert isinstance(emb, Fake)
    assert emb.kwargs["api_key"] == "sk-from-request"  # per-request override wins


def test_get_embeddings_gemini(monkeypatch):
    module, Fake = _fake_module("langchain_google_genai", "GoogleGenerativeAIEmbeddings")
    monkeypatch.setitem(sys.modules, "langchain_google_genai", module)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "gemini")
    monkeypatch.setenv("EMBEDDING_MODEL", "models/text-embedding-004")
    config.get_settings.cache_clear()

    emb = embeddings.get_embeddings()
    assert isinstance(emb, Fake)


def test_get_embeddings_sentence_transformers(monkeypatch):
    module, Fake = _fake_module("langchain_huggingface", "HuggingFaceEmbeddings")
    monkeypatch.setitem(sys.modules, "langchain_huggingface", module)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "sentence-transformers")
    monkeypatch.setenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    config.get_settings.cache_clear()
    embeddings._local_embeddings.cache_clear()

    emb = embeddings.get_embeddings()
    assert isinstance(emb, Fake)
    embeddings._local_embeddings.cache_clear()


def test_get_embeddings_missing_local_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "langchain_huggingface", None)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "sentence-transformers")
    config.get_settings.cache_clear()

    with pytest.raises(ImportError, match="requirements-local"):
        embeddings.get_embeddings()


def test_get_embeddings_unsupported_provider(monkeypatch):
    monkeypatch.setattr(
        embeddings, "get_settings", lambda: SimpleNamespace(embedding_provider="bogus")
    )
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        embeddings.get_embeddings()


# --- LLM ---
def test_get_llm_openai_uses_request_key(monkeypatch):
    module, Fake = _fake_module("langchain_openai", "ChatOpenAI")
    monkeypatch.setitem(sys.modules, "langchain_openai", module)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    config.get_settings.cache_clear()

    model = llm.get_llm(api_key="sk-req")
    assert isinstance(model, Fake)
    assert model.kwargs["api_key"] == "sk-req"


def test_get_llm_anthropic(monkeypatch):
    module, Fake = _fake_module("langchain_anthropic", "ChatAnthropic")
    monkeypatch.setitem(sys.modules, "langchain_anthropic", module)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-3-5-sonnet-latest")
    config.get_settings.cache_clear()

    assert isinstance(llm.get_llm(), Fake)


def test_get_llm_gemini(monkeypatch):
    module, Fake = _fake_module("langchain_google_genai", "ChatGoogleGenerativeAI")
    monkeypatch.setitem(sys.modules, "langchain_google_genai", module)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-1.5-flash")
    config.get_settings.cache_clear()

    model = llm.get_llm()
    assert isinstance(model, Fake)
    assert "google_api_key" in model.kwargs


def test_get_llm_ollama(monkeypatch):
    module, Fake = _fake_module("langchain_ollama", "ChatOllama")
    monkeypatch.setitem(sys.modules, "langchain_ollama", module)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3")
    config.get_settings.cache_clear()

    model = llm.get_llm()
    assert isinstance(model, Fake)
    assert model.kwargs["base_url"]


def test_get_llm_provider_override_uses_provider_default_model(monkeypatch):
    module, Fake = _fake_module("langchain_anthropic", "ChatAnthropic")
    monkeypatch.setitem(sys.modules, "langchain_anthropic", module)
    monkeypatch.setenv("LLM_PROVIDER", "openai")  # server default
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    config.get_settings.cache_clear()

    # Per-request override to a different provider -> uses that provider's
    # default model (not the OpenAI model name).
    model = llm.get_llm(provider="anthropic")
    assert isinstance(model, Fake)
    assert model.kwargs["model"] == "claude-3-5-sonnet-latest"


def test_get_llm_unsupported_provider(monkeypatch):
    monkeypatch.setattr(
        llm,
        "get_settings",
        lambda: SimpleNamespace(llm_provider="bogus", llm_model="x"),
    )
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        llm.get_llm()
