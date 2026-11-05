from __future__ import annotations

import pytest
from pydantic import BaseModel

from core.providers.base import LLMError
from core.providers.openai_compat import OpenAICompatibleClient
from core.providers.registry import (
    FallbackClient,
    ProviderSpec,
    build_llm_client,
    build_provider_config,
    resolve_provider_specs,
)


class Answer(BaseModel):
    value: str


class StubClient:
    name = "mock"
    active_model = None

    def generate_structured(self, prompt, schema, *, system=None):
        return Answer(value="mock")


def test_auto_detect_single_key():
    assert resolve_provider_specs({"DEEPSEEK_API_KEY": "x"}) == [ProviderSpec("deepseek")]


def test_auto_detect_multiple_keys_requires_explicit_provider():
    with pytest.raises(LLMError, match="Multiple LLM API keys"):
        resolve_provider_specs({"DEEPSEEK_API_KEY": "x", "OPENAI_API_KEY": "y"})


def test_explicit_provider_wins_over_detection():
    specs = resolve_provider_specs(
        {"DEEPSEEK_API_KEY": "x", "OPENAI_API_KEY": "y", "LLM_PROVIDER": "openai"}
    )
    assert specs == [ProviderSpec("openai")]


def test_llm_backend_alias_is_still_supported():
    specs = resolve_provider_specs({"OPENAI_API_KEY": "x", "LLM_BACKEND": "openai"})
    assert specs == [ProviderSpec("openai")]


def test_custom_provider_detected_from_base_url_and_model():
    specs = resolve_provider_specs(
        {"LLM_BASE_URL": "http://localhost:8080/v1", "LLM_MODEL": "local-model"}
    )
    assert specs == [ProviderSpec("custom")]


def test_unknown_provider_raises():
    with pytest.raises(LLMError, match="Unknown LLM_PROVIDER"):
        resolve_provider_specs({"LLM_PROVIDER": "does-not-exist"})


def test_provider_config_uses_safe_defaults():
    config = build_provider_config("deepseek", {"DEEPSEEK_API_KEY": "x"})

    assert config.name == "deepseek"
    assert config.models == ["deepseek-flash"]
    assert config.base_url == "https://api.deepseek.com"
    assert config.structured_mode == "json_object"
    assert config.extra_body == {"thinking": {"type": "disabled"}}


def test_provider_config_requires_a_key():
    with pytest.raises(LLMError, match="DEEPSEEK_API_KEY is empty"):
        build_provider_config("deepseek", {})


def test_provider_config_model_override():
    config = build_provider_config(
        "deepseek", {"DEEPSEEK_API_KEY": "x"}, model_override="deepseek-v4-pro"
    )

    assert config.models[0] == "deepseek-v4-pro"


def test_model_fallbacks_are_deduplicated():
    config = build_provider_config(
        "deepseek",
        {
            "DEEPSEEK_API_KEY": "x",
            "LLM_MODEL_FALLBACKS": "deepseek-v4-pro,deepseek-flash",
        },
    )

    assert config.models == ["deepseek-flash", "deepseek-v4-pro"]


def test_fallback_providers_are_appended():
    specs = resolve_provider_specs(
        {
            "DEEPSEEK_API_KEY": "x",
            "OPENAI_API_KEY": "y",
            "LLM_PROVIDER": "deepseek",
            "LLM_FALLBACK_PROVIDERS": "openai:gpt-4.1-mini",
        }
    )

    assert specs == [ProviderSpec("deepseek"), ProviderSpec("openai", "gpt-4.1-mini")]


def test_build_llm_client_returns_mock_when_no_key():
    client = build_llm_client(lambda: StubClient(), env={})

    assert client.name == "mock"


def test_build_llm_client_without_key_and_without_mock_raises():
    with pytest.raises(LLMError, match="No LLM API key found"):
        build_llm_client(env={})


def test_explicit_mock_wins_even_when_a_key_exists():
    client = build_llm_client(
        lambda: StubClient(), env={"DEEPSEEK_API_KEY": "x", "LLM_BACKEND": "mock"}
    )

    assert client.name == "mock"


def test_build_llm_client_uses_detected_provider():
    client = build_llm_client(env={"DEEPSEEK_API_KEY": "x"})

    assert isinstance(client, OpenAICompatibleClient)
    assert client.name == "deepseek"
    assert client.active_model == "deepseek-flash"


def test_build_llm_client_wraps_fallback_providers():
    client = build_llm_client(
        env={
            "DEEPSEEK_API_KEY": "x",
            "OPENAI_API_KEY": "y",
            "LLM_PROVIDER": "deepseek",
            "LLM_FALLBACK_PROVIDERS": "openai",
        }
    )

    assert isinstance(client, FallbackClient)
    assert client.name == "deepseek"


def test_generic_model_does_not_leak_to_fallback_provider():
    client = build_llm_client(
        env={
            "DEEPSEEK_API_KEY": "x",
            "OPENAI_API_KEY": "y",
            "LLM_PROVIDER": "deepseek",
            "LLM_MODEL": "deepseek-v4-pro",
            "LLM_MODEL_FALLBACKS": "deepseek-flash",
            "LLM_FALLBACK_PROVIDERS": "openai",
        }
    )

    assert isinstance(client, FallbackClient)
    assert client._clients[0].active_model == "deepseek-v4-pro"
    assert client._clients[1].active_model == "gpt-4.1-mini"


def test_unconfigured_fallback_provider_is_skipped():
    client = build_llm_client(
        env={
            "DEEPSEEK_API_KEY": "x",
            "LLM_PROVIDER": "deepseek",
            "LLM_FALLBACK_PROVIDERS": "openai",
        }
    )

    assert isinstance(client, OpenAICompatibleClient)
    assert client.name == "deepseek"


def test_explicit_provider_without_key_raises():
    with pytest.raises(LLMError, match="OPENAI_API_KEY is empty"):
        build_llm_client(env={"LLM_PROVIDER": "openai"})
