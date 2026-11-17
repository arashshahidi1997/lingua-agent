"""Course definitions (hand-authored YAML) and per-learner progress.

A course is static, reviewable data: units → lessons → items, plus stories and
role-play scenarios. Exercises are generated from the items (`exercises.py`), so
the YAML never has to spell out a single quiz question.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..models.base import utcnow


class CourseItem(BaseModel):
    id: str
    text: str
    tr: str | None = None
    gloss: str
    note: str | None = None


class CourseLesson(BaseModel):
    id: str
    title: str
    kind: Literal["script", "words", "phrases", "grammar"] = "words"
    note: str | None = None
    items: list[CourseItem]


class CourseUnit(BaseModel):
    id: str
    title: str
    goal: str = ""
    lessons: list[CourseLesson]
    story: str | None = None
    scenario: str | None = None


class Speaker(BaseModel):
    name: str
    voice: Literal["male", "female"] = "female"


class StoryLine(CourseItem):
    id: str = ""  # filled in by the loader: "<story>-<index>"
    speaker: str


class StoryDef(BaseModel):
    id: str
    unit: str
    kind: Literal["story", "dialogue"] = "story"
    title: str
    title_gloss: str = ""
    speakers: dict[str, Speaker]
    lines: list[StoryLine]


class ScenarioPhrase(BaseModel):
    text: str
    tr: str | None = None
    gloss: str


class ScenarioDef(BaseModel):
    id: str
    unit: str
    title: str
    title_target: str = ""
    setting: str
    persona: str
    goal: str
    opener: ScenarioPhrase
    useful: list[ScenarioPhrase] = Field(default_factory=list)


class CourseDef(BaseModel):
    id: str
    target: str
    support: str
    level: str
    title: str
    description: str = ""
    units: list[CourseUnit]
    stories: list[StoryDef] = Field(default_factory=list)
    scenarios: list[ScenarioDef] = Field(default_factory=list)

    # -- lookups -------------------------------------------------------------

    def lessons(self) -> list[tuple[CourseUnit, CourseLesson]]:
        return [(u, lesson) for u in self.units for lesson in u.lessons]

    def unit(self, unit_id: str) -> CourseUnit | None:
        return next((u for u in self.units if u.id == unit_id), None)

    def lesson(self, lesson_id: str) -> tuple[CourseUnit, CourseLesson] | None:
        return next(((u, lesson) for u, lesson in self.lessons() if lesson.id == lesson_id), None)

    def items(self) -> dict[str, CourseItem]:
        return {i.id: i for _, lesson in self.lessons() for i in lesson.items}

    def story(self, story_id: str) -> StoryDef | None:
        return next((s for s in self.stories if s.id == story_id), None)

    def scenario(self, scenario_id: str) -> ScenarioDef | None:
        return next((s for s in self.scenarios if s.id == scenario_id), None)


# ---- progress -----------------------------------------------------------------

class LessonRecord(BaseModel):
    best_score: float
    attempts: int = 1
    completed_at: datetime = Field(default_factory=utcnow)


class ItemStats(BaseModel):
    seen: int = 0
    correct: int = 0
    wrong: int = 0
    last_seen: datetime | None = None

    @property
    def weakness(self) -> float:
        """Higher = needs more practice. Unseen-in-practice items sit in the middle."""
        return (self.wrong + 1) / (self.correct + self.wrong + 2)


class CourseProgress(BaseModel):
    course_id: str
    lessons: dict[str, LessonRecord] = Field(default_factory=dict)
    quizzes: dict[str, LessonRecord] = Field(default_factory=dict)  # by unit id
    items: dict[str, ItemStats] = Field(default_factory=dict)
    events: list[str] = Field(default_factory=list)  # applied event ids (offline replays are ignored)
    updated_at: datetime = Field(default_factory=utcnow)


class ActivityDay(BaseModel):
    day: date
    seconds: int = 0
    sessions: int = 0
