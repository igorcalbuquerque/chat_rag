"""LLM provider factory.

Returns a LangChain chat model selected by configuration. Supports OpenAI,
Anthropic, Google Gemini and a fully local Ollama option so the system runs
with or without paid API credits.

``api_key`` lets a caller override the configured provider key per request
(bring-your-own-key). When omitted, the key from the environment is used.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings


def get_llm(api_key: str | None = None, provider: str | None = None) -> BaseChatModel:
    """Build a chat model.

    ``provider`` overrides the configured LLM provider per request (the visitor
    can pick OpenAI/Anthropic/Gemini/Ollama in the UI); ``api_key`` overrides
    that provider's key. Both fall back to the server configuration when omitted.
    The model name follows the provider so a per-request provider doesn't reuse
    a model name meant for another one.
    """
    settings = get_settings()
    provider = provider or settings.llm_provider
    # Use the configured model only when it matches the configured provider;
    # otherwise fall back to a sensible default for the chosen provider.
    model = settings.llm_model if provider == settings.llm_provider else None

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=api_key or settings.openai_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.max_tokens,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model or "claude-3-5-sonnet-latest",
            api_key=api_key or settings.anthropic_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.max_tokens,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model or "gemini-1.5-flash",
            google_api_key=api_key or settings.google_api_key,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.max_tokens,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model or "llama3",
            base_url=settings.ollama_base_url,
            temperature=settings.llm_temperature,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")
