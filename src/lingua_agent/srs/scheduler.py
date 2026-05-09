"""Scheduler protocol — pluggable so SM-2 can be swapped for FSRS later."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Protocol

from ..models.srs import Flashcard, ReviewEvent


class Scheduler(Protocol):
    name: str

    def update(self, card: Flashcard, rating: int, *, reviewed_at: datetime | None = None) -> tuple[Flashcard, ReviewEvent]:
        """Apply a rating (0..5) and return the mutated card + a review event."""

    def due(self, cards: Iterable[Flashcard], *, now: datetime | None = None) -> list[Flashcard]:
        ...
