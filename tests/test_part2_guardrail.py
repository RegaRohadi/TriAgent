from __future__ import annotations

from part2_scraper.guardrail import count_words, enforce_length, truncate_to_words
from part2_scraper.mock_llm import MockSummarizerLLM
from part2_scraper.models import DocumentSummary

class StubLLM:

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.prompts: list[str] = []

    def generate_structured(self, prompt, schema, *, system=None):
        self.prompts.append(prompt)
        return DocumentSummary(summary=self.replies.pop(0), key_points=[])

def words(n: int) -> str:
    return " ".join(["word"] * (n - 1)) + " end."

def test_summary_within_budget_passes_untouched():
    llm = StubLLM()
    result = enforce_length(llm, words(50), max_words=100, min_words=20)

    assert result.within_budget
    assert result.enforced_by == "model"
    assert result.attempts == 0
    assert llm.prompts == [], "no rewrite should be requested"

def test_overlong_summary_is_rewritten():
    llm = StubLLM(words(80))
    result = enforce_length(llm, words(200), max_words=100, min_words=20)

    assert result.within_budget
    assert result.enforced_by == "retry"
    assert result.attempts == 1
    assert result.word_count <= 100

def test_rewrite_prompt_quotes_the_actual_count():
    llm = StubLLM(words(80))
    enforce_length(llm, words(200), max_words=100, min_words=20)

    prompt = llm.prompts[0]
    assert "200 words" in prompt
    assert "hard limit is 100" in prompt
    assert "100 words over" in prompt

def test_a_model_that_never_complies_gets_truncated():
    llm = StubLLM(words(300), words(280))
    result = enforce_length(llm, words(400), max_words=100, min_words=20, max_attempts=2)

    assert result.enforced_by == "truncation"
    assert result.within_budget
    assert result.word_count <= 100

def test_too_short_is_a_failure_too():
    llm = StubLLM("Summary.", "Summary.")
    result = enforce_length(llm, "Summary.", max_words=100, min_words=20, max_attempts=2)

    assert not result.within_budget, "an unusably short summary must be reported, not passed"
    assert result.word_count < 20

def test_short_summary_asks_for_expansion_not_shortening():
    llm = StubLLM(words(40))
    enforce_length(llm, "Too short.", max_words=100, min_words=20)

    assert "below the 20-word minimum" in llm.prompts[0]
    assert "Do not invent anything" in llm.prompts[0]

def test_truncation_stops_on_a_sentence_boundary():
    text = "First sentence here. Second sentence here. Third sentence here."
    truncated = truncate_to_words(text, 8)

    assert truncated == "First sentence here. Second sentence here."
    assert truncated.endswith(".")

def test_truncation_leaves_short_text_alone():
    text = "Already short enough."
    assert truncate_to_words(text, 100) == text

def test_a_single_oversized_sentence_falls_back_to_a_word_cut():
    text = " ".join(["word"] * 200) + "."
    truncated = truncate_to_words(text, 10)

    assert count_words(truncated) <= 11
    assert truncated.endswith("…")

def test_mock_llm_overshoots_so_the_guardrail_path_is_exercised():
    mock = MockSummarizerLLM()
    verbose = mock.generate_structured("Section summaries:\nsome content here", DocumentSummary)

    assert count_words(verbose.summary) > 100
