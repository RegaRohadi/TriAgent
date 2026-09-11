from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel

from part1_email_agent.models import (
    Category,
    CategoryScore,
    ClassificationResult,
    DraftResponse,
    RefundEntities,
    VerificationResult,
)

CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.BILLING: (
        "invoice", "bill", "charge", "charged", "payment", "refund", "price", "tagihan",
        "bayar", "faktur", "pembayaran", "biaya", "langganan", "subscription", "renew",
    ),
    Category.TECHNICAL: (
        "error", "bug", "sync", "integration", "login", "api", "crash", "not working",
        "failed", "quota", "sso", "gagal", "tidak bisa", "eror", "koneksi",
    ),
    Category.FEEDBACK: (
        "suggest", "suggestion", "feature request", "would be great", "improve", "feedback",
        "saran", "masukan", "usulan", "sebaiknya",
    ),
    Category.ACCOUNT: (
        "admin rights", "transfer admin", "add user", "remove user", "seat", "permission",
        "account settings", "hak akses", "pengguna baru", "data deletion", "privacy",
    ),
}

AMOUNT_PATTERN = re.compile(
    r"(?:(USD|SGD|MYR|IDR|RM|Rp|\$)\s*([\d.,]+))|(?:([\d.,]+)\s*(USD|SGD|MYR|IDR))", re.I
)
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
REFUND_PATTERN = re.compile(r"\b(refund|money back|reimburse|cancel.*(charge|subscription)|pengembalian dana)\b", re.I)
PRODUCT_PATTERN = re.compile(r"\b(google workspace|google cloud|gcp|netsuite|jumpcloud|zoom|meraki)\b", re.I)
CHUNK_SOURCE_PATTERN = re.compile(r"\[(KB-[A-Z]+-\d+)\s+§")
NUMBER_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?\b")

CURRENCY_ALIASES = {"$": "USD", "RM": "MYR", "RP": "IDR"}

class MockLLM:
    name = "mock"

    def generate_structured(self, prompt: str, schema: type[BaseModel], *, system: str | None = None):
        if schema is ClassificationResult:
            return self._classify(prompt)
        if schema is RefundEntities:
            return self._extract_entities(prompt)
        if schema is DraftResponse:
            return self._draft(prompt)
        if schema is VerificationResult:
            return self._verify(prompt)
        raise NotImplementedError(f"MockLLM has no handler for {schema.__name__}")

    @staticmethod
    def _section(prompt: str, start_marker: str, end_marker: str | None = None) -> str:
        if start_marker not in prompt:
            return ""
        body = prompt.split(start_marker, 1)[1]
        if end_marker and end_marker in body:
            body = body.split(end_marker, 1)[0]
        return body.strip()

    def _target_email(self, prompt: str) -> str:
        for marker in ("Now classify this email:", "Customer email:", "Email:"):
            if marker in prompt:
                return prompt.rsplit(marker, 1)[1].replace("Output:", "").strip()
        return prompt

    def _classify(self, prompt: str) -> ClassificationResult:
        text = self._target_email(prompt).lower()
        labels: list[CategoryScore] = []
        for category, keywords in CATEGORY_KEYWORDS.items():
            hits = [kw for kw in keywords if kw in text]
            if hits:
                confidence = min(0.95, 0.7 + 0.05 * len(hits))
                labels.append(
                    CategoryScore(category=category, confidence=confidence, reason=f"matched keywords: {hits[:3]}")
                )

        if not labels:
            return ClassificationResult(
                labels=[
                    CategoryScore(
                        category=Category.GENERAL, confidence=0.3, reason="no category-specific signal found"
                    )
                ]
            )
        labels.sort(key=lambda label: label.confidence, reverse=True)
        return ClassificationResult(labels=labels)

    def _extract_entities(self, prompt: str) -> RefundEntities:
        text = self._target_email(prompt)
        mentions = bool(REFUND_PATTERN.search(text))

        amount, currency = None, None
        match = AMOUNT_PATTERN.search(text)
        if match:
            symbol = (match.group(1) or match.group(4) or "").upper()
            raw_amount = match.group(2) or match.group(3) or ""
            currency = CURRENCY_ALIASES.get(symbol, symbol) or None
            cleaned = raw_amount.replace(",", "") if raw_amount.count(",") <= 1 else raw_amount.replace(",", "")
            try:
                amount = float(cleaned)
            except ValueError:
                amount = None

        date_match = DATE_PATTERN.search(text)
        purchase_date = date_match.group(1) if date_match else None
        if purchase_date:
            try:
                date.fromisoformat(purchase_date)
            except ValueError:
                purchase_date = None

        product_match = PRODUCT_PATTERN.search(text)
        return RefundEntities(
            mentions_refund=mentions,
            amount=amount,
            currency=currency,
            purchase_date=purchase_date,
            product=product_match.group(1) if product_match else None,
        )

    def _draft(self, prompt: str) -> DraftResponse:
        context = self._section(prompt, "Knowledge base context:", "Customer email:")
        question = self._section(prompt, "Customer email:")
        doc_ids = sorted(set(CHUNK_SOURCE_PATTERN.findall(context)))
        excerpt = " ".join(context.split())[:400].rsplit(" ", 1)[0]
        text = (
            "Thank you for contacting Rega's Support.\n\n"
            f"Based on our knowledge base: {excerpt}\n\n"
            "If anything above does not fully address your situation, a specialist will follow up."
        )
        answerable = bool(doc_ids) and self._context_covers_question(question, context)
        return DraftResponse(text=text, citations=doc_ids, fully_answerable=answerable)

    @staticmethod
    def _context_covers_question(question: str, context: str, min_overlap: float = 0.12) -> bool:
        words = {w for w in re.findall(r"[a-zA-Z]{5,}", question.lower())}
        if not words:
            return True
        context_words = set(re.findall(r"[a-zA-Z]{5,}", context.lower()))
        return len(words & context_words) / len(words) >= min_overlap

    def _verify(self, prompt: str) -> VerificationResult:
        context = self._section(prompt, "Source excerpts:", "Draft reply:")
        draft = self._section(prompt, "Draft reply:")
        context_numbers = set(NUMBER_PATTERN.findall(context))
        unsupported = [n for n in NUMBER_PATTERN.findall(draft) if n not in context_numbers]
        return VerificationResult(
            fully_grounded=not unsupported,
            unsupported_claims=[f"number '{n}' not present in sources" for n in sorted(set(unsupported))],
        )
