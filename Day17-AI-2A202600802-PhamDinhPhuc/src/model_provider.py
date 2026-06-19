from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """Student TODO: define the provider configuration shared by the agents.

    Required providers for this lab:
    - openai
    - custom (OpenAI-compatible base URL)
    - gemini
    - anthropic
    - ollama
    - openrouter
    """

    provider: str
    model_name: str
    temperature: float
    api_key: str | None = None
    base_url: str | None = None


def normalize_provider(value: str) -> str:
    """Map aliases to standard provider names."""
    val = value.strip().lower()
    if val in ("openai", "open-ai"):
        return "openai"
    if val in ("google", "gemini", "google-genai"):
        return "gemini"
    if val in ("anthropic", "anthorpic"):
        return "anthropic"
    if val in ("ollama",):
        return "ollama"
    if val in ("openrouter",):
        return "openrouter"
    if val in ("custom",):
        return "custom"
    return val


def build_chat_model(config: ProviderConfig):
    """Instantiate the real chat model for the selected provider."""
    prov = normalize_provider(config.provider)
    
    if prov == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key
        )
    elif prov == "custom":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
            base_url=config.base_url
        )
    elif prov == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key
        )
    elif prov == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key
        )
    elif prov == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=config.model_name,
                temperature=config.temperature,
                base_url=config.base_url
            )
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOllama
                return ChatOllama(
                    model=config.model_name,
                    temperature=config.temperature,
                    base_url=config.base_url
                )
            except ImportError:
                raise RuntimeError("langchain-ollama and langchain-community are not installed properly")
    elif prov == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")

