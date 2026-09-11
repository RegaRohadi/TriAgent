from __future__ import annotations

import re

from pydantic import BaseModel

from part2_scraper.models import DocumentSummary, SectionSummary

WORD = re.compile(r"[A-Za-z0-9']+")

class MockSummarizerLLM:
    name = "mock"

    def __init__(self, section_words: int = 40, document_words: int = 160) -> None:
        self.section_words = section_words
        self.document_words = document_words
        self.calls: list[str] = []

    def generate_structured(self, prompt: str, schema: type[BaseModel], *, system: str | None = None):
        self.calls.append(schema.__name__)

        if schema is SectionSummary:
            return SectionSummary(summary=self._condense(prompt, self.section_words))

        if schema is DocumentSummary:
            limit = self._requested_limit(prompt)
            if limit is not None:
                return DocumentSummary(summary=self._condense(prompt, limit), key_points=[])
            return DocumentSummary(
                summary=self._condense(prompt, self.document_words),
                key_points=["First point.", "Second point."],
            )

        raise NotImplementedError(f"MockSummarizerLLM has no handler for {schema.__name__}")

    @staticmethod
    def _requested_limit(prompt: str) -> int | None:
        match = re.search(r"hard limit is (\d+)", prompt)
        return int(match.group(1)) if match else None

    @staticmethod
    def _condense(prompt: str, words: int) -> str:
        body = prompt.split("Section content:")[-1].split("Section summaries:")[-1]
        tokens = WORD.findall(body) or ["summary"]
        picked = (tokens * ((words // len(tokens)) + 1))[:words]
        return " ".join(picked).strip() + "."
