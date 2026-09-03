import httpx
from ollama import Client, ResponseError
from pydantic import ValidationError

from app.llm.provider import T


class OllamaProvider:
    def __init__(self, base_url: str, default_model: str) -> None:
        self._client = Client(host=base_url)
        self._default_model = default_model

    def generate_structured(self, prompt: str, schema: type[T], model: str | None = None) -> T:
        target_model = model or self._default_model
        schema_dict = schema.model_json_schema()

        response = self._client.generate(model=target_model, prompt=prompt, format=schema_dict)
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
                model=target_model, prompt=retry_prompt, format=schema_dict
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
