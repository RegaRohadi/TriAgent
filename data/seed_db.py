from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.logging_config import configure_logging, get_logger
from part1_email_agent.ticketing import TicketStore

log = get_logger(__name__)

NOW = datetime.now(timezone.utc)

SEED_CONTACTS: list[tuple[str, str, float]] = [
    ("rina.wijaya@lippomall.example", "Invoice question", 6.0),
    ("rina.wijaya@lippomall.example", "Still waiting for an answer", 4.0),
    ("rina.wijaya@lippomall.example", "Following up again", 2.0),
    ("rina.wijaya@lippomall.example", "Third follow up, please respond", 0.5),
    ("anna.lim@unionbook.example", "Onboarding question", 3.0),
    ("david.tan@craftmark.example", "License upgrade", 12.0),
    ("siti.rahayu@bollore.example", "Meraki hardware delivery", 20.0),
]

def seed(reset: bool = False) -> None:
    store = TicketStore()
    if reset and store.db_path.exists():
        store.db_path.unlink()
        store = TicketStore()

    for customer, subject, days_ago in SEED_CONTACTS:
        store.record_contact(customer, subject, when=NOW - timedelta(days=days_ago))

    log.info("seeded", contacts=len(SEED_CONTACTS), db=str(store.db_path))
    for customer in sorted({c for c, _, _ in SEED_CONTACTS}):
        flagged, count = store.is_frequent_contact(customer)
        log.info("contact_summary", customer=customer, recent_contacts=count, would_escalate=flagged)

if __name__ == "__main__":
    configure_logging()
    seed(reset="--reset" in sys.argv)
