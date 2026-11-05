from __future__ import annotations

from typing import Any

import requests

from core.providers.base import BaseStructuredClient, LLMError, ProviderConfig


class OpenAICompatibleClient(BaseStructuredClient):
    """Adapter for OpenAI Chat Completions and every compatible provider.

    Works with DeepSeek, OpenAI, Gemini's OpenAI-compatible endpoint,
    OpenRouter, Groq, Mistral, Together, Fireworks, Ollama, LM Studio,
    vLLM and any custom endpoint that speaks the same protocol.
    """

    def __init__(self, config: ProviderConfig, **kwargs: Any) -> None:
        super().__init__(config, **kwargs)
        base = config.base_url.rstrip("/")
        self._url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.config.extra_headers}
        if self.config.api_key:
            headers[self.config.auth_header] = f"{self.config.auth_prefix}{self.config.api_key}"
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
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        if correction:
            messages.append({"role": "user", "content": correction})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            self.config.max_tokens_field: self.config.max_tokens,
            **self.config.extra_body,
        }
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature

        if mode == "json_schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "schema": schema.model_json_schema(),
                    "strict": True,
                },
            }
        elif mode == "json_object":
            payload["response_format"] = {"type": "json_object"}

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
        if data.get("error"):
            raise LLMError(f"{self.name} error: {data['error']}")

        choices = data.get("choices") or []
        if not choices:
            raise LLMError(f"{self.name} returned no choices")

        choice = choices[0] or {}
        finish = choice.get("finish_reason")
        if finish == "length":
            raise LLMError(
                f"{self.name} truncated the JSON output because max_tokens was reached"
            )
        if finish in {"content_filter", "insufficient_system_resource", "aborted"}:
            raise LLMError(f"{self.name} stopped the response: {finish}")

        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") in (None, "text")
            )
        if not isinstance(content, str) or not content.strip():
            raise LLMError(f"{self.name} returned empty content")
        return content
