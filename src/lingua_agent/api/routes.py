"""HTTP API routes."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from .. import __version__
from ..ai import get_provider
from ..config import Settings
from ..ingest import ingest_text
from ..languages import list_languages
from ..models import Flashcard, LearnerProfile, LessonUnit, ReviewEvent, TutorSession
from ..srs import SM2Scheduler, export_cards_csv
from ..storage import JsonRepository
from ..tutor.agent import reply as tutor_reply
from ..tutor.session import open_session
from . import schemas as S


# Settings dependency: app.state.settings is set in main.py; this lets tests
# override it via dependency_overrides without monkeypatching env vars.
def get_settings() -> Settings:  # pragma: no cover - replaced by app dependency
    raise RuntimeError("settings dependency was not wired up")


router = APIRouter(prefix="/api", tags=["lingua-agent"])


# ---- helpers --------------------------------------------------------------

def _profile_path(s: Settings) -> Path:
    return s.data_dir / "learner_profile.json"


def _load_profile(s: Settings) -> LearnerProfile:
    p = _profile_path(s)
    if p.exists():
        return LearnerProfile.model_validate(json.loads(p.read_text("utf-8")))
    return LearnerProfile()


def _save_profile(s: Settings, profile: LearnerProfile) -> None:
    p = _profile_path(s)
    p.write_text(json.dumps(profile.model_dump(mode="json"), ensure_ascii=False, indent=2),
                 encoding="utf-8")


def _card_out(card: Flashcard) -> S.CardOut:
    return S.CardOut(
        id=card.id, front=card.front, back=card.back,
        source_language=card.source_language, target_language=card.target_language,
        direction=card.direction.value, card_type=card.card_type.value,
        interval=card.interval, ease_factor=card.ease_factor,
        repetitions=card.repetitions, lapses=card.lapses,
        needs_extra_review=card.needs_extra_review, due_at=card.due_at,
    )


def _unit_item(unit: LessonUnit) -> S.UnitListItem:
    return S.UnitListItem(
        id=unit.id, title=unit.title,
        source_language=unit.source_language, target_language=unit.target_language,
        cefr_level=unit.cefr_level,
        vocabulary_count=len(unit.vocabulary_ids),
        grammar_count=len(unit.grammar_ids),
        exercise_count=len(unit.exercise_ids),
        flashcard_count=len(unit.flashcard_ids),
        created_at=unit.created_at,
    )


# ---- routes ---------------------------------------------------------------

@router.get("/health", response_model=S.HealthResponse)
def health(s: Settings = Depends(get_settings)) -> S.HealthResponse:
    return S.HealthResponse(status="ok", version=__version__, ai_provider=s.ai_provider)


@router.get("/languages", response_model=list[S.LanguageOut])
def languages() -> list[S.LanguageOut]:
    return [S.LanguageOut(
        code=lang.code, name=lang.name, native_name=lang.native_name,
        script=lang.script.value, direction=lang.direction.value,
        transliteration_supported=lang.transliteration_supported,
    ) for lang in list_languages()]


@router.get("/profile", response_model=LearnerProfile)
def get_profile(s: Settings = Depends(get_settings)) -> LearnerProfile:
    return _load_profile(s)


@router.put("/profile", response_model=LearnerProfile)
def update_profile(patch: S.LearnerProfilePatch, s: Settings = Depends(get_settings)) -> LearnerProfile:
    profile = _load_profile(s)
    data = profile.model_dump()
    for k, v in patch.model_dump(exclude_none=True).items():
        data[k] = v
    profile = LearnerProfile.model_validate(data)
    profile.updated_at = datetime.utcnow().replace(tzinfo=profile.updated_at.tzinfo)
    _save_profile(s, profile)
    return profile


@router.post("/ingest/text", response_model=S.IngestSummary)
def ingest_text_endpoint(req: S.IngestTextRequest, s: Settings = Depends(get_settings)) -> S.IngestSummary:
    provider = get_provider(s.ai_provider)
    try:
        result = ingest_text(
            text=req.text, title=req.title,
            source_language=req.source_language, target_language=req.target_language,
            support_language=req.support_language, cefr_level=req.cefr_level,
            tags=req.tags, provider=provider, settings=s,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return S.IngestSummary(
        unit_id=result.unit.id,
        document_id=result.document.id,
        title=result.unit.title,
        source_language=result.unit.source_language,
        target_language=result.unit.target_language,
        vocabulary_count=len(result.vocabulary),
        grammar_count=len(result.grammar),
        exercise_count=len(result.exercises),
        flashcard_count=len(result.flashcards),
        unit_path=result.unit_path,
    )


@router.get("/units", response_model=list[S.UnitListItem])
def list_units(target: str | None = None, s: Settings = Depends(get_settings)) -> list[S.UnitListItem]:
    units = JsonRepository(s.data_dir, "lessons", LessonUnit).list()
    if target:
        units = [u for u in units if u.target_language == target]
    units.sort(key=lambda u: u.created_at, reverse=True)
    return [_unit_item(u) for u in units]


@router.get("/units/{unit_id}", response_model=LessonUnit)
def get_unit(unit_id: str, s: Settings = Depends(get_settings)) -> LessonUnit:
    unit = JsonRepository(s.data_dir, "lessons", LessonUnit).get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail=f"unit not found: {unit_id}")
    return unit


@router.get("/cards/due", response_model=list[S.CardOut])
def cards_due(target: str | None = None, limit: int = 50, s: Settings = Depends(get_settings)) -> list[S.CardOut]:
    cards = JsonRepository(s.data_dir, "flashcards", Flashcard).list()
    if target:
        cards = [c for c in cards if c.target_language == target]
    due = SM2Scheduler().due(cards)[:limit]
    return [_card_out(c) for c in due]


@router.post("/cards/{card_id}/review", response_model=S.ReviewResponse)
def review_card(card_id: str, req: S.ReviewRequest, s: Settings = Depends(get_settings)) -> S.ReviewResponse:
    cards_repo = JsonRepository(s.data_dir, "flashcards", Flashcard)
    reviews_repo = JsonRepository(s.data_dir, "reviews", ReviewEvent)
    card = cards_repo.get(card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"card not found: {card_id}")
    sched = SM2Scheduler()
    card, event = sched.update(card, req.rating)
    cards_repo.save(card)
    reviews_repo.save(event)
    return S.ReviewResponse(
        card=_card_out(card),
        interval_after=card.interval,
        ease_after=card.ease_factor,
        repetitions_after=card.repetitions,
    )


@router.post("/tutor/sessions", response_model=S.TutorSessionOut)
def create_session(req: S.OpenSessionRequest, s: Settings = Depends(get_settings)) -> S.TutorSessionOut:
    sess = open_session(source=req.source_language, target=req.target_language,
                         support=req.support_language, settings=s)
    return _session_out(sess)


@router.get("/tutor/sessions/{session_id}", response_model=S.TutorSessionOut)
def get_session(session_id: str, s: Settings = Depends(get_settings)) -> S.TutorSessionOut:
    sess = JsonRepository(s.data_dir, "sessions", TutorSession).get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    return _session_out(sess)


@router.post("/tutor/sessions/{session_id}/messages", response_model=S.TutorMessageResponse)
def send_message(session_id: str, req: S.TutorMessageRequest, s: Settings = Depends(get_settings)) -> S.TutorMessageResponse:
    repo = JsonRepository(s.data_dir, "sessions", TutorSession)
    sess = repo.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    profile = _load_profile(s)
    provider = get_provider(s.ai_provider)
    msg = tutor_reply(session=sess, learner=profile, user_message=req.content, provider=provider)
    repo.save(sess)
    return S.TutorMessageResponse(role=msg.role, content=msg.content, created_at=msg.created_at)


@router.get("/export/anki")
def export_anki(target: str, s: Settings = Depends(get_settings)) -> FileResponse:
    cards = [c for c in JsonRepository(s.data_dir, "flashcards", Flashcard).list()
             if c.target_language == target]
    if not cards:
        raise HTTPException(status_code=404, detail=f"no cards for target={target}")
    out = s.content_dir / "exports" / f"{target}.csv"
    export_cards_csv(cards, out)
    return FileResponse(out, media_type="text/tab-separated-values", filename=f"lingua-agent-{target}.csv")


def _session_out(sess: TutorSession) -> S.TutorSessionOut:
    return S.TutorSessionOut(
        id=sess.id,
        source_language=sess.source_language,
        target_language=sess.target_language,
        support_language=sess.support_language,
        messages=[m.model_dump(mode="json") for m in sess.messages],
        created_at=sess.created_at,
        updated_at=sess.updated_at,
    )
