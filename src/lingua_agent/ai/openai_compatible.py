"""OpenAI-compatible provider (Phase 5 — stub).

Wired up but raises until activated. Implementing the actual call is a Phase 5
task: needs `openai` extras installed, schema-aware JSON mode with retries,
and prompt-cache headers. See `docs/roadmap.md`.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from ..config import Settings
from .base import ChatMessage, ChatResponse, GenerationError

T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()
        if not self.settings.openai_api_key:
            raise GenerationError(
                "OPENAI_API_KEY is not set. Set it in your environment or switch LINGUA_AI_PROVIDER=mock."
            )

    def generate_structured(self, prompt: str, schema: type[T], *, context: dict[str, Any] | None = None) -> T:
        raise NotImplementedError("OpenAI-compatible provider is a Phase 5 deliverable. Use mock for MVP.")

    def chat(self, messages: list[ChatMessage], *, tools: list[dict[str, Any]] | None = None) -> ChatResponse:
        raise NotImplementedError("OpenAI-compatible provider is a Phase 5 deliverable. Use mock for MVP.")
