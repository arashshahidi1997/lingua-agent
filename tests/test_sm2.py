from datetime import datetime, timedelta, timezone

import pytest

from lingua_agent.models import CardDirection, CardType, Flashcard
from lingua_agent.srs import SM2Scheduler


def _new_card(**overrides) -> Flashcard:
    base = dict(
        id="card_test",
        front="coffee",
        back="caffè",
        source_language="en",
        target_language="it",
        direction=CardDirection.PRODUCTION,
        card_type=CardType.VOCAB,
    )
    base.update(overrides)
    return Flashcard(**base)


def test_first_correct_review_sets_one_day_interval():
    card = _new_card()
    sched = SM2Scheduler()
    now = datetime(2026, 5, 9, tzinfo=timezone.utc)
    card, ev = sched.update(card, 5, reviewed_at=now)
    assert card.interval == 1
    assert card.repetitions == 1
    assert card.due_at == now + timedelta(days=1)
    assert ev.interval_after == 1


def test_second_correct_review_sets_six_days():
    card = _new_card(repetitions=1, interval=1)
    sched = SM2Scheduler()
    card, _ = sched.update(card, 5)
    assert card.interval == 6
    assert card.repetitions == 2


def test_subsequent_review_uses_ease_factor():
    card = _new_card(repetitions=2, interval=6, ease_factor=2.5)
    sched = SM2Scheduler()
    card, _ = sched.update(card, 5)
    # ceil(6 * (2.5 + 0.10)) = ceil(15.6) = 16
    assert card.interval == 16
    assert card.repetitions == 3
    assert card.ease_factor == pytest.approx(2.6, abs=1e-9)


def test_ease_factor_floor():
    # Drive EF down to floor with consecutive q=3 ratings.
    card = _new_card(repetitions=2, interval=6, ease_factor=1.4)
    sched = SM2Scheduler()
    card, _ = sched.update(card, 3)  # delta = -0.14, but should clamp to 1.3
    assert card.ease_factor == pytest.approx(1.3, abs=1e-9)


def test_q3_marks_extra_review():
    card = _new_card(repetitions=2, interval=6, ease_factor=2.5)
    sched = SM2Scheduler()
    now = datetime(2026, 5, 9, tzinfo=timezone.utc)
    card, _ = sched.update(card, 3, reviewed_at=now)
    assert card.needs_extra_review is True
    assert card.due_at == now
    # Same-day successful follow-up clears the flag and pushes due forward.
    card, _ = sched.update(card, 4, reviewed_at=now)
    assert card.needs_extra_review is False
    assert card.due_at == now + timedelta(days=card.interval)


def test_lapse_resets_state_and_increments_lapses():
    card = _new_card(repetitions=3, interval=15, ease_factor=2.6)
    sched = SM2Scheduler()
    now = datetime(2026, 5, 9, tzinfo=timezone.utc)
    card, _ = sched.update(card, 1, reviewed_at=now)
    assert card.repetitions == 0
    assert card.interval == 0
    assert card.due_at == now
    assert card.lapses == 1
    # EF is unchanged on lapse per upstream SM-2.
    assert card.ease_factor == pytest.approx(2.6, abs=1e-9)


def test_due_filter_returns_only_overdue_cards():
    sched = SM2Scheduler()
    now = datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc)
    due_card = _new_card(id="card_due", due_at=now - timedelta(days=1))
    not_yet = _new_card(id="card_future", due_at=now + timedelta(days=1))
    out = sched.due([due_card, not_yet], now=now)
    assert [c.id for c in out] == ["card_due"]


def test_invalid_rating():
    sched = SM2Scheduler()
    with pytest.raises(ValueError):
        sched.update(_new_card(), 7)
