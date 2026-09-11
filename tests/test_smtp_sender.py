from __future__ import annotations

import pytest

from part1_email_agent.models import IncomingEmail
from part1_email_agent.smtp_sender import EmailSender

class FakeSMTP:

    sent_messages: list = []
    commands: list = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port
        self._ehlo_done = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def ehlo(self):
        self._ehlo_done = True
        FakeSMTP.commands.append("ehlo")

    def has_extn(self, name):
        return self._ehlo_done

    def starttls(self):
        FakeSMTP.commands.append("starttls")

    def login(self, user, password):
        self.login_args = (user, password)
        FakeSMTP.commands.append("login")

    def send_message(self, message):
        FakeSMTP.commands.append("send")
        FakeSMTP.sent_messages.append(message)

def make_sender(**overrides) -> EmailSender:
    defaults = dict(
        host="smtp.example.com", port=587, user="bot@pointstar-consulting.example",
        password="secret", from_address="support@pointstar-consulting.example", from_name="Rega's Support",
    )
    return EmailSender(**{**defaults, **overrides})

def test_disabled_sender_does_not_attempt_a_connection(monkeypatch):
    monkeypatch.setattr("smtplib.SMTP", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not connect")))
    sender = make_sender(host="")

    result = sender.send_reply(
        IncomingEmail(sender="customer@realdomain.com", subject="Invoice", body="..."),
        "Here is your answer.",
        trace_id="abc123",
    )

    assert result.sent is False
    assert result.reason == "smtp_not_configured"

def test_enabled_sender_sends_and_sets_headers(monkeypatch):
    FakeSMTP.sent_messages = []
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    sender = make_sender()
    original = IncomingEmail(
        sender="customer@realdomain.com", subject="Invoice question", body="...",
        message_id="<orig-123@customer.example>",
    )

    result = sender.send_reply(original, "Here is your answer.", trace_id="trace-42")

    assert result.sent is True
    assert result.reason == "sent"
    assert len(FakeSMTP.sent_messages) == 1
    sent = FakeSMTP.sent_messages[0]
    assert sent["To"] == "customer@realdomain.com"
    assert sent["Subject"] == "Re: Invoice question"
    assert sent["In-Reply-To"] == "<orig-123@customer.example>"
    assert sent["X-PointStar-Trace-Id"] == "trace-42"
    assert sent.get_content().strip() == "Here is your answer."

def test_subject_is_not_double_prefixed(monkeypatch):
    FakeSMTP.sent_messages = []
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    sender = make_sender()
    original = IncomingEmail(sender="customer@realdomain.com", subject="Re: Invoice question", body="...")

    sender.send_reply(original, "Answer.", trace_id="t1")

    assert FakeSMTP.sent_messages[0]["Subject"] == "Re: Invoice question"

def test_sends_without_auth_when_relay_does_not_offer_it(monkeypatch):
    class NoAuthSMTP(FakeSMTP):
        def has_extn(self, name):
            return False

        def login(self, user, password):
            raise AssertionError("login() must not be called when AUTH is not offered")

    FakeSMTP.sent_messages = []
    monkeypatch.setattr("smtplib.SMTP", NoAuthSMTP)
    sender = make_sender()

    result = sender.send_reply(
        IncomingEmail(sender="customer@realdomain.com", subject="Hi", body="..."), "Answer.", trace_id="t3"
    )

    assert result.sent is True
    assert len(FakeSMTP.sent_messages) == 1

def test_starttls_is_negotiated_before_login(monkeypatch):
    FakeSMTP.sent_messages, FakeSMTP.commands = [], []
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)

    result = make_sender().send_reply(
        IncomingEmail(sender="customer@realdomain.com", subject="Hi", body="..."), "Answer.", trace_id="t-tls"
    )

    assert result.sent is True
    assert FakeSMTP.commands == ["ehlo", "starttls", "ehlo", "login", "send"]

@pytest.mark.parametrize(
    "address",
    [
        "kevin.ong@ojets.example",
        "someone@example.com",
        "tester@my-app.invalid",
        "user@service.test",
    ],
)
def test_reserved_test_domains_are_never_emailed(monkeypatch, address):
    monkeypatch.setattr("smtplib.SMTP", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not connect")))

    result = make_sender().send_reply(
        IncomingEmail(sender=address, subject="Hi", body="..."), "Answer.", trace_id="t-reserved"
    )

    assert result.sent is False
    assert result.reason == "undeliverable_recipient"

def test_real_domains_are_still_sent_to(monkeypatch):
    FakeSMTP.sent_messages, FakeSMTP.commands = [], []
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)

    result = make_sender().send_reply(
        IncomingEmail(sender="someone@gmail.com", subject="Hi", body="..."), "Answer.", trace_id="t-real"
    )

    assert result.sent is True

def test_acknowledgement_carries_ticket_number_and_threads_the_reply(monkeypatch):
    FakeSMTP.sent_messages = []
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    original = IncomingEmail(
        sender="customer@realdomain.com", subject="Data hilang", body="...", message_id="<orig-9@customer.example>",
    )

    result = make_sender().send_acknowledgement(original, trace_id="abc123def456")

    assert result.sent is True
    sent = FakeSMTP.sent_messages[0]
    body = sent.get_content()
    assert "abc123def456" in body, "the customer needs the ticket number to follow up"
    assert "Rega's Support" in body
    assert sent["Subject"] == "Re: Data hilang"
    assert sent["In-Reply-To"] == "<orig-9@customer.example>"
    assert sent["X-PointStar-Trace-Id"] == "abc123def456"

def test_acknowledgement_respects_disabled_smtp(monkeypatch):
    monkeypatch.setattr("smtplib.SMTP", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not connect")))

    result = make_sender(host="").send_acknowledgement(
        IncomingEmail(sender="customer@realdomain.com", subject="Hi", body="..."), trace_id="t-off"
    )

    assert result.sent is False
    assert result.reason == "smtp_not_configured"

def test_smtp_failure_is_reported_not_raised(monkeypatch):
    import smtplib

    class BoomSMTP(FakeSMTP):
        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr("smtplib.SMTP", BoomSMTP)
    sender = make_sender()

    result = sender.send_reply(
        IncomingEmail(sender="customer@realdomain.com", subject="Hi", body="..."), "Answer.", trace_id="t2"
    )

    assert result.sent is False
    assert result.reason == "smtp_error"
    assert "SMTPAuthenticationError" in result.detail
