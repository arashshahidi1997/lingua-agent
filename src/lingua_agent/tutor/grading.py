"""Grading helpers.

Three modes (see Exercise.grading_mode):
- deterministic: normalize and compare against expected/acceptable answers.
- llm_rubric:    handed to AIProvider with a rubric prompt (Phase 5).
- hybrid:        deterministic first; fall back to llm_rubric if it doesn't
                 match (so common phrasings count as correct without a model
                 call, and harder cases get a graded explanation).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..models import Exercise


@dataclass
class GradingResult:
    correct: bool
    score: float
    feedback: str


_PUNCT_RE = re.compile(r"[\s\.,!?;:'\"\-\(\)\[\]\{\}،؟。！？]+")
# Persian zero-width-non-joiner (U+200C) is structurally meaningful but learners
# often omit it; we strip it before comparison so its absence isn't penalised.
_ZWNJ = "‌"


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(_ZWNJ, "")
    text = _PUNCT_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def grade_attempt_deterministic(exercise: Exercise, answer: str) -> GradingResult:
    candidates = []
    if exercise.expected_answer:
        candidates.append(exercise.expected_answer)
    candidates.extend(exercise.acceptable_answers or [])
    norm_answer = normalize(answer)
    norm_candidates = [normalize(c) for c in candidates if c]
    if not norm_candidates:
        return GradingResult(correct=False, score=0.0,
                              feedback="No reference answer is set for this exercise.")
    if norm_answer in norm_candidates:
        return GradingResult(correct=True, score=1.0, feedback="Correct.")
    return GradingResult(
        correct=False,
        score=0.0,
        feedback=f"Expected one of: {', '.join(candidates)}",
    )
