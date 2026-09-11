from __future__ import annotations

import re
import time

import requests

from core.config import settings
from core.logging_config import get_logger
from part2_scraper.models import FetchResult

log = get_logger(__name__)

ALLOWED_TYPES = {"text/html", "application/xhtml+xml", "text/plain", ""}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
CHARSET_PATTERN = re.compile(r"charset=[\"']?([\w\-]+)", re.I)
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
BLOCKED_STATUS = {401, 403}
ANTIBOT_RETRYABLE_STATUS = {429, 503}

class FetchError(RuntimeError):
    pass

class _Transient(Exception):
    def __init__(self, status_code: int):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code

def detect_encoding(content_type_header: str, body: bytes) -> str:
    header_match = CHARSET_PATTERN.search(content_type_header)
    if header_match:
        return header_match.group(1)

    head = body[:2048].decode("ascii", errors="ignore")
    meta_match = CHARSET_PATTERN.search(head)
    return meta_match.group(1) if meta_match else "utf-8"

def _fetch_with_camoufox(url: str, max_bytes: int) -> FetchResult:
    try:
        from camoufox.sync_api import Camoufox
    except ImportError as exc:
        raise FetchError(
            "camoufox is not installed; run `pip install camoufox[geoip]` and "
            "`python -m camoufox fetch` to enable the anti-bot fallback"
        ) from exc

    started = time.perf_counter()
    timeout_ms = settings.scraper_camoufox_timeout * 1000

    with Camoufox(headless=True, humanize=True) as browser:
        page = browser.new_page()
        try:
            response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
            html = page.content()
            final_url = page.url
            status_code = response.status if response else 200
            content_type = ""
            if response:
                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        except Exception as exc:
            raise FetchError(f"{url} could not be fetched via camoufox: {exc}") from exc
        finally:
            page.close()

    total = len(html.encode("utf-8", errors="ignore"))
    if total > max_bytes:
        raise FetchError(f"{url} exceeds the {max_bytes:,}-byte limit (via camoufox)")

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    log.info(
        "page_fetched_via_camoufox", url=final_url, bytes=total,
        content_type=content_type, status_code=status_code, elapsed_ms=elapsed_ms,
    )
    return FetchResult(
        url=final_url,
        html=html,
        status_code=status_code,
        content_type=content_type or "text/html",
        bytes_downloaded=total,
        elapsed_ms=elapsed_ms,
    )

def fetch(url: str, *, max_bytes: int | None = None, attempts: int = 3) -> FetchResult:
    max_bytes = max_bytes or settings.scraper_max_bytes
    timeout = (settings.scraper_connect_timeout, settings.scraper_read_timeout)
    last_error: Exception | None = None
    blocked_status: int | None = None

    for attempt in range(1, attempts + 1):
        started = time.perf_counter()
        try:
            with requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
                timeout=timeout,
                stream=True,
                allow_redirects=True,
            ) as response:
                if response.status_code in RETRYABLE_STATUS:
                    raise _Transient(response.status_code)
                response.raise_for_status()

                header = response.headers.get("Content-Type", "")
                content_type = header.split(";")[0].strip().lower()
                if content_type not in ALLOWED_TYPES:
                    raise FetchError(f"{url} is {content_type}, not an HTML page")

                blocks, total = [], 0
                for block in response.iter_content(8192):
                    total += len(block)
                    if total > max_bytes:
                        raise FetchError(f"{url} exceeds the {max_bytes:,}-byte limit")
                    blocks.append(block)

                body = b"".join(blocks)
                encoding = detect_encoding(header, body)
                elapsed_ms = round((time.perf_counter() - started) * 1000)

                log.info(
                    "page_fetched", url=response.url, bytes=total,
                    content_type=content_type, encoding=encoding, elapsed_ms=elapsed_ms,
                )
                return FetchResult(
                    url=response.url,
                    html=body.decode(encoding, errors="replace"),
                    status_code=response.status_code,
                    content_type=content_type,
                    bytes_downloaded=total,
                    elapsed_ms=elapsed_ms,
                )

        except (_Transient, requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if isinstance(exc, _Transient) and exc.status_code in ANTIBOT_RETRYABLE_STATUS:
                blocked_status = exc.status_code
            log.warning("fetch_retry", url=url, attempt=attempt, error=str(exc)[:200])
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in BLOCKED_STATUS:
                blocked_status = status
                last_error = exc
                break
            raise FetchError(f"{url} returned HTTP {status}") from exc
        except requests.RequestException as exc:
            raise FetchError(f"{url} could not be fetched: {exc}") from exc

    if blocked_status is not None:
        if not settings.scraper_camoufox_enabled:
            raise FetchError(
                f"{url} returned HTTP {blocked_status}, which looks like a bot block; "
                "set SCRAPER_CAMOUFOX_ENABLED=true to retry with a stealth browser"
            )
        log.info("fetch_falling_back_to_camoufox", url=url, blocked_status=blocked_status)
        try:
            return _fetch_with_camoufox(url, max_bytes)
        except FetchError as exc:
            log.warning("camoufox_fallback_failed", url=url, error=str(exc)[:200])
            raise FetchError(f"{url} was blocked (HTTP {blocked_status}) and the camoufox fallback also failed: {exc}") from exc

    raise FetchError(f"{url} failed after {attempts} attempts: {last_error}")
