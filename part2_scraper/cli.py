from __future__ import annotations

import argparse
import time

from core.logging_config import configure_logging
from part2_scraper import naive_scraper, pipeline
from part2_scraper.models import PageSummary

def print_summary(result: PageSummary) -> None:
    print("\n" + "=" * 78)
    print(f"{result.title}")
    print(f"  {result.url}")
    print("-" * 78)
    sent_ratio = 1 - (result.extracted_chars / result.raw_bytes) if result.raw_bytes else 0
    print(f"  fetched        : {result.raw_bytes:,} bytes")
    print(f"  sent to llm    : {result.extracted_chars:,} chars  ({sent_ratio:.0%} smaller than the raw page)")
    print(f"  extraction     : {result.extraction_strategy}, "
          f"{result.reduction_ratio:.0%} of the page's text dropped as chrome")
    print(f"  strategy       : {result.strategy}  ({result.chunk_count} chunk(s), "
          f"{result.reduce_rounds} extra reduce round(s))")
    print(f"  llm calls      : {result.llm_calls}")
    print(f"  summary length : {result.word_count} words  (enforced by: {result.guardrail_enforced_by})")
    if not result.within_budget:
        print("  WARNING        : summary is outside the configured budget")
    print(f"  elapsed        : {result.elapsed_ms} ms")
    print("-" * 78)
    print(f"\n{result.summary}\n")
    if result.key_points:
        print("Key points:")
        for point in result.key_points:
            print(f"  - {point}")
    print("=" * 78)

def cmd_summarize(args: argparse.Namespace) -> int:
    print_summary(pipeline.summarize_url(args.url, max_words=args.max_words))
    return 0

def cmd_compare(args: argparse.Namespace) -> int:
    print("\n--- BEFORE (naive_scraper.py) " + "-" * 47)
    started = time.perf_counter()
    try:
        naive = naive_scraper.scrape_and_summarize(args.url)
        elapsed = round((time.perf_counter() - started) * 1000)
        print(f"  {len(naive.split())} words, {elapsed} ms")
        print(f"\n{naive}\n")
    except Exception as exc:
        elapsed = round((time.perf_counter() - started) * 1000)
        print(f"  FAILED after {elapsed} ms: {type(exc).__name__}: {str(exc)[:300]}\n")

    print("--- AFTER (pipeline.py) " + "-" * 53)
    try:
        print_summary(pipeline.summarize_url(args.url, max_words=args.max_words))
    except Exception as exc:
        print(f"  FAILED: {type(exc).__name__}: {str(exc)[:300]}")
        return 1
    return 0

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="part2_scraper", description="Scrape and summarize a web page")
    parser.add_argument("--log-json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sum = sub.add_parser("summarize", help="fetch, extract and summarize one URL")
    p_sum.add_argument("url")
    p_sum.add_argument("--max-words", type=int, default=None)
    p_sum.set_defaults(func=cmd_summarize)

    p_cmp = sub.add_parser("compare", help="run the naive script and the fixed pipeline side by side")
    p_cmp.add_argument("url")
    p_cmp.add_argument("--max-words", type=int, default=None)
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    configure_logging(json_output=args.log_json, level="WARNING" if args.quiet else "INFO")
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
