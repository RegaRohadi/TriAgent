from __future__ import annotations

import dataclasses

import pytest
import requests

from part2_scraper import fetcher, summarizer
from part2_scraper.fetcher import FetchError, detect_encoding
from part2_scraper.mock_llm import MockSummarizerLLM
from part2_scraper.models import ExtractedContent

PARAGRAPH = (
    "Nimbus Cloud resells Google Workspace and Oracle NetSuite. "
    "Refund eligibility differs by product and by plan type. "
)

def content(text: str) -> ExtractedContent:
    return ExtractedContent(
        title="Test page", text=text, char_count=len(text),
        strategy="semantic", link_density=0.05, reduction_ratio=0.8,
    )

def test_short_page_uses_a_single_call():
    llm = MockSummarizerLLM()
    result = summarizer.summarize(llm, content(PARAGRAPH), max_chunk_tokens=2000)

    assert result.strategy == "single_pass"
    assert result.llm_calls == 1, "map-reduce on one chunk would waste a call"
    assert result.chunk_count == 1

def test_long_page_uses_map_reduce():
    llm = MockSummarizerLLM()
    result = summarizer.summarize(llm, content(PARAGRAPH * 300), max_chunk_tokens=300)

    assert result.strategy == "map_reduce"
    assert result.chunk_count > 1
    assert result.llm_calls >= result.chunk_count + 1

def test_map_phase_calls_the_model_once_per_chunk():
    llm = MockSummarizerLLM()
    result = summarizer.summarize(llm, content(PARAGRAPH * 300), max_chunk_tokens=300)

    section_calls = llm.calls.count("SectionSummary")
    assert section_calls >= result.chunk_count

def test_summarizing_empty_content_raises():
    with pytest.raises(summarizer.SummarizationError):
        summarizer.summarize(MockSummarizerLLM(), content("   "))

class FakeResponse:
    def __init__(self, *, status=200, headers=None, body=b"<html></html>", url="https://example.com"):
        self.status_code = status
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}
        self._body = body
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def iter_content(self, size):
        for i in range(0, len(self._body), size):
            yield self._body[i : i + size]

def test_non_html_content_type_is_rejected(monkeypatch):
    monkeypatch.setattr(
        requests, "get",
        lambda *a, **k: FakeResponse(headers={"Content-Type": "application/pdf"}),
    )
    with pytest.raises(FetchError, match="not an HTML page"):
        fetcher.fetch("https://example.com/file.pdf")

def test_oversized_page_is_aborted_mid_download(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(body=b"x" * 50_000))

    with pytest.raises(FetchError, match="exceeds"):
        fetcher.fetch("https://example.com", max_bytes=10_000)

def test_client_errors_are_not_retried(monkeypatch):
    attempts = {"n": 0}

    def counting_get(*args, **kwargs):
        attempts["n"] += 1
        return FakeResponse(status=404)

    monkeypatch.setattr(requests, "get", counting_get)
    with pytest.raises(FetchError, match="404"):
        fetcher.fetch("https://example.com", attempts=3)

    assert attempts["n"] == 1, "a 404 never becomes a 200 — retrying only wastes time"

def test_transient_errors_are_retried(monkeypatch):
    attempts = {"n": 0}

    def flaky_get(*args, **kwargs):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise requests.ConnectionError("connection reset")
        return FakeResponse(body=b"<html><body>ok</body></html>")

    monkeypatch.setattr(requests, "get", flaky_get)
    monkeypatch.setattr("time.sleep", lambda _: None)

    result = fetcher.fetch("https://example.com", attempts=3)
    assert attempts["n"] == 3
    assert "ok" in result.html

def test_blocked_status_without_camoufox_gives_clear_error(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(status=403))
    monkeypatch.setattr(fetcher, "settings", dataclasses.replace(fetcher.settings, scraper_camoufox_enabled=False))

    with pytest.raises(FetchError, match="403.*camoufox|bot block"):
        fetcher.fetch("https://example.com", attempts=3)

def test_blocked_status_is_not_retried_with_plain_requests(monkeypatch):
    attempts = {"n": 0}

    def counting_get(*args, **kwargs):
        attempts["n"] += 1
        return FakeResponse(status=403)

    monkeypatch.setattr(requests, "get", counting_get)
    monkeypatch.setattr(fetcher, "settings", dataclasses.replace(fetcher.settings, scraper_camoufox_enabled=False))

    with pytest.raises(FetchError):
        fetcher.fetch("https://example.com", attempts=3)

    assert attempts["n"] == 1, "a hard block should go straight to the camoufox decision, not retry"

def test_blocked_status_falls_back_to_camoufox_when_enabled(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(status=403))
    monkeypatch.setattr(fetcher, "settings", dataclasses.replace(fetcher.settings, scraper_camoufox_enabled=True))

    fake_result = fetcher.FetchResult(
        url="https://example.com", html="<html>rendered</html>",
        status_code=200, content_type="text/html", bytes_downloaded=20, elapsed_ms=5,
    )
    calls = {"n": 0}

    def fake_camoufox(url, max_bytes):
        calls["n"] += 1
        return fake_result

    monkeypatch.setattr(fetcher, "_fetch_with_camoufox", fake_camoufox)

    result = fetcher.fetch("https://example.com", attempts=3)
    assert result is fake_result
    assert calls["n"] == 1

def test_camoufox_fallback_failure_is_reported_clearly(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(status=403))
    monkeypatch.setattr(fetcher, "settings", dataclasses.replace(fetcher.settings, scraper_camoufox_enabled=True))

    def failing_camoufox(url, max_bytes):
        raise FetchError("no browser binary")

    monkeypatch.setattr(fetcher, "_fetch_with_camoufox", failing_camoufox)

    with pytest.raises(FetchError, match="blocked.*camoufox fallback also failed"):
        fetcher.fetch("https://example.com", attempts=3)

def test_charset_from_header_is_used():
    assert detect_encoding("text/html; charset=windows-1252", b"") == "windows-1252"

def test_missing_charset_falls_back_to_meta_tag():
    body = b'<html><head><meta charset="utf-8"></head>'
    assert detect_encoding("text/html", body).lower() == "utf-8"

def test_missing_charset_everywhere_defaults_to_utf8_not_latin1():
    assert detect_encoding("text/html", b"<html><body>hi</body></html>") == "utf-8"
