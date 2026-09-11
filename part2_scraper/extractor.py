from __future__ import annotations

import re

from bs4 import BeautifulSoup

from core.logging_config import get_logger
from part2_scraper.models import ExtractedContent

log = get_logger(__name__)

NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript", "svg", "button"]

NOISE_HINTS = re.compile(
    r"(nav|menu|sidebar|footer|header|banner|cookie|consent|advert|ads?[-_]|"
    r"promo|share|social|comment|related|recommend|newsletter|subscribe|"
    r"breadcrumb|pagination|widget|popup|modal)",
    re.I,
)

STRUCTURAL_TAGS = {"html", "body", "main", "article"}
MIN_BLOCK_CHARS = 200

class ExtractionError(RuntimeError):
    pass

def link_density(node) -> float:
    text_length = len(node.get_text(strip=True))
    if text_length == 0:
        return 1.0
    link_length = sum(len(a.get_text(strip=True)) for a in node.find_all("a"))
    return min(link_length / text_length, 1.0)

def normalize(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return " ".join(soup.title.string.split())
    heading = soup.find("h1")
    return " ".join(heading.get_text().split()) if heading else "(untitled)"

def _find_semantic_container(soup: BeautifulSoup):
    candidates = soup.find_all(["article", "main"]) + soup.find_all(attrs={"role": "main"})
    best = max(candidates, key=lambda n: len(n.get_text(strip=True)), default=None)
    return best if best and len(best.get_text(strip=True)) >= MIN_BLOCK_CHARS else None

def _find_densest_block(soup: BeautifulSoup):
    best, best_score = None, 0.0
    for node in soup.find_all(["div", "section", "td"]):
        text_length = len(node.get_text(strip=True))
        if text_length < MIN_BLOCK_CHARS:
            continue
        score = text_length * (1 - link_density(node))
        if score > best_score:
            best, best_score = node, score
    return best or soup.body or soup

def extract(html: str, *, min_chars: int = MIN_BLOCK_CHARS) -> ExtractedContent:
    soup = BeautifulSoup(html, "html.parser")
    raw_length = len(soup.get_text(strip=True))

    title = _extract_title(soup)

    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()
    for attribute in ("class", "id"):
        for tag in soup.find_all(attrs={attribute: NOISE_HINTS}):
            if tag.name not in STRUCTURAL_TAGS:
                tag.decompose()

    node = _find_semantic_container(soup)
    strategy = "semantic"
    if node is None:
        node, strategy = _find_densest_block(soup), "density"
    if node is None:
        raise ExtractionError("no content block found in the page")

    text = normalize(node.get_text("\n"))
    if len(text) < min_chars:
        raise ExtractionError(
            f"only {len(text)} characters of text recovered from a {raw_length}-character page — "
            "it is most likely rendered by JavaScript, which this fetcher cannot execute"
        )

    result = ExtractedContent(
        title=title,
        text=text,
        char_count=len(text),
        strategy=strategy,
        link_density=round(link_density(node), 3),
        reduction_ratio=round(1 - len(text) / raw_length, 3) if raw_length else 0.0,
    )
    log.info(
        "content_extracted", strategy=strategy, chars=result.char_count,
        raw_chars=raw_length, reduction=result.reduction_ratio,
    )
    return result
