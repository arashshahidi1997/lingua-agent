from lingua_agent.tutor.tools import TOOL_REGISTRY


def test_required_tools_registered():
    expected = {
        "get_learner_profile",
        "update_learner_profile",
        "list_due_cards",
        "add_flashcard",
        "grade_exercise_attempt",
        "generate_exercise",
        "explain_mistake",
        "compare_languages",
        "switch_language_pair",
        "recommend_next_activity",
    }
    assert expected.issubset(set(TOOL_REGISTRY))


def test_tools_carry_schemas_and_side_effect():
    for name, spec in TOOL_REGISTRY.items():
        assert spec.name == name
        assert spec.side_effect in {"read", "write", "external"}
        assert isinstance(spec.args_schema, dict)
        assert isinstance(spec.result_schema, dict)
