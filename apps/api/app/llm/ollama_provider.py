import httpx
from ollama import Client, ResponseError
from pydantic import ValidationError

from app.llm.provider import T

_DEFAULT_TIMEOUT_SECONDS = 120.0


class OllamaProvider:
    def __init__(
        self, base_url: str, default_model: str, timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        # Discovered while smoke-testing the Milestone 5 evaluation runner:
        # the ollama client's default httpx timeout is None (unbounded), so
        # a stalled generation could hang a scenario — and the whole
        # benchmark run behind it — forever. Bounded to the same order as
        # the investigation loop's own wall-clock budget (engine.py's
        # _WALL_CLOCK_TIMEOUT_SECONDS).
        self._client = Client(host=base_url, timeout=timeout_seconds)
        self._default_model = default_model

    def generate_structured(self, prompt: str, schema: type[T], model: str | None = None) -> T:
        target_model = model or self._default_model
        schema_dict = schema.model_json_schema()

        # qwen3 is a hybrid-thinking model: left at its default, it spends an
        # unbounded, highly variable number of tokens on a hidden reasoning
        # trace before emitting the JSON this call actually wants (observed
        # 0.5s with think=False vs. 21.7s with the default on an identical
        # prompt), which is what pushed several Phase 2 benchmark runs past
        # the client's 120s timeout. The trace is pure overhead for a
        # schema-validated structured-output call.
        response = self._client.generate(
            model=target_model, prompt=prompt, format=schema_dict, think=False
        )
        try:
            return schema.model_validate_json(response.response or "")
        except ValidationError as first_error:
            # PRD §20 failure mode "Invalid model JSON": retry once with the
            # validation feedback fed back into the prompt, then fail clearly.
            retry_prompt = (
                f"{prompt}\n\nYour previous response was not valid JSON matching "
                f"the required schema. Validation error: {first_error}\n"
                "Respond again with corrected JSON only, matching the schema exactly."
            )
            retry_response = self._client.generate(
                model=target_model, prompt=retry_prompt, format=schema_dict, think=False
            )
            try:
                return schema.model_validate_json(retry_response.response or "")
            except ValidationError as second_error:
                raise ValueError(
                    f"Model '{target_model}' failed to produce output matching "
                    f"{schema.__name__} after 2 attempts: {second_error}"
                ) from second_error

    def health_check(self) -> bool:
        try:
            self._client.list()
            return True
        except (ResponseError, httpx.ConnectError, httpx.TimeoutException):
            return False
