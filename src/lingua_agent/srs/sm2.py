"""SM-2 spaced-repetition scheduler.

Algorithm reference: https://github.com/open-spaced-repetition/sm-2 (MIT).
Re-implemented in pure Python with the upstream semantics:

    rating  effect
    0..2    lapse: n=0, I=0, due=now, EF unchanged, lapses += 1
    3       correct-but-hard: update EF, recompute interval, mark needs_extra_review
            and set due=now (same-day re-review). Only on a successful follow-up
            (rating ≥ 4) do we actually schedule due += interval.
    4..5    correct: update EF, recompute interval, due += interval

Interval rule: n==0 → 1d, n==1 → 6d, n>=2 → ceil(I × EF). EF floor 1.3.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Iterable

from ..ids import make_id
from ..models.base import utcnow
from ..models.srs import Flashcard, ReviewEvent


EF_MIN = 1.3


def _ef_delta(q: int) -> float:
    # Standard SM-2 EF update: q=5 +0.10, q=4 0.00, q=3 −0.14, ≤2 unchanged.
    return 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)


def _next_interval(n: int, current_interval: int, ef: float) -> int:
    if n == 0:
        return 1
    if n == 1:
        return 6
    return max(1, math.ceil(current_interval * ef))


def _ensure_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class SM2Scheduler:
    name = "sm2"

    def update(
        self,
        card: Flashcard,
        rating: int,
        *,
        reviewed_at: datetime | None = None,
    ) -> tuple[Flashcard, ReviewEvent]:
        if not 0 <= rating <= 5:
            raise ValueError(f"rating must be in 0..5, got {rating}")
        now = _ensure_aware(reviewed_at or utcnow())

        # Snapshot for the audit event.
        ef_before = card.ease_factor
        interval_before = card.interval
        reps_before = card.repetitions

        if card.needs_extra_review:
            # Same-day follow-up after a previous q==3.
            if rating >= 4:
                card.needs_extra_review = False
                card.due_at = now + timedelta(days=card.interval)
            # else: stay flagged, keep due=now, do nothing.
        elif rating >= 3:
            # Correct path.
            new_ef = max(EF_MIN, card.ease_factor + _ef_delta(rating))
            new_interval = _next_interval(card.repetitions, card.interval, new_ef)
            card.ease_factor = new_ef
            card.interval = new_interval
            card.repetitions += 1
            if rating >= 4:
                card.due_at = now + timedelta(days=new_interval)
            else:
                # rating == 3: same-day re-review required.
                card.needs_extra_review = True
                card.due_at = now
        else:
            # Lapse.
            card.repetitions = 0
            card.interval = 0
            card.lapses += 1
            card.due_at = now
            # EF unchanged on lapse, per SM-2.

        event = ReviewEvent(
            id=make_id("rev", card.id, now.isoformat(), str(rating)),
            card_id=card.id,
            rating=rating,
            reviewed_at=now,
            interval_before=interval_before,
            interval_after=card.interval,
            ease_before=ef_before,
            ease_after=card.ease_factor,
            repetitions_before=reps_before,
            repetitions_after=card.repetitions,
        )
        return card, event

    def due(self, cards: Iterable[Flashcard], *, now: datetime | None = None) -> list[Flashcard]:
        now = _ensure_aware(now or utcnow())
        return sorted((c for c in cards if c.due_at <= now), key=lambda c: c.due_at)
