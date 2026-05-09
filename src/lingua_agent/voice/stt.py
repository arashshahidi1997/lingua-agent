from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class TranscriptionResult(BaseModel):
    text: str
    language: str | None = None
    confidence: float | None = None


class STTProvider(Protocol):
    name: str

    def transcribe(self, audio: bytes, *, language_hint: str | None = None) -> TranscriptionResult: ...
