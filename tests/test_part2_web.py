from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from core.config import settings
from part2_scraper import web
from part2_scraper.extractor import ExtractionError
from part2_scraper.fetcher import FetchError
from part2_scraper.models import PageSummary

PUBLIC_URL = "http://93.184.216.34/article"

@pytest.fixture
def client():
    return TestClient(web.app)

def page_summary(**overrides) -> PageSummary:
    data = dict(
        url=PUBLIC_URL, title="Article", summary="A short grounded summary.", key_points=["One."],
        strategy="single_pass", extraction_strategy="semantic", raw_bytes=10_000, extracted_chars=2_000,
        reduction_ratio=0.4, chunk_count=1, llm_calls=1, word_count=4, guardrail_enforced_by="model",
        within_budget=True, elapsed_ms=120,
    )
    data.update(overrides)
    return PageSummary(**data)

def must_not_fetch(*args, **kwargs):
    raise AssertionError("a refused URL must never reach the fetcher")

@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/",
        "http://localhost/admin",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
    ],
)
def test_non_public_addresses_are_refused(client, monkeypatch, url):
    monkeypatch.setattr(web.pipeline, "summarize_url", must_not_fetch)

    response = client.post("/api/summarize", json={"url": url})

    assert response.status_code == 400
    assert "non-public" in response.json()["detail"]

@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "javascript:alert(1)", "not a url"])
def test_non_http_schemes_are_refused(client, monkeypatch, url):
    monkeypatch.setattr(web.pipeline, "summarize_url", must_not_fetch)
    assert client.post("/api/summarize", json={"url": url}).status_code == 400

def test_compare_applies_the_same_guard(client, monkeypatch):
    monkeypatch.setattr(web.pipeline, "summarize_url", must_not_fetch)
    monkeypatch.setattr(web.naive_scraper, "scrape_and_summarize", must_not_fetch)
    assert client.post("/api/compare", json={"url": "http://127.0.0.1/"}).status_code == 400

def test_summarize_returns_the_pipeline_result(client, monkeypatch):
    captured = {}

    def fake(url, llm=None, max_words=None):
        captured.update(url=url, max_words=max_words)
        return page_summary()

    monkeypatch.setattr(web.pipeline, "summarize_url", fake)

    response = client.post("/api/summarize", json={"url": PUBLIC_URL, "max_words": 80})

    assert response.status_code == 200
    assert response.json()["summary"] == "A short grounded summary."
    assert captured == {"url": PUBLIC_URL, "max_words": 80}

@pytest.mark.parametrize("exc,status", [(FetchError("HTTP 404"), 502), (ExtractionError("JavaScript"), 422)])
def test_pipeline_errors_map_to_http_statuses(client, monkeypatch, exc, status):
    def boom(*args, **kwargs):
        raise exc

    monkeypatch.setattr(web.pipeline, "summarize_url", boom)
    assert client.post("/api/summarize", json={"url": PUBLIC_URL}).status_code == status

def test_a_budget_below_the_guardrail_minimum_is_rejected(client, monkeypatch):
    monkeypatch.setattr(web.pipeline, "summarize_url", must_not_fetch)
    too_small = settings.summary_min_words - 1
    assert client.post("/api/summarize", json={"url": PUBLIC_URL, "max_words": too_small}).status_code == 422

def test_compare_shows_a_naive_failure_next_to_the_fixed_result(client, monkeypatch):
    def naive_blocked(url, llm=None):
        raise ConnectionError("blocked by the site")

    monkeypatch.setattr(web.naive_scraper, "scrape_and_summarize", naive_blocked)
    monkeypatch.setattr(web.pipeline, "summarize_url", lambda *a, **k: page_summary())

    body = client.post("/api/compare", json={"url": PUBLIC_URL}).json()

    assert "blocked by the site" in body["naive"]["error"]
    assert body["fixed"]["error"] is None
    assert body["fixed"]["result"]["summary"] == "A short grounded summary."

def test_a_hanging_naive_run_is_cut_off(client, monkeypatch):
    monkeypatch.setattr(web, "NAIVE_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(web.naive_scraper, "scrape_and_summarize", lambda url, llm=None: time.sleep(1) or "late")
    monkeypatch.setattr(web.pipeline, "summarize_url", lambda *a, **k: page_summary())

    body = client.post("/api/compare", json={"url": PUBLIC_URL}).json()

    assert "no timeout" in body["naive"]["error"]
    assert body["fixed"]["result"] is not None

def test_health_reports_the_word_budget(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["summary_max_words"] == settings.summary_max_words
    assert body["summary_min_words"] == settings.summary_min_words

def test_the_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Compare before / after" in response.text
