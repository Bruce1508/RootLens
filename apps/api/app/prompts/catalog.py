from app.prompts.definitions.decomposition_planner_v1 import DECOMPOSITION_PLANNER_V1
from app.prompts.schemas import PromptDefinition

_CATALOG: dict[str, PromptDefinition] = {
    DECOMPOSITION_PLANNER_V1.name: DECOMPOSITION_PLANNER_V1,
}


def get_prompt_definition(name: str) -> PromptDefinition:
    return _CATALOG[name]


def list_prompt_names() -> list[str]:
    return list(_CATALOG.keys())
