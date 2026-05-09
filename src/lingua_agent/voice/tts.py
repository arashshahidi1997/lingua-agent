from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class SynthesisResult(BaseModel):
    audio: bytes
    sample_rate: int
    mime_type: str = "audio/wav"


class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str, *, language: str, voice: str | None = None) -> SynthesisResult: ...
