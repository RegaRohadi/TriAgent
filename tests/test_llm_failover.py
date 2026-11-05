from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from core.providers.base import LLMError, ProviderConfig, classify_error
from core.providers.openai_compat import OpenAICompatibleClient
from core.providers.registry import FallbackClient


class Answer(BaseModel):
    value: str


class FakeHTTPError(Exception):
    def __init__(self, status_code: int, message: str = "") -> None:
        self.response = SimpleNamespace(status_code=status_code)
        super().__init__(message or f"{status_code} error")


class FakeResponse:
    def __init__(self, payload: dict | None = None, status_code: int = 200) -> None:
        self._payload = payload or {}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise FakeHTTPError(self.status_code)

    def json(self) -> dict:
        return self._payload


class FakeHTTP:
    def __init__(self, behaviour: dict[str, object]) -> None:
        self.behaviour = behaviour
        self.calls: list[str] = []
        self.payloads: list[dict] = []
        self.headers: list[dict[str, str]] = []
        self.urls: list[str] = []
        self._counts: dict[str, int] = {}

    def post(self, url, json=None, headers=None, timeout=None):
        payload = json or {}
        model = payload.get("model", "unknown")
        self.calls.append(model)
        self.payloads.append(payload)
        self.headers.append(headers or {})
        self.urls.append(url)

        outcome = self.behaviour.get(model, "ok")
        if isinstance(outcome, list):
            index = min(self._counts.get(model, 0), len(outcome) - 1)
            self._counts[model] = index + 1
            outcome = outcome[index]
        if callable(outcome):
            outcome = outcome(payload)
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, FakeResponse):
            return outcome
        if isinstance(outcome, dict):
            return FakeResponse(outcome)
        return FakeResponse(ok_json(f"answered-by-{model}"))


def ok_payload(content: str, finish: str = "stop") -> dict:
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


def ok_json(value: str) -> dict:
    return ok_payload(json.dumps({"value": value}))


def build(
    behaviour: dict[str, object],
    models=("model-a", "model-b", "model-c"),
    structured_mode: str = "json_object",
    **kwargs,
) -> OpenAICompatibleClient:
    config = ProviderConfig(
        name="test",
        kind="openai",
        api_key="unused",
        base_url="https://example.test/v1",
        models=list(models),
        structured_mode=structured_mode,
        timeout=5.0,
        max_tokens=1024,
    )
    return OpenAICompatibleClient(
        config,
        http=FakeHTTP(behaviour),
        sleep=lambda _: None,
        max_attempts_per_model=2,
        **kwargs,
    )


def make_client(name: str, behaviour: dict[str, object]) -> OpenAICompatibleClient:
    config = ProviderConfig(
        name=name,
        kind="openai",
        api_key="unused",
        base_url="https://example.test/v1",
        models=["model-a"],
        structured_mode="json_object",
        timeout=5.0,
        max_tokens=1024,
    )
    return OpenAICompatibleClient(
        config,
        http=FakeHTTP(behaviour),
        sleep=lambda _: None,
        max_attempts_per_model=1,
    )


@pytest.mark.parametrize(
    "exc,expected",
    [
        (FakeHTTPError(429), "quota"),
        (FakeHTTPError(404), "unavailable"),
        (FakeHTTPError(401), "auth"),
        (FakeHTTPError(402), "balance"),
        (RuntimeError("500 INTERNAL"), "transient"),
        (TimeoutError("read timed out"), "transient"),
        (RuntimeError("429 RESOURCE_EXHAUSTED"), "quota"),
        (RuntimeError("404 NOT_FOUND"), "unavailable"),
    ],
)
def test_error_classification(exc, expected):
    assert classify_error(exc) == expected


def test_falls_back_to_next_model_on_quota_error():
    client = build({"model-a": FakeHTTPError(429)})

    result = client.generate_structured("prompt", Answer)

    assert result.value == "answered-by-model-b"
    assert client.active_model == "model-b"
    assert client._http.calls == ["model-a", "model-b"]


def test_skips_retired_model_and_never_retries_it():
    client = build({"model-a": FakeHTTPError(404)})

    client.generate_structured("first", Answer)
    client.generate_structured("second", Answer)

    assert client._http.calls == ["model-a", "model-b", "model-b"]


def test_exhausted_model_is_skipped_until_cooldown_expires():
    client = build({"model-a": FakeHTTPError(429)}, quota_cooldown=600.0)

    client.generate_structured("first", Answer)
    client.generate_structured("second", Answer)

    assert client._http.calls == ["model-a", "model-b", "model-b"]


def test_transient_error_retries_the_same_model_before_switching():
    client = build({"model-a": FakeHTTPError(503)}, quota_cooldown=0.0)

    client.generate_structured("prompt", Answer)

    assert client._http.calls[:2] == ["model-a", "model-a"]


def test_error_names_every_model_when_all_are_exhausted():
    client = build({m: FakeHTTPError(429) for m in ("model-a", "model-b", "model-c")})

    with pytest.raises(LLMError) as excinfo:
        client.generate_structured("prompt", Answer)

    for model in ("model-a", "model-b", "model-c"):
        assert model in str(excinfo.value)


def test_recovered_model_is_used_again_after_cooldown():
    behaviour = {"model-a": FakeHTTPError(429)}
    client = build(behaviour, quota_cooldown=0.0)

    client.generate_structured("first", Answer)
    behaviour.pop("model-a")
    result = client.generate_structured("second", Answer)

    assert result.value == "answered-by-model-a"
    assert client.active_model == "model-a"


def test_request_contains_schema_auth_and_base_url():
    client = build({})

    client.generate_structured("prompt", Answer)

    payload = client._http.payloads[0]
    assert client._http.urls[0] == "https://example.test/v1/chat/completions"
    assert client._http.headers[0]["Authorization"] == "Bearer unused"
    assert payload["response_format"] == {"type": "json_object"}
    system = payload["messages"][0]["content"]
    assert "JSON Schema" in system
    assert '"value"' in system


def test_markdown_fences_are_stripped():
    client = build({"model-a": ok_payload('```json\n{"value": "ok"}\n```')})

    assert client.generate_structured("prompt", Answer).value == "ok"


def test_invalid_json_retries_with_correction():
    client = build({"model-a": [ok_payload("not json"), ok_json("recovered")]})

    result = client.generate_structured("prompt", Answer)

    assert result.value == "recovered"
    assert client._http.calls == ["model-a", "model-a"]
    assert "invalid" in client._http.payloads[1]["messages"][-1]["content"]


def test_downgrades_json_schema_to_json_object():
    client = build(
        {
            "model-a": [
                FakeHTTPError(400, "response_format json_schema is not supported"),
                ok_json("ok"),
            ]
        },
        structured_mode="json_schema",
    )

    result = client.generate_structured("prompt", Answer)

    assert result.value == "ok"
    assert client._structured_mode == "json_object"
    assert client._http.payloads[0]["response_format"]["type"] == "json_schema"
    assert client._http.payloads[1]["response_format"]["type"] == "json_object"


def test_auth_error_raises_immediately():
    client = build({"model-a": FakeHTTPError(401)})

    with pytest.raises(LLMError) as excinfo:
        client.generate_structured("prompt", Answer)

    assert excinfo.value.kind == "auth"
    assert client._http.calls == ["model-a"]


def test_balance_error_raises_immediately():
    client = build({"model-a": FakeHTTPError(402)})

    with pytest.raises(LLMError) as excinfo:
        client.generate_structured("prompt", Answer)

    assert excinfo.value.kind == "balance"
    assert client._http.calls == ["model-a"]


def test_truncated_output_is_retried():
    client = build(
        {"model-a": [ok_payload('{"value":', finish="length"), ok_json("complete")]}
    )

    result = client.generate_structured("prompt", Answer)

    assert result.value == "complete"
    assert client._http.calls == ["model-a", "model-a"]


def test_fallback_client_tries_next_provider():
    first = make_client("first", {"model-a": FakeHTTPError(429)})
    second = make_client("second", {"model-a": ok_json("second-provider")})
    client = FallbackClient([first, second])

    result = client.generate_structured("prompt", Answer)

    assert result.value == "second-provider"
    assert client.name == "second"
    assert client.active_model == "model-a"
