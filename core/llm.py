from __future__ import annotations

import time
from typing import Callable, Protocol, TypeVar

from pydantic import BaseModel

from core.config import settings
from core.logging_config import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

class LLMError(RuntimeError):
    pass

class LLMClient(Protocol):
    name: str

    def generate_structured(self, prompt: str, schema: type[T], *, system: str | None = None) -> T: ...

def classify_error(exc: Exception) -> str:
    text = str(exc)
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return "quota"
    if "404" in text or "NOT_FOUND" in text:
        return "unavailable"
    return "transient"

class GeminiClient:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        models: list[str],
        max_attempts_per_model: int = 2,
        quota_cooldown: float = 60.0,
        client: object | None = None,
    ) -> None:
        if not models:
            raise LLMError("GeminiClient needs at least one model")
        if client is None:
            from google import genai

            client = genai.Client(api_key=api_key)
        self._client = client
        self._models = models
        self._max_attempts = max_attempts_per_model
        self._quota_cooldown = quota_cooldown
        self._blocked_until: dict[str, float] = {}
        self.active_model = models[0]

    def _available_models(self) -> list[str]:
        now = time.monotonic()
        return [m for m in self._models if self._blocked_until.get(m, 0.0) <= now]

    def _block(self, model: str, kind: str) -> None:
        if kind == "unavailable":
            self._blocked_until[model] = float("inf")
        else:
            self._blocked_until[model] = time.monotonic() + self._quota_cooldown

    def generate_structured(self, prompt: str, schema: type[T], *, system: str | None = None) -> T:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=schema,
        )

        candidates = self._available_models()
        if not candidates:
            raise LLMError(
                f"Every configured Gemini model is rate limited or unavailable: {', '.join(self._models)}. "
                "Wait for the quota window to reset, or add more models to GEMINI_MODEL_FALLBACKS."
            )

        last_error: Exception | None = None
        for model in candidates:
            for attempt in range(1, self._max_attempts + 1):
                started = time.perf_counter()
                try:
                    response = self._client.models.generate_content(model=model, contents=prompt, config=config)
                    elapsed_ms = round((time.perf_counter() - started) * 1000)
                    parsed = response.parsed
                    if parsed is None:
                        parsed = schema.model_validate_json(response.text)
                    if model != self.active_model:
                        log.info("llm_model_switched", to=model, from_=self.active_model)
                        self.active_model = model
                    log.debug("llm_call", model=model, schema=schema.__name__, elapsed_ms=elapsed_ms)
                    return parsed
                except Exception as exc:
                    last_error = exc
                    kind = classify_error(exc)
                    log.warning(
                        "llm_retry", model=model, kind=kind, attempt=attempt,
                        schema=schema.__name__, error=str(exc)[:200],
                    )
                    if kind in ("quota", "unavailable"):
                        self._block(model, kind)
                        break
                    if attempt < self._max_attempts:
                        time.sleep(2 ** (attempt - 1))

        raise LLMError(f"All Gemini models failed ({', '.join(candidates)}): {last_error}") from last_error

def build_llm_client(mock_factory: Callable[[], LLMClient] | None = None) -> LLMClient:
    backend = settings.llm_backend
    if backend == "gemini":
        if not settings.gemini_api_key:
            raise LLMError("LLM_BACKEND=gemini but GEMINI_API_KEY is empty")
        return GeminiClient(settings.gemini_api_key, settings.gemini_models)

    if mock_factory is None:
        raise LLMError(
            "LLM_BACKEND resolves to 'mock' but no mock client was supplied. "
            "Set GEMINI_API_KEY, or pass mock_factory=... from the calling package."
        )
    return mock_factory()
