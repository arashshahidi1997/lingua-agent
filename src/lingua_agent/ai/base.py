"""Provider Protocol + shared response types."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel


class GenerationError(RuntimeError):
    """Raised when a provider fails to produce schema-valid output after retries."""


class ChatMessage(BaseModel):
    role: str
    content: str
    name: str | None = None


class ChatResponse(BaseModel):
    content: str
    tool_calls: list[dict[str, Any]] = []
    raw: dict[str, Any] | None = None


T = TypeVar("T", bound=BaseModel)


class AIProvider(Protocol):
    name: str

    def generate_structured(self, prompt: str, schema: type[T], *, context: dict[str, Any] | None = None) -> T:
        ...

    def chat(self, messages: list[ChatMessage], *, tools: list[dict[str, Any]] | None = None) -> ChatResponse:
        ...
