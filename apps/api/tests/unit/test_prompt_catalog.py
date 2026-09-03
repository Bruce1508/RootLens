import pytest


def test_get_prompt_definition_returns_decomposition_planner_v2() -> None:
    from app.prompts.catalog import get_prompt_definition

    definition = get_prompt_definition("decomposition_planner")

    assert definition.name == "decomposition_planner"
    assert definition.version == "v2"
    assert "{metric}" in definition.template
    assert "{cancellation_current_value}" in definition.template


def test_get_prompt_definition_raises_for_unknown_prompt() -> None:
    from app.prompts.catalog import get_prompt_definition

    with pytest.raises(KeyError):
        get_prompt_definition("nonexistent_prompt")
