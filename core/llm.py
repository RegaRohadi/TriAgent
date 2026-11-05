"""Public LLM surface.

The concrete provider adapters live in :mod:`core.providers`.  Everything
outside this module imports ``LLMClient``, ``LLMError`` and
``build_llm_client`` from here, so swapping providers never touches agent code.
"""

from __future__ import annotations

from core.providers import LLMClient, LLMError, build_llm_client, classify_error

__all__ = ["LLMClient", "LLMError", "build_llm_client", "classify_error"]
