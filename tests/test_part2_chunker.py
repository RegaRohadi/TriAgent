from __future__ import annotations

from part2_scraper.chunker import CHARS_PER_TOKEN, chunk_text, estimate_tokens

PARAGRAPH = (
    "Nimbus Cloud resells Google Workspace, Google Cloud Platform and Oracle NetSuite. "
    "Refund terms differ by product, so the applicable clause depends on the subscription. "
)

def test_short_text_stays_one_chunk():
    chunks = chunk_text("A short page.", max_tokens=2000)
    assert len(chunks) == 1
    assert chunks[0].index == 0

def test_empty_text_produces_no_chunks():
    assert chunk_text("   ") == []

def test_long_text_is_split():
    chunks = chunk_text(PARAGRAPH * 200, max_tokens=200)
    assert len(chunks) > 1

def test_every_chunk_fits_the_budget():
    max_tokens = 200
    for chunk in chunk_text(PARAGRAPH * 200, max_tokens=max_tokens, overlap_tokens=0):
        assert chunk.estimated_tokens <= max_tokens

def test_chunks_are_indexed_in_order():
    chunks = chunk_text(PARAGRAPH * 100, max_tokens=200)
    assert [c.index for c in chunks] == list(range(len(chunks)))

def test_paragraph_boundaries_are_preferred():
    text = "\n\n".join(f"Paragraph number {i}. {PARAGRAPH}" for i in range(12))
    chunks = chunk_text(text, max_tokens=200, overlap_tokens=0)
    for chunk in chunks:
        assert not chunk.text.startswith(" ")

def test_a_single_oversized_word_is_still_split():
    blob = "x" * 10_000
    chunks = chunk_text(blob, max_tokens=100, overlap_tokens=0)
    assert len(chunks) > 1
    assert all(c.estimated_tokens <= 100 for c in chunks)

def test_overlap_carries_context_forward():
    text = "\n\n".join(f"Section {i}. {PARAGRAPH}" for i in range(20))
    with_overlap = chunk_text(text, max_tokens=250, overlap_tokens=60)
    without_overlap = chunk_text(text, max_tokens=250, overlap_tokens=0)

    joined_with = sum(len(c.text) for c in with_overlap)
    joined_without = sum(len(c.text) for c in without_overlap)
    assert joined_with > joined_without, "overlap must repeat some text between chunks"

def test_token_estimate_is_conservative():
    text = "a" * 350
    assert estimate_tokens(text) >= len(text) / 4
    assert CHARS_PER_TOKEN < 4
