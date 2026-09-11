from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.config import settings
from part1_email_agent.precheck import CriticalSignalDetector

@pytest.fixture(scope="module")
def detector(request):
    from core.embeddings import HashingEmbedder

    return CriticalSignalDetector(embedder=HashingEmbedder(), threshold=2.0)

@pytest.mark.parametrize(
    "text,expected_category",
    [
        ("We have data loss on our production system", "data_loss"),
        ("all our customer records disappeared after the sync", "data_loss"),
        ("Data kami hilang setelah sinkronisasi semalam", "data_loss"),
        ("There is a service outage affecting our office", "service_outage"),
        ("The platform is down since this morning", "service_outage"),
        ("Sistem tidak bisa diakses sejak pagi", "service_outage"),
        ("I think our account was hacked", "security_breach"),
        ("There was unauthorized access to our admin console", "security_breach"),
        ("Akun kami dibobol orang tidak dikenal", "security_breach"),
    ],
)
def test_critical_keywords_are_detected(detector, text, expected_category):
    outcome = detector.detect(text)
    assert outcome.triggered
    assert outcome.reason == f"critical_keyword:{expected_category}"
    assert outcome.evidence

@pytest.mark.parametrize(
    "text",
    [
        "Where can I download my invoice for last month?",
        "Could you add two more seats to our Google Workspace plan?",
        "Saya ingin tahu cara mengganti admin utama akun kami",
        "It would be great if the dashboard had a dark mode",
    ],
)
def test_ordinary_emails_do_not_trigger(detector, text):
    assert not detector.detect(text).triggered

@pytest.mark.skipif(
    settings.embedding_backend == "hash",
    reason="needs the real embedding model; the hash fallback is not semantic",
)
@pytest.mark.parametrize(
    "text",
    [
        "bagaimana cara menambah user di akun saya",
        "How do I add another user to my account?",
        "Tolong hapus satu pengguna dari akun kami karena sudah resign.",
        "Halo, sejak pagi saya tidak bisa masuk ke akun saya. Bagaimana caranya reset password?",
    ],
)
def test_routine_account_requests_are_not_incidents(text):
    from core.embeddings import get_embedder

    detector = CriticalSignalDetector(embedder=get_embedder())
    assert not detector.detect(text).triggered

@pytest.mark.skipif(
    settings.embedding_backend == "hash",
    reason="needs the real embedding model; the hash fallback is not semantic",
)
@pytest.mark.parametrize(
    "text",
    [
        "Sepertinya ada orang lain yang masuk ke akun perusahaan kami tanpa izin.",
        "There are logins from an IP address in another country that we do not recognise.",
        "Setelah migrasi kemarin, sebagian besar catatan pelanggan kami tidak ditemukan lagi.",
    ],
)
def test_real_incidents_still_escalate(text):
    from core.embeddings import get_embedder

    detector = CriticalSignalDetector(embedder=get_embedder())
    assert detector.detect(text).triggered

def test_frequency_rule_counts_only_the_window(store):
    now = datetime.now(timezone.utc)
    customer = "repeat@customer.example"

    for days_ago in (6, 4, 2, 1):
        store.record_contact(customer, "follow up", when=now - timedelta(days=days_ago))
    flagged, count = store.is_frequent_contact(customer)
    assert (flagged, count) == (True, 4)

def test_frequency_rule_ignores_old_contacts(store):
    now = datetime.now(timezone.utc)
    customer = "occasional@customer.example"

    for days_ago in (30, 20, 10, 8):
        store.record_contact(customer, "old ticket", when=now - timedelta(days=days_ago))
    store.record_contact(customer, "recent", when=now - timedelta(days=1))

    flagged, count = store.is_frequent_contact(customer)
    assert (flagged, count) == (False, 1)

def test_exactly_three_contacts_is_not_an_escalation(store):
    now = datetime.now(timezone.utc)
    customer = "borderline@customer.example"
    for days_ago in (5, 3, 1):
        store.record_contact(customer, "question", when=now - timedelta(days=days_ago))

    flagged, count = store.is_frequent_contact(customer)
    assert (flagged, count) == (False, 3)
