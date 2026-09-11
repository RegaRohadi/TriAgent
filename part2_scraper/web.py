from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from core.config import settings
from core.llm import LLMClient, LLMError, build_llm_client
from core.logging_config import configure_logging, get_logger
from part2_scraper import naive_scraper, pipeline
from part2_scraper.extractor import ExtractionError
from part2_scraper.fetcher import FetchError
from part2_scraper.mock_llm import MockSummarizerLLM
from part2_scraper.summarizer import SummarizationError

log = get_logger(__name__)

NAIVE_TIMEOUT_SECONDS = 90.0

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield

app = FastAPI(title="Scrape & Summarize", version="1.0.0", lifespan=lifespan)

@lru_cache(maxsize=1)
def get_llm() -> LLMClient:
    return build_llm_client(mock_factory=MockSummarizerLLM)

class SummarizeRequest(BaseModel):
    url: str
    max_words: int | None = Field(default=None, ge=settings.summary_min_words, le=500)

def _resolve(host: str) -> list[str]:
    return [info[4][0] for info in socket.getaddrinfo(host, None)]

def validate_public_url(url: str) -> str:
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http:// and https:// URLs can be summarized")
    if not parts.hostname:
        raise HTTPException(status_code=400, detail="The URL has no host")

    try:
        addresses = _resolve(parts.hostname)
    except (socket.gaierror, UnicodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Cannot resolve {parts.hostname}") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise HTTPException(
                status_code=400,
                detail=f"{parts.hostname} resolves to a non-public address ({ip}); refusing to fetch it",
            )
    return url

@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_backend": get_llm().name,
        "summary_max_words": settings.summary_max_words,
        "summary_min_words": settings.summary_min_words,
        "chunk_max_tokens": settings.chunk_max_tokens,
        "map_workers": settings.map_workers,
    }

@app.post("/api/summarize")
async def summarize(request: SummarizeRequest) -> dict:
    url = await asyncio.to_thread(validate_public_url, request.url)
    try:
        result = await asyncio.to_thread(pipeline.summarize_url, url, get_llm(), request.max_words)
    except FetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (SummarizationError, LLMError) as exc:
        raise HTTPException(status_code=502, detail=f"Summarization failed: {exc}") from exc
    return asdict(result)

async def _naive_side(url: str, llm: LLMClient) -> dict:
    started = time.perf_counter()

    def elapsed() -> int:
        return round((time.perf_counter() - started) * 1000)

    try:
        summary = await asyncio.wait_for(
            asyncio.to_thread(naive_scraper.scrape_and_summarize, url, llm), NAIVE_TIMEOUT_SECONDS
        )
    except TimeoutError:
        return {
            "summary": None, "word_count": 0, "elapsed_ms": elapsed(),
            "error": f"did not finish within {NAIVE_TIMEOUT_SECONDS:.0f} s — "
                     "the naive script sets no timeout of its own (defect 1)",
        }
    except Exception as exc:
        return {"summary": None, "word_count": 0, "elapsed_ms": elapsed(), "error": f"{type(exc).__name__}: {exc}"[:400]}
    return {"summary": summary, "word_count": len(summary.split()), "elapsed_ms": elapsed(), "error": None}

async def _fixed_side(url: str, llm: LLMClient, max_words: int | None) -> dict:
    try:
        result = await asyncio.to_thread(pipeline.summarize_url, url, llm, max_words)
    except Exception as exc:
        return {"result": None, "error": f"{type(exc).__name__}: {exc}"[:400]}
    return {"result": asdict(result), "error": None}

@app.post("/api/compare")
async def compare(request: SummarizeRequest) -> dict:
    url = await asyncio.to_thread(validate_public_url, request.url)
    llm = get_llm()
    naive, fixed = await asyncio.gather(_naive_side(url, llm), _fixed_side(url, llm, request.max_words))
    log.info("compare_done", url=url, naive_ok=naive["error"] is None, fixed_ok=fixed["error"] is None)
    return {"url": url, "naive": naive, "fixed": fixed}

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
