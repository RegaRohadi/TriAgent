from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.config import settings
from core.llm import LLMClient
from part1_email_agent.models import RefundEntities

EXTRACTION_SYSTEM = (
    "You extract structured facts from customer emails. Report only what the customer "
    "explicitly states. Never guess or infer a value that is not written in the email."
)

FX_TO_USD = {"USD": 1.0, "SGD": 0.74, "MYR": 0.21, "IDR": 0.000061}

COVERED_REFUND_PRODUCTS = (
    "google workspace",
    "google cloud",
    "gcp",
    "netsuite",
    "jumpcloud",
    "zoom",
    "meraki",
    "professional services",
    "implementation",
)

@dataclass
class ThresholdCheck:
    exceeded: bool
    reason: str | None = None
    detail: str | None = None

def extract_refund_entities(llm: LLMClient, email_text: str) -> RefundEntities:
    prompt = f"""Extract refund-related facts from this customer email.

Set mentions_refund=true only if the customer asks about a refund, a cancellation
with money back, or reversing a charge.
Leave a field null when the email does not state it. Do not infer or estimate.
Today's date is {date.today().isoformat()}.

Email:
{email_text}"""
    return llm.generate_structured(prompt, RefundEntities, system=EXTRACTION_SYSTEM)

def to_usd(amount: float, currency: str | None) -> float | None:
    rate = FX_TO_USD.get((currency or "USD").upper())
    return None if rate is None else amount * rate

def check_refund_thresholds(entities: RefundEntities, today: date | None = None) -> ThresholdCheck:
    today = today or date.today()

    if entities.amount is not None:
        usd = to_usd(entities.amount, entities.currency)
        if usd is not None and usd > settings.refund_amount_threshold_usd:
            return ThresholdCheck(
                True,
                "refund_amount_exceeds_threshold",
                f"{entities.amount} {entities.currency or 'USD'} ≈ USD {usd:.2f} > "
                f"USD {settings.refund_amount_threshold_usd:.0f}",
            )

    if entities.purchase_date:
        try:
            purchased = date.fromisoformat(entities.purchase_date)
        except ValueError:
            purchased = None
        if purchased:
            age_days = (today - purchased).days
            if age_days > settings.refund_age_days_threshold:
                return ThresholdCheck(
                    True,
                    "refund_request_too_old",
                    f"charge is {age_days} days old > {settings.refund_age_days_threshold} days",
                )

    if entities.product and "netsuite" in entities.product.lower():
        return ThresholdCheck(
            True, "netsuite_contract_requires_review", "NetSuite contracts always require Finance/Legal review"
        )

    if not entities.product:
        return ThresholdCheck(
            True, "refund_product_unspecified", "no product named, so no §2 clause can be applied"
        )
    if not any(known in entities.product.lower() for known in COVERED_REFUND_PRODUCTS):
        return ThresholdCheck(
            True, "refund_scenario_not_covered", f"'{entities.product}' has no refund terms in KB-POLICY-001 §2"
        )

    return ThresholdCheck(False)
