from __future__ import annotations

import smtplib
import uuid
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

from core.config import settings
from core.logging_config import get_logger
from part1_email_agent.models import IncomingEmail

log = get_logger(__name__)

UNDELIVERABLE_DOMAINS = (".example", ".invalid", ".test", ".localhost")
UNDELIVERABLE_EXACT = ("example.com", "example.org", "example.net")

def is_undeliverable(address: str) -> bool:
    domain = address.rsplit("@", 1)[-1].strip().lower()
    return domain in UNDELIVERABLE_EXACT or domain.endswith(UNDELIVERABLE_DOMAINS)

@dataclass
class SendResult:
    sent: bool
    reason: str
    detail: str | None = None

ACKNOWLEDGEMENT_TEMPLATE = """Halo,

Terima kasih telah menghubungi {from_name}.

Pesan ini otomatis. Laporan Anda dengan nomor tiket {trace_id} sudah kami terima. \
Mohon ditunggu ya, tim kami akan segera menindaklanjuti pesan Anda untuk proses \
pengecekan lebih lanjut.

Sebagai informasi tambahan, mohon untuk tidak memberikan kode OTP, PIN, atau kata \
sandi kepada pihak manapun untuk mencegah adanya penyalahgunaan akun.

Terima kasih,
{from_name}"""

class EmailSender:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        from_address: str | None = None,
        from_name: str | None = None,
    ) -> None:
        self.host = host if host is not None else settings.smtp_host
        self.port = port if port is not None else settings.smtp_port
        self.user = user if user is not None else settings.smtp_user
        self.password = password if password is not None else settings.smtp_password
        self.from_address = from_address if from_address is not None else settings.smtp_from_address
        self.from_name = from_name if from_name is not None else settings.smtp_from_name

    @property
    def enabled(self) -> bool:
        return bool(self.host and self.user and self.password and self.from_address)

    def send_reply(self, original: IncomingEmail, reply_text: str, trace_id: str) -> SendResult:
        return self._send(original, trace_id, subject=self._reply_subject(original.subject), body=reply_text)

    def send_acknowledgement(self, original: IncomingEmail, trace_id: str) -> SendResult:
        body = ACKNOWLEDGEMENT_TEMPLATE.format(from_name=self.from_name, trace_id=trace_id)
        return self._send(original, trace_id, subject=self._reply_subject(original.subject), body=body)

    def _send(self, original: IncomingEmail, trace_id: str, subject: str, body: str) -> SendResult:
        if not self.enabled:
            log.info("smtp_disabled_skip_send", trace_id=trace_id, to=original.sender)
            return SendResult(sent=False, reason="smtp_not_configured")

        if is_undeliverable(original.sender):
            log.info("skip_send_reserved_domain", trace_id=trace_id, to=original.sender)
            return SendResult(
                sent=False,
                reason="undeliverable_recipient",
                detail=f"{original.sender} uses a reserved test domain and cannot receive mail",
            )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.from_name, self.from_address))
        message["To"] = original.sender
        message["X-TriAgent-Trace-Id"] = trace_id
        message["Message-ID"] = f"<{uuid.uuid4().hex}@nimbus-cloud.example>"
        if original.message_id:
            message["In-Reply-To"] = original.message_id
            message["References"] = original.message_id
        message.set_content(body)

        try:
            if self.port == 465:
                client_cls, client_kwargs = smtplib.SMTP_SSL, {}
            else:
                client_cls, client_kwargs = smtplib.SMTP, {}

            with client_cls(self.host, self.port, timeout=15, **client_kwargs) as client:
                client.ehlo()
                if self.port != 465 and client.has_extn("STARTTLS"):
                    client.starttls()
                    client.ehlo()
                if client.has_extn("AUTH"):
                    client.login(self.user, self.password)
                client.send_message(message)
            log.info("email_sent", trace_id=trace_id, to=original.sender, subject=message["Subject"])
            return SendResult(sent=True, reason="sent")
        except (smtplib.SMTPException, OSError) as exc:
            log.error("smtp_send_failed", trace_id=trace_id, to=original.sender, error=str(exc)[:300])
            return SendResult(sent=False, reason="smtp_error", detail=f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _reply_subject(subject: str) -> str:
        stripped = subject.strip()
        return stripped if stripped.lower().startswith("re:") else f"Re: {stripped}"
