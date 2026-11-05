from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from core.logging_config import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

STRUCTURED_MODES = ("json_schema", "json_object", "prompt")


class LLMError(RuntimeError):
    """A provider request failed.

    ``kind`` is one of: auth, balance, quota, unavailable, transient.
    """

    def __init__(self, message: str, *, kind: str = "transient", status: int | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.status = status


class LLMClient(Protocol):
    name: str
    active_model: str | None

    def generate_structured(self, prompt: str, schema: type[T], *, system: str | None = None) -> T: ...


@dataclass
class ProviderConfig:
    """Everything a provider adapter needs to make one request."""

    name: str
    kind: str
    api_key: str
    base_url: str
    models: list[str]
    timeout: float = 120.0
    max_tokens: int = 8192
    structured_mode: str = "auto"
    temperature: float | None = 0.0
    max_tokens_field: str = "max_tokens"
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    extra_headers: dict[str, str] = field(default_factory=dict)
    extra_body: dict[str, Any] = field(default_factory=dict)
    anthropic_version: str = "2023-06-01"

    @property
    def model(self) -> str:
        return self.models[0]


def status_code(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(exc, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def classify_error(exc: Exception) -> str:
    """Map provider/network/validation errors to a small retry vocabulary."""

    status = status_code(exc)
    text = str(exc)
    lower = text.lower()

    if (
        status == 429
        or "429" in text
        or "rate limit" in lower
        or "too many requests" in lower
        or "resource_exhausted" in lower
    ):
        return "quota"
    if status == 402 or "402" in text or "insufficient balance" in lower or "insufficient_quota" in lower:
        return "balance"
    if (
        status in (401, 403)
        or "401" in text
        or "403" in text
        or "unauthorized" in lower
        or "invalid api key" in lower
        or "authentication" in lower
    ):
        return "auth"
    if (
        status in (400, 404, 422)
        or "404" in text
        or "not found" in lower
        or "not_found" in lower
        or "model_not_found" in lower
        or "unsupported" in lower
    ):
        return "unavailable"
    return "transient"


def strip_json_fences(text: str) -> str:
    """Remove Markdown fences and isolate the outermost JSON object if needed."""

    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    if cleaned and not cleaned.startswith(("{", "[")):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]
    return cleaned.strip()


def schema_instruction(schema: type[BaseModel]) -> str:
    schema_json = json.dumps(schema.model_json_schema(), indent=2, ensure_ascii=False)
    return (
        "Return ONLY one valid json object that matches the JSON Schema below. "
        "Do not wrap it in Markdown fences, do not add commentary, and do not omit "
        "required fields.\n\n"
        f"JSON Schema:\n{schema_json}"
    )


def build_system_prompt(system: str | None, schema: type[BaseModel]) -> str:
    parts: list[str] = []
    if system:
        parts.append(system.strip())
    parts.append(schema_instruction(schema))
    return "\n\n".join(parts)


def next_structured_mode(mode: str) -> str | None:
    if mode == "auto":
        return "json_schema"
    if mode not in STRUCTURED_MODES:
        return None
    index = STRUCTURED_MODES.index(mode)
    return STRUCTURED_MODES[index + 1] if index + 1 < len(STRUCTURED_MODES) else None


class BaseStructuredClient:
    """Shared retry, failover and JSON validation for every provider adapter."""

    name: str

    def __init__(
        self,
        config: ProviderConfig,
        *,
        max_attempts_per_model: int = 2,
        quota_cooldown: float = 60.0,
        http: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not config.models:
            raise LLMError(f"{type(self).__name__} needs at least one model")
        self.config = config
        self.name = config.name
        self.active_model = config.models[0]
        self._models = list(config.models)
        self._max_attempts = max(1, max_attempts_per_model)
        self._quota_cooldown = quota_cooldown
        self._http = http
        self._sleep = sleep
        self._blocked_until: dict[str, float] = {}
        self._structured_mode = config.structured_mode or "auto"

    def _available_models(self) -> list[str]:
        now = time.monotonic()
        return [m for m in self._models if self._blocked_until.get(m, 0.0) <= now]

    def _block(self, model: str, kind: str) -> None:
        if kind == "unavailable":
            self._blocked_until[model] = float("inf")
        else:
            self._blocked_until[model] = time.monotonic() + self._quota_cooldown

    @staticmethod
    def _should_downgrade(exc: Exception, mode: str) -> bool:
        if mode not in ("json_schema", "json_object"):
            return False
        if status_code(exc) not in (400, 422):
            return False
        text = str(exc).lower()
        return any(
            token in text
            for token in (
                "response_format",
                "json_schema",
                "json_object",
                "schema",
                "not supported",
                "unsupported",
                "unknown parameter",
            )
        )

    def _request(
        self,
        model: str,
        prompt: str,
        system: str,
        *,
        schema: type[BaseModel],
        mode: str,
        correction: str | None = None,
    ) -> str:
        raise NotImplementedError

    def generate_structured(self, prompt: str, schema: type[T], *, system: str | None = None) -> T:
        candidates = self._available_models()
        if not candidates:
            raise LLMError(
                f"Every configured {self.name} model is rate limited or unavailable: "
                f"{', '.join(self._models)}. Wait for the quota window to reset or add "
                "fallback models with LLM_MODEL_FALLBACKS."
            )

        system_prompt = build_system_prompt(system, schema)
        mode = self._structured_mode if self._structured_mode not in ("", "auto") else "json_schema"
        last_error: Exception | None = None

        for model in candidates:
            correction: str | None = None
            attempt = 1
            while attempt <= self._max_attempts:
                started = time.perf_counter()
                try:
                    text = self._request(
                        model,
                        prompt,
                        system_prompt,
                        schema=schema,
                        mode=mode,
                        correction=correction,
                    )
                    cleaned = strip_json_fences(text)
                    if not cleaned:
                        raise ValueError("model returned empty content")
                    parsed = schema.model_validate_json(cleaned)
                    elapsed_ms = round((time.perf_counter() - started) * 1000)
                    if model != self.active_model:
                        log.info(
                            "llm_model_switched",
                            provider=self.name,
                            to=model,
                            from_=self.active_model,
                        )
                        self.active_model = model
                    log.debug(
                        "llm_call",
                        provider=self.name,
                        model=model,
                        schema=schema.__name__,
                        mode=mode,
                        elapsed_ms=elapsed_ms,
                    )
                    return parsed
                except Exception as exc:
                    last_error = exc
                    if isinstance(exc, LLMError):
                        kind = exc.kind
                    elif isinstance(exc, (ValidationError, ValueError)):
                        kind = "transient"
                    else:
                        kind = classify_error(exc)
                    log.warning(
                        "llm_retry",
                        provider=self.name,
                        model=model,
                        kind=kind,
                        attempt=attempt,
                        schema=schema.__name__,
                        error=str(exc)[:300],
                    )

                    if kind in ("auth", "balance"):
                        raise LLMError(
                            f"{self.name} rejected the request ({kind}): {exc}", kind=kind
                        ) from exc

                    if self._should_downgrade(exc, mode):
                        new_mode = next_structured_mode(mode)
                        if new_mode:
                            log.warning(
                                "llm_structured_mode_downgraded",
                                provider=self.name,
                                from_=mode,
                                to=new_mode,
                            )
                            mode = new_mode
                            self._structured_mode = new_mode
                            continue

                    if kind in ("quota", "unavailable"):
                        self._block(model, kind)
                        break

                    if isinstance(exc, (ValidationError, ValueError, json.JSONDecodeError)):
                        if attempt < self._max_attempts:
                            correction = (
                                f"Your previous response was invalid: {str(exc)[:500]}. "
                                "Return only a valid json object that matches the JSON Schema."
                            )
                    if attempt < self._max_attempts:
                        self._sleep(2 ** (attempt - 1))
                    attempt += 1

        raise LLMError(
            f"All configured {self.name} models failed ({', '.join(candidates)}): {last_error}"
        ) from last_error
