"""LessonUnit — the canonical lesson entity, mirrored to a markdown file."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utcnow


class ReadingPair(BaseModel):
    source: str
    target: str


class LessonUnit(BaseModel):
    id: str
    title: str
    source_language: str
    target_language: str
    support_language: str | None = None
    cefr_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"] | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    vocabulary_ids: list[str] = Field(default_factory=list)
    grammar_ids: list[str] = Field(default_factory=list)
    exercise_ids: list[str] = Field(default_factory=list)
    flashcard_ids: list[str] = Field(default_factory=list)
    bilingual_reading: list[ReadingPair] = Field(default_factory=list)
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
