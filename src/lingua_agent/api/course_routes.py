"""HTTP routes for Product v2: courses and the Path, exercises, practice, Today,
stories, Talk, speech, recordings, and imported audio.

The contract lives in web/src/lib/course-api.ts; keep the two in step.
"""

from __future__ import annotations

import json
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from ..ai import get_provider
from ..config import Settings
from ..course import cloze
from ..course import exercises as X
from ..course.cloze import Cloze
from ..course import store
from ..course.models import (
    CourseDef,
    CourseItem,
    CourseProgress,
    ItemStats,
    LessonRecord,
    ScenarioDef,
    StoryDef,
)
from ..course.talk import TalkMessage, TalkSession, chatbot_prompt, opener_turn, persona_name, summarize, take_turn
from ..ids import make_id, short_hash
from ..materials import MaterialsError, build_provider
from ..materials.registry import find_source
from ..models import Flashcard, LearnerProfile, ReviewEvent
from ..models.base import utcnow
from ..models.srs import CardDirection, CardType
from ..srs import SM2Scheduler
from ..storage import JsonRepository
from ..voice import piper
from ..voice.native import native_count, pick_take
from ..voice.subtitles import parse_transcript
from .identity import charge_model_call, check_guest_storage, identify, require_owner
from .routes import get_settings

router = APIRouter(prefix="/api", tags=["lingua-agent v2"])


def require_talk(s: Settings = Depends(get_settings)) -> None:
    if not s.talk_enabled:
        raise HTTPException(404, "Talk is turned off.")

QUIZ_PASS = 0.7


# ---- schemas --------------------------------------------------------------------

class LessonSummary(BaseModel):
    id: str
    title: str
    kind: str
    item_count: int
    state: Literal["locked", "current", "done"]
    best_score: float | None


class UnitSummary(BaseModel):
    id: str
    title: str
    goal: str
    lessons: list[LessonSummary]
    story_id: str | None
    scenario_id: str | None
    story_unlocked: bool
    scenario_unlocked: bool
    quiz_state: Literal["locked", "current", "done"]
    done: bool


class CourseSummary(BaseModel):
    id: str
    title: str
    description: str
    target: str
    support: str
    level: str
    progress: float
    lessons_done: int
    lessons_total: int


class NextLesson(BaseModel):
    unit_id: str
    lesson_id: str
    title: str
    unit_title: str


class CourseOut(CourseSummary):
    units: list[UnitSummary]
    next_lesson: NextLesson | None


class LessonDetail(BaseModel):
    id: str
    unit_id: str
    title: str
    kind: str
    note: str | None
    items: list[CourseItem]


class ExerciseSession(BaseModel):
    id: str
    title: str
    course_id: str
    target: str
    exercises: list[X.Exercise]


class ItemResult(BaseModel):
    item_id: str
    correct: bool


class CompleteRequest(BaseModel):
    results: list[ItemResult] = Field(default_factory=list)
    seconds: int = Field(0, ge=0, le=6 * 3600)
    event_id: str | None = Field(None, max_length=80, description="Idempotency key: a replay is ignored.")


class CompleteResponse(BaseModel):
    score: float
    passed: bool
    cards_added: int
    unlocked: str | None


class StorySummary(BaseModel):
    id: str
    course_id: str
    unit_id: str
    kind: str
    title: str
    title_gloss: str
    line_count: int
    unlocked: bool


class StoryOut(StorySummary):
    speakers: dict[str, dict]
    lines: list[dict]


class ScenarioSummary(BaseModel):
    id: str
    course_id: str
    unit_id: str
    title: str
    title_target: str
    goal: str
    unlocked: bool


class ScenarioOut(ScenarioSummary):
    setting: str
    persona: str
    persona_name: str
    opener: CourseItem
    useful: list[CourseItem]


class TodayOut(BaseModel):
    course: CourseSummary | None
    next_lesson: NextLesson | None
    due_count: int
    learned_count: int
    minutes_today: int
    daily_goal_minutes: int
    streak_days: int
    story: StorySummary | None
    scenario: ScenarioSummary | None
    checkpoint: dict | None = None  # {unit_id, unit_title}: lessons done, quiz not passed


class OpenTalkRequest(BaseModel):
    target: str
    support: str = "en"
    scenario_id: str | None = None


class TalkSessionOut(BaseModel):
    id: str
    scenario: ScenarioOut | None
    target: str
    support: str
    messages: list[TalkMessage]
    ended: bool
    summary: dict | None = None


class SayRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class TalkSummaryOut(BaseModel):
    went_well: str
    mistakes: list[dict]
    new_words: list[CourseItem]
    cards_added: int


class SpeechInfo(BaseModel):
    server_tts: dict[str, bool]
    stt: bool
    native_texts: int = 0  # texts with a native speaker's recorded takes


class RecordingMeta(BaseModel):
    id: str
    ref: str
    language: str
    mime_type: str
    filename: str
    seconds: float | None = None
    created_at: datetime = Field(default_factory=utcnow)


class RecordingOut(BaseModel):
    id: str
    ref: str
    language: str
    mime_type: str
    seconds: float | None
    created_at: datetime
    url: str


class Cue(BaseModel):
    start: float
    end: float
    text: str
    tr: str | None = None
    gloss: str | None = None


class AudioMeta(BaseModel):
    id: str
    title: str
    language: str
    mime_type: str
    filename: str
    source: Literal["upload", "materials"]
    cues: list[Cue] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class AudioOut(BaseModel):
    id: str
    title: str
    language: str
    mime_type: str
    source: str
    has_transcript: bool
    created_at: datetime
    url: str


class AudioDetail(AudioOut):
    cues: list[Cue]


class FromMaterialsRequest(BaseModel):
    source: str
    path: str
    language: str
    title: str | None = None


# ---- course helpers -------------------------------------------------------------

def _course_or_404(s: Settings, course_id: str) -> CourseDef:
    course = store.get_course(s, course_id)
    if course is None:
        raise HTTPException(404, f"course not found: {course_id}")
    return course


def _ordered_lessons(course: CourseDef) -> list[str]:
    return [lesson.id for _, lesson in course.lessons()]


def _lesson_states(course: CourseDef, prog: CourseProgress) -> dict[str, str]:
    """Done lessons are done; the first not-done lesson is current; the rest are locked."""
    states: dict[str, str] = {}
    current_given = False
    for lid in _ordered_lessons(course):
        if lid in prog.lessons:
            states[lid] = "done"
        elif not current_given:
            states[lid] = "current"
            current_given = True
        else:
            states[lid] = "locked"
    return states


def _unit_unlocked(course: CourseDef, prog: CourseProgress, unit_id: str) -> bool:
    if course.units and course.units[0].id == unit_id:
        return True
    unit = course.unit(unit_id)
    return bool(unit) and any(lesson.id in prog.lessons for lesson in unit.lessons)


def _summary(course: CourseDef, prog: CourseProgress) -> CourseSummary:
    total = len(_ordered_lessons(course))
    done = sum(1 for lid in _ordered_lessons(course) if lid in prog.lessons)
    return CourseSummary(id=course.id, title=course.title, description=course.description,
                         target=course.target, support=course.support, level=course.level,
                         progress=done / total if total else 0.0, lessons_done=done, lessons_total=total)


def _next_lesson(course: CourseDef, prog: CourseProgress) -> NextLesson | None:
    for unit, lesson in course.lessons():
        if lesson.id not in prog.lessons:
            return NextLesson(unit_id=unit.id, lesson_id=lesson.id, title=lesson.title, unit_title=unit.title)
    return None


def _course_out(course: CourseDef, prog: CourseProgress) -> CourseOut:
    states = _lesson_states(course, prog)
    units = []
    for unit in course.units:
        lessons = [LessonSummary(id=lesson.id, title=lesson.title, kind=lesson.kind,
                                 item_count=len(lesson.items), state=states[lesson.id],
                                 best_score=prog.lessons[lesson.id].best_score if lesson.id in prog.lessons else None)
                   for lesson in unit.lessons]
        all_done = all(ls.state == "done" for ls in lessons)
        # Reached = the first unit, or one of its lessons is current or done. From then on its quiz is open:
        # before the lessons are done it's a test-out (passing marks them done).
        reached = unit is course.units[0] or any(ls.state != "locked" for ls in lessons)
        quiz = prog.quizzes.get(unit.id)
        quiz_state = "done" if quiz and quiz.best_score >= QUIZ_PASS else ("current" if reached else "locked")
        units.append(UnitSummary(id=unit.id, title=unit.title, goal=unit.goal, lessons=lessons,
                                 story_id=unit.story, scenario_id=unit.scenario,
                                 story_unlocked=_unit_unlocked(course, prog, unit.id),
                                 scenario_unlocked=_unit_unlocked(course, prog, unit.id),
                                 quiz_state=quiz_state, done=all_done))
    return CourseOut(**_summary(course, prog).model_dump(), units=units, next_lesson=_next_lesson(course, prog))


def _learned_items(course: CourseDef, prog: CourseProgress) -> list[CourseItem]:
    return [i for _, lesson in course.lessons() if lesson.id in prog.lessons for i in lesson.items]


def _pool_upto(course: CourseDef, lesson_id: str) -> list[CourseItem]:
    """Items of this lesson and every earlier one: distractors the learner has seen."""
    out: list[CourseItem] = []
    for _, lesson in course.lessons():
        out += lesson.items
        if lesson.id == lesson_id:
            break
    return out


def _card_id(course_id: str, item_id: str) -> str:
    return f"card_{short_hash(course_id, item_id, length=14)}"


def _add_cards(s: Settings, course: CourseDef, items: list[CourseItem], tag: str) -> int:
    repo = JsonRepository(s.data_dir, "flashcards", Flashcard)
    added = 0
    for item in items:
        cid = _card_id(course.id, item.id)
        if repo.get(cid) is not None:
            continue
        back = f"{item.text} · {item.tr}" if item.tr else item.text
        repo.save(Flashcard(id=cid, front=item.gloss, back=back, target_text=item.text, target_tr=item.tr,
                            source_language=course.support, target_language=course.target,
                            direction=CardDirection.PRODUCTION,
                            card_type=CardType.SENTENCE if len(X.words(item.text)) > 1 else CardType.VOCAB,
                            mnemonic=item.note, tags=[f"course:{course.id}", tag]))
        added += 1
    return added


def _apply_results(prog: CourseProgress, results: list[ItemResult]) -> float:
    for r in results:
        st = prog.items.setdefault(r.item_id, ItemStats())
        st.seen += 1
        st.last_seen = utcnow()
        if r.correct:
            st.correct += 1
        else:
            st.wrong += 1
    return sum(r.correct for r in results) / len(results) if results else 1.0


def _replayed(prog: CourseProgress, event_id: str | None) -> bool:
    """True when this event was already applied (an offline replay); records it otherwise."""
    if not event_id:
        return False
    if event_id in prog.events:
        return True
    prog.events = [*prog.events[-499:], event_id]
    return False


def _attempt_seed(prog: CourseProgress, key: str) -> str:
    rec = prog.lessons.get(key) or prog.quizzes.get(key)
    return str(rec.attempts if rec else 0)


# ---- courses / Path -----------------------------------------------------------------

@router.get("/courses", response_model=list[CourseSummary])
def list_courses(target: str | None = None, support: str | None = None,
                 s: Settings = Depends(get_settings)) -> list[CourseSummary]:
    out = []
    for c in store.load_courses(s):
        if (target and c.target != target) or (support and c.support != support):
            continue
        out.append(_summary(c, store.load_progress(s, c.id)))
    return out


@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: str, s: Settings = Depends(get_settings)) -> CourseOut:
    course = _course_or_404(s, course_id)
    return _course_out(course, store.load_progress(s, course_id))


@router.get("/courses/{course_id}/lessons/{lesson_id}", response_model=LessonDetail)
def get_lesson(course_id: str, lesson_id: str, s: Settings = Depends(get_settings)) -> LessonDetail:
    course = _course_or_404(s, course_id)
    found = course.lesson(lesson_id)
    if not found:
        raise HTTPException(404, f"lesson not found: {lesson_id}")
    unit, lesson = found
    return LessonDetail(id=lesson.id, unit_id=unit.id, title=lesson.title, kind=lesson.kind,
                        note=lesson.note, items=lesson.items)


@router.get("/courses/{course_id}/lessons/{lesson_id}/session", response_model=ExerciseSession)
def lesson_session(course_id: str, lesson_id: str, mode: str = "learn",
                   s: Settings = Depends(get_settings)) -> ExerciseSession:
    course = _course_or_404(s, course_id)
    found = course.lesson(lesson_id)
    if not found:
        raise HTTPException(404, f"lesson not found: {lesson_id}")
    _, lesson = found
    prog = store.load_progress(s, course_id)
    if mode == "fast":
        # Fast track: no introductions, no transliteration crutch, one exercise per item and a match.
        exs = X.quiz_session(lesson.id, lesson.items, _pool_upto(course, lesson.id),
                             n=len(lesson.items), seed=_attempt_seed(prog, lesson.id))
    else:
        exs = X.lesson_session(lesson.id, lesson.items, _pool_upto(course, lesson.id),
                               kind=lesson.kind, seed=_attempt_seed(prog, lesson.id))
    return ExerciseSession(id=lesson.id, title=lesson.title, course_id=course.id, target=course.target, exercises=exs)


@router.post("/courses/{course_id}/lessons/{lesson_id}/complete", response_model=CompleteResponse)
def complete_lesson(course_id: str, lesson_id: str, req: CompleteRequest,
                    s: Settings = Depends(get_settings)) -> CompleteResponse:
    course = _course_or_404(s, course_id)
    found = course.lesson(lesson_id)
    if not found:
        raise HTTPException(404, f"lesson not found: {lesson_id}")
    unit, lesson = found
    prog = store.load_progress(s, course_id)
    if _replayed(prog, req.event_id):
        rec = prog.lessons.get(lesson.id)
        return CompleteResponse(score=rec.best_score if rec else 0.0, passed=True, cards_added=0, unlocked=None)
    score = _apply_results(prog, req.results)
    store.record(prog.lessons, lesson.id, score)
    prog.updated_at = utcnow()
    store.save_progress(s, prog)
    store.log_activity(s, req.seconds)
    added = _add_cards(s, course, lesson.items, f"unit:{unit.id}")
    nxt = _next_lesson(course, prog)
    unit_done = all(lesson_.id in prog.lessons for lesson_ in unit.lessons)
    unlocked = f"{unit.id}:quiz" if unit_done and unit.id not in prog.quizzes else (nxt.lesson_id if nxt else None)
    return CompleteResponse(score=score, passed=True, cards_added=added, unlocked=unlocked)


@router.get("/courses/{course_id}/units/{unit_id}/quiz", response_model=ExerciseSession)
def unit_quiz(course_id: str, unit_id: str, s: Settings = Depends(get_settings)) -> ExerciseSession:
    course = _course_or_404(s, course_id)
    unit = course.unit(unit_id)
    if not unit:
        raise HTTPException(404, f"unit not found: {unit_id}")
    items = [i for lesson in unit.lessons for i in lesson.items]
    prog = store.load_progress(s, course_id)
    pool = _pool_upto(course, unit.lessons[-1].id)
    exs = X.quiz_session(f"{unit.id}-quiz", items, pool, seed=_attempt_seed(prog, unit.id))
    return ExerciseSession(id=f"{unit.id}:quiz", title=f"{unit.title} · checkpoint", course_id=course.id, target=course.target, exercises=exs)


@router.post("/courses/{course_id}/units/{unit_id}/quiz/complete", response_model=CompleteResponse)
def complete_unit_quiz(course_id: str, unit_id: str, req: CompleteRequest,
                       s: Settings = Depends(get_settings)) -> CompleteResponse:
    course = _course_or_404(s, course_id)
    unit = course.unit(unit_id)
    if not unit:
        raise HTTPException(404, f"unit not found: {unit_id}")
    prog = store.load_progress(s, course_id)
    if _replayed(prog, req.event_id):
        rec = prog.quizzes.get(unit.id)
        return CompleteResponse(score=rec.best_score if rec else 0.0,
                                passed=bool(rec and rec.best_score >= QUIZ_PASS), cards_added=0, unlocked=None)
    score = _apply_results(prog, req.results)
    store.record(prog.quizzes, unit.id, score)
    passed = score >= QUIZ_PASS
    if passed:
        # Testing out: a passed checkpoint counts the unit's lessons as done.
        for lesson in unit.lessons:
            prog.lessons.setdefault(lesson.id, LessonRecord(best_score=score))
    prog.updated_at = utcnow()
    store.save_progress(s, prog)
    store.log_activity(s, req.seconds)
    added = _add_cards(s, course, [i for lesson in unit.lessons for i in lesson.items], f"unit:{unit.id}") if passed else 0
    nxt = _next_lesson(course, prog)
    return CompleteResponse(score=score, passed=passed, cards_added=added,
                            unlocked=nxt.lesson_id if (passed and nxt) else None)


@router.get("/courses/{course_id}/practice", response_model=ExerciseSession)
def practice(course_id: str, n: int = 12, s: Settings = Depends(get_settings)) -> ExerciseSession:
    course = _course_or_404(s, course_id)
    prog = store.load_progress(s, course_id)
    learned = _learned_items(course, prog)
    if not learned:
        raise HTTPException(409, "Finish a lesson first: practice draws on what you've learned.")
    cards = {c.id: c for c in JsonRepository(s.data_dir, "flashcards", Flashcard).list()
             if c.target_language == course.target}
    now = utcnow()

    def priority(item: CourseItem) -> tuple:
        card = cards.get(_card_id(course.id, item.id))
        due = card is not None and card.due_at <= now
        st = prog.items.get(item.id)
        return (not due, -(st.weakness if st else 0.5))

    learned.sort(key=priority)
    picked = learned[: max(1, min(n, 30))]
    seed = str(sum(st.seen for st in prog.items.values()))
    exs = X.practice_session("practice", picked, learned, seed=seed)
    return ExerciseSession(id="practice", title="Practice", course_id=course.id, target=course.target, exercises=exs)


@router.post("/courses/{course_id}/practice/complete", response_model=CompleteResponse)
def complete_practice(course_id: str, req: CompleteRequest, s: Settings = Depends(get_settings)) -> CompleteResponse:
    course = _course_or_404(s, course_id)
    prog = store.load_progress(s, course_id)
    if _replayed(prog, req.event_id):
        return CompleteResponse(score=0.0, passed=True, cards_added=0, unlocked=None)
    score = _apply_results(prog, req.results)
    # Practice also counts as review: nudge the matching flashcards through SM-2, with history.
    repo = JsonRepository(s.data_dir, "flashcards", Flashcard)
    reviews = JsonRepository(s.data_dir, "reviews", ReviewEvent)
    sched = SM2Scheduler()
    per_item: dict[str, list[bool]] = {}
    for r in req.results:
        per_item.setdefault(r.item_id, []).append(r.correct)
    for item_id, outcomes in per_item.items():
        card = repo.get(_card_id(course.id, item_id))
        if card is not None and card.is_due():
            card, event = sched.update(card, 4 if all(outcomes) else 2)
            repo.save(card)
            reviews.save(event)
    prog.updated_at = utcnow()
    store.save_progress(s, prog)
    store.log_activity(s, req.seconds)
    return CompleteResponse(score=score, passed=True, cards_added=0, unlocked=None)


# ---- Today ------------------------------------------------------------------------

def _profile(s: Settings) -> LearnerProfile:
    p = s.data_dir / "learner_profile.json"
    return LearnerProfile.model_validate(json.loads(p.read_text("utf-8"))) if p.exists() else LearnerProfile()


def _story_summary(course: CourseDef, prog: CourseProgress, st: StoryDef) -> StorySummary:
    return StorySummary(id=st.id, course_id=course.id, unit_id=st.unit, kind=st.kind, title=st.title,
                        title_gloss=st.title_gloss, line_count=len(st.lines),
                        unlocked=_unit_unlocked(course, prog, st.unit))


def _scenario_summary(course: CourseDef, prog: CourseProgress, sc: ScenarioDef) -> ScenarioSummary:
    return ScenarioSummary(id=sc.id, course_id=course.id, unit_id=sc.unit, title=sc.title,
                           title_target=sc.title_target, goal=sc.goal,
                           unlocked=_unit_unlocked(course, prog, sc.unit))


def _current_unit_id(course: CourseDef, prog: CourseProgress) -> str | None:
    nxt = _next_lesson(course, prog)
    return nxt.unit_id if nxt else (course.units[-1].id if course.units else None)


def _pick_for_unit(entries: list, unit_order: list[str], current: str | None):
    """The entry for the current unit if unlocked, else the latest unlocked one."""
    unlocked = [e for e in entries if e.unlocked]
    for e in unlocked:
        if e.unit_id == current:
            return e
    unlocked.sort(key=lambda e: unit_order.index(e.unit_id) if e.unit_id in unit_order else -1)
    return unlocked[-1] if unlocked else None


@router.get("/today", response_model=TodayOut)
def today(target: str, support: str = "en", s: Settings = Depends(get_settings)) -> TodayOut:
    cards = [c for c in JsonRepository(s.data_dir, "flashcards", Flashcard).list() if c.target_language == target]
    due = len(SM2Scheduler().due(cards))
    days = store.load_activity(s)
    goal = 10
    course = next((c for c in store.load_courses(s) if c.target == target and c.support == support), None)
    if course is None:
        return TodayOut(course=None, next_lesson=None, due_count=due, learned_count=0,
                        minutes_today=store.minutes_today(days), daily_goal_minutes=goal,
                        streak_days=store.streak(days), story=None, scenario=None)
    prog = store.load_progress(s, course.id)
    order = [u.id for u in course.units]
    current = _current_unit_id(course, prog)
    story = _pick_for_unit([_story_summary(course, prog, st) for st in course.stories], order, current)
    scen = _pick_for_unit([_scenario_summary(course, prog, sc) for sc in course.scenarios], order, current)
    checkpoint = next(({"unit_id": u.id, "unit_title": u.title} for u in course.units
                       if all(lesson.id in prog.lessons for lesson in u.lessons)
                       and not (u.id in prog.quizzes and prog.quizzes[u.id].best_score >= QUIZ_PASS)), None)
    return TodayOut(checkpoint=checkpoint, course=_summary(course, prog), next_lesson=_next_lesson(course, prog), due_count=due,
                    learned_count=len(_learned_items(course, prog)),
                    minutes_today=store.minutes_today(days), daily_goal_minutes=goal,
                    streak_days=store.streak(days), story=story, scenario=scen)


# ---- stories ------------------------------------------------------------------------

@router.get("/stories", response_model=list[StorySummary])
def list_stories(target: str, support: str = "en", s: Settings = Depends(get_settings)) -> list[StorySummary]:
    out = []
    for c in store.load_courses(s):
        if c.target == target and c.support == support:
            prog = store.load_progress(s, c.id)
            out += [_story_summary(c, prog, st) for st in c.stories]
    return out


@router.get("/stories/{story_id}", response_model=StoryOut)
def get_story(story_id: str, s: Settings = Depends(get_settings)) -> StoryOut:
    found = store.find_story(s, story_id)
    if not found:
        raise HTTPException(404, f"story not found: {story_id}")
    course, st = found
    summ = _story_summary(course, store.load_progress(s, course.id), st)
    return StoryOut(**summ.model_dump(), speakers={k: v.model_dump() for k, v in st.speakers.items()},
                    lines=[ln.model_dump() for ln in st.lines])


# ---- fill in the blanks ------------------------------------------------------------------

class ClozeCheckRequest(BaseModel):
    answers: dict[str, str]   # gap id → what the learner typed or picked
    seed: int = 0
    focus: str = "mixed"


class ClozeCheckResponse(BaseModel):
    correct: dict[str, bool]
    answers: dict[str, str]   # gap id → the right word
    score: float


@router.get("/stories/{story_id}/cloze", response_model=Cloze)
def story_cloze(story_id: str, focus: str = "mixed", seed: int = 0, s: Settings = Depends(get_settings)) -> Cloze:
    """The story with gaps chosen by a grammar focus (mixed, verbs, prepositions, vocab); new seed, new gaps."""
    found = store.find_story(s, story_id)
    if not found:
        raise HTTPException(404, f"story not found: {story_id}")
    course, st = found
    return cloze.build(course, st, focus=focus, seed=seed)


@router.post("/stories/{story_id}/cloze/check", response_model=ClozeCheckResponse)
def story_cloze_check(story_id: str, req: ClozeCheckRequest, s: Settings = Depends(get_settings)) -> ClozeCheckResponse:
    found = store.find_story(s, story_id)
    if not found:
        raise HTTPException(404, f"story not found: {story_id}")
    course, st = found
    z = cloze.build(course, st, focus=req.focus, seed=req.seed)
    gaps = {p.gap.id: p.gap for ln in z.lines for p in ln.parts if p.gap}
    correct = {gid: cloze.check(g.answer, req.answers.get(gid, ""), g.tr) for gid, g in gaps.items()}
    return ClozeCheckResponse(correct=correct, answers={gid: g.answer for gid, g in gaps.items()},
                              score=sum(correct.values()) / len(correct) if correct else 1.0)


# ---- Talk ---------------------------------------------------------------------------

def _scenario_out(course: CourseDef, prog: CourseProgress, sc: ScenarioDef) -> ScenarioOut:
    def item(p, i: int) -> CourseItem:
        return CourseItem(id=f"{sc.id}-{i}", text=p.text, tr=p.tr, gloss=p.gloss)
    return ScenarioOut(**_scenario_summary(course, prog, sc).model_dump(), setting=sc.setting,
                       persona=sc.persona, persona_name=persona_name(sc), opener=item(sc.opener, 0),
                       useful=[item(p, i + 1) for i, p in enumerate(sc.useful)])


@router.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios(target: str, support: str = "en", s: Settings = Depends(get_settings)) -> list[ScenarioSummary]:
    out = []
    for c in store.load_courses(s):
        if c.target == target and c.support == support:
            prog = store.load_progress(s, c.id)
            out += [_scenario_summary(c, prog, sc) for sc in c.scenarios]
    return out


class ChatbotPrompt(BaseModel):
    prompt: str
    voice: bool


@router.get("/scenarios/{scenario_id}/prompt", response_model=ChatbotPrompt)
def scenario_prompt(scenario_id: str, voice: bool = False, s: Settings = Depends(get_settings)) -> ChatbotPrompt:
    """A role-play prompt for the learner's own AI chatbot (ChatGPT, Claude, Gemini, …)."""
    found = store.find_scenario(s, scenario_id)
    if not found:
        raise HTTPException(404, f"scenario not found: {scenario_id}")
    course, sc = found
    return ChatbotPrompt(prompt=chatbot_prompt(course, sc, voice=voice), voice=voice)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioOut)
def get_scenario(scenario_id: str, s: Settings = Depends(get_settings)) -> ScenarioOut:
    found = store.find_scenario(s, scenario_id)
    if not found:
        raise HTTPException(404, f"scenario not found: {scenario_id}")
    course, sc = found
    return _scenario_out(course, store.load_progress(s, course.id), sc)


def _talk_repo(s: Settings) -> JsonRepository:
    return JsonRepository(s.data_dir, "talk", TalkSession)


def _talk_out(s: Settings, sess: TalkSession) -> TalkSessionOut:
    scen = None
    if sess.scenario_id and (found := store.find_scenario(s, sess.scenario_id)):
        course, sc = found
        scen = _scenario_out(course, store.load_progress(s, course.id), sc)
    return TalkSessionOut(id=sess.id, scenario=scen, target=sess.target, support=sess.support,
                          messages=sess.messages, ended=sess.ended, summary=sess.summary)


def _talk_or_404(s: Settings, session_id: str) -> TalkSession:
    sess = _talk_repo(s).get(session_id)
    if not sess:
        raise HTTPException(404, f"talk session not found: {session_id}")
    return sess


@router.post("/talk/sessions", response_model=TalkSessionOut, dependencies=[Depends(require_talk)])
def open_talk(req: OpenTalkRequest, s: Settings = Depends(get_settings)) -> TalkSessionOut:
    course_id = None
    messages: list[TalkMessage] = []
    if req.scenario_id:
        found = store.find_scenario(s, req.scenario_id)
        if not found:
            raise HTTPException(404, f"scenario not found: {req.scenario_id}")
        course, sc = found
        course_id = course.id
        turn = opener_turn(sc)
        messages.append(TalkMessage(role="assistant", content=turn.text, turn=turn))
    sess = TalkSession(id=make_id("talk", req.target, req.scenario_id or "free", utcnow().isoformat()),
                       course_id=course_id, scenario_id=req.scenario_id, target=req.target,
                       support=req.support, messages=messages)
    _talk_repo(s).save(sess)
    return _talk_out(s, sess)


@router.get("/talk/sessions/latest", response_model=TalkSessionOut, dependencies=[Depends(require_talk)])
def latest_talk(target: str, scenario_id: str | None = None, s: Settings = Depends(get_settings)) -> TalkSessionOut:
    """The most recent conversation that hasn't ended, to resume it."""
    open_ = [t for t in _talk_repo(s).list()
             if t.target == target and t.scenario_id == scenario_id and not t.ended]
    if not open_:
        raise HTTPException(404, "no open conversation")
    return _talk_out(s, max(open_, key=lambda t: t.updated_at))


@router.get("/talk/sessions/{session_id}", response_model=TalkSessionOut, dependencies=[Depends(require_talk)])
def get_talk(session_id: str, s: Settings = Depends(get_settings)) -> TalkSessionOut:
    return _talk_out(s, _talk_or_404(s, session_id))


@router.post("/talk/sessions/{session_id}/messages", response_model=TalkMessage, dependencies=[Depends(require_talk)])
def say(session_id: str, req: SayRequest, request: Request, s: Settings = Depends(get_settings)) -> TalkMessage:
    sess = _talk_or_404(s, session_id)
    if sess.ended:
        raise HTTPException(409, "This conversation has ended. Start a new one.")
    charge_model_call(request, s)
    found = store.find_scenario(s, sess.scenario_id) if sess.scenario_id else None
    course, sc = found if found else (None, None)
    started = utcnow()
    reply = take_turn(get_provider(s.ai_provider), sess, sc, course, req.content.strip())
    _talk_repo(s).save(sess)
    store.log_activity(s, int((utcnow() - started).total_seconds()) + 20)
    return reply


@router.post("/talk/sessions/{session_id}/end", response_model=TalkSummaryOut, dependencies=[Depends(require_talk)])
def end_talk(session_id: str, request: Request, s: Settings = Depends(get_settings)) -> TalkSummaryOut:
    sess = _talk_or_404(s, session_id)
    if sess.ended and sess.summary is not None:
        return TalkSummaryOut(**sess.summary)
    if any(m.role == "user" for m in sess.messages):
        charge_model_call(request, s)
    found = store.find_scenario(s, sess.scenario_id) if sess.scenario_id else None
    course, sc = found if found else (None, None)
    draft = summarize(get_provider(s.ai_provider), sess, sc)
    words = [CourseItem(id=f"{sess.id}-w{i}", text=w.text.strip(), tr=w.tr, gloss=w.gloss.strip())
             for i, w in enumerate(draft.new_words) if w.text.strip() and w.gloss.strip()]
    # One card per word, whichever session it came from; words the course teaches already have theirs.
    taught = {" ".join(i.text.split()) for c in store.load_courses(s) if c.target == sess.target
              for i in c.items().values()}
    fresh = [CourseItem(id=f"word:{' '.join(w.text.split())}", text=w.text, tr=w.tr, gloss=w.gloss)
             for w in words if " ".join(w.text.split()) not in taught]
    added = 0
    if fresh:
        talk_deck = CourseDef(id=f"talk-{sess.target}", target=sess.target, support=sess.support,
                              level="A1", title="Talk", units=[])
        added = _add_cards(s, talk_deck, fresh, "talk")
    out = TalkSummaryOut(went_well=draft.went_well, mistakes=[m.model_dump() for m in draft.mistakes],
                         new_words=words, cards_added=added)
    sess.ended = True
    sess.summary = out.model_dump(mode="json")
    _talk_repo(s).save(sess)
    return out


# ---- activity -----------------------------------------------------------------------

class ActivityRequest(BaseModel):
    seconds: int = Field(ge=0, le=6 * 3600)
    kind: Literal["story", "audio", "review", "other"] = "other"
    event_id: str | None = Field(None, max_length=80)


@router.post("/activity", status_code=204)
def log_activity_endpoint(req: ActivityRequest, s: Settings = Depends(get_settings)) -> Response:
    """Time spent outside lessons (stories, audio, the diary) toward the daily goal and streak."""
    seen_path = s.data_dir / "activity_events.json"
    if req.event_id:
        try:
            seen = json.loads(seen_path.read_text("utf-8")) if seen_path.exists() else []
        except ValueError:
            seen = []
        if req.event_id in seen:
            return Response(status_code=204)
        seen_path.write_text(json.dumps([*seen[-499:], req.event_id]), encoding="utf-8")
    if req.seconds:
        store.log_activity(s, req.seconds)
    return Response(status_code=204)


# ---- who am I ------------------------------------------------------------------------

class WhoAmI(BaseModel):
    login: str
    name: str
    owner: bool


@router.get("/me", response_model=WhoAmI)
def me(request: Request) -> WhoAmI:
    who = identify(request)
    return WhoAmI(login=who.login, name=who.name, owner=who.owner)


# ---- speech -------------------------------------------------------------------------

@router.get("/speech", response_model=SpeechInfo)
def speech_info(s: Settings = Depends(get_settings)) -> SpeechInfo:
    langs = sorted(set(piper.DEFAULT_VOICES) | {p.name for p in piper.voices_dir(s).glob("*") if p.is_dir()})
    native = native_count(s)
    return SpeechInfo(server_tts={lang: piper.tts_available(s, lang) or (lang == "fa" and native > 0) for lang in langs},
                      stt=piper.stt_available(), native_texts=native)


@router.get("/tts")
def tts(lang: str, text: str, request: Request, s: Settings = Depends(get_settings)) -> FileResponse:
    if not re.fullmatch(r"[a-z]{2,3}", lang):
        raise HTTPException(400, "bad language code")
    # A native speaker's take wins when one exists: a random one of the takes each time, so learners hear
    # natural variation. Not cacheable for that reason.
    native = pick_take(s, text)
    if native is not None:
        path, take = native
        return FileResponse(path, media_type="audio/mp4",
                            headers={"Cache-Control": "no-store", "X-Voice": take.get("speaker", "native")})
    if not piper.tts_available(s, lang):
        raise HTTPException(404, f"no local voice for {lang}")
    if not piper.is_cached(s, text, lang):
        # Course text is synthesised once and shared; a guest's new text counts against their daily cap.
        charge_model_call(request, s)
    try:
        path = piper.synthesize(s, text, lang)
    except piper.SpeechError as exc:
        raise HTTPException(400, str(exc)) from exc
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "public, max-age=86400"})  # a day: native takes may replace it


# ---- recordings ---------------------------------------------------------------------

_AUDIO_EXT = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a", "audio/mpeg": ".mp3",
              "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/aac": ".aac", "audio/flac": ".flac"}
MAX_RECORDING = 20 * 1024 * 1024
MAX_AUDIO = 300 * 1024 * 1024


def _ext_for(upload: UploadFile) -> tuple[str, str]:
    mime = (upload.content_type or "").split(";")[0].strip() or "application/octet-stream"
    ext = Path(upload.filename or "").suffix.lower()
    if not ext or len(ext) > 6:
        ext = _AUDIO_EXT.get(mime, mimetypes.guess_extension(mime) or ".bin")
    if not mime.startswith("audio/") and not mime.startswith("video/"):
        guessed = mimetypes.guess_type(f"x{ext}")[0]
        if not guessed or not (guessed.startswith("audio/") or guessed.startswith("video/")):
            raise HTTPException(415, "That doesn't look like an audio file.")
        mime = guessed
    return mime, ext


def _save_upload(upload: UploadFile, dest: Path, limit: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with dest.open("wb") as f:
        while chunk := upload.file.read(1 << 20):
            size += len(chunk)
            if size > limit:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File too large (max {limit // (1024 * 1024)} MB).")
            f.write(chunk)


def _rec_repo(s: Settings) -> JsonRepository:
    return JsonRepository(s.data_dir, "recordings", RecordingMeta)


def _rec_out(m: RecordingMeta) -> RecordingOut:
    return RecordingOut(id=m.id, ref=m.ref, language=m.language, mime_type=m.mime_type, seconds=m.seconds,
                        created_at=m.created_at, url=f"/api/recordings/{m.id}/file")


@router.get("/recordings", response_model=list[RecordingOut])
def list_recordings(ref: str | None = None, ref_prefix: str | None = None, language: str | None = None,
                    s: Settings = Depends(get_settings)) -> list[RecordingOut]:
    recs = [m for m in _rec_repo(s).list()
            if (ref is None or m.ref == ref) and (ref_prefix is None or m.ref.startswith(ref_prefix))
            and (language is None or m.language == language)]
    recs.sort(key=lambda m: m.created_at, reverse=True)
    return [_rec_out(m) for m in recs]


@router.post("/recordings", response_model=RecordingOut, status_code=201)
def add_recording(request: Request, file: UploadFile = File(...), ref: str = Form(...),
                  language: str = Form(...), seconds: float | None = Form(None),
                  s: Settings = Depends(get_settings)) -> RecordingOut:
    check_guest_storage(request, s, int(request.headers.get("content-length") or 0))
    mime, ext = _ext_for(file)
    rid = make_id("rec", ref, utcnow().isoformat())
    meta = RecordingMeta(id=rid, ref=ref[:200], language=language[:8], mime_type=mime,
                         filename=f"{rid}{ext}", seconds=seconds)
    _save_upload(file, _rec_repo(s).dir / meta.filename, MAX_RECORDING)
    _rec_repo(s).save(meta)
    store.log_activity(s, int(seconds or 0))
    return _rec_out(meta)


@router.get("/recordings/{rec_id}/file")
def recording_file(rec_id: str, s: Settings = Depends(get_settings)) -> FileResponse:
    meta = _rec_repo(s).get(rec_id)
    if not meta:
        raise HTTPException(404, "recording not found")
    return FileResponse(_rec_repo(s).dir / meta.filename, media_type=meta.mime_type)


@router.delete("/recordings/{rec_id}", status_code=204)
def delete_recording(rec_id: str, s: Settings = Depends(get_settings)) -> Response:
    repo = _rec_repo(s)
    meta = repo.get(rec_id)
    if not meta:
        raise HTTPException(404, "recording not found")
    (repo.dir / meta.filename).unlink(missing_ok=True)
    repo.delete(rec_id)
    return Response(status_code=204)


# ---- imported audio -------------------------------------------------------------------

def _audio_repo(s: Settings) -> JsonRepository:
    return JsonRepository(s.data_dir, "audio", AudioMeta)


def _audio_out(m: AudioMeta) -> AudioOut:
    return AudioOut(id=m.id, title=m.title, language=m.language, mime_type=m.mime_type, source=m.source,
                    has_transcript=bool(m.cues), created_at=m.created_at, url=f"/api/audio/{m.id}/file")


def _audio_or_404(s: Settings, audio_id: str) -> AudioMeta:
    meta = _audio_repo(s).get(audio_id)
    if not meta:
        raise HTTPException(404, "audio not found")
    return meta


@router.get("/audio", response_model=list[AudioOut])
def list_audio(language: str | None = None, s: Settings = Depends(get_settings)) -> list[AudioOut]:
    items = sorted((m for m in _audio_repo(s).list() if language is None or m.language == language),
                   key=lambda m: m.created_at, reverse=True)
    return [_audio_out(m) for m in items]


@router.get("/audio/{audio_id}", response_model=AudioDetail)
def get_audio(audio_id: str, s: Settings = Depends(get_settings)) -> AudioDetail:
    meta = _audio_or_404(s, audio_id)
    return AudioDetail(**_audio_out(meta).model_dump(), cues=meta.cues)


@router.post("/audio", response_model=AudioOut, status_code=201)
def upload_audio(request: Request, file: UploadFile = File(...), language: str = Form(...),
                 title: str | None = Form(None), transcript: UploadFile | None = File(None),
                 s: Settings = Depends(get_settings)) -> AudioOut:
    check_guest_storage(request, s, int(request.headers.get("content-length") or 0))
    mime, ext = _ext_for(file)
    name = title or Path(file.filename or "audio").stem
    aid = make_id("audio", name, utcnow().isoformat())
    cues: list[Cue] = []
    if transcript is not None and transcript.filename:
        raw = transcript.file.read(5 * 1024 * 1024).decode("utf-8", "replace")
        cues = [Cue(**c) for c in parse_transcript(raw, transcript.filename)]
    meta = AudioMeta(id=aid, title=name[:200], language=language[:8], mime_type=mime,
                     filename=f"{aid}{ext}", source="upload", cues=cues)
    _save_upload(file, _audio_repo(s).dir / meta.filename, MAX_AUDIO)
    _audio_repo(s).save(meta)
    return _audio_out(meta)


@router.post("/audio/from-materials", response_model=AudioOut, status_code=201,
             dependencies=[Depends(require_owner)])
def audio_from_materials(req: FromMaterialsRequest, s: Settings = Depends(get_settings)) -> AudioOut:
    cfg = find_source(_profile(s), req.source)
    if cfg is None:
        raise HTTPException(404, f"materials source not found: {req.source}")
    provider = build_provider(cfg)
    try:
        entry = provider.metadata(req.path)
        if entry.size_bytes and entry.size_bytes > MAX_AUDIO:
            raise HTTPException(413, "File too large (max 300 MB).")
        data = provider.read(req.path)
    except MaterialsError as exc:
        raise HTTPException(400, str(exc)) from exc
    ext = Path(req.path).suffix.lower() or ".bin"
    mime = mimetypes.guess_type(f"x{ext}")[0] or "application/octet-stream"
    if not (mime.startswith("audio/") or mime.startswith("video/")):
        raise HTTPException(415, "That doesn't look like an audio file.")
    name = req.title or Path(req.path).stem
    aid = make_id("audio", name, utcnow().isoformat())
    meta = AudioMeta(id=aid, title=name[:200], language=req.language[:8], mime_type=mime,
                     filename=f"{aid}{ext}", source="materials")
    path = _audio_repo(s).dir / meta.filename
    path.write_bytes(data)
    # A sidecar transcript next to the file (same stem, .srt/.vtt) comes along if present.
    stem = req.path.rsplit(".", 1)[0]
    for sub_ext in (".srt", ".vtt"):
        try:
            raw = provider.read(stem + sub_ext).decode("utf-8", "replace")
        except MaterialsError:
            continue
        meta.cues = [Cue(**c) for c in parse_transcript(raw)]
        break
    _audio_repo(s).save(meta)
    return _audio_out(meta)


@router.get("/audio/{audio_id}/file")
def audio_file(audio_id: str, s: Settings = Depends(get_settings)) -> FileResponse:
    meta = _audio_or_404(s, audio_id)
    return FileResponse(_audio_repo(s).dir / meta.filename, media_type=meta.mime_type)


@router.post("/audio/{audio_id}/transcribe", response_model=AudioDetail, dependencies=[Depends(require_owner)])
def transcribe_audio(audio_id: str, s: Settings = Depends(get_settings)) -> AudioDetail:
    meta = _audio_or_404(s, audio_id)
    if not piper.stt_available():
        raise HTTPException(501, "Transcription needs faster-whisper: pip install faster-whisper")
    try:
        cues = piper.transcribe_cues(_audio_repo(s).dir / meta.filename, language=meta.language)
    except piper.SpeechError as exc:
        raise HTTPException(422, str(exc)) from exc
    meta.cues = [Cue(**c) for c in cues]
    _audio_repo(s).save(meta)
    return AudioDetail(**_audio_out(meta).model_dump(), cues=meta.cues)


@router.delete("/audio/{audio_id}", status_code=204)
def delete_audio(audio_id: str, s: Settings = Depends(get_settings)) -> Response:
    meta = _audio_or_404(s, audio_id)
    (_audio_repo(s).dir / meta.filename).unlink(missing_ok=True)
    _audio_repo(s).delete(audio_id)
    return Response(status_code=204)
