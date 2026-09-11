from __future__ import annotations

import pytest

from part1_email_agent import automated_sender

@pytest.mark.parametrize(
    "sender",
    [
        "no-reply@accounts.google.com",
        "noreply@service.com",
        "no_reply@service.com",
        "do-not-reply@billing.example-corp.com",
        "donotreply@bank.com",
        "MAILER-DAEMON@mx.google.com",
        "postmaster@relay.net",
        "bounces+123@sendgrid.net",
        "notifications@github.com",
        "newsletter@company.com",
    ],
)
def test_no_reply_style_senders_are_automated(sender):
    result = automated_sender.check(sender)
    assert result.is_automated
    assert result.reason == "no_reply_sender"

@pytest.mark.parametrize(
    "sender",
    [
        "anna.lim@unionbook.example",
        "kevin.ong@ojets.example",
        "replyto@customer.com",
        "noreplacement@vendor.com",
        "andrew.notton@firm.com",
    ],
)
def test_ordinary_customers_are_not_automated(sender):
    assert not automated_sender.check(sender).is_automated

def test_auto_submitted_header_marks_machine_mail():
    result = automated_sender.check("someone@company.com", {"Auto-Submitted": "auto-generated"})
    assert result.is_automated
    assert result.reason == "auto_submitted_header"

def test_auto_submitted_no_is_a_real_person():
    assert not automated_sender.check("someone@company.com", {"Auto-Submitted": "no"}).is_automated

@pytest.mark.parametrize("precedence", ["bulk", "list", "junk"])
def test_bulk_precedence_is_automated(precedence):
    result = automated_sender.check("someone@company.com", {"Precedence": precedence})
    assert result.is_automated
    assert result.reason == "bulk_precedence"

@pytest.mark.parametrize("header", ["List-Id", "List-Unsubscribe", "List-Post"])
def test_mailing_list_headers_are_automated(header):
    result = automated_sender.check("list@group.com", {header: "<something>"})
    assert result.is_automated
    assert result.reason == "mailing_list"

def test_header_lookup_is_case_insensitive():
    assert automated_sender.check("x@y.com", {"AUTO-SUBMITTED": "auto-replied"}).is_automated

def test_own_mailbox_is_filtered_to_prevent_a_mail_loop():
    result = automated_sender.check(
        "support@pointstar-consulting.com", own_addresses={"support@pointstar-consulting.com"}
    )
    assert result.is_automated
    assert result.reason == "own_address"

def test_own_address_matching_ignores_case_and_spacing():
    result = automated_sender.check("  Support@PointStar.COM ", own_addresses={"support@pointstar.com"})
    assert result.is_automated

def test_empty_own_addresses_are_not_treated_as_matches():
    assert not automated_sender.check("customer@company.com", own_addresses={"", None}).is_automated

def test_evidence_is_recorded_for_the_audit_trail():
    result = automated_sender.check("no-reply@accounts.google.com")
    assert result.evidence == "no-reply@accounts.google.com"
