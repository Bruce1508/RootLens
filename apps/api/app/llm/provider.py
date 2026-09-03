from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    # §25.10: keep model-specific code behind this interface — callers
    # never import the `ollama` client directly.
    def generate_structured(self, prompt: str, schema: type[T], model: str | None = None) -> T: ...

    def health_check(self) -> bool: ...
