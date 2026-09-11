from __future__ import annotations

import pytest
from pydantic import BaseModel

from core.llm import GeminiClient, LLMError, classify_error

class Answer(BaseModel):
    value: str

class FakeResponse:
    def __init__(self, parsed):
        self.parsed = parsed
        self.text = "{}"

class FakeModels:
    def __init__(self, behaviour: dict[str, object]):
        self.behaviour = behaviour
        self.calls: list[str] = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        outcome = self.behaviour.get(model, "ok")
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(Answer(value=f"answered-by-{model}"))

class FakeClient:
    def __init__(self, behaviour: dict[str, object]):
        self.models = FakeModels(behaviour)

def build(behaviour, models=("model-a", "model-b", "model-c"), **kwargs) -> GeminiClient:
    return GeminiClient(
        api_key="unused", models=list(models), client=FakeClient(behaviour),
        max_attempts_per_model=2, **kwargs,
    )

def quota_error() -> Exception:
    return RuntimeError("429 RESOURCE_EXHAUSTED. You exceeded your current quota")

def missing_model_error() -> Exception:
    return RuntimeError("404 NOT_FOUND. This model is no longer available to new users")

@pytest.mark.parametrize(
    "exc,expected",
    [
        (quota_error(), "quota"),
        (missing_model_error(), "unavailable"),
        (RuntimeError("500 INTERNAL"), "transient"),
        (TimeoutError("read timed out"), "transient"),
    ],
)
def test_error_classification(exc, expected):
    assert classify_error(exc) == expected

def test_falls_back_to_next_model_on_quota_error():
    client = build({"model-a": quota_error()})

    result = client.generate_structured("prompt", Answer)

    assert result.value == "answered-by-model-b"
    assert client.active_model == "model-b"
    assert client._client.models.calls == ["model-a", "model-b"]

def test_skips_retired_model_and_never_retries_it():
    client = build({"model-a": missing_model_error()})

    client.generate_structured("first", Answer)
    client.generate_structured("second", Answer)

    assert client._client.models.calls == ["model-a", "model-b", "model-b"]

def test_exhausted_model_is_skipped_until_cooldown_expires():
    client = build({"model-a": quota_error()}, quota_cooldown=600.0)

    client.generate_structured("first", Answer)
    client.generate_structured("second", Answer)

    assert client._client.models.calls == ["model-a", "model-b", "model-b"]

def test_transient_error_retries_the_same_model_before_switching():
    client = build({"model-a": RuntimeError("503 UNAVAILABLE")}, quota_cooldown=0.0)

    client.generate_structured("prompt", Answer)

    assert client._client.models.calls[:2] == ["model-a", "model-a"]

def test_error_names_every_model_when_all_are_exhausted():
    client = build({m: quota_error() for m in ("model-a", "model-b", "model-c")})

    with pytest.raises(LLMError) as excinfo:
        client.generate_structured("prompt", Answer)

    for model in ("model-a", "model-b", "model-c"):
        assert model in str(excinfo.value)

def test_recovered_model_is_used_again_after_cooldown():
    behaviour = {"model-a": quota_error()}
    client = build(behaviour, quota_cooldown=0.0)

    client.generate_structured("first", Answer)
    behaviour.pop("model-a")
    result = client.generate_structured("second", Answer)

    assert result.value == "answered-by-model-a"
    assert client.active_model == "model-a"
