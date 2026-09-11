from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from core.llm import LLMClient, build_llm_client
from part2_scraper.mock_llm import MockSummarizerLLM
from part2_scraper.models import DocumentSummary

NAIVE_SYSTEM = "You summarize web pages."

def scrape_and_summarize(url: str, llm: LLMClient | None = None) -> str:
    llm = llm or build_llm_client(mock_factory=MockSummarizerLLM)

    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = llm.generate_structured(
        f"Summarize this concisely:\n\n{text}",
        DocumentSummary,
        system=NAIVE_SYSTEM,
    )
    return result.summary

if __name__ == "__main__":
    import sys

    print(scrape_and_summarize(sys.argv[1]))
