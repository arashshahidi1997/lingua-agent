import pytest

from lingua_agent.models import Exercise, ExerciseAttempt, ExerciseType, GradingMode
from lingua_agent.tutor.grading import grade_attempt_deterministic


def _ex(**overrides) -> Exercise:
    base = dict(
        id="ex_test",
        type=ExerciseType.TRANSLATE_A_TO_B,
        source_language="en",
        target_language="it",
        prompt="Translate: coffee",
        expected_answer="caffè",
        acceptable_answers=["il caffè", "un caffè"],
        difficulty=2,
        grading_mode=GradingMode.DETERMINISTIC,
    )
    base.update(overrides)
    return Exercise(**base)


def test_exact_match_correct():
    result = grade_attempt_deterministic(_ex(), "caffè")
    assert result.correct
    assert result.score == 1.0


def test_acceptable_alternate_correct():
    result = grade_attempt_deterministic(_ex(), "Un Caffè")
    assert result.correct


def test_persian_zwnj_tolerance():
    ex = _ex(target_language="fa", expected_answer="می‌رود", acceptable_answers=[])
    # Learner typed it without ZWNJ — should still pass.
    result = grade_attempt_deterministic(ex, "میرود")
    assert result.correct


def test_incorrect_answer_returns_feedback():
    result = grade_attempt_deterministic(_ex(), "tea")
    assert not result.correct
    assert "caffè" in result.feedback


def test_difficulty_bounds():
    with pytest.raises(Exception):  # pydantic ValidationError
        Exercise(
            id="ex_x", type=ExerciseType.CLOZE, source_language="en", target_language="it",
            prompt="x", difficulty=10,
        )


def test_attempt_score_bounds():
    with pytest.raises(Exception):
        ExerciseAttempt(id="a", exercise_id="x", learner_id="default",
                         answer="x", correct=True, score=1.5)
