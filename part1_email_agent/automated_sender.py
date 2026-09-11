from __future__ import annotations

import re
from dataclasses import dataclass

NO_REPLY_LOCALPART = re.compile(
    r"^(no[-_.]?reply|do[-_.]?not[-_.]?reply|donotreply|noreply|mailer[-_.]?daemon|postmaster|"
    r"bounce[sd]?|notifications?|alerts?|automated|auto[-_.]?confirm|newsletter|digest)([-_.+].*)?$",
    re.I,
)

AUTO_SUBMITTED_HEADER = "auto-submitted"
BULK_PRECEDENCE = {"bulk", "list", "junk", "auto_reply"}
LIST_HEADERS = ("list-id", "list-unsubscribe", "list-post")

@dataclass
class AutomatedCheck:
    is_automated: bool
    reason: str | None = None
    evidence: str | None = None

def check(
    sender: str,
    headers: dict[str, str] | None = None,
    own_addresses: set[str] | None = None,
) -> AutomatedCheck:
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    sender_address = sender.strip().lower()

    if own_addresses and sender_address in {a.strip().lower() for a in own_addresses if a}:
        return AutomatedCheck(True, "own_address", f"{sender_address} is this system's own mailbox")

    auto_submitted = headers.get(AUTO_SUBMITTED_HEADER, "").strip().lower()
    if auto_submitted and not auto_submitted.startswith("no"):
        return AutomatedCheck(True, "auto_submitted_header", f"Auto-Submitted: {auto_submitted}")

    precedence = headers.get("precedence", "").strip().lower()
    if precedence in BULK_PRECEDENCE:
        return AutomatedCheck(True, "bulk_precedence", f"Precedence: {precedence}")

    for header in LIST_HEADERS:
        if headers.get(header):
            return AutomatedCheck(True, "mailing_list", f"{header} present")

    local_part = sender.split("@", 1)[0].strip().lower()
    if NO_REPLY_LOCALPART.match(local_part):
        return AutomatedCheck(True, "no_reply_sender", sender)

    return AutomatedCheck(False)
