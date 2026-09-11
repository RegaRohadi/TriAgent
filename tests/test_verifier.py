from __future__ import annotations

import pytest

from part1_email_agent import verifier
from part1_email_agent.models import DraftResponse, RetrievedChunkView, VerificationResult

class StubLLM:
    def __init__(self, result: VerificationResult):
        self.result = result

    def generate_structured(self, prompt, schema, *, system=None):
        return self.result

DESK = "Rega's Support"

CHUNKS = [
    RetrievedChunkView(
        text="[KB-FAQ-003 §Q1] Try a password reset, or sign in through the JumpCloud portal.",
        doc_id="KB-FAQ-003", section="Q1", score=0.7,
    )
]

def draft(text: str, citations=("KB-FAQ-003",)) -> DraftResponse:
    return DraftResponse(text=text, citations=list(citations), fully_answerable=True)

@pytest.mark.parametrize(
    "flagged",
    ["Rega's Support", "regas support", "Best regards, Rega's Support", "Regards, Rega's Support", "  "],
)
def test_signature_is_not_treated_as_an_unsupported_claim(flagged):
    llm = StubLLM(VerificationResult(fully_grounded=False, unsupported_claims=[flagged]))

    result = verifier.verify_draft(llm, draft("Try a password reset. Rega's Support"), CHUNKS, desk_name=DESK)

    assert result.fully_grounded, "the desk signing its own name must not block the reply"
    assert result.unsupported_claims == []

def test_a_real_unsupported_claim_still_blocks():
    llm = StubLLM(
        VerificationResult(fully_grounded=False, unsupported_claims=["refunds are processed in 3 days"])
    )

    result = verifier.verify_draft(llm, draft("Refunds take 3 days. Rega's Support"), CHUNKS, desk_name=DESK)

    assert not result.fully_grounded
    assert result.unsupported_claims == ["refunds are processed in 3 days"]

def test_signature_is_dropped_but_real_claims_survive():
    llm = StubLLM(
        VerificationResult(
            fully_grounded=False, unsupported_claims=["Rega's Support", "you get a full refund"]
        )
    )

    result = verifier.verify_draft(llm, draft("..."), CHUNKS, desk_name=DESK)

    assert result.unsupported_claims == ["you get a full refund"]
    assert not result.fully_grounded

def test_grounded_draft_passes_untouched():
    llm = StubLLM(VerificationResult(fully_grounded=True, unsupported_claims=[]))

    assert verifier.verify_draft(llm, draft("Try a password reset."), CHUNKS, desk_name=DESK).fully_grounded

def test_citation_outside_the_retrieved_set_is_invalid():
    check = verifier.check_citations(draft("...", citations=["KB-POLICY-999"]), CHUNKS)
    assert not check.valid
    assert check.invalid_citations == ["KB-POLICY-999"]

def test_a_draft_with_no_citations_at_all_is_invalid():
    assert not verifier.check_citations(draft("...", citations=[]), CHUNKS).valid

def test_matching_citation_is_valid():
    assert verifier.check_citations(draft("...", citations=["KB-FAQ-003"]), CHUNKS).valid
