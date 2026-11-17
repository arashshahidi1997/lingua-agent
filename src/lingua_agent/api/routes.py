"""HTTP API routes."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response

from .. import __version__
from ..ai import get_provider
from ..config import Settings
from ..course.store import log_activity
from ..ids import short_hash
from ..ingest import ingest_text
from ..languages import list_languages
from ..materials import MaterialsError, MaterialsSourceConfig, build_provider
from ..materials.registry import find_source
from ..models import (
    Exercise,
    Flashcard,
    GrammarPoint,
    LearnerProfile,
    LessonUnit,
    ReviewEvent,
    VocabularyItem,
)
from ..srs import SM2Scheduler, export_cards_csv
from ..storage import JsonRepository
from . import schemas as S
from .identity import charge_model_call, require_owner


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


def _card_target(card: Flashcard) -> tuple[str | None, str | None]:
    if card.target_text:
        return card.target_text, card.target_tr
    # Course and Talk cards made before target_text existed: back is "text · tr".
    if any(t.startswith(("course:", "talk")) for t in card.tags):
        text, _, tr = card.back.partition(" · ")
        return text.strip(), (tr.strip() or None)
    return None, None


def _card_out(card: Flashcard) -> S.CardOut:
    text, tr = _card_target(card)
    return S.CardOut(
        id=card.id, front=card.front, back=card.back,
        source_language=card.source_language, target_language=card.target_language,
        direction=card.direction.value, card_type=card.card_type.value,
        interval=card.interval, ease_factor=card.ease_factor,
        repetitions=card.repetitions, lapses=card.lapses,
        needs_extra_review=card.needs_extra_review, due_at=card.due_at,
        text=text, tr=tr,
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
    return S.HealthResponse(status="ok", version=__version__, ai_provider=s.ai_provider,
                            ai_label=_ai_label(s), features={"talk": s.talk_enabled})


def _ai_label(s: Settings) -> str:
    """The model in plain words, e.g. "Ollama · qwen2.5:7b, on this computer"."""
    if s.ai_provider == "openai":
        url = s.openai_base_url
        local = any(h in url for h in ("localhost", "127.0.0.1", "[::1]"))
        host = ("Ollama" if ":11434" in url else "a local server") if local else url.split("//")[-1].split("/")[0]
        return f"{host} · {s.openai_model}" + (", on this computer" if local else "")
    return {"mock": "Mock replies (no AI model)", "anthropic": f"Claude API · {s.anthropic_model}",
            "claude-max": "Claude (Claude Max subscription)"}.get(s.ai_provider, s.ai_provider)


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
def ingest_text_endpoint(req: S.IngestTextRequest, request: Request,
                         s: Settings = Depends(get_settings)) -> S.IngestSummary:
    charge_model_call(request, s, 5)  # a lesson is about five model calls
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


@router.delete("/units/{unit_id}", status_code=204)
def delete_unit(unit_id: str, s: Settings = Depends(get_settings)) -> Response:
    """Delete a lesson made from your own text, with what only it uses (words, grammar, exercises, cards)."""
    units = JsonRepository(s.data_dir, "lessons", LessonUnit)
    unit = units.get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail=f"unit not found: {unit_id}")
    others = [u for u in units.list() if u.id != unit_id]
    for bucket, model, field in (("vocabulary", VocabularyItem, "vocabulary_ids"),
                                 ("grammar", GrammarPoint, "grammar_ids"),
                                 ("exercises", Exercise, "exercise_ids"),
                                 ("flashcards", Flashcard, "flashcard_ids")):
        still_used = {i for u in others for i in getattr(u, field)}
        repo = JsonRepository(s.data_dir, bucket, model)
        for entity_id in getattr(unit, field):
            if entity_id not in still_used:
                repo.delete(entity_id)
    (s.content_dir / "units" / f"{unit.id}.md").unlink(missing_ok=True)
    units.delete(unit_id)
    return Response(status_code=204)


@router.get("/units/{unit_id}/detail", response_model=S.UnitDetail)
def get_unit_detail(unit_id: str, s: Settings = Depends(get_settings)) -> S.UnitDetail:
    """Return the unit with all referenced entities inlined.

    Saves the React modal a fan-out of N-by-id GETs: it opens with one
    round-trip and renders the full vocab / grammar / exercises lists.
    """
    unit = JsonRepository(s.data_dir, "lessons", LessonUnit).get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail=f"unit not found: {unit_id}")

    vocab_repo = JsonRepository(s.data_dir, "vocabulary", VocabularyItem)
    grammar_repo = JsonRepository(s.data_dir, "grammar", GrammarPoint)
    ex_repo = JsonRepository(s.data_dir, "exercises", Exercise)
    card_repo = JsonRepository(s.data_dir, "flashcards", Flashcard)

    def _resolve(repo: JsonRepository, ids: list[str]) -> list[dict]:
        out = []
        for entity_id in ids:
            entity = repo.get(entity_id)
            if entity is not None:
                out.append(entity.model_dump(mode="json"))
        return out

    return S.UnitDetail(
        id=unit.id, title=unit.title,
        source_language=unit.source_language, target_language=unit.target_language,
        support_language=unit.support_language, cefr_level=unit.cefr_level,
        summary=unit.summary,
        bilingual_reading=[p.model_dump(mode="json") for p in unit.bilingual_reading],
        tags=unit.tags,
        vocabulary=_resolve(vocab_repo, unit.vocabulary_ids),
        grammar=_resolve(grammar_repo, unit.grammar_ids),
        exercises=_resolve(ex_repo, unit.exercise_ids),
        flashcards=_resolve(card_repo, unit.flashcard_ids),
    )


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
    event_id = f"rev_{short_hash(req.event_id, length=20)}" if req.event_id else None
    if event_id and reviews_repo.get(event_id) is not None:
        # A replay from the offline queue: already applied.
        return S.ReviewResponse(card=_card_out(card), interval_after=card.interval,
                                ease_after=card.ease_factor, repetitions_after=card.repetitions)
    sched = SM2Scheduler()
    card, event = sched.update(card, req.rating)
    if event_id:
        event = event.model_copy(update={"id": event_id})
    cards_repo.save(card)
    reviews_repo.save(event)
    log_activity(s, req.seconds)
    return S.ReviewResponse(
        card=_card_out(card),
        interval_after=card.interval,
        ease_after=card.ease_factor,
        repetitions_after=card.repetitions,
    )


@router.get("/export/anki")
def export_anki(target: str, s: Settings = Depends(get_settings)) -> FileResponse:
    cards = [c for c in JsonRepository(s.data_dir, "flashcards", Flashcard).list()
             if c.target_language == target]
    if not cards:
        raise HTTPException(status_code=404, detail=f"no cards for target={target}")
    out = s.content_dir / "exports" / f"{target}.csv"
    export_cards_csv(cards, out)
    return FileResponse(out, media_type="text/tab-separated-values", filename=f"lingua-agent-{target}.csv")


# ---- Materials adapter (Phase 6c) -----------------------------------------

@router.get("/materials/sources", response_model=list[S.MaterialsSourceOut],
            dependencies=[Depends(require_owner)])
def materials_sources(s: Settings = Depends(get_settings)) -> list[S.MaterialsSourceOut]:
    profile = _load_profile(s)
    out: list[S.MaterialsSourceOut] = []
    for cfg in profile.materials_sources:
        try:
            available = build_provider(cfg).is_available()
        except MaterialsError:
            available = False
        out.append(S.MaterialsSourceOut(
            name=cfg.name, provider=cfg.provider, root=cfg.root,
            read_only=cfg.read_only, available=available, notes=cfg.notes,
        ))
    return out


@router.post("/materials/sources", response_model=S.MaterialsSourceOut, status_code=201,
             dependencies=[Depends(require_owner)])
def materials_add_source(req: S.AddMaterialsSourceRequest,
                          s: Settings = Depends(get_settings)) -> S.MaterialsSourceOut:
    profile = _load_profile(s)
    if any(src.name == req.name for src in profile.materials_sources):
        raise HTTPException(status_code=409, detail=f"source named {req.name!r} already exists")
    cfg = MaterialsSourceConfig(
        name=req.name, provider=req.provider, root=req.root,  # type: ignore[arg-type]
        read_only=req.read_only, notes=req.notes,
    )
    profile.materials_sources.append(cfg)
    _save_profile(s, profile)
    try:
        available = build_provider(cfg).is_available()
    except MaterialsError:
        available = False
    return S.MaterialsSourceOut(
        name=cfg.name, provider=cfg.provider, root=cfg.root,
        read_only=cfg.read_only, available=available, notes=cfg.notes,
    )


@router.delete("/materials/sources/{name}", status_code=204,
             dependencies=[Depends(require_owner)])
def materials_remove_source(name: str, s: Settings = Depends(get_settings)) -> None:
    profile = _load_profile(s)
    before = len(profile.materials_sources)
    profile.materials_sources = [src for src in profile.materials_sources if src.name != name]
    if len(profile.materials_sources) == before:
        raise HTTPException(status_code=404, detail=f"no such source: {name!r}")
    _save_profile(s, profile)


@router.get("/materials/list", response_model=S.MaterialsListResponse,
             dependencies=[Depends(require_owner)])
def materials_list(source: str, folder: str = "",
                    s: Settings = Depends(get_settings)) -> S.MaterialsListResponse:
    profile = _load_profile(s)
    cfg = find_source(profile, source)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"no such source: {source!r}")
    provider = build_provider(cfg)
    if not provider.is_available():
        return S.MaterialsListResponse(
            source=source, folder=folder, available=False, entries=[],
            error=f"source {source!r} is not available right now",
        )
    try:
        entries = provider.list(folder)
    except MaterialsError as exc:
        return S.MaterialsListResponse(
            source=source, folder=folder, available=True, entries=[], error=str(exc),
        )
    return S.MaterialsListResponse(
        source=source, folder=folder, available=True,
        entries=[S.MaterialsEntryOut.model_validate(e.model_dump()) for e in entries],
    )


@router.post("/materials/ingest", response_model=S.IngestSummary,
             dependencies=[Depends(require_owner)])
def materials_ingest(req: S.MaterialsIngestRequest,
                      s: Settings = Depends(get_settings)) -> S.IngestSummary:
    profile = _load_profile(s)
    cfg = find_source(profile, req.source)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"no such source: {req.source!r}")
    provider = build_provider(cfg)
    try:
        entry = provider.metadata(req.path)
    except MaterialsError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if entry.is_dir:
        raise HTTPException(status_code=400, detail=f"path is a directory: {req.path!r}")
    if entry.size_bytes is not None and entry.size_bytes > req.max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"file too large ({entry.size_bytes} > {req.max_bytes} bytes); raise max_bytes if you really mean it",
        )
    try:
        raw = provider.read(req.path)
    except MaterialsError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415,
                             detail=f"file is not utf-8 text ({entry.mime_type or 'unknown mime'}); "
                                    "binary ingest (audio/PDF/...) lands in a later phase")

    # Derive defaults: title from the file name; source_language from the
    # path's first segment if it's a known ISO code.
    title = req.title or Path(req.path).stem.replace("_", " ").strip() or "Untitled lesson"
    source_lang = req.source_language
    if source_lang is None:
        first = req.path.split("/", 1)[0]
        if len(first) in (2, 3) and first.isalpha() and first.islower():
            source_lang = first  # likely an ISO code matching our registry
    if source_lang is None:
        raise HTTPException(
            status_code=400,
            detail="source_language not provided and could not be derived from path",
        )

    ai = get_provider(s.ai_provider)
    try:
        result = ingest_text(
            text=text, title=title,
            source_language=source_lang, target_language=req.target_language,
            support_language=req.support_language, cefr_level=req.cefr_level,
            tags=[f"material:{req.source}", f"path:{req.path}"],
            provider=ai, settings=s,
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
