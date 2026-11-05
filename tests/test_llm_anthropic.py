from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from core.providers.anthropic import AnthropicClient
from core.providers.base import LLMError, ProviderConfig


class Answer(BaseModel):
    value: str


class FakeHTTPError(Exception):
    def __init__(self, status_code: int, message: str = "") -> None:
        self.response = SimpleNamespace(status_code=status_code)
        super().__init__(message or f"{status_code} error")


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise FakeHTTPError(self.status_code)

    def json(self) -> dict:
        return self._payload


class FakeHTTP:
    def __init__(self, payload: dict | Exception) -> None:
        self.payload = payload
        self.calls: list[dict] = []
        self.headers: list[dict] = []
        self.urls: list[str] = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(json or {})
        self.headers.append(headers or {})
        self.urls.append(url)
        if isinstance(self.payload, Exception):
            raise self.payload
        return FakeResponse(self.payload)


def build(payload: dict | Exception) -> AnthropicClient:
    config = ProviderConfig(
        name="anthropic",
        kind="anthropic",
        api_key="test-key",
        base_url="https://api.anthropic.com",
        models=["claude-test"],
        structured_mode="tool",
        timeout=5.0,
        max_tokens=1024,
        auth_header="x-api-key",
        auth_prefix="",
    )
    return AnthropicClient(
        config,
        http=FakeHTTP(payload),
        sleep=lambda _: None,
        max_attempts_per_model=1,
    )


def test_request_uses_native_anthropic_shape():
    payload = {
        "stop_reason": "tool_use",
        "content": [
            {
                "type": "tool_use",
                "name": "structured_output",
                "input": {"value": "ok"},
            }
        ],
    }
    client = build(payload)

    result = client.generate_structured("prompt", Answer, system="Be precise.")

    assert result.value == "ok"
    request = client._http.calls[0]
    headers = client._http.headers[0]
    assert client._http.urls[0] == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == "test-key"
    assert headers["anthropic-version"] == "2023-06-01"
    assert request["system"].startswith("Be precise.")
    assert "JSON Schema" in request["system"]
    assert request["tools"][0]["input_schema"]["properties"]["value"]["type"] == "string"
    assert request["tool_choice"] == {"type": "tool", "name": "structured_output"}


def test_text_block_falls_back_to_json_parsing():
    payload = {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": '{"value": "from-text"}'}],
    }
    client = build(payload)

    assert client.generate_structured("prompt", Answer).value == "from-text"


def test_max_tokens_truncation_raises():
    payload = {
        "stop_reason": "max_tokens",
        "content": [{"type": "text", "text": '{"value":'}],
    }
    client = build(payload)

    with pytest.raises(LLMError, match="truncated"):
        client.generate_structured("prompt", Answer)
