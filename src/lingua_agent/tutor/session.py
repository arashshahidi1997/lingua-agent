"""Session helpers — open a session, recommend next activity."""

from __future__ import annotations

from typing import Any

from ..config import Settings
from ..ids import make_id
from ..models import Flashcard, LearnerProfile, TutorSession
from ..models.base import utcnow
from ..storage import JsonRepository


def _sessions_repo(settings: Settings) -> JsonRepository:
    settings.ensure_dirs()
    return JsonRepository(settings.data_dir, "sessions", TutorSession)


def open_session(*, source: str, target: str, support: str | None = "en",
                 settings: Settings | None = None) -> TutorSession:
    settings = settings or Settings.load()
    session = TutorSession(
        id=make_id("sess", source, target, utcnow().isoformat()),
        source_language=source,
        target_language=target,
        support_language=support,
    )
    _sessions_repo(settings).save(session)
    return session


def recommend_next_activity(*, profile: LearnerProfile, due_cards: list[Flashcard]) -> dict[str, Any]:
    if due_cards:
        return {
            "kind": "review_due",
            "reason": f"You have {len(due_cards)} card(s) due for review.",
            "payload": {"count": len(due_cards), "first_card_id": due_cards[0].id},
        }
    if not profile.target_languages:
        return {
            "kind": "rest",
            "reason": "No active target languages — set one with `lingua-agent profile set`.",
            "payload": {},
        }
    target = profile.target_languages[0].code
    return {
        "kind": "fresh_material",
        "reason": f"No reviews due. Try ingesting new {target} material.",
        "payload": {"target_language": target},
    }
