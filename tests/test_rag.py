from __future__ import annotations

from core.rag import KnowledgeBase, chunk_document

SAMPLE = """PointStar Cloud Solutions - Refund Policy
Document ID: KB-POLICY-001
1. Scope
This policy governs refunds for subscriptions billed directly by PointStar.
6. Cases Requiring Human Review
The request involves an Oracle NetSuite contract.
The refund amount exceeds USD 500.
"""

def test_chunks_carry_document_id_and_section():
    chunks = chunk_document(SAMPLE, doc_id="KB-POLICY-001", source_file="refund_policy.pdf")
    sections = {c.section for c in chunks}

    assert all(c.doc_id == "KB-POLICY-001" for c in chunks)
    assert "1. Scope" in sections
    assert any(s.startswith("6. Cases Requiring Human Review") for s in sections)

def test_chunk_text_is_prefixed_for_citation():
    chunk = chunk_document(SAMPLE, "KB-POLICY-001", "refund_policy.pdf")[0]
    assert chunk.text.startswith("[KB-POLICY-001 §")

def test_faq_questions_become_sections():
    faq = "Document ID: KB-FAQ-002\nQ1. What payment methods do you accept?\nWe accept major credit cards.\n"
    sections = {c.section for c in chunk_document(faq, "KB-FAQ-002", "faq_billing.pdf")}
    assert any(s.startswith("Q1.") for s in sections)

def test_retrieval_returns_nothing_when_below_floor(embedder):
    chunks = chunk_document(SAMPLE, "KB-POLICY-001", "refund_policy.pdf")
    kb = KnowledgeBase(chunks, embedder.encode([c.text for c in chunks]), embedder)

    assert kb.retrieve("anything at all", min_score=1.01) == []

def test_retrieval_returns_scored_chunks(embedder):
    chunks = chunk_document(SAMPLE, "KB-POLICY-001", "refund_policy.pdf")
    kb = KnowledgeBase(chunks, embedder.encode([c.text for c in chunks]), embedder)

    results = kb.retrieve("refund policy scope", k=2, min_score=0.0)
    assert results
    assert all(r.doc_id == "KB-POLICY-001" for r in results)
    assert results[0].score >= results[-1].score
    assert results[0].citation.startswith("KB-POLICY-001 §")
