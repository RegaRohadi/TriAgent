from __future__ import annotations

import email
import imaplib
import re
from email.header import decode_header, make_header
from email.message import Message
from pathlib import Path

from core.config import settings
from core.logging_config import get_logger
from part1_email_agent.models import IncomingEmail

log = get_logger(__name__)

ADDRESS_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value

def _extract_body(message: Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        for part in message.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    return re.sub(r"<[^>]+>", " ", html)
        return ""

    payload = message.get_payload(decode=True)
    if payload:
        return payload.decode(message.get_content_charset() or "utf-8", errors="replace")
    return str(message.get_payload())

TRIAGE_HEADERS = (
    "Auto-Submitted", "Precedence", "List-Id", "List-Unsubscribe", "List-Post",
    "X-Auto-Response-Suppress",
)

def parse_message(message: Message) -> IncomingEmail:
    sender_raw = _decode(message.get("From"))
    address_match = ADDRESS_PATTERN.search(sender_raw)
    return IncomingEmail(
        sender=(address_match.group(0) if address_match else sender_raw).lower(),
        subject=_decode(message.get("Subject")),
        body=_extract_body(message).strip(),
        message_id=message.get("Message-ID"),
        headers={h.lower(): _decode(message.get(h)) for h in TRIAGE_HEADERS if message.get(h)},
    )

def load_eml(path: Path) -> IncomingEmail:
    with path.open("rb") as handle:
        return parse_message(email.message_from_binary_file(handle))

def load_sample_emails(directory: Path | None = None) -> list[tuple[Path, IncomingEmail]]:
    directory = directory or settings.sample_email_dir
    return [(path, load_eml(path)) for path in sorted(directory.glob("*.eml"))]

def parse_pasted_text(raw: str, fallback_sender: str = "unknown@customer.example") -> IncomingEmail:
    if re.match(r"^(From|Subject|To|Date):", raw.strip(), re.I | re.M):
        return parse_message(email.message_from_string(raw))

    lines = raw.strip().splitlines()
    subject = lines[0].strip()[:120] if lines else "(no subject)"
    return IncomingEmail(sender=fallback_sender, subject=subject, body=raw.strip())

def fetch_from_imap(limit: int = 5) -> list[IncomingEmail]:
    if not settings.imap_enabled:
        raise RuntimeError("IMAP is not configured. Set IMAP_HOST, IMAP_USER and IMAP_PASSWORD in .env")

    log.info("imap_connect", host=settings.imap_host, folder=settings.imap_folder)
    with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as client:
        client.login(settings.imap_user, settings.imap_password)
        client.select(settings.imap_folder)
        status, data = client.search(None, "ALL")
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")

        message_ids = data[0].split()[-limit:]
        emails: list[IncomingEmail] = []
        for message_id in reversed(message_ids):
            status, payload = client.fetch(message_id, "(RFC822)")
            if status != "OK" or not payload or not isinstance(payload[0], tuple):
                continue
            emails.append(parse_message(email.message_from_bytes(payload[0][1])))
        log.info("imap_fetched", count=len(emails))
        return emails
