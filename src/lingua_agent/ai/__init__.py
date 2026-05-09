from .base import AIProvider, ChatResponse, GenerationError
from .mock import MockProvider

__all__ = ["AIProvider", "ChatResponse", "GenerationError", "MockProvider", "get_provider"]


def get_provider(name: str | None = None):
    """Resolve a provider by name.

    Supported names:
    - `mock`        — deterministic, schema-valid; default and what tests use.
    - `openai`      — any OpenAI-compatible endpoint (OpenAI itself, Ollama,
                      Google AI Studio, DashScope, OpenRouter, vLLM, ...).
    - `anthropic`   — Anthropic API with prompt caching. Needs ANTHROPIC_API_KEY.
    - `claude-max`  — uses your Claude Pro/Max subscription via the Claude
                      Code CLI (no API key, billed against subscription quota).

    Real providers are imported lazily so missing optional deps don't break
    the default `mock` path.
    """
    name = (name or "mock").strip().lower().replace("_", "-")
    if name == "mock":
        return MockProvider()
    if name == "openai":
        from .openai_compatible import OpenAICompatibleProvider
        return OpenAICompatibleProvider()
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name in ("claude-max", "claude-code", "claude-pro"):
        from .claude_agent_sdk_provider import ClaudeAgentSDKProvider
        return ClaudeAgentSDKProvider()
    raise ValueError(f"unknown AI provider: {name!r}")
