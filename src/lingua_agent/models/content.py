"""Content entities: Document, segments, vocabulary, grammar."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import Provenance, utcnow


class Document(BaseModel):
    id: str
    title: str
    source_language: str
    text: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class TextSegment(BaseModel):
    document_id: str
    index: int
    kind: Literal["paragraph", "sentence"]
    text: str


class Sentence(BaseModel):
    id: str
    document_id: str
    index: int
    text: str
    language: str


class VocabularyItem(BaseModel):
    id: str
    lemma: str
    surface: str
    target_language: str
    translations: dict[str, list[str]] = Field(default_factory=dict)
    pos: str | None = None
    gender: Literal["m", "f", "n"] | None = None
    transliteration: str | None = None
    example_sentence_id: str | None = None
    example_text: str | None = None
    cefr_level: str | None = None
    provenance: Provenance = Field(default_factory=Provenance)


class GrammarPoint(BaseModel):
    id: str
    target_language: str
    name: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    cefr_level: str | None = None
    support_language: str | None = None
    provenance: Provenance = Field(default_factory=Provenance)
