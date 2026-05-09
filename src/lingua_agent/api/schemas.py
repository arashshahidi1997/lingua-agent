"""Request / response schemas for the HTTP API.

Kept separate from the storage models so we can evolve the wire format
independently. For now most response schemas are direct projections; we'll
add view-models if/when the React side asks for shapes the storage models
don't fit naturally.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    ai_provider: str


class LanguageOut(BaseModel):
    code: str
    name: str
    native_name: str
    script: str
    direction: str
    transliteration_supported: bool


class LearnerProfilePatch(BaseModel):
    display_name: str | None = None
    preferred_support_language: str | None = None
    ui_language: str | None = None
    correction_style: str | None = None
    interests: list[str] | None = None
    native_languages: list[str] | None = None


class IngestTextRequest(BaseModel):
    text: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_language: str
    target_language: str
    support_language: str | None = None
    cefr_level: str | None = None
    tags: list[str] = Field(default_factory=list)


class IngestSummary(BaseModel):
    unit_id: str
    document_id: str
    title: str
    source_language: str
    target_language: str
    vocabulary_count: int
    grammar_count: int
    exercise_count: int
    flashcard_count: int
    unit_path: str | None = None


class UnitListItem(BaseModel):
    id: str
    title: str
    source_language: str
    target_language: str
    cefr_level: str | None = None
    vocabulary_count: int
    grammar_count: int
    exercise_count: int
    flashcard_count: int
    created_at: datetime


class UnitDetail(BaseModel):
    """Lesson unit with all referenced entities inlined.

    Saves the React client a fan-out of N-by-id GETs: the modal opens with
    one round-trip and renders the full vocab / grammar / exercises lists.
    """
    id: str
    title: str
    source_language: str
    target_language: str
    support_language: str | None
    cefr_level: str | None
    summary: str | None
    bilingual_reading: list[dict]
    tags: list[str]
    vocabulary: list[dict]
    grammar: list[dict]
    exercises: list[dict]
    flashcards: list[dict]


class CardOut(BaseModel):
    id: str
    front: str
    back: str
    source_language: str
    target_language: str
    direction: str
    card_type: str
    interval: int
    ease_factor: float
    repetitions: int
    lapses: int
    needs_extra_review: bool
    due_at: datetime


class ReviewRequest(BaseModel):
    rating: int = Field(ge=0, le=5)


class ReviewResponse(BaseModel):
    card: CardOut
    interval_after: int
    ease_after: float
    repetitions_after: int


class TutorSessionOut(BaseModel):
    id: str
    source_language: str
    target_language: str
    support_language: str | None
    messages: list[dict]
    created_at: datetime
    updated_at: datetime


class OpenSessionRequest(BaseModel):
    source_language: str
    target_language: str
    support_language: str | None = "en"


class TutorMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class TutorMessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime
