from __future__ import annotations

from datetime import date

import pytest

from part1_email_agent.entities import check_refund_thresholds
from part1_email_agent.models import RefundEntities

def entities(**kwargs) -> RefundEntities:
    return RefundEntities(**{"mentions_refund": True, "product": "Google Workspace", **kwargs})

def test_amount_below_limit_stays_automated():
    assert not check_refund_thresholds(entities(amount=120, currency="USD")).exceeded

def test_amount_above_limit_escalates():
    result = check_refund_thresholds(entities(amount=12000, currency="USD"))
    assert result.exceeded
    assert result.reason == "refund_amount_exceeds_threshold"

def test_amount_is_converted_before_comparison():
    assert not check_refund_thresholds(entities(amount=1_000_000, currency="IDR")).exceeded
    assert check_refund_thresholds(entities(amount=20_000_000, currency="IDR")).exceeded

def test_old_request_escalates():
    result = check_refund_thresholds(
        entities(purchase_date="2026-01-01"), today=date(2026, 9, 10)
    )
    assert result.exceeded
    assert result.reason == "refund_request_too_old"

def test_recent_request_does_not_escalate():
    result = check_refund_thresholds(
        entities(purchase_date="2026-09-05"), today=date(2026, 9, 10)
    )
    assert not result.exceeded

def test_netsuite_always_escalates():
    result = check_refund_thresholds(entities(product="Oracle NetSuite", amount=10))
    assert result.exceeded
    assert result.reason == "netsuite_contract_requires_review"

@pytest.mark.parametrize("bad_date", ["not-a-date", "09/05/2026", ""])
def test_unparseable_date_is_ignored_not_crashed(bad_date):
    assert not check_refund_thresholds(entities(purchase_date=bad_date)).exceeded

def test_unnamed_product_escalates():
    result = check_refund_thresholds(RefundEntities(mentions_refund=True, product=None))
    assert result.exceeded
    assert result.reason == "refund_product_unspecified"

def test_product_outside_the_policy_escalates():
    result = check_refund_thresholds(entities(product="classroom training seat"))
    assert result.exceeded
    assert result.reason == "refund_scenario_not_covered"

@pytest.mark.parametrize(
    "product", ["Google Workspace", "GCP", "JumpCloud", "Zoom", "Cisco Meraki", "implementation services"]
)
def test_covered_products_stay_automated(product):
    assert not check_refund_thresholds(entities(product=product)).exceeded
