from .base import AIProvider, ChatResponse, GenerationError
from .mock import MockProvider

__all__ = ["AIProvider", "ChatResponse", "GenerationError", "MockProvider", "get_provider"]


def get_provider(name: str | None = None):
    """Resolve a provider by name (`mock` / `openai` / `anthropic`).

    Real providers are imported lazily so missing optional deps don't break
    the default `mock` path.
    """
    name = (name or "mock").strip().lower()
    if name == "mock":
        return MockProvider()
    if name == "openai":
        from .openai_compatible import OpenAICompatibleProvider
        return OpenAICompatibleProvider()
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    raise ValueError(f"unknown AI provider: {name!r}")
