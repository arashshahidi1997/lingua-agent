"""SRS entities: Flashcard and ReviewEvent."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, Field

from .base import Provenance, utcnow


class CardDirection(str, Enum):
    RECOGNITION = "recognition"  # target → source/support
    PRODUCTION = "production"    # source/support → target
    CLOZE = "cloze"


class CardType(str, Enum):
    VOCAB = "vocab"
    SENTENCE = "sentence"
    GRAMMAR = "grammar"
    CLOZE = "cloze"


def _epoch() -> datetime:
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


class Flashcard(BaseModel):
    id: str
    front: str
    back: str
    source_language: str
    target_language: str
    direction: CardDirection
    card_type: CardType
    vocabulary_item_id: str | None = None
    sentence_id: str | None = None
    mnemonic: str | None = None
    examples: list[str] = Field(default_factory=list)
    audio_ref: str | None = None
    image_ref: str | None = None
    tags: list[str] = Field(default_factory=list)

    # SM-2 state
    due_at: datetime = Field(default_factory=utcnow)
    interval: int = 0           # days
    ease_factor: float = 2.5    # floor 1.3
    repetitions: int = 0        # consecutive correct (n)
    lapses: int = 0             # added beyond upstream SM-2 to ease FSRS migration
    needs_extra_review: bool = False  # SM-2 q==3 same-day flag

    provenance: Provenance = Field(default_factory=Provenance)
    created_at: datetime = Field(default_factory=utcnow)

    def is_due(self, *, now: datetime | None = None) -> bool:
        now = now or utcnow()
        return self.due_at <= now


class ReviewEvent(BaseModel):
    id: str
    card_id: str
    rating: int = Field(ge=0, le=5)
    reviewed_at: datetime = Field(default_factory=utcnow)
    interval_before: int
    interval_after: int
    ease_before: float
    ease_after: float
    repetitions_before: int
    repetitions_after: int


def in_days(n: int) -> timedelta:
    return timedelta(days=n)
