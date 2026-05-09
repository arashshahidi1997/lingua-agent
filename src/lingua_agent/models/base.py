"""Shared model primitives."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Provenance(BaseModel):
    """Where a piece of model-generated content came from. Attached to every
    entity field that may be authored by an AI provider rather than the user."""

    generated: bool = False
    model: str | None = None
    source_doc_id: str | None = None
    confidence: Literal["high", "medium", "low", "uncertain"] | None = None
    created_at: datetime = Field(default_factory=utcnow)

    @classmethod
    def by_user(cls) -> "Provenance":
        return cls(generated=False)

    @classmethod
    def by_model(cls, model: str, *, source_doc_id: str | None = None,
                 confidence: Literal["high", "medium", "low", "uncertain"] = "medium") -> "Provenance":
        return cls(generated=True, model=model, source_doc_id=source_doc_id, confidence=confidence)
