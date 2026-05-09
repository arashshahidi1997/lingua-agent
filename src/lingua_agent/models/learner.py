"""Learner profile + memory."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utcnow


class KnownLanguage(BaseModel):
    code: str
    cefr_level: str | None = None  # A1..C2 or None


class TargetLanguage(BaseModel):
    code: str
    cefr_goal: str = "B1"


class MemoryEntry(BaseModel):
    id: str
    kind: Literal["fact", "preference", "weakness"]
    text: str
    created_at: datetime = Field(default_factory=utcnow)


class LearnerProfile(BaseModel):
    id: str = "default"
    display_name: str = "Learner"
    native_languages: list[str] = Field(default_factory=lambda: ["en"])
    known_languages: list[KnownLanguage] = Field(default_factory=list)
    target_languages: list[TargetLanguage] = Field(default_factory=list)
    preferred_support_language: str = "en"
    ui_language: str = "en"
    correction_style: Literal["gentle", "direct"] = "gentle"
    interests: list[str] = Field(default_factory=list)
    last_active_pair: tuple[str, str] | None = None
    memory: list[MemoryEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
