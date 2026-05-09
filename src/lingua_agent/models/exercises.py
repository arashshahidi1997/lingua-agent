"""Exercise definitions and learner attempts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .base import Provenance, utcnow


class ExerciseType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    CLOZE = "cloze"
    TRANSLATE_A_TO_B = "translate_a_to_b"
    TRANSLATE_B_TO_A = "translate_b_to_a"
    FREE_WRITE = "free_write"
    SENTENCE_ORDERING = "sentence_ordering"
    MATCH_PAIRS = "match_pairs"
    MORPHOLOGY_PARSE = "morphology_parse"
    LISTENING_DICTATION = "listening_dictation"
    SPEAKING_PROMPT = "speaking_prompt"
    MINIMAL_PAIR = "minimal_pair"


class GradingMode(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM_RUBRIC = "llm_rubric"
    HYBRID = "hybrid"


class GeneratedFrom(BaseModel):
    unit_id: str | None = None
    document_id: str | None = None
    vocabulary_ids: list[str] = Field(default_factory=list)
    grammar_ids: list[str] = Field(default_factory=list)


class Exercise(BaseModel):
    id: str
    type: ExerciseType
    source_language: str
    target_language: str
    prompt: str
    expected_answer: str | None = None
    acceptable_answers: list[str] = Field(default_factory=list)
    choices: list[str] = Field(default_factory=list)  # for multiple_choice / match_pairs
    hints: list[str] = Field(default_factory=list)
    explanation: str | None = None
    difficulty: int = Field(default=1, ge=1, le=5)
    skill_tags: list[str] = Field(default_factory=list)
    generated_from: GeneratedFrom = Field(default_factory=GeneratedFrom)
    grading_mode: GradingMode = GradingMode.DETERMINISTIC
    provenance: Provenance = Field(default_factory=Provenance)


class ExerciseAttempt(BaseModel):
    id: str
    exercise_id: str
    learner_id: str
    answer: str
    correct: bool
    score: float = Field(ge=0.0, le=1.0)
    feedback: str = ""
    attempted_at: datetime = Field(default_factory=utcnow)
