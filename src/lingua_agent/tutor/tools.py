"""Typed tutor tools.

Every tool is declared as a `ToolSpec` carrying typed `Args` and `Result`
Pydantic models plus a side-effect classification. Phase 6 will wire these
into a real LLM via `tutor/agent.py`; today they're a registry the CLI can
introspect and the mock provider can simulate against.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SideEffect = Literal["read", "write", "external"]


class ToolSpec(BaseModel):
    name: str
    description: str
    args_schema: dict[str, Any]
    result_schema: dict[str, Any]
    side_effect: SideEffect


# --- Args / Result schemas -------------------------------------------------

class _Empty(BaseModel):
    pass


class GetLearnerProfileResult(BaseModel):
    profile: dict[str, Any]


class UpdateLearnerProfileArgs(BaseModel):
    patch: dict[str, Any]


class ListDueCardsArgs(BaseModel):
    target_language: str | None = None
    limit: int = 20


class ListDueCardsResult(BaseModel):
    cards: list[dict[str, Any]]


class AddFlashcardArgs(BaseModel):
    front: str
    back: str
    source_language: str
    target_language: str
    direction: Literal["recognition", "production", "cloze"] = "production"
    card_type: Literal["vocab", "sentence", "grammar", "cloze"] = "vocab"
    examples: list[str] = Field(default_factory=list)
    mnemonic: str | None = None


class GradeExerciseAttemptArgs(BaseModel):
    exercise_id: str
    answer: str


class GradeExerciseAttemptResult(BaseModel):
    correct: bool
    score: float
    feedback: str


class GenerateExerciseArgs(BaseModel):
    unit_id: str
    type: str
    difficulty: int = 2


class ExplainMistakeArgs(BaseModel):
    answer: str
    expected: str
    source_language: str
    target_language: str


class CompareLanguagesArgs(BaseModel):
    source_language: str
    target_language: str
    item: str


class SwitchLanguagePairArgs(BaseModel):
    source: str
    target: str
    support: str | None = None


class RecommendNextActivityResult(BaseModel):
    kind: Literal["review_due", "new_exercise", "fresh_material", "rest"]
    reason: str
    payload: dict[str, Any] = Field(default_factory=dict)


# --- Registry --------------------------------------------------------------

def _spec(name: str, description: str, args: type[BaseModel], result: type[BaseModel],
          side_effect: SideEffect) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=description,
        args_schema=args.model_json_schema(),
        result_schema=result.model_json_schema(),
        side_effect=side_effect,
    )


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "get_learner_profile": _spec(
        "get_learner_profile",
        "Return the current learner profile (level goals, interests, weaknesses).",
        _Empty, GetLearnerProfileResult, "read",
    ),
    "update_learner_profile": _spec(
        "update_learner_profile",
        "Apply a partial update to the learner profile. Logged.",
        UpdateLearnerProfileArgs, _Empty, "write",
    ),
    "list_due_cards": _spec(
        "list_due_cards",
        "Return SRS cards due now, optionally filtered by target language.",
        ListDueCardsArgs, ListDueCardsResult, "read",
    ),
    "add_flashcard": _spec(
        "add_flashcard",
        "Insert a new flashcard. Marked with provenance.",
        AddFlashcardArgs, _Empty, "write",
    ),
    "grade_exercise_attempt": _spec(
        "grade_exercise_attempt",
        "Grade an answer against an exercise's expected/acceptable answers.",
        GradeExerciseAttemptArgs, GradeExerciseAttemptResult, "write",
    ),
    "generate_exercise": _spec(
        "generate_exercise",
        "Generate a new exercise of the given type and difficulty for a unit.",
        GenerateExerciseArgs, _Empty, "external",
    ),
    "explain_mistake": _spec(
        "explain_mistake",
        "Pedagogical explanation for why an answer is incorrect.",
        ExplainMistakeArgs, _Empty, "external",
    ),
    "compare_languages": _spec(
        "compare_languages",
        "Contrastive note about how an item is realised in source vs target.",
        CompareLanguagesArgs, _Empty, "external",
    ),
    "switch_language_pair": _spec(
        "switch_language_pair",
        "Update session and learner profile to use a different language pair.",
        SwitchLanguagePairArgs, _Empty, "write",
    ),
    "recommend_next_activity": _spec(
        "recommend_next_activity",
        "Suggest the next thing to do: review due cards, a new exercise, or fresh material.",
        _Empty, RecommendNextActivityResult, "read",
    ),
}
