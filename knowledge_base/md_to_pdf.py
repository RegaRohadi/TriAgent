import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable,
    ListItem, HRFlowable,
)

SRC_DIR = Path(__file__).parent / "markdown"
OUT_DIR = Path(__file__).parent / "pdf"
OUT_DIR.mkdir(exist_ok=True)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], spaceBefore=12, spaceAfter=8))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=10, spaceAfter=6))
styles.add(ParagraphStyle("Body", parent=styles["BodyText"], spaceAfter=6, leading=14))
styles.add(ParagraphStyle("Meta", parent=styles["BodyText"], textColor=colors.grey, fontSize=9, leading=12))
styles.add(ParagraphStyle("Quote", parent=styles["BodyText"], textColor=colors.HexColor("#444444"),
                           leftIndent=14, fontName="Helvetica-Oblique", spaceAfter=6))

def inline(text):
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text

def parse_table(lines):
    rows = [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in lines
        if not re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$", line.strip())
    ]
    return rows

def is_block_start(line):
    return (
        not line.strip()
        or line.startswith("#")
        or line.startswith(">")
        or line.strip() == "---"
        or line.strip().startswith("|")
        or re.match(r"^\s*-\s+", line)
        or re.match(r"^\d+\.\s+", line)
    )

def collect_wrapped(lines, i, strip_prefix=""):
    text = re.sub(strip_prefix, "", lines[i]).strip() if strip_prefix else lines[i].strip()
    i += 1
    while i < len(lines) and lines[i].strip() and not is_block_start(lines[i]):
        text += " " + lines[i].strip()
        i += 1
    return text, i

def build_story(md_text):
    story = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), styles["H1"]))
            i += 1
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), styles["H2"]))
            i += 1
        elif line.startswith("**Document ID:**") or line.startswith("**Version:**") or \
             line.startswith("**Last Updated:**") or line.startswith("**Owner:**") or \
             line.startswith("**Status:**") or line.startswith("**Category:**"):
            story.append(Paragraph(inline(line), styles["Meta"]))
            i += 1
        elif line.startswith(">"):
            text, i = collect_wrapped(lines, i, strip_prefix=r"^>\s?")
            story.append(Paragraph(inline(text), styles["Quote"]))
        elif line.strip() == "---":
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))
            story.append(Spacer(1, 8))
            i += 1
        elif line.strip().startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            rows = parse_table(table_lines)
            data = [[Paragraph(inline(c), styles["Body"]) for c in r] for r in rows]
            t = Table(data, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        elif re.match(r"^\s*-\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*-\s+", lines[i]):
                text, i = collect_wrapped(lines, i, strip_prefix=r"^\s*-\s+")
                items.append(Paragraph(inline(text), styles["Body"]))
            story.append(ListFlowable([ListItem(p) for p in items], bulletType="bullet", leftIndent=16))
        elif re.match(r"^\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                text, i = collect_wrapped(lines, i, strip_prefix=r"^\d+\.\s+")
                items.append(Paragraph(inline(text), styles["Body"]))
            story.append(ListFlowable([ListItem(p) for p in items], bulletType="1", leftIndent=16))
        else:
            text, i = collect_wrapped(lines, i)
            story.append(Paragraph(inline(text), styles["Body"]))
    return story

def convert(md_path: Path):
    pdf_path = OUT_DIR / (md_path.stem + ".pdf")
    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    story = build_story(md_path.read_text(encoding="utf-8"))
    doc.build(story)
    print(f"wrote {pdf_path}")

if __name__ == "__main__":
    for md_file in sorted(SRC_DIR.glob("*.md")):
        convert(md_file)
