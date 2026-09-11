from __future__ import annotations

import os

os.environ.setdefault("LLM_BACKEND", "mock")
os.environ.setdefault("EMBEDDING_BACKEND", "hash")
os.environ.setdefault("RETRIEVAL_MIN_SCORE", "0.0")
os.environ.setdefault("CHAT_RETRIEVAL_MIN_SCORE", "0.0")
os.environ.setdefault("GEMINI_API_KEY", "")
for _leaky_var in ("IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM_ADDRESS"):
    os.environ[_leaky_var] = ""

import pytest

from core.embeddings import HashingEmbedder
from part1_email_agent.models import IncomingEmail
from part1_email_agent.ticketing import TicketStore

@pytest.fixture(scope="session")
def embedder() -> HashingEmbedder:
    return HashingEmbedder()

@pytest.fixture
def store(tmp_path) -> TicketStore:
    return TicketStore(db_path=tmp_path / "test.db")

@pytest.fixture
def make_email():
    def _make(body: str, subject: str = "Test subject", sender: str = "customer@example.com") -> IncomingEmail:
        return IncomingEmail(sender=sender, subject=subject, body=body)

    return _make
