import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from ollama import ResponseError

from app.llm.ollama_provider import OllamaProvider
from app.llm.schemas import DecompositionPlan

_VALID_PLAN_JSON = json.dumps(
    {
        "metric": "product_revenue",
        "primary_driver_hypothesis": "order_volume",
        "rationale": "Order count fell 20% while average order value was flat.",
        "recommended_next_dimension": "customer_state",
    }
)

_INVALID_PLAN_JSON = json.dumps({"metric": "product_revenue"})  # missing required fields


def _provider_with_fake_client() -> tuple[OllamaProvider, MagicMock]:
    provider = OllamaProvider(base_url="http://fake-ollama:11434", default_model="qwen3:8b")
    fake_client = MagicMock()
    provider._client = fake_client
    return provider, fake_client


def test_generate_structured_returns_valid_instance_on_first_try() -> None:
    provider, fake_client = _provider_with_fake_client()
    fake_client.generate.return_value = SimpleNamespace(response=_VALID_PLAN_JSON)

    result = provider.generate_structured("investigate revenue drop", DecompositionPlan)

    assert result == DecompositionPlan.model_validate_json(_VALID_PLAN_JSON)
    assert fake_client.generate.call_count == 1


def test_generate_structured_uses_default_model_when_none_given() -> None:
    provider, fake_client = _provider_with_fake_client()
    fake_client.generate.return_value = SimpleNamespace(response=_VALID_PLAN_JSON)

    provider.generate_structured("investigate revenue drop", DecompositionPlan)

    assert fake_client.generate.call_args.kwargs["model"] == "qwen3:8b"


def test_generate_structured_uses_explicit_model_override() -> None:
    provider, fake_client = _provider_with_fake_client()
    fake_client.generate.return_value = SimpleNamespace(response=_VALID_PLAN_JSON)

    provider.generate_structured(
        "investigate revenue drop", DecompositionPlan, model="qwen3:30b-a3b"
    )

    assert fake_client.generate.call_args.kwargs["model"] == "qwen3:30b-a3b"


def test_generate_structured_passes_schema_as_format() -> None:
    provider, fake_client = _provider_with_fake_client()
    fake_client.generate.return_value = SimpleNamespace(response=_VALID_PLAN_JSON)

    provider.generate_structured("investigate revenue drop", DecompositionPlan)

    assert fake_client.generate.call_args.kwargs["format"] == DecompositionPlan.model_json_schema()


def test_generate_structured_retries_once_on_invalid_json_then_succeeds() -> None:
    provider, fake_client = _provider_with_fake_client()
    fake_client.generate.side_effect = [
        SimpleNamespace(response=_INVALID_PLAN_JSON),
        SimpleNamespace(response=_VALID_PLAN_JSON),
    ]

    result = provider.generate_structured("investigate revenue drop", DecompositionPlan)

    assert result == DecompositionPlan.model_validate_json(_VALID_PLAN_JSON)
    assert fake_client.generate.call_count == 2
    retry_prompt = fake_client.generate.call_args_list[1].kwargs["prompt"]
    assert "Validation error" in retry_prompt
    assert "investigate revenue drop" in retry_prompt


def test_generate_structured_raises_after_two_failed_attempts() -> None:
    provider, fake_client = _provider_with_fake_client()
    fake_client.generate.side_effect = [
        SimpleNamespace(response=_INVALID_PLAN_JSON),
        SimpleNamespace(response=_INVALID_PLAN_JSON),
    ]

    with pytest.raises(ValueError, match="qwen3:8b"):
        provider.generate_structured("investigate revenue drop", DecompositionPlan)

    assert fake_client.generate.call_count == 2


def test_health_check_returns_true_when_list_succeeds() -> None:
    provider, fake_client = _provider_with_fake_client()
    fake_client.list.return_value = SimpleNamespace(models=[])

    assert provider.health_check() is True


def test_health_check_returns_false_on_connection_error() -> None:
    provider, fake_client = _provider_with_fake_client()
    fake_client.list.side_effect = httpx.ConnectError("connection refused")

    assert provider.health_check() is False


def test_health_check_returns_false_on_response_error() -> None:
    provider, fake_client = _provider_with_fake_client()
    fake_client.list.side_effect = ResponseError("model registry unavailable", 500)

    assert provider.health_check() is False


def _ollama_is_reachable() -> bool:
    try:
        httpx.get("http://localhost:11434/api/tags", timeout=1.0)
        return True
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not _ollama_is_reachable(), reason="local Ollama daemon is not running")
def test_generate_structured_against_live_local_ollama() -> None:
    """Proves the Milestone 2 exit criterion for real: the backend receives
    a schema-valid structured planning response from a local model — no
    mocking of the HTTP layer in this one test."""
    provider = OllamaProvider(base_url="http://localhost:11434", default_model="qwen3:8b")

    result = provider.generate_structured(
        "Revenue was $10,000 last period and $7,500 this period. Order count "
        "fell from 200 to 140 while average order value stayed roughly "
        "constant. Decide the primary driver and which dimension to inspect "
        "next.",
        DecompositionPlan,
    )

    assert isinstance(result, DecompositionPlan)
    assert result.primary_driver_hypothesis in ("order_volume", "average_order_value", "mixed")
    assert result.recommended_next_dimension in ("customer_state", "product_category")
    assert len(result.rationale) > 0
