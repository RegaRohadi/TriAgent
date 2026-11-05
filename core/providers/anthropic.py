from __future__ import annotations

import json
from typing import Any

import requests

from core.providers.base import BaseStructuredClient, LLMError, ProviderConfig


class AnthropicClient(BaseStructuredClient):
    """Adapter for Anthropic's native Messages API.

    Structured output uses a forced tool call whose ``input_schema`` is the
    Pydantic JSON Schema, which keeps the result valid even though Anthropic
    does not expose OpenAI's ``response_format`` field.
    """

    def __init__(self, config: ProviderConfig, **kwargs: Any) -> None:
        super().__init__(config, **kwargs)
        base = config.base_url.rstrip("/")
        if base.endswith("/v1/messages"):
            self._url = base
        elif base.endswith("/v1"):
            self._url = f"{base}/messages"
        else:
            self._url = f"{base}/v1/messages"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": self.config.anthropic_version,
            **self.config.extra_headers,
        }
        if self.config.api_key:
            headers[self.config.auth_header] = (
                f"{self.config.auth_prefix}{self.config.api_key}"
            )
        return headers

    def _request(
        self,
        model: str,
        prompt: str,
        system: str,
        *,
        schema: type,
        mode: str,
        correction: str | None = None,
    ) -> str:
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        if correction:
            messages.append({"role": "user", "content": correction})

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": self.config.max_tokens,
            "system": system,
            "messages": messages,
            "tools": [
                {
                    "name": "structured_output",
                    "description": "Return the structured answer as JSON.",
                    "input_schema": schema.model_json_schema(),
                }
            ],
            "tool_choice": {"type": "tool", "name": "structured_output"},
            **self.config.extra_body,
        }
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature

        client = self._http or requests
        response = client.post(
            self._url,
            json=payload,
            headers=self._headers(),
            timeout=self.config.timeout,
        )
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError(f"{self.name} returned a non-JSON response") from exc
        if not isinstance(data, dict):
            raise LLMError(f"{self.name} returned an unexpected response")
        if data.get("type") == "error" or data.get("error"):
            raise LLMError(f"{self.name} error: {data.get('error')}")

        stop = data.get("stop_reason")
        if stop == "max_tokens":
            raise LLMError(
                f"{self.name} truncated the JSON output because max_tokens was reached"
            )

        blocks = data.get("content") or []
        for block in blocks:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "structured_output"
            ):
                return json.dumps(block.get("input") or {}, ensure_ascii=False)

        text = "".join(
            block.get("text", "")
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if not text.strip():
            raise LLMError(f"{self.name} returned empty content")
        return text
