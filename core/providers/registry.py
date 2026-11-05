from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from core.logging_config import get_logger
from core.providers.anthropic import AnthropicClient
from core.providers.base import (
    LLMClient,
    LLMError,
    ProviderConfig,
    STRUCTURED_MODES,
)
from core.providers.openai_compat import OpenAICompatibleClient

log = get_logger(__name__)


@dataclass(frozen=True)
class ProviderPreset:
    name: str
    kind: str
    key_env: str
    base_url: str
    base_url_env: str
    model_env: str
    default_model: str = ""
    structured_mode: str = "auto"
    max_tokens_field: str = "max_tokens"
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    extra_headers: tuple[tuple[str, str], ...] = ()
    extra_body: tuple[tuple[str, Any], ...] = ()
    anthropic_version: str = "2023-06-01"


PRESETS: dict[str, ProviderPreset] = {
    "deepseek": ProviderPreset(
        name="deepseek",
        kind="openai",
        key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com",
        base_url_env="DEEPSEEK_BASE_URL",
        model_env="DEEPSEEK_MODEL",
        default_model="deepseek-flash",
        structured_mode="json_object",
        extra_body=(("thinking", {"type": "disabled"}),),
    ),
    "openai": ProviderPreset(
        name="openai",
        kind="openai",
        key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        base_url_env="OPENAI_BASE_URL",
        model_env="OPENAI_MODEL",
        default_model="gpt-4.1-mini",
        structured_mode="json_schema",
    ),
    "anthropic": ProviderPreset(
        name="anthropic",
        kind="anthropic",
        key_env="ANTHROPIC_API_KEY",
        base_url="https://api.anthropic.com",
        base_url_env="ANTHROPIC_BASE_URL",
        model_env="ANTHROPIC_MODEL",
        default_model="claude-sonnet-4-5",
        structured_mode="tool",
        auth_header="x-api-key",
        auth_prefix="",
        anthropic_version="2023-06-01",
    ),
    "gemini": ProviderPreset(
        name="gemini",
        kind="openai",
        key_env="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        base_url_env="GEMINI_BASE_URL",
        model_env="GEMINI_MODEL",
        default_model="gemini-3.8-flash",
        structured_mode="json_schema",
    ),
    "openrouter": ProviderPreset(
        name="openrouter",
        kind="openai",
        key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
        base_url_env="OPENROUTER_BASE_URL",
        model_env="OPENROUTER_MODEL",
        structured_mode="auto",
    ),
    "groq": ProviderPreset(
        name="groq",
        kind="openai",
        key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
        base_url_env="GROQ_BASE_URL",
        model_env="GROQ_MODEL",
        structured_mode="json_object",
    ),
    "mistral": ProviderPreset(
        name="mistral",
        kind="openai",
        key_env="MISTRAL_API_KEY",
        base_url="https://api.mistral.ai/v1",
        base_url_env="MISTRAL_BASE_URL",
        model_env="MISTRAL_MODEL",
        default_model="mistral-small-latest",
        structured_mode="json_object",
    ),
    "together": ProviderPreset(
        name="together",
        kind="openai",
        key_env="TOGETHER_API_KEY",
        base_url="https://api.together.xyz/v1",
        base_url_env="TOGETHER_BASE_URL",
        model_env="TOGETHER_MODEL",
        structured_mode="auto",
    ),
    "fireworks": ProviderPreset(
        name="fireworks",
        kind="openai",
        key_env="FIREWORKS_API_KEY",
        base_url="https://api.fireworks.ai/inference/v1",
        base_url_env="FIREWORKS_BASE_URL",
        model_env="FIREWORKS_MODEL",
        structured_mode="auto",
    ),
    "ollama": ProviderPreset(
        name="ollama",
        kind="openai",
        key_env="",
        base_url="http://localhost:11434/v1",
        base_url_env="OLLAMA_BASE_URL",
        model_env="OLLAMA_MODEL",
        structured_mode="prompt",
    ),
    "lmstudio": ProviderPreset(
        name="lmstudio",
        kind="openai",
        key_env="",
        base_url="http://localhost:1234/v1",
        base_url_env="LMSTUDIO_BASE_URL",
        model_env="LMSTUDIO_MODEL",
        structured_mode="prompt",
    ),
    "custom": ProviderPreset(
        name="custom",
        kind="openai",
        key_env="LLM_API_KEY",
        base_url="",
        base_url_env="LLM_BASE_URL",
        model_env="LLM_MODEL",
        structured_mode="auto",
    ),
}

ALIASES = {
    "claude": "anthropic",
    "google": "gemini",
    "openai-compatible": "custom",
    "openai_compatible": "custom",
}

KEYLESS_PROVIDERS = {"ollama", "lmstudio", "custom"}


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    model: str = ""


def _split_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _env_json(name: str, env: Mapping[str, str]) -> dict[str, Any]:
    raw = env.get(name, "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(f"{name} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise LLMError(f"{name} must be a JSON object")
    return value


def _env_float(name: str, default: float, env: Mapping[str, str]) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise LLMError(f"{name} must be a number") from exc


def _env_int(name: str, default: int, env: Mapping[str, str]) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise LLMError(f"{name} must be an integer") from exc


def _env_temperature(env: Mapping[str, str]) -> float | None:
    raw = env.get("LLM_TEMPERATURE")
    if raw is None:
        return 0.0
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise LLMError("LLM_TEMPERATURE must be a number or empty") from exc


def _normalise_name(name: str) -> str:
    cleaned = name.strip().lower()
    return ALIASES.get(cleaned, cleaned)


def _parse_spec(raw: str) -> ProviderSpec:
    name, separator, model = raw.partition(":")
    return ProviderSpec(name=_normalise_name(name), model=model.strip() if separator else "")


def detect_providers(env: Mapping[str, str] | None = None) -> list[str]:
    """Return providers that have a usable key (or a complete custom config)."""

    env = env or os.environ
    found: list[str] = []
    for name, preset in PRESETS.items():
        if name in KEYLESS_PROVIDERS:
            continue
        if env.get(preset.key_env, "").strip():
            found.append(name)

    if env.get("LLM_BASE_URL", "").strip() and env.get("LLM_MODEL", "").strip():
        found.append("custom")
    return _dedupe(found)


def resolve_provider_specs(env: Mapping[str, str] | None = None) -> list[ProviderSpec]:
    env = env or os.environ
    explicit_raw = (env.get("LLM_PROVIDER", "") or env.get("LLM_BACKEND", "") or "auto").strip()
    explicit = explicit_raw.lower()

    if explicit in ("", "auto"):
        detected = detect_providers(env)
        if not detected:
            return []
        if len(detected) > 1:
            raise LLMError(
                "Multiple LLM API keys are configured. Fill only one key, or set "
                "LLM_PROVIDER to choose one of: " + ", ".join(detected)
            )
        primary = ProviderSpec(name=detected[0])
    elif explicit == "mock":
        return []
    else:
        primary = _parse_spec(explicit_raw)
        if primary.name not in PRESETS:
            raise LLMError(
                f"Unknown LLM_PROVIDER={primary.name!r}. Choose one of: "
                f"{', '.join(sorted(PRESETS))}, auto, mock"
            )

    specs = [primary]
    for item in _split_list(env.get("LLM_FALLBACK_PROVIDERS", "")):
        spec = _parse_spec(item)
        if spec.name not in PRESETS:
            raise LLMError(
                f"Unknown provider {spec.name!r} in LLM_FALLBACK_PROVIDERS. "
                f"Choose one of: {', '.join(sorted(PRESETS))}"
            )
        specs.append(spec)

    seen: set[tuple[str, str]] = set()
    result: list[ProviderSpec] = []
    for spec in specs:
        key = (spec.name, spec.model)
        if key not in seen:
            seen.add(key)
            result.append(spec)
    return result


def build_provider_config(
    name: str,
    env: Mapping[str, str] | None = None,
    *,
    model_override: str = "",
    is_primary: bool = True,
) -> ProviderConfig:
    env = env or os.environ
    preset = PRESETS.get(name)
    if preset is None:
        raise LLMError(f"Unknown LLM provider {name!r}")

    api_key = env.get(preset.key_env, "").strip() if preset.key_env else ""
    if preset.key_env and preset.name not in KEYLESS_PROVIDERS and not api_key:
        raise LLMError(
            f"{preset.key_env} is empty. Fill it in .env so TriAgent can use {preset.name}."
        )

    base_url = env.get(preset.base_url_env, "").strip() or preset.base_url
    if not base_url:
        raise LLMError(
            f"{preset.name} has no base URL. Set {preset.base_url_env} in .env."
        )

    generic_model = env.get("LLM_MODEL", "").strip() if is_primary else ""
    model = (
        model_override.strip()
        or generic_model
        or env.get(preset.model_env, "").strip()
        or preset.default_model
    )
    if not model:
        raise LLMError(
            f"Set {preset.model_env} in .env (there is no safe default model for {preset.name})."
        )

    generic_fallbacks = env.get("LLM_MODEL_FALLBACKS", "").strip() if is_primary else ""
    fallback_raw = (
        generic_fallbacks
        or env.get(f"{preset.name.upper()}_MODEL_FALLBACKS", "").strip()
    )
    models = _dedupe([model, *_split_list(fallback_raw)])

    structured_mode = (
        env.get("LLM_STRUCTURED_MODE", "").strip().lower() or preset.structured_mode
    )
    if preset.kind == "anthropic":
        structured_mode = "tool"
    elif structured_mode not in (*STRUCTURED_MODES, "auto"):
        raise LLMError(
            f"LLM_STRUCTURED_MODE={structured_mode!r} is invalid. "
            f"Choose auto, {', '.join(STRUCTURED_MODES)}."
        )

    return ProviderConfig(
        name=preset.name,
        kind=preset.kind,
        api_key=api_key,
        base_url=base_url,
        models=models,
        timeout=_env_float("LLM_TIMEOUT", 120.0, env),
        max_tokens=_env_int("LLM_MAX_TOKENS", 8192, env),
        structured_mode=structured_mode,
        temperature=_env_temperature(env),
        max_tokens_field=env.get("LLM_MAX_TOKENS_FIELD", "").strip()
        or preset.max_tokens_field,
        auth_header=env.get("LLM_AUTH_HEADER", "").strip() or preset.auth_header,
        auth_prefix=env.get("LLM_AUTH_PREFIX", preset.auth_prefix),
        extra_headers={**dict(preset.extra_headers), **_env_json("LLM_EXTRA_HEADERS", env)},
        extra_body={**dict(preset.extra_body), **_env_json("LLM_EXTRA_BODY", env)},
        anthropic_version=env.get("ANTHROPIC_VERSION", "").strip()
        or preset.anthropic_version,
    )


class FallbackClient:
    """Try providers in order when the active one is exhausted or misconfigured."""

    def __init__(self, clients: list[LLMClient]) -> None:
        if not clients:
            raise LLMError("FallbackClient needs at least one client")
        self._clients = clients
        self.name = clients[0].name
        self.active_model = clients[0].active_model

    def generate_structured(self, prompt: str, schema: type, *, system: str | None = None):
        errors: list[str] = []
        for client in self._clients:
            try:
                result = client.generate_structured(prompt, schema, system=system)
                self.name = client.name
                self.active_model = getattr(client, "active_model", None)
                return result
            except Exception as exc:
                errors.append(f"{client.name}: {str(exc)[:300]}")
                log.warning(
                    "llm_provider_failed",
                    provider=client.name,
                    error=str(exc)[:300],
                )
        raise LLMError("All configured LLM providers failed: " + " | ".join(errors))


def build_client(
    spec: ProviderSpec,
    env: Mapping[str, str] | None = None,
    *,
    is_primary: bool = True,
    **kwargs: Any,
) -> LLMClient:
    config = build_provider_config(
        spec.name, env, model_override=spec.model, is_primary=is_primary
    )
    if config.kind == "anthropic":
        return AnthropicClient(config, **kwargs)
    return OpenAICompatibleClient(config, **kwargs)


def build_llm_client(
    mock_factory: Callable[[], LLMClient] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    **kwargs: Any,
) -> LLMClient:
    env = env or os.environ
    specs = resolve_provider_specs(env)
    if not specs:
        if mock_factory is None:
            raise LLMError(
                "No LLM API key found. Fill one provider key in .env "
                "(DEEPSEEK_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, "
                "OPENROUTER_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY, TOGETHER_API_KEY, "
                "or FIREWORKS_API_KEY), or set LLM_PROVIDER=custom with LLM_BASE_URL "
                "and LLM_MODEL. Set LLM_PROVIDER=mock to run without a key."
            )
        return mock_factory()

    clients: list[LLMClient] = []
    for index, spec in enumerate(specs):
        try:
            clients.append(build_client(spec, env, is_primary=index == 0, **kwargs))
        except LLMError as exc:
            if index == 0:
                raise
            log.warning(
                "llm_fallback_provider_skipped",
                provider=spec.name,
                error=str(exc)[:300],
            )

    if not clients:
        raise LLMError("No configured LLM provider could be built.")
    if len(clients) == 1:
        return clients[0]
    return FallbackClient(clients)
