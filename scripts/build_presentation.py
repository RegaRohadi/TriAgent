"""Generate the Developer Intern technical assessment presentation.

Reproducible python-pptx generator. Run:
    python scripts/build_presentation.py

Output: presentation/TriAgent_Presentation.pptx
All content is grounded in the repository source. Anything not verifiable from
the repository is marked [NEEDS MY INPUT] or "Proposed".
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = PROJECT_ROOT / "presentation" / "TriAgent_Presentation.pptx"

# ----------------------------------------------------------------------------
# Design system
# ----------------------------------------------------------------------------
W, H = 13.333, 7.5
FONT = "Segoe UI"
MONO = "Consolas"

NAVY = RGBColor(0x0B, 0x1F, 0x3A)
NAVY2 = RGBColor(0x13, 0x2C, 0x4D)
NAVY3 = RGBColor(0x1B, 0x3A, 0x63)
LIGHT = RGBColor(0xE8, 0xEF, 0xF9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY = RGBColor(0x9F, 0xB0, 0xC7)
MUTED = RGBColor(0x6C, 0x82, 0xA2)
ACCENT = RGBColor(0x3B, 0x82, 0xF6)
ACCENT_D = RGBColor(0x1D, 0x4E, 0xD8)
AMBER = RGBColor(0xF5, 0x9E, 0x0B)
GREEN = RGBColor(0x22, 0xC5, 0x5E)
RED = RGBColor(0xEF, 0x44, 0x44)

FOOTER = "TriAgent  |  Developer Intern Technical Assessment"


# ----------------------------------------------------------------------------
# Low level helpers
# ----------------------------------------------------------------------------
def blank(prs, background=NAVY):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(W), Inches(H))
    bg.fill.solid()
    bg.fill.fore_color.rgb = background
    bg.line.fill.background()
    bg.shadow.inherit = False
    return slide


def rect(slide, l, t, w, h, fill, rounded=False, radius=0.08, line=None, line_w=1.0):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_w)
    shape.shadow.inherit = False
    if rounded:
        try:
            shape.adjustments[0] = radius
        except Exception:
            pass
    return shape


def textbox(slide, l, t, w, h, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    return tf


def para(tf, text, size=13, color=LIGHT, bold=False, italic=False, align=PP_ALIGN.LEFT,
         bullet=None, space_after=4, space_before=0, font=FONT, line_spacing=1.0, first=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.space_before = Pt(space_before)
    p.line_spacing = line_spacing
    if bullet:
        r0 = p.add_run()
        r0.text = bullet + "  "
        r0.font.size = Pt(size)
        r0.font.bold = True
        r0.font.name = font
        r0.font.color.rgb = ACCENT
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = font
    r.font.color.rgb = color
    return p


def bullets(slide, l, t, w, h, items, size=13, color=LIGHT, space=6, line_spacing=1.05,
            bullet="\u25AA", font=FONT):
    tf = textbox(slide, l, t, w, h)
    for i, item in enumerate(items):
        if isinstance(item, tuple):
            head, tail = item
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(space)
            p.line_spacing = line_spacing
            r0 = p.add_run(); r0.text = bullet + "  "
            r0.font.size = Pt(size); r0.font.bold = True; r0.font.name = font; r0.font.color.rgb = ACCENT
            r1 = p.add_run(); r1.text = head
            r1.font.size = Pt(size); r1.font.bold = True; r1.font.name = font; r1.font.color.rgb = WHITE
            r2 = p.add_run(); r2.text = tail
            r2.font.size = Pt(size); r2.font.name = font; r2.font.color.rgb = color
        else:
            para(tf, item, size=size, color=color, bullet=bullet, space_after=space,
                 line_spacing=line_spacing, font=font, first=(i == 0))
    return tf


def slide_title(slide, text, kicker=None):
    if kicker:
        tf = textbox(slide, 0.62, 0.28, 12.1, 0.28)
        para(tf, kicker.upper(), size=10.5, color=ACCENT, bold=True, space_after=0, first=True)
        top = 0.5
    else:
        top = 0.4
    tf = textbox(slide, 0.62, top, 12.1, 0.62, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, text, size=25, color=WHITE, bold=True, space_after=0, first=True)
    rect(slide, 0.63, 1.08, 1.5, 0.055, ACCENT)


def footer(slide, number):
    tf = textbox(slide, 0.62, 7.08, 9.0, 0.3)
    para(tf, FOOTER, size=8, color=MUTED, space_after=0, first=True)
    tf2 = textbox(slide, 11.6, 7.08, 1.1, 0.3)
    para(tf2, str(number), size=8.5, color=GREY, align=PP_ALIGN.RIGHT, space_after=0, first=True)


def key_message(slide, text):
    rect(slide, 0.62, 6.5, 12.1, 0.48, NAVY2, rounded=True, radius=0.14)
    rect(slide, 0.62, 6.5, 0.075, 0.48, ACCENT)
    tf = textbox(slide, 0.85, 6.5, 11.7, 0.48, anchor=MSO_ANCHOR.MIDDLE)
    p = tf.paragraphs[0]
    r0 = p.add_run(); r0.text = "KEY: "
    r0.font.size = Pt(11); r0.font.bold = True; r0.font.name = FONT; r0.font.color.rgb = ACCENT
    r1 = p.add_run(); r1.text = text
    r1.font.size = Pt(11); r1.font.name = FONT; r1.font.color.rgb = LIGHT


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def add_table(slide, data, l, t, w, h, col_ratios=None, font=10, header_font=10.5,
              row_h=0.34, header_fill=NAVY3, body_fill=NAVY2, alt_fill=RGBColor(0x10, 0x26, 0x42)):
    rows, cols = len(data), len(data[0])
    gtbl = slide.shapes.add_table(rows, cols, Inches(l), Inches(t), Inches(w), Inches(h))
    tbl = gtbl.table
    tbl.first_row = True
    tbl.horz_banding = False
    if col_ratios:
        total = sum(col_ratios)
        for i, ratio in enumerate(col_ratios):
            tbl.columns[i].width = Emu(int(Inches(w) * ratio / total))
    for r in range(rows):
        tbl.rows[r].height = Inches(row_h if r else row_h + 0.02)
        for c in range(cols):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.06)
            cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = header_fill
            else:
                cell.fill.fore_color.rgb = body_fill if r % 2 else alt_fill
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.space_after = Pt(0)
            run = p.add_run()
            run.text = str(data[r][c])
            run.font.name = FONT
            run.font.size = Pt(header_font if r == 0 else font)
            run.font.bold = (r == 0)
            run.font.color.rgb = WHITE if r == 0 else LIGHT
    return tbl


def card(slide, l, t, w, h, heading, items, accent=ACCENT, heading_size=13, body_size=10.5):
    rect(slide, l, t, w, h, NAVY2, rounded=True, radius=0.06)
    rect(slide, l, t, w, 0.06, accent)
    tf = textbox(slide, l + 0.16, t + 0.14, w - 0.32, h - 0.24)
    para(tf, heading, size=heading_size, color=WHITE, bold=True, space_after=5, first=True)
    for item in items:
        para(tf, item, size=body_size, color=LIGHT, bullet="\u2013", space_after=3, line_spacing=1.0)


# ----------------------------------------------------------------------------
# Slides
# ----------------------------------------------------------------------------
def slide_01_title(prs):
    slide = blank(prs)
    rect(slide, 0, 0, W, 0.14, ACCENT)
    rect(slide, 0.9, 1.5, 0.09, 2.1, ACCENT)
    tf = textbox(slide, 1.25, 1.45, 11.0, 1.2)
    para(tf, "TriAgent", size=40, color=WHITE, bold=True, space_after=4, first=True)
    para(tf, "Email Agent  ·  Web Scraper  ·  Document Agent", size=16, color=GREY, space_after=0)
    tf = textbox(slide, 1.27, 3.05, 10.5, 0.7)
    para(tf, "Deterministic code decides; the LLM extracts and writes.",
         size=17, color=ACCENT, italic=True, space_after=0, first=True)
    rect(slide, 1.27, 4.05, 5.4, 0.02, NAVY3)
    tf = textbox(slide, 1.27, 4.25, 10.5, 0.9)
    para(tf, "Rega  ·  Developer Intern Candidate", size=15, color=WHITE, bold=True, space_after=3, first=True)
    para(tf, "Interview walkthrough  ·  [NEEDS MY INPUT: full name / role / date]",
         size=11, color=MUTED, space_after=0)
    tf = textbox(slide, 1.27, 6.2, 11.5, 0.5)
    para(tf, "LangGraph  ·  DeepSeek / OpenAI / Anthropic / Gemini (auto-detect)  ·  FastAPI  ·  SQLite  ·  sentence-transformers  ·  pytest",
         size=11, color=GREY, space_after=0, first=True)
    notes(slide, (
        "SCHEDULE (30-60s): Introduce yourself and the assessment in one line. "
        "Say the subtitle out loud: 'The core principle is that deterministic code decides; the LLM only extracts and writes.' "
        "Name the three subsystems and the shared core.\n\n"
        "REMEMBER: This is an engineering-decision walkthrough, not a feature demo.\n\n"
        "FOLLOW-UP Q: What does 'deterministic code decides' actually mean?\n"
        "A: Money, security and escalation rules are enforced in Python (thresholds, regex, citation checks). "
        "The model is used for understanding and language, never as the authority on policy."
    ))


def slide_02_problem(prs):
    slide = blank(prs)
    slide_title(slide, "Problem & Objective", kicker="The Problem")
    card(slide, 0.62, 1.35, 5.9, 4.55, "Business requirements", [
        "Handle inbound support email for a cloud reseller (Google Workspace, GCP, NetSuite, JumpCloud, Zoom, Meraki).",
        "Never give an unsafe or invented answer about refunds, money or policy.",
        "Escalate critical issues and policy exceptions to a human.",
        "Avoid replying twice to the same email.",
    ], accent=ACCENT, heading_size=14, body_size=11.5)
    card(slide, 6.82, 1.35, 5.9, 4.55, "Engineering requirements", [
        "Ground every factual claim in approved knowledge-base documents.",
        "Cope with long pages / content beyond the model context window (scraper).",
        "Explicit, testable control flow with an audit trail per email.",
        "Graceful behaviour when the model, a tool or the network fails.",
        "Run offline in CI (no API key required for tests).",
    ], accent=AMBER, heading_size=14, body_size=11.5)
    key_message(slide, "A single LLM call cannot do this: no grounding, no context-window strategy, "
                       "no deterministic policy checks, no idempotency, no audit trail.")
    footer(slide, 2)
    notes(slide, (
        "SCHEDULE (30-60s): Set up the problem in two buckets. Business: answer email safely and escalate exceptions. "
        "Engineering: ground answers, survive long content, keep control flow testable and observable. "
        "Then deliver the punchline about why one prompt is not enough.\n\n"
        "REMEMBER: The hard part is not generating text; it is making correct, safe decisions under uncertainty.\n\n"
        "FOLLOW-UP Q: Why can't you just prompt a big model with all the policy documents?\n"
        "A: Context windows overflow, the model can still hallucinate amounts, and there is no way to guarantee or audit a numeric policy rule. "
        "So we retrieve only relevant chunks and enforce limits in code."
    ))


def slide_03_overview(prs):
    slide = blank(prs)
    slide_title(slide, "Solution Overview", kicker="System Design")
    rect(slide, 0.62, 1.32, 12.1, 0.62, NAVY3, rounded=True, radius=0.12)
    tf = textbox(slide, 0.82, 1.32, 11.7, 0.62, anchor=MSO_ANCHOR.MIDDLE)
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = "core/ shared foundation:  "
    r.font.size = Pt(12); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = ACCENT
    r = p.add_run(); r.text = "config (typed settings)  ·  provider-agnostic LLM client with model/provider failover  ·  embeddings  ·  RAG (PDF index + cache)  ·  structured logging"
    r.font.size = Pt(12); r.font.name = FONT; r.font.color.rgb = LIGHT

    card(slide, 0.62, 2.18, 3.86, 3.5, "Part 1 — Email Agent", [
        "LangGraph state machine (9 nodes).",
        "Triage, precheck, classify, retrieve,",
        "refund guard, draft, verify.",
        "Outcome: auto-reply or human ticket.",
        "SQLite ticketing + idempotency.",
    ], accent=ACCENT, heading_size=13, body_size=10.5)
    card(slide, 4.73, 2.18, 3.86, 3.5, "Part 2 — Scraper", [
        "Deterministic pipeline (not an agent).",
        "fetch \u2192 extract main content \u2192 chunk",
        "\u2192 map-reduce summarize \u2192 length guardrail.",
        "Includes the broken naive baseline",
        "for side-by-side comparison.",
    ], accent=GREEN, heading_size=13, body_size=10.5)
    card(slide, 8.85, 2.18, 3.86, 3.5, "Part 3 — Document Agent", [
        "LangGraph: route \u2192 retrieve \u2192",
        "calculate \u2192 respond.",
        "Grounded chat over one handbook.",
        "Session memory + AST calculator tool.",
        "Refuses questions outside the document.",
    ], accent=AMBER, heading_size=13, body_size=10.5)
    key_message(slide, "End to end: input \u2192 detect/classify \u2192 retrieve ground truth \u2192 deterministic guard \u2192 generate \u2192 validate \u2192 respond or escalate.")
    footer(slide, 3)
    notes(slide, (
        "SCHEDULE (30-60s): Walk left to right. Everything sits on the shared core. "
        "Part 1 is an agent that can hand off to a human; Part 2 is deliberately a plain pipeline; Part 3 is a grounded chat agent. "
        "Close with the common end-to-end shape.\n\n"
        "REMEMBER: One codebase, one config, three different problem shapes \u2014 and I matched the architecture to each shape.\n\n"
        "FOLLOW-UP Q: Why is Part 2 a pipeline if the other two are agents?\n"
        "A: Summarizing a page has a fixed sequence with no branching decisions; adding agentic routing would add cost and failure modes with no benefit. "
        "Use an agent only when decisions actually branch."
    ))


def slide_04_architecture(prs):
    slide = blank(prs)
    slide_title(slide, "Architecture", kicker="System Design")

    rect(slide, 0.62, 1.3, 12.1, 0.5, NAVY3, rounded=True, radius=0.14)
    tf = textbox(slide, 0.8, 1.3, 11.7, 0.5, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, "Interfaces:  React web UI (Part 1)   ·   FastAPI REST API   ·   CLI",
         size=11.5, color=LIGHT, space_after=0, first=True)

    card(slide, 0.62, 1.98, 3.86, 2.62, "Part 1  Email Agent", [
        "triage \u2192 precheck \u2192 classify \u2192 retrieve",
        "\u2192 refund_guard \u2192 draft \u2192 verify",
        "\u2192 auto_reply  |  route_human",
    ], accent=ACCENT, heading_size=12.5, body_size=10)
    card(slide, 4.73, 1.98, 3.86, 2.62, "Part 2  Scraper", [
        "fetcher (timeouts, size cap, retry)",
        "extractor (semantic / density)",
        "chunker \u2192 map-reduce \u2192 guardrail",
    ], accent=GREEN, heading_size=12.5, body_size=10)
    card(slide, 8.85, 1.98, 3.86, 2.62, "Part 3  Document Agent", [
        "route \u2192 retrieve \u2192 calculate \u2192 respond",
        "router picks tools; AST calculator",
        "session memory (turns + durable facts)",
    ], accent=AMBER, heading_size=12.5, body_size=10)

    rect(slide, 0.62, 4.72, 12.1, 0.62, NAVY3, rounded=True, radius=0.12)
    tf = textbox(slide, 0.82, 4.72, 11.7, 0.62, anchor=MSO_ANCHOR.MIDDLE)
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = "Shared state:  "
    r.font.size = Pt(11.5); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = ACCENT
    r = p.add_run(); r.text = "SQLite (tickets, contacts, idempotency, dead-letter)  ·  session JSON  ·  KB index cache  ·  SMTP / IMAP adapters"
    r.font.size = Pt(11.5); r.font.name = FONT; r.font.color.rgb = LIGHT

    rect(slide, 0.62, 5.5, 12.1, 0.82, RGBColor(0x3A, 0x1E, 0x0A), rounded=True, radius=0.1)
    tf = textbox(slide, 0.85, 5.5, 11.6, 0.82, anchor=MSO_ANCHOR.MIDDLE)
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = "Deterministic control points:  "
    r.font.size = Pt(11.5); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = AMBER
    r = p.add_run(); r.text = "critical-signal detection  ·  refund thresholds in Python  ·  citation existence check  ·  confidence floors  ·  fail-closed node wrapper  ·  SSRF guard"
    r.font.size = Pt(11.5); r.font.name = FONT; r.font.color.rgb = LIGHT

    footer(slide, 4)
    notes(slide, (
        "SCHEDULE (45-60s): Trace one arrow: UI/API calls the shared core, which builds a model client and a knowledge base. "
        "Part 1 can stop at any node and emit a human ticket (human-in-the-loop). "
        "Point at the amber bar: these are the places where Python, not the model, makes the decision.\n\n"
        "REMEMBER: The architecture separates 'what the model perceives' from 'what the system is allowed to do'.\n\n"
        "FOLLOW-UP Q: Where exactly is the human-in-the-loop?\n"
        "A: In Part 1, any failed or uncertain check routes to route_human, which stores a ticket and sends an acknowledgement. "
        "A human can reply from the web UI, guarded so an already-resolved ticket cannot be answered twice."
    ))


def slide_05_state_machine(prs):
    slide = blank(prs)
    slide_title(slide, "Agentic Workflow / State Machine", kicker="Agent Design")
    tf = textbox(slide, 0.62, 1.28, 12.1, 0.3)
    para(tf, "Part 1 \u2014 LangGraph state machine", size=12.5, color=ACCENT, bold=True, space_after=0, first=True)

    nodes = ["triage", "precheck", "classify", "retrieve", "refund_guard", "draft_reply", "verify", "auto_reply"]
    x = 0.62
    bw = 1.32
    gap = 0.16
    top = 1.72
    for i, name in enumerate(nodes):
        fill = ACCENT_D if name in ("refund_guard", "verify") else NAVY3
        rect(slide, x, top, bw, 0.56, fill, rounded=True, radius=0.18)
        tfn = textbox(slide, x + 0.03, top, bw - 0.06, 0.56, anchor=MSO_ANCHOR.MIDDLE)
        para(tfn, name, size=9, color=WHITE, bold=True, align=PP_ALIGN.CENTER, space_after=0, first=True)
        if i < len(nodes) - 1:
            ar = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + bw + 0.005), Inches(top + 0.19),
                                        Inches(gap - 0.01), Inches(0.18))
            ar.fill.solid(); ar.fill.fore_color.rgb = ACCENT; ar.line.fill.background(); ar.shadow.inherit = False
        x += bw + gap

    rect(slide, 4.35, 2.55, 3.2, 0.5, RGBColor(0x3A, 0x1E, 0x0A), rounded=True, radius=0.16)
    tfn = textbox(slide, 4.42, 2.55, 3.06, 0.5, anchor=MSO_ANCHOR.MIDDLE)
    para(tfn, "route_human  (ticket + acknowledgement)", size=9, color=AMBER, bold=True, align=PP_ALIGN.CENTER, space_after=0, first=True)
    for cx in (1.28, 3.0, 4.72, 6.44, 8.16, 9.88, 11.6):
        ar = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(cx - 0.06), Inches(2.28), Inches(0.12), Inches(0.27))
        ar.fill.solid(); ar.fill.fore_color.rgb = AMBER; ar.line.fill.background(); ar.shadow.inherit = False

    tf = textbox(slide, 0.62, 3.18, 12.1, 0.3)
    para(tf, "Every node can exit to route_human on failure or low confidence (fail-closed).", size=10, color=GREY, space_after=0, first=True)

    card(slide, 0.62, 3.6, 5.9, 2.75, "Why this is agentic (not a script)", [
        "Conditional routing: the next node depends on state.",
        "Tool/decision selection and confidence gating.",
        "Self-check + one bounded retry: verify \u2192 redraft \u2192 escalate.",
        "Explicit termination: auto_reply, route_human, or ignored.",
        "State (TicketState) is accumulated and traced per step.",
    ], accent=ACCENT, heading_size=13, body_size=11)
    card(slide, 6.82, 3.6, 5.9, 2.75, "Part 3 \u2014 second, smaller machine", [
        "route \u2192 (retrieve) \u2192 (calculate) \u2192 respond.",
        "Router returns a typed decision, not free text.",
        "Retrieve only for handbook facts; calculate only for real arithmetic.",
        "Memory questions and greetings call no tool at all.",
        "Note: Part 2 is intentionally linear \u2014 no branching to justify.",
    ], accent=AMBER, heading_size=13, body_size=11)
    footer(slide, 5)
    notes(slide, (
        "SCHEDULE (45-60s): Walk the eight nodes once, then point at the redraft loop and the amber exit. "
        "Emphasize the three properties that make it agentic: branching, self-verification, and termination/escalation.\n\n"
        "REMEMBER: 'Agentic' here means controlled branching with an escape hatch \u2014 not unbounded autonomy.\n\n"
        "FOLLOW-UP Q: Isn't a verify-then-retry loop dangerous \u2014 it could loop forever?\n"
        "A: It is bounded: MAX_REDRAFT_ATTEMPTS defaults to 1, then the email escalates. The retry also receives the exact verifier feedback."
    ))


def slide_06_guardrails(prs):
    slide = blank(prs)
    slide_title(slide, "Critical Guardrails & Safety", kicker="Safety & Control")
    layers = [
        ("1  Triage", "Drops automated mail (no-reply, mailing lists, own address) before any LLM call \u2014 prevents reply loops.", ACCENT),
        ("2  Precheck", "Regex rules + embedding-anchor similarity (with a contrastive margin vs benign anchors) detect data loss, outages, breaches. Also flags frequent contacts (>3 in 7 days).", RED),
        ("3  Classify", "Model labels categories; any top confidence below 0.6 escalates instead of guessing.", ACCENT),
        ("4  Retrieve", "If no KB chunk clears RETRIEVAL_MIN_SCORE (0.30), escalate \u2014 never invent context.", GREEN),
        ("5  Refund guard", "Model extracts amount/date/product; Python enforces > USD 500, > 90 days, NetSuite review, and unknown product.", AMBER),
        ("6  Verify", "Citation IDs must exist; an independent fact-check flags unsupported claims; one redraft, then escalate.", ACCENT_D),
    ]
    y = 1.3
    for name, desc, color in layers:
        rect(slide, 0.62, y, 12.1, 0.66, NAVY2, rounded=True, radius=0.08)
        rect(slide, 0.62, y, 0.09, 0.66, color)
        tf = textbox(slide, 0.85, y, 2.15, 0.66, anchor=MSO_ANCHOR.MIDDLE)
        para(tf, name, size=12, color=WHITE, bold=True, space_after=0, first=True)
        tf = textbox(slide, 3.05, y, 9.5, 0.66, anchor=MSO_ANCHOR.MIDDLE)
        para(tf, desc, size=10.5, color=LIGHT, space_after=0, line_spacing=0.98, first=True)
        y += 0.72
    key_message(slide, "The AI suggests; deterministic code decides. Every uncertain path fails closed to a human.")
    footer(slide, 6)
    notes(slide, (
        "SCHEDULE (45-60s): This is the safety story. Precheck runs before any model call and combines fast regex with semantic similarity, "
        "with a benign margin so normal requests do not trigger it. The refund guard is the clearest example: the model only extracts facts, "
        "Python compares them to limits.\n\n"
        "REMEMBER: Safety is layered, and the last layer is always escalation.\n\n"
        "FOLLOW-UP Q: Why combine regex and embeddings instead of one?\n"
        "A: Regex is precise and cheap but brittle to paraphrases; embeddings catch paraphrases but can false-positive. "
        "Using both, with the semantic layer requiring a margin over benign anchors, raises recall while keeping false positives manageable \u2014 and false positives only cost a human review, not a wrong reply."
    ))


def slide_07_retrieval(prs):
    slide = blank(prs)
    slide_title(slide, "Knowledge Retrieval / Grounded Responses", kicker="Grounding")
    steps = ["Retrieve", "Context", "Generate", "Validate"]
    x = 0.62
    for i, s in enumerate(steps):
        shp = slide.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(x), Inches(1.35), Inches(2.35), Inches(0.7))
        shp.fill.solid(); shp.fill.fore_color.rgb = NAVY3 if i % 2 == 0 else NAVY2
        shp.line.fill.background(); shp.shadow.inherit = False
        tf = shp.text_frame; tf.word_wrap = True
        para(tf, s, size=13, color=WHITE, bold=True, align=PP_ALIGN.CENTER, space_after=0, first=True)
        x += 2.6
    rect(slide, 0.62, 2.2, 5.9, 4.1, NAVY2, rounded=True, radius=0.05)
    tf = textbox(slide, 0.82, 2.34, 5.5, 3.85)
    para(tf, "How grounding works", size=13.5, color=WHITE, bold=True, space_after=7, first=True)
    for t in [
        "PDFs are parsed, split into section-aware chunks, embedded, and cached by a fingerprint.",
        "A query is expanded into several standalone sub-queries; results are merged and floored by a minimum score.",
        "The draft may only use retrieved excerpts and must cite the document IDs it used.",
        "A citation check rejects invented IDs; a separate fact-check rejects unsupported claims.",
    ]:
        para(tf, t, size=10.5, color=LIGHT, bullet="\u2013", space_after=5, line_spacing=1.0)
    card(slide, 6.82, 2.2, 5.9, 4.1, "When the KB cannot answer", [
        "Nothing clears the score floor \u2192 escalate, no draft.",
        "Context retrieved but incomplete \u2192 the draft marks itself not fully answerable \u2192 escalate.",
        "Part 3 is stricter: if the handbook does not contain the fact, it says so plainly and sets fully_answerable=false.",
        "No silent guessing, no filling gaps with general knowledge.",
    ], accent=AMBER, heading_size=13.5, body_size=11)
    key_message(slide, "Grounding is a control, not a prompt trick: retrieve \u2192 constrain \u2192 cite \u2192 verify \u2192 escalate if unsure.")
    footer(slide, 7)
    notes(slide, (
        "SCHEDULE (45-60s): Explain the four-step flow and the two independent checks. "
        "Stress the escape path: if the knowledge base does not clear the floor, the agent escalates rather than answering.\n\n"
        "REMEMBER: A confident-sounding answer is not the goal; a grounded, cited answer is.\n\n"
        "FOLLOW-UP Q: What if two documents conflict?\n"
        "A: Retrieval returns both, but the policy layer prefers the refund policy for refund questions, and anything NetSuite-related or above threshold goes to a human. "
        "The system never silently chooses between conflicting policy clauses."
    ))


def slide_08_scraper(prs):
    slide = blank(prs)
    slide_title(slide, "Technical Implementation \u2014 Scraper (Part 2)", kicker="Implementation")
    card(slide, 0.62, 1.32, 5.9, 2.55, "Bottleneck in the naive baseline", [
        "No timeout and no status/content-type checks.",
        "get_text() pulls scripts, nav, ads and boilerplate.",
        "The whole page goes to the model in one call.",
        "Large pages overflow the context window and fail.",
    ], accent=RED, heading_size=13, body_size=11)
    card(slide, 6.82, 1.32, 5.9, 2.55, "The fix (fixed pipeline)", [
        "Fetch: connect/read timeouts, byte cap, content-type check, retry with backoff, optional stealth-browser fallback.",
        "Extract: semantic container (article/main) or densest text block, noise removed.",
        "Chunk: token-aware recursive split with overlap.",
        "Summarize: map-reduce; final length guardrail.",
    ], accent=GREEN, heading_size=13, body_size=10.5)
    rect(slide, 0.62, 4.02, 12.1, 1.0, NAVY2, rounded=True, radius=0.08)
    tf = textbox(slide, 0.85, 4.12, 11.6, 0.82)
    para(tf, "Length guardrail: measure word count \u2192 if outside budget, ask for a rewrite quoting the real count \u2192 if still out, truncate at a sentence boundary.",
         size=10.5, color=LIGHT, bullet="\u2013", space_after=3, first=True)
    para(tf, "Observed on a demo page (mock model): fetched 244,683 bytes \u2192 15,986 chars sent to the model (93% smaller), 30% of page text dropped as chrome, guardrail enforced by retry.",
         size=10.5, color=GREY, bullet="\u2013", space_after=0)
    key_message(slide, "Don't ask the model to fix a data problem: fetch safely, extract the real content, chunk to fit, then constrain the output.")
    footer(slide, 8)
    notes(slide, (
        "SCHEDULE (45-60s): Show the naive failure first, then the four-step fix. "
        "The length guardrail is the interesting bit: it measures, asks the model to rewrite while quoting the actual count, and only truncates as a last resort. "
        "Numbers shown are from a mock-model demo run, so treat them as plumbing evidence, not model quality.\n\n"
        "REMEMBER: The bottleneck was input size and noise, not model capability \u2014 so the fix is upstream of the model.\n\n"
        "FOLLOW-UP Q: Why not just use a bigger context window?\n"
        "A: Bigger windows are costly and still degrade with noise. Extraction plus chunking is cheaper, faster, and keeps the important facts. "
        "Map-reduce also gives a bounded, predictable cost per page."
    ))


def slide_09_memory_tools(prs):
    slide = blank(prs)
    slide_title(slide, "Memory & Tool Calling (Part 3)", kicker="Memory & Tools")
    card(slide, 0.62, 1.35, 5.9, 4.45, "Conversation memory", [
        "Short-term: a rolling window of recent turns (default 6 turns).",
        "Long-term: durable facts the user states \u2014 name, company, plan, seat count.",
        "Saved per session as JSON (session id is normalised to prevent path abuse).",
        "Facts and history are injected as prompt context on the next turn.",
        "Clear failure mode: only what the user said is stored; no inferred facts.",
    ], accent=ACCENT, heading_size=13.5, body_size=11)
    card(slide, 6.82, 1.35, 5.9, 2.05, "The router decides, code executes", [
        "Router returns a typed decision: needs_document, needs_calculation, queries, expression, memory_updates.",
        "Model chooses; the graph then calls the tool.",
    ], accent=AMBER, heading_size=13, body_size=10.5)
    card(slide, 6.82, 3.55, 2.9, 2.25, "document_search", [
        "Hybrid multi-query retrieval over the handbook.",
        "Returns labelled sections for citation.",
    ], accent=GREEN, heading_size=11.5, body_size=9.8)
    card(slide, 9.82, 3.55, 2.9, 2.25, "calculator", [
        "AST whitelist \u2014 never eval().",
        "Guards division by zero, huge exponents, NaN/inf.",
    ], accent=ACCENT, heading_size=11.5, body_size=9.8)
    key_message(slide, "A tool is called only when it is needed: greetings and memory questions trigger no tool at all.")
    footer(slide, 9)
    notes(slide, (
        "SCHEDULE (45-60s): Separate two ideas: memory (what we know about the user) and tools (what the agent can do). "
        "The router's job is the decision; the graph's job is execution. Point out the calculator uses an AST whitelist, not eval.\n\n"
        "REMEMBER: Over-calling tools is a real failure mode \u2014 it adds latency and can inject unnecessary context.\n\n"
        "FOLLOW-UP Q: How does the agent know not to search the handbook for 'what's my name'?\n"
        "A: The router is instructed and few-shot-prompted to set needs_document=false for memory and small-talk turns; that decision is explicit and shown in the trace, and demo runs confirm no tool is called."
    ))


def slide_10_reliability(prs):
    slide = blank(prs)
    slide_title(slide, "Reliability & Failure Handling", kicker="Reliability")
    data = [
        ["Failure", "Detection", "Response"],
        ["Model quota / unavailable", "Error classified as quota or unavailable", "Fail over to the next configured model; cooldown the blocked one"],
        ["Any node raises", "try/except wrapper around every node", "Fail closed: set route_to_human, record the error in the trace"],
        ["Invalid / missing citation", "Citation IDs checked against retrieved chunks", "Bounded redraft once, then escalate"],
        ["Unsupported claims", "Independent fact-check of the draft", "Bounded redraft once, then escalate"],
        ["No KB context", "Minimum-score floor on retrieval", "Escalate; do not draft"],
        ["Duplicate delivery", "Message claim + attempt counter", "Idempotent skip; dead-letter after retries"],
        ["Bad HTTP / oversize page", "Timeout, status, content-type, size checks", "Retry with backoff, then surface an error (no partial summary)"],
        ["Private / SSRF URL", "DNS resolves to a non-global address", "Refuse the request"],
        ["Tool error", "ToolResult(ok=false)", "Say it could not compute; keep answering the rest"],
    ]
    add_table(slide, data, 0.62, 1.3, 12.1, 5.0, col_ratios=[2.0, 3.1, 4.2], font=9.3, header_font=10.2, row_h=0.48)
    footer(slide, 10)
    notes(slide, (
        "SCHEDULE (45-60s): Cover the table in three groups: model/network failures (failover, retry), logic/uncertainty failures (fail closed, redraft then escalate), "
        "and delivery failures (idempotent claim, dead-letter).\n\n"
        "REMEMBER: There is no silent failure mode \u2014 every failure is either retried, escalated, or surfaced as an explicit message.\n\n"
        "FOLLOW-UP Q: What if the same email is delivered twice at the same moment?\n"
        "A: claim_message runs inside BEGIN IMMEDIATE and records a message_attempts row, so only one worker wins the claim; the other skips. "
        "A TTL handles stale in-progress claims, and repeated failures become dead-letters for inspection."
    ))


def slide_11_testing(prs):
    slide = blank(prs)
    slide_title(slide, "Testing & Evaluation", kicker="Test & Evaluation")
    data = [
        ["Area", "Representative tests", "Functions"],
        ["Email pipeline", "graph, ticketing, entities, verifier, precheck, automated_sender", "72"],
        ["Scraper", "chunker, extractor, guardrail, pipeline, web", "57"],
        ["Document agent", "agent graph, tools, memory, web", "47"],
        ["Shared core", "rag, llm failover, metrics, poller, web API", "43"],
        ["Reliability", "smtp sender, fetch jobs", "18"],
    ]
    add_table(slide, data, 0.62, 1.3, 7.5, 3.6, col_ratios=[1.5, 5.0, 0.9], font=10, header_font=10.5, row_h=0.62)
    card(slide, 8.32, 1.3, 4.4, 3.6, "Evaluation in the running system", [
        "/api/metrics: auto-resolution rate, route reasons, latency p50/p95, node errors, redrafts.",
        "/api/dead-letters for failed messages.",
        "calibrate_precheck.py tunes the semantic threshold.",
        "smtp_e2e_check.py exercises real delivery.",
        "267 test functions total, fully offline.",
    ], accent=GREEN, heading_size=12.5, body_size=10.2)
    key_message(slide, "Deterministic mocks make the non-deterministic parts testable: we test decisions and guardrails, not model prose.")
    footer(slide, 11)
    notes(slide, (
        "SCHEDULE (45-60s): Explain the strategy: a mock LLM and a hashing embedder make the whole suite offline and deterministic, "
        "so CI runs without an API key. We assert on control flow, guardrails and tool decisions. "
        "Then mention the in-app metrics for ongoing evaluation. Counts are from static analysis of the test files.\n\n"
        "REMEMBER: We do not try to unit-test the model's wording; we test that the system reacts correctly to whatever the model returns.\n\n"
        "FOLLOW-UP Q: How do you test something non-deterministic?\n"
        "A: You isolate it. The LLM sits behind a small interface; tests inject a mock that returns fixed or adversarial outputs, "
        "so we can assert escalation, redraft and error paths precisely. Real-model quality is a separate, offline evaluation."
    ))


def slide_12_tradeoffs(prs):
    slide = blank(prs)
    slide_title(slide, "Trade-offs & Design Decisions", kicker="Engineering Judgement")
    data = [
        ["Trade-off", "Decision", "Why", "Downside / when to revisit"],
        ["LLM flexibility vs deterministic rules", "Rules for money/security; LLM for language", "Auditable, testable, safe", "Rules need maintenance; revisit as policy grows"],
        ["Single agent vs multiple agents", "Single graph per task", "Simpler, one trace, fewer failure modes", "Multi-agent only if roles genuinely differ"],
        ["LangGraph vs raw API calls", "LangGraph for branching tasks; plain pipeline for the scraper", "Explicit states and conditional edges", "Framework weight; raw code is fine when linear"],
        ["Full automation vs human-in-the-loop", "Escalate critical / uncertain cases", "Some decisions should not be automated", "Human load grows with false positives"],
        ["Long context vs retrieval + chunking", "Retrieve only relevant chunks", "Cheaper, faster, more accurate", "Retrieval misses hurt; needs good chunking/ranking"],
        ["More reasoning steps vs latency/cost", "Bounded retries and few calls per item", "Predictable cost and latency", "Less adaptive; revisit for hard cases"],
    ]
    add_table(slide, data, 0.62, 1.28, 12.1, 5.1, col_ratios=[2.1, 2.4, 2.5, 3.0], font=8.6, header_font=9.6, row_h=0.72)
    footer(slide, 12)
    notes(slide, (
        "SCHEDULE (60s): Do not read the table. Pick two rows and go deep \u2014 the rules-vs-LLM split and the human-in-the-loop decision. "
        "For each, state the decision, the reason, and the downside honestly.\n\n"
        "REMEMBER: A good engineer names the downside of their own choice; that is what makes the design credible.\n\n"
        "FOLLOW-UP Q: Which trade-off was hardest?\n"
        "A: Drawing the line on what the model may decide. Too strict and it is just a rules engine; too loose and money/security outcomes become non-deterministic. "
        "I chose to keep extraction and language in the model, and all consequential decisions in code."
    ))


def slide_13_observability(prs):
    slide = blank(prs)
    slide_title(slide, "Observability / AgentOps", kicker="Agent Operations")
    card(slide, 0.62, 1.32, 3.86, 2.35, "What we log", [
        "Structured logs via structlog (JSON optional).",
        "A trace_id bound to every step of one email.",
        "Node outcomes, evidence, elapsed_ms.",
    ], accent=ACCENT, heading_size=12.5, body_size=10.4)
    card(slide, 4.73, 1.32, 3.86, 2.35, "Decision tracing", [
        "Every node emits a TraceEvent.",
        "Ticket payload stores the full trace.",
        "Model switches and retries are logged.",
    ], accent=GREEN, heading_size=12.5, body_size=10.4)
    card(slide, 8.85, 1.32, 3.86, 2.35, "Metrics & errors", [
        "/api/metrics: auto-resolution rate, route reasons, p50/p95 latency, node errors, redrafts.",
        "/api/dead-letters for failed messages.",
    ], accent=AMBER, heading_size=12.5, body_size=10.4)
    rect(slide, 0.62, 3.85, 12.1, 2.45, NAVY2, rounded=True, radius=0.05)
    tf = textbox(slide, 0.85, 3.99, 11.6, 2.2)
    para(tf, "Debugging an incorrect answer", size=13, color=WHITE, bold=True, space_after=6, first=True)
    para(tf, "1. Replay the trace_id and read the node trace in order.", size=10.5, color=LIGHT, bullet="\u2013", space_after=3)
    para(tf, "2. Check what was retrieved and the scores \u2014 was the right context present?", size=10.5, color=LIGHT, bullet="\u2013", space_after=3)
    para(tf, "3. Check the classification and confidence \u2014 was the route reasonable?", size=10.5, color=LIGHT, bullet="\u2013", space_after=3)
    para(tf, "4. Check citations and the verification result \u2014 where did the claim enter?", size=10.5, color=LIGHT, bullet="\u2013", space_after=3)
    para(tf, "Gap: per-call token/cost accounting is not implemented yet \u2014 Proposed next step.", size=10.5, color=AMBER, bullet="\u2013", space_after=0)
    footer(slide, 13)
    notes(slide, (
        "SCHEDULE (45-60s): Explain that the same structure that makes it testable makes it debuggable. "
        "Given a wrong answer, we replay the trace and localise the fault: retrieval, classification, or generation. "
        "Be explicit that cost/token tracking is a gap.\n\n"
        "REMEMBER: Observability is designed in from the start via per-node traces, not bolted on afterwards.\n\n"
        "FOLLOW-UP Q: How would you evaluate the agent after deployment?\n"
        "A: Track the auto-resolution rate against escalation reasons, watch latency percentiles and node error rates, "
        "and sample escalated tickets to check whether they should have been automated. Threshold calibration uses the same signal."
    ))


def slide_14_limitations(prs):
    slide = blank(prs)
    slide_title(slide, "Limitations & Future Improvements", kicker="Roadmap")
    card(slide, 0.62, 1.35, 5.9, 4.45, "Honest current limitations", [
        "Tests and demos run on a mock model; real provider output quality is not asserted here.",
        "Thresholds are sensible defaults, not yet calibrated on real traffic.",
        "Currency conversion uses a static FX table.",
        "SQLite is single-file; the IMAP poller runs in-process.",
        "Session memory is stored unencrypted.",
        "SSRF check resolves DNS once (residual DNS-rebinding).",
        "No token/cost accounting.",
    ], accent=RED, heading_size=13.5, body_size=10.8)
    card(slide, 6.82, 1.35, 5.9, 4.45, "Proposed next steps", [
        "Golden-set evaluation against the real model; calibrate thresholds from it.",
        "Add retrieval re-ranking to reduce missed context.",
        "Move ingestion to a queue (e.g. Redis/Celery) and the DB to Postgres.",
        "Add token/cost metrics and budget alerts.",
        "Encrypt sessions and define retention; pin resolved IPs.",
        "Per-tenant policies instead of global thresholds.",
    ], accent=GREEN, heading_size=13.5, body_size=10.8)
    key_message(slide, "I would rather state these limits myself than have a reviewer find them.")
    footer(slide, 14)
    notes(slide, (
        "SCHEDULE (45-60s): Be candid and specific. Distinguish what is implemented from what is proposed. "
        "Do not say 'improve accuracy' \u2014 name the mechanism: calibration, re-ranking, queueing, cost metrics.\n\n"
        "REMEMBER: Naming real limitations is a strength, not a weakness; it signals production awareness.\n\n"
        "FOLLOW-UP Q: What is the single most important next step?\n"
        "A: A golden-set evaluation against the real model, because it turns every threshold and prompt choice from a guess into a measured decision \u2014 "
        "and it will drive the other improvements."
    ))


def slide_15_qa(prs):
    slide = blank(prs)
    slide_title(slide, "Reviewer Q&A Preparation", kicker="Interview Preparation")
    data = [
        ["Question", "Short answer"],
        ["Why is this an agent, not a pipeline?", "Branching state machine with tool selection, self-check/retry and explicit escalation."],
        ["Why not let the LLM judge criticality?", "Safety decisions must be deterministic and testable; regex + embeddings + code thresholds."],
        ["How do you prevent hallucinations?", "Ground in retrieved KB, force citations, validate IDs, independent fact-check, else escalate."],
        ["Model returns an invalid classification?", "Schema-validated output; low confidence escalates; node errors fail closed."],
        ["KB has no answer?", "Score floor \u2192 escalate; drafts mark themselves not fully answerable."],
        ["How do you test non-determinism?", "Mock LLM behind an interface; test control flow and guardrails, not prose."],
        ["How do you control latency/cost?", "Few calls per item, temperature 0, bounded retries, top-k retrieval; cost metrics proposed."],
        ["How would it scale?", "Idempotent claim + dead-letter; move to Postgres/queue and horizontal workers."],
        ["What if a tool fails?", "ToolResult(ok=false); answer states it could not compute."],
        ["Why human-in-the-loop?", "Policy, money and security exceptions should not be auto-decided."],
    ]
    add_table(slide, data, 0.62, 1.28, 12.1, 5.1, col_ratios=[3.0, 8.0], font=9.6, header_font=10.4, row_h=0.5)
    footer(slide, 15)
    notes(slide, (
        "SCHEDULE (30-45s): Do not read this slide. Use it as a map: say 'I prepared answers to the likely hard questions' and then offer to go deeper on any row. "
        "The full set of 20 questions with answers is in the speaker notes appendix.\n\n"
        "REMEMBER: Confidence comes from having a concrete, honest answer for each row \u2014 not from avoiding the question.\n\n"
        "FOLLOW-UP Q: Which of these is your weakest answer?\n"
        "A: Scaling to thousands of emails, because the current storage and poller are single-node. I have a concrete plan (queue + Postgres + horizontal workers) "
        "but I have not implemented or load-tested it yet."
    ))


def slide_16_closing(prs):
    slide = blank(prs)
    slide_title(slide, "Key Takeaways", kicker="Summary")
    principles = [
        ("Controlled autonomy", "The model proposes; deterministic code authorizes every consequential action."),
        ("Grounded generation", "Answers come from retrieved documents, carry citations, and are independently verified."),
        ("Reliability by design", "Fail-closed nodes, bounded retries, idempotent processing, model failover."),
        ("Testability & observability", "267 offline tests, per-node traces, and metrics that make behaviour explainable."),
    ]
    y = 1.4
    for title, desc in principles:
        rect(slide, 0.62, y, 12.1, 0.92, NAVY2, rounded=True, radius=0.07)
        rect(slide, 0.62, y, 0.09, 0.92, ACCENT)
        tf = textbox(slide, 0.9, y, 11.6, 0.92, anchor=MSO_ANCHOR.MIDDLE)
        p = tf.paragraphs[0]
        r = p.add_run(); r.text = title + "  \u2014  "
        r.font.size = Pt(14); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = WHITE
        r = p.add_run(); r.text = desc
        r.font.size = Pt(12.5); r.font.name = FONT; r.font.color.rgb = LIGHT
        y += 1.02
    rect(slide, 0.62, 5.6, 12.1, 1.0, NAVY3, rounded=True, radius=0.08)
    tf = textbox(slide, 0.9, 5.6, 11.5, 1.0, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, "\u201cI optimized for trustworthy behaviour under uncertainty \u2014 not for maximum autonomy.\u201d",
         size=15, color=ACCENT, italic=True, align=PP_ALIGN.CENTER, space_after=0, first=True)
    footer(slide, 16)
    notes(slide, (
        "SCHEDULE (30-45s): Close on the four principles. Deliver the closing line slowly. "
        "Then invite the reviewer to pick any decision to drill into.\n\n"
        "REMEMBER: The throughline is trust: every design choice exists to make the system's behaviour predictable and safe.\n\n"
        "FOLLOW-UP Q: What would you change if you had more time?\n"
        "A: Run a golden-set evaluation against the real model to calibrate thresholds, then add retrieval re-ranking and token/cost metrics \u2014 "
        "the improvements that turn tuning from guesswork into measurement."
    ))


def slide_a1_tests(prs):
    slide = blank(prs)
    slide_title(slide, "Appendix \u2014 Test Coverage Matrix", kicker="Appendix A")
    data = [
        ["Test file", "Focus", "Count"],
        ["test_graph.py", "Part 1 state transitions, escalation, redraft", "21"],
        ["test_web_api.py", "Part 1 REST endpoints + reply guards", "17"],
        ["test_ticketing.py", "Idempotency, claims, dead-letters", "16"],
        ["test_part3_agent.py", "Route/retrieve/calculate/respond", "15"],
        ["test_part2_pipeline.py", "End-to-end scraper pipeline", "15"],
        ["test_part2_extractor.py", "Content extraction (semantic/density)", "13"],
        ["test_part3_memory.py", "Window, durable facts, persistence", "13"],
        ["test_automated_sender.py", "Triage of automated mail", "11"],
    ]
    add_table(slide, data, 0.62, 1.3, 12.1, 5.0, col_ratios=[3.0, 7.0, 1.0], font=10.2, header_font=11, row_h=0.5)
    tf = textbox(slide, 0.62, 6.45, 12.1, 0.4)
    para(tf, "267 test functions across 22 files; the remaining files cover precheck, entities, verifier, RAG, failover, metrics, poller, SMTP, fetch jobs and Part 2/3 web + tools.",
         size=9.5, color=GREY, space_after=0, first=True)
    footer(slide, "A1")
    notes(slide, "Reference slide. Use only if the reviewer asks for test detail. Counts come from a static count of test functions.")


def slide_a2_config(prs):
    slide = blank(prs)
    slide_title(slide, "Appendix \u2014 Configurable Behaviour (defaults)", kicker="Appendix B")
    data = [
        ["Setting", "Default", "Meaning"],
        ["SEMANTIC_PRECHECK_THRESHOLD", "0.45", "Semantic critical-signal sensitivity"],
        ["CLASSIFICATION_CONFIDENCE_THRESHOLD", "0.6", "Below this, escalate instead of answering"],
        ["RETRIEVAL_MIN_SCORE / TOP_K", "0.30 / 8", "Grounding floor and number of chunks"],
        ["REFUND_AMOUNT_THRESHOLD_USD", "500", "Escalate refunds above this amount"],
        ["REFUND_AGE_DAYS_THRESHOLD", "90", "Escalate older purchases"],
        ["CONTACT_FREQUENCY_THRESHOLD / WINDOW", "3 / 7 days", "Frequent-contact escalation"],
        ["MAX_REDRAFT_ATTEMPTS", "1", "Bounded self-correction"],
        ["MAX_MESSAGE_ATTEMPTS", "3", "Retries before dead-letter"],
        ["MEMORY_WINDOW_TURNS / MAX_FACTS", "6 / 25", "Part 3 memory limits"],
    ]
    add_table(slide, data, 0.62, 1.3, 12.1, 5.2, col_ratios=[4.0, 1.8, 5.2], font=10, header_font=10.8, row_h=0.5)
    footer(slide, "A2")
    notes(slide, "Reference slide. All values come from core/config.py defaults and .env.example.")


def slide_a3_verify(prs):
    slide = blank(prs)
    slide_title(slide, "Appendix \u2014 Claims to Verify Before Presenting", kicker="Appendix C")
    items = [
        "Real-model quality: were the three parts ever run end-to-end against a live provider (DeepSeek/OpenAI/Anthropic/Gemini), or only in mock mode?",
        "Confirm the configured provider model names exist and are reachable in your environment.",
        "Test pass rate: only the number of test functions is counted here; run the suite and record the pass/fail result.",
        "Demo metrics (latency, cosine scores, byte counts) were produced in mock mode and are plumbing evidence, not model quality.",
        "Whether camoufox was actually installed and its fallback exercised, or left disabled.",
        "Whether IMAP/SMTP credentials in .env point to a real mailbox used for a live end-to-end demo.",
        "Confirm your name, role and the official assessment title for the title slide.",
    ]
    tf = textbox(slide, 0.62, 1.35, 12.1, 5.4)
    for i, item in enumerate(items):
        para(tf, item, size=12.5, color=LIGHT, bullet="\u25A1", space_after=10, line_spacing=1.05, first=(i == 0))
    footer(slide, "A3")
    notes(slide, "Private checklist. Resolve every item and delete this slide before the real interview.")


# ----------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------
def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    slide_01_title(prs)
    slide_02_problem(prs)
    slide_03_overview(prs)
    slide_04_architecture(prs)
    slide_05_state_machine(prs)
    slide_06_guardrails(prs)
    slide_07_retrieval(prs)
    slide_08_scraper(prs)
    slide_09_memory_tools(prs)
    slide_10_reliability(prs)
    slide_11_testing(prs)
    slide_12_tradeoffs(prs)
    slide_13_observability(prs)
    slide_14_limitations(prs)
    slide_15_qa(prs)
    slide_16_closing(prs)
    slide_a1_tests(prs)
    slide_a2_config(prs)
    slide_a3_verify(prs)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PATH))
    print(f"wrote {OUT_PATH} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
