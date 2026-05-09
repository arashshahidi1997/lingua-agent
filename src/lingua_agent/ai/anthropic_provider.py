"""Anthropic provider (Phase 5 — stub). See openai_compatible.py."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from ..config import Settings
from .base import ChatMessage, ChatResponse, GenerationError

T = TypeVar("T", bound=BaseModel)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()
        if not self.settings.anthropic_api_key:
            raise GenerationError(
                "ANTHROPIC_API_KEY is not set. Set it in your environment or switch LINGUA_AI_PROVIDER=mock."
            )

    def generate_structured(self, prompt: str, schema: type[T], *, context: dict[str, Any] | None = None) -> T:
        raise NotImplementedError("Anthropic provider is a Phase 5 deliverable. Use mock for MVP.")

    def chat(self, messages: list[ChatMessage], *, tools: list[dict[str, Any]] | None = None) -> ChatResponse:
        raise NotImplementedError("Anthropic provider is a Phase 5 deliverable. Use mock for MVP.")
