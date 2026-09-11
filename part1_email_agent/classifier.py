from __future__ import annotations

import json

from core.llm import LLMClient
from part1_email_agent.models import ClassificationResult

SYSTEM_PROMPT = (
    "You are an email triage classifier for PointStar, a cloud consulting company that resells "
    "Google Workspace, Google Cloud Platform, Oracle NetSuite, JumpCloud, Zoom and Cisco Meraki, "
    "and delivers implementation/consulting services. Classify support emails accurately and "
    "report honest confidence scores. Never invent a category outside the allowed list."
)

FEW_SHOT_EXAMPLES: list[dict] = [
    {
        "email": "Subject: Tagihan naik\n\nKenapa tagihan Google Workspace saya bulan ini lebih mahal dari biasanya?",
        "output": {
            "labels": [
                {"category": "billing", "confidence": 0.95, "reason": "menanyakan kenaikan tagihan Google Workspace"}
            ]
        },
    },
    {
        "email": "Subject: Sync error\n\nOur NetSuite to Google Sheets integration keeps failing since yesterday. I already reconnected the OAuth token but it still errors.",
        "output": {
            "labels": [
                {"category": "technical", "confidence": 0.93, "reason": "NetSuite-Google Sheets integration failing"}
            ]
        },
    },
    {
        "email": "Subject: Dua masalah\n\nTagihan JumpCloud saya naik dua kali lipat, dan sejak upgrade paket itu SSO saya juga jadi sering logout sendiri.",
        "output": {
            "labels": [
                {"category": "billing", "confidence": 0.88, "reason": "tagihan JumpCloud naik dua kali lipat"},
                {"category": "technical", "confidence": 0.82, "reason": "SSO logout sendiri setelah upgrade"},
            ]
        },
    },
    {
        "email": "Subject: Suggestion\n\nIt would be great if your onboarding dashboard had a dark mode.",
        "output": {
            "labels": [{"category": "feedback", "confidence": 0.9, "reason": "feature suggestion for dark mode"}]
        },
    },
    {
        "email": "Subject: Admin change\n\nPlease transfer the admin rights of our account to our new IT manager.",
        "output": {
            "labels": [{"category": "account", "confidence": 0.91, "reason": "request to transfer admin rights"}]
        },
    },
    {
        "email": "Subject: Tolong dicek\n\nAda masalah nih, tolong dicek ya.",
        "output": {
            "labels": [
                {"category": "general", "confidence": 0.3, "reason": "tidak ada detail spesifik tentang masalahnya"}
            ]
        },
    },
]

def build_prompt(email_text: str) -> str:
    examples = "\n\n".join(
        f"Email:\n{example['email']}\nOutput: {json.dumps(example['output'], ensure_ascii=False)}"
        for example in FEW_SHOT_EXAMPLES
    )
    return f"""Classify the email into one or more of these categories:
billing, technical, feedback, account, general.

Rules:
- Assign every category that genuinely applies; an email may have several.
- confidence is your honest probability (0-1) that the label is correct.
- If the email is too vague to categorise, return "general" with a low confidence (<0.5).
- The emails may be in English or Indonesian.

Examples of correct output:

{examples}

Now classify this email:

Email:
{email_text}
Output:"""

def classify_email(llm: LLMClient, email_text: str) -> ClassificationResult:
    return llm.generate_structured(build_prompt(email_text), ClassificationResult, system=SYSTEM_PROMPT)
