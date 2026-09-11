from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message

from core.embeddings import HashingEmbedder
from core.rag import KnowledgeBase, chunk_document
from part1_email_agent.graph import EmailAgent
from part1_email_agent.mock_llm import MockLLM
from part1_email_agent.models import IncomingEmail
from part1_email_agent.precheck import CriticalSignalDetector
from part1_email_agent.smtp_sender import EmailSender
from part1_email_agent.ticketing import TicketStore

received: list = []

class CapturingHandler(Message):
    def handle_message(self, message):
        received.append(message)

KB_TEXT = """Document ID: KB-FAQ-002
Q3. How do I get a copy of my invoice?
Invoices are auto-emailed to your billing contact and available under Account Settings.
"""

def main() -> None:
    controller = Controller(CapturingHandler(), hostname="127.0.0.1", port=1025)
    controller.start()
    print("local SMTP test server listening on 127.0.0.1:1025")

    try:
        embedder = HashingEmbedder()
        chunks = chunk_document(KB_TEXT, "KB-FAQ-002", "faq_billing.pdf")
        kb = KnowledgeBase(chunks, embedder.encode([c.text for c in chunks]), embedder)
        sender = EmailSender(
            host="127.0.0.1", port=1025, user="test", password="test",
            from_address="support@pointstar-consulting.example", from_name="Rega's Support",
        )
        agent = EmailAgent(
            llm=MockLLM(), kb=kb, store=TicketStore(db_path=Path("data/smtp_e2e_test.db")),
            detector=CriticalSignalDetector(embedder=embedder, threshold=2.0), sender=sender,
        )

        original = IncomingEmail(
            sender="realcustomer@example.com", subject="Invoice copy please",
            body="Where can I get a copy of my invoice?",
        )
        state = agent.process(original, record_contact=False)

        print(f"\nfinal_action  = {state.final_action}")
        print(f"email_sent    = {state.email_sent}")
        print(f"send_status   = {state.send_status}")

        assert state.email_sent is True, "graph did not report the email as sent"
        assert len(received) == 1, f"SMTP server received {len(received)} messages, expected 1"
        msg = received[0]
        assert msg["To"] == "realcustomer@example.com"
        assert msg["Subject"] == "Re: Invoice copy please"
        print(f"\nSMTP server actually received a message:")
        print(f"  From: {msg['From']}")
        print(f"  To: {msg['To']}")
        print(f"  Subject: {msg['Subject']}")
        print("\nPASS: end-to-end send confirmed against a real (local) SMTP server.")
    finally:
        controller.stop()
        Path("data/smtp_e2e_test.db").unlink(missing_ok=True)

if __name__ == "__main__":
    main()
