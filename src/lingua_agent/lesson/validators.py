"""Light validators for lesson units."""

from __future__ import annotations

from ..languages.registry import has_language
from ..models import LessonUnit


class LessonValidationError(ValueError):
    pass


def validate_unit(unit: LessonUnit) -> None:
    if not unit.title:
        raise LessonValidationError("title is required")
    if not has_language(unit.source_language):
        raise LessonValidationError(f"unknown source_language: {unit.source_language}")
    if not has_language(unit.target_language):
        raise LessonValidationError(f"unknown target_language: {unit.target_language}")
    if unit.source_language == unit.target_language:
        raise LessonValidationError("source_language and target_language must differ")
    if unit.support_language and not has_language(unit.support_language):
        raise LessonValidationError(f"unknown support_language: {unit.support_language}")
