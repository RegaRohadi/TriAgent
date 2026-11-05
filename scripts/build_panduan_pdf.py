from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MD_PATH = PROJECT_ROOT / "docs" / "PANDUAN_TRIAGENT.md"
PDF_PATH = PROJECT_ROOT / "PANDUAN_TRIAGENT.pdf"

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm
AVAILABLE_W = PAGE_W - 2 * MARGIN

CODE_LINE_CHARS = 104

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("DocH1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                          fontSize=20, leading=24, spaceBefore=6, spaceAfter=14,
                          textColor=colors.HexColor("#111111")))
styles.add(ParagraphStyle("DocH2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                          fontSize=14, leading=18, spaceBefore=16, spaceAfter=8,
                          textColor=colors.HexColor("#1a3c6e")))
styles.add(ParagraphStyle("DocH3", parent=styles["Heading3"], fontName="Helvetica-Bold",
                          fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=5,
                          textColor=colors.HexColor("#333333")))
styles.add(ParagraphStyle("DocH4", parent=styles["Heading4"], fontName="Helvetica-Bold",
                          fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=4,
                          textColor=colors.HexColor("#333333")))
styles.add(ParagraphStyle("DocBody", parent=styles["BodyText"], fontName="Helvetica",
                          fontSize=9.5, leading=13.5, spaceAfter=6, alignment=TA_LEFT))
styles.add(ParagraphStyle("DocQuote", parent=styles["BodyText"], fontName="Helvetica-Oblique",
                          fontSize=9.5, leading=13.5, leftIndent=14, rightIndent=8,
                          textColor=colors.HexColor("#444444"), spaceAfter=8))
styles.add(ParagraphStyle("DocCode", parent=styles["BodyText"], fontName="Courier",
                          fontSize=7.4, leading=9.6, leftIndent=6, rightIndent=6,
                          backColor=colors.HexColor("#f4f4f4"), borderPadding=4,
                          spaceBefore=4, spaceAfter=8, textColor=colors.HexColor("#111111")))
styles.add(ParagraphStyle("DocCell", parent=styles["BodyText"], fontName="Helvetica",
                          fontSize=8.2, leading=11, spaceAfter=0))
styles.add(ParagraphStyle("DocCellHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
                          fontSize=8.4, leading=11, spaceAfter=0, textColor=colors.HexColor("#111111")))
styles.add(ParagraphStyle("DocCaption", parent=styles["BodyText"], fontName="Helvetica-Oblique",
                          fontSize=8, leading=11, alignment=1, spaceBefore=3, spaceAfter=2,
                          textColor=colors.HexColor("#666666")))


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(
        r"`([^`]+)`",
        r'<font face="Courier" size="8.4" color="#a33a00">\1</font>',
        text,
    )
    return text


SEPARATOR_ROW = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$")
IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$")


def build_image(alt: str, rel_path: str):
    path = (MD_PATH.parent / rel_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Gambar tidak ditemukan: {path}")
    img = Image(str(path))
    scale = min(AVAILABLE_W / img.imageWidth, 720.0 / img.imageHeight)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale
    img.hAlign = "CENTER"
    parts = [Spacer(1, 4), img]
    if alt:
        parts.append(Paragraph(f"<i>{esc(alt)}</i>", styles["DocCaption"]))
    parts.append(Spacer(1, 10))
    return parts


def is_table_row(line: str) -> bool:
    return line.strip().startswith("|")


def parse_table(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        if SEPARATOR_ROW.match(line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def build_table(rows: list[list[str]]):
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]

    weights = []
    for c in range(ncols):
        longest = max((len(r[c]) for r in rows), default=1)
        weights.append(min(max(longest, 8), 55))
    total = sum(weights)
    col_widths = [AVAILABLE_W * w / total for w in weights]

    data = []
    for r_index, row in enumerate(rows):
        style = styles["DocCellHead"] if r_index == 0 else styles["DocCell"]
        data.append([Paragraph(inline(cell), style) for cell in row])

    table = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def wrap_code(line: str, width: int = CODE_LINE_CHARS) -> list[str]:
    if len(line) <= width:
        return [line]
    return [line[i:i + width] for i in range(0, len(line), width)]


def is_block_start(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or stripped.startswith("#")
        or stripped.startswith("|")
        or stripped.startswith(">")
        or stripped.startswith("```")
        or stripped.startswith("<!--")
        or stripped == "---"
        or re.match(r"^\s*-\s+", line)
        or re.match(r"^\d+\.\s+", line)
    )


def collect_wrapped(lines: list[str], i: int) -> tuple[str, int]:
    parts = [lines[i].strip()]
    i += 1
    while i < len(lines) and lines[i].strip() and not is_block_start(lines[i]):
        parts.append(lines[i].strip())
        i += 1
    return " ".join(parts), i


def build_story(md_text: str):
    story = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped == "<!-- pagebreak -->":
            story.append(PageBreak())
            i += 1
            continue

        image_match = IMAGE_RE.match(stripped)
        if image_match:
            story.extend(build_image(image_match.group(1), image_match.group(2)))
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                for piece in wrap_code(lines[i].rstrip("\n")):
                    code_lines.append(piece)
                i += 1
            i += 1
            story.append(Preformatted("\n".join(code_lines), styles["DocCode"]))
            continue

        if stripped.startswith("#### "):
            story.append(Paragraph(inline(stripped[5:]), styles["DocH4"]))
            i += 1
            continue

        if stripped.startswith("### "):
            story.append(Paragraph(inline(stripped[4:]), styles["DocH3"]))
            i += 1
            continue

        if stripped.startswith("## "):
            story.append(Paragraph(inline(stripped[3:]), styles["DocH2"]))
            i += 1
            continue

        if stripped.startswith("# "):
            story.append(Paragraph(inline(stripped[2:]), styles["DocH1"]))
            i += 1
            continue

        if stripped == "---":
            story.append(Spacer(1, 3))
            story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))
            story.append(Spacer(1, 5))
            i += 1
            continue

        if is_table_row(line):
            table_lines = []
            while i < len(lines) and is_table_row(lines[i]):
                table_lines.append(lines[i])
                i += 1
            rows = parse_table(table_lines)
            if rows:
                story.append(Spacer(1, 2))
                story.append(build_table(rows))
                story.append(Spacer(1, 8))
            continue

        if re.match(r"^\s*-\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*-\s+", lines[i]):
                text = re.sub(r"^\s*-\s+", "", lines[i]).strip()
                i += 1
                while i < len(lines) and lines[i].strip() and not is_block_start(lines[i]):
                    text += " " + lines[i].strip()
                    i += 1
                items.append(ListItem(Paragraph(inline(text), styles["DocBody"])))
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=14,
                                      bulletFontSize=8, spaceAfter=6))
            continue

        if re.match(r"^\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                text = re.sub(r"^\d+\.\s+", "", lines[i]).strip()
                i += 1
                while i < len(lines) and lines[i].strip() and not is_block_start(lines[i]):
                    text += " " + lines[i].strip()
                    i += 1
                items.append(ListItem(Paragraph(inline(text), styles["DocBody"])))
            story.append(ListFlowable(items, bulletType="1", leftIndent=16,
                                      bulletFontSize=8, spaceAfter=6))
            continue

        if stripped.startswith(">"):
            text, i = collect_wrapped(lines, i)
            text = re.sub(r"^>\s?", "", text)
            story.append(Paragraph(inline(text), styles["DocQuote"]))
            continue

        text, i = collect_wrapped(lines, i)
        story.append(Paragraph(inline(text), styles["DocBody"]))

    return story


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawString(MARGIN, 1.05 * cm, "PANDUAN LENGKAP TRIAGENT")
    canvas.drawRightString(PAGE_W - MARGIN, 1.05 * cm, f"Halaman {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#dddddd"))
    canvas.line(MARGIN, 1.35 * cm, PAGE_W - MARGIN, 1.35 * cm)
    canvas.restoreState()


def main() -> int:
    if not MD_PATH.exists():
        raise SystemExit(f"Sumber markdown tidak ditemukan: {MD_PATH}")

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        topMargin=1.6 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        title="Panduan Lengkap TriAgent",
        author="Panduan Arsitektur",
    )
    story = build_story(MD_PATH.read_text(encoding="utf-8"))
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"wrote {PDF_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
