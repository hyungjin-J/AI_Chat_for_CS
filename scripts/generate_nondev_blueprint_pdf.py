#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


def resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_date_stamp(value: str | None) -> str:
    if value:
        return value
    return dt.datetime.now().strftime("%Y%m%d")


def register_korean_font() -> str:
    candidates = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/NanumGothic.ttf"),
    ]
    for font_path in candidates:
        if font_path.exists():
            font_name = f"font_{font_path.stem.lower()}"
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            return font_name
    raise FileNotFoundError(
        "Korean font not found. Install 'malgun.ttf' or 'NanumGothic.ttf' on this machine."
    )


def md_inline_to_paragraph_text(raw: str) -> str:
    text = escape(raw.strip())
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = text.replace("`", "")
    return text


def build_styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName=font_name,
            fontSize=28,
            alignment=TA_LEFT,
            leading=36,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=7 * mm,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=12,
            alignment=TA_LEFT,
            leading=20,
            textColor=colors.HexColor("#334155"),
            spaceAfter=5 * mm,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=10.5,
            alignment=TA_LEFT,
            leading=16,
            textColor=colors.HexColor("#475569"),
            spaceAfter=2 * mm,
        ),
        "toc_title": ParagraphStyle(
            "toc_title",
            parent=base["Heading1"],
            fontName=font_name,
            fontSize=18,
            leading=26,
            textColor=colors.HexColor("#1e3a8a"),
            spaceAfter=5 * mm,
        ),
        "toc_level1": ParagraphStyle(
            "toc_level1",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=11,
            leading=16,
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=1 * mm,
        ),
        "toc_level2": ParagraphStyle(
            "toc_level2",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            leftIndent=6 * mm,
            firstLineIndent=0,
            textColor=colors.HexColor("#475569"),
            spaceAfter=0.8 * mm,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=font_name,
            fontSize=17,
            leading=25,
            textColor=colors.HexColor("#1e3a8a"),
            alignment=TA_LEFT,
            spaceBefore=2.5 * mm,
            spaceAfter=2.2 * mm,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=13,
            leading=20,
            textColor=colors.HexColor("#1e40af"),
            alignment=TA_LEFT,
            spaceBefore=3 * mm,
            spaceAfter=1.4 * mm,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName=font_name,
            fontSize=11.5,
            leading=18,
            textColor=colors.HexColor("#1d4ed8"),
            alignment=TA_LEFT,
            spaceBefore=2.5 * mm,
            spaceAfter=1.3 * mm,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=11.2,
            leading=19,
            textColor=colors.HexColor("#111827"),
            alignment=TA_JUSTIFY,
            firstLineIndent=4 * mm,
            spaceAfter=2 * mm,
        ),
        "body_compact": ParagraphStyle(
            "body_compact",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10.6,
            leading=17,
            textColor=colors.HexColor("#111827"),
            alignment=TA_LEFT,
            firstLineIndent=0,
            spaceAfter=1.6 * mm,
        ),
        "list0": ParagraphStyle(
            "list0",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10.8,
            leading=17,
            leftIndent=6 * mm,
            firstLineIndent=-2 * mm,
            spaceAfter=1.5 * mm,
        ),
        "list1": ParagraphStyle(
            "list1",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10.8,
            leading=17,
            leftIndent=10 * mm,
            firstLineIndent=-2 * mm,
            spaceAfter=1.5 * mm,
        ),
        "list2": ParagraphStyle(
            "list2",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10.8,
            leading=17,
            leftIndent=15 * mm,
            firstLineIndent=-2 * mm,
            spaceAfter=1.5 * mm,
        ),
        "callout": ParagraphStyle(
            "callout",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10.7,
            leading=17,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
            leftIndent=0,
            borderColor=colors.HexColor("#93c5fd"),
            borderWidth=0.8,
            borderPadding=7,
            backColor=colors.HexColor("#eff6ff"),
            spaceBefore=1.2 * mm,
            spaceAfter=3 * mm,
        ),
        "divider_label": ParagraphStyle(
            "divider_label",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=1 * mm,
        ),
        "image_caption": ParagraphStyle(
            "image_caption",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=9.5,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
            spaceBefore=1.2 * mm,
            spaceAfter=2.4 * mm,
        ),
    }


def make_heading(text: str, style: ParagraphStyle, toc_level: int) -> Paragraph:
    heading = Paragraph(md_inline_to_paragraph_text(text), style)
    heading.toc_level = toc_level
    return heading


def make_callout(styles: dict[str, ParagraphStyle], label: str, content: str) -> Paragraph:
    text = f"<b>{escape(label)}</b><br/>{md_inline_to_paragraph_text(content)}"
    return Paragraph(text, styles["callout"])


def resolve_md_image(path_text: str, base_dir: Path) -> Path:
    p = Path(path_text.strip())
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def markdown_to_story(md_text: str, styles: dict[str, ParagraphStyle], base_dir: Path) -> list:
    story = []
    lines = md_text.splitlines()
    seen_title = False
    chapter_count = 0

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            story.append(Spacer(1, 1.5 * mm))
            continue

        stripped = line.strip()
        if stripped == "---":
            story.append(Spacer(1, 0.8 * mm))
            story.append(HRFlowable(color=colors.HexColor("#dbeafe"), width="100%", thickness=0.8))
            story.append(Spacer(1, 1.3 * mm))
            continue

        callout_match = re.match(r"^\[(핵심 요약|실무 팁|주의|한눈에 보기)\]\s*(.+)$", stripped)
        if callout_match:
            story.append(make_callout(styles, callout_match.group(1), callout_match.group(2)))
            continue

        image_match = re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped)
        if image_match:
            caption = image_match.group(1).strip()
            image_ref = image_match.group(2).strip()
            image_path = resolve_md_image(image_ref, base_dir)
            if image_path.exists():
                story.append(Spacer(1, 1.5 * mm))
                img = Image(str(image_path))
                img._restrictSize(168 * mm, 102 * mm)
                story.append(img)
                if caption:
                    story.append(Paragraph(md_inline_to_paragraph_text(caption), styles["image_caption"]))
            else:
                story.append(
                    Paragraph(
                        md_inline_to_paragraph_text(f"[이미지 누락] {image_ref}"),
                        styles["body_compact"],
                    )
                )
            continue

        if line.startswith("# "):
            # First markdown title is used as cover title and skipped in body.
            if not seen_title:
                seen_title = True
                continue
            chapter_text = line[2:]
            if re.match(r"^\d+장\.", chapter_text):
                if chapter_count > 0:
                    story.append(PageBreak())
                chapter_count += 1
                story.append(Paragraph("CHAPTER", styles["divider_label"]))
            story.append(make_heading(chapter_text, styles["h1"], toc_level=0))
            story.append(HRFlowable(color=colors.HexColor("#bfdbfe"), width="100%", thickness=0.8))
            continue
        if line.startswith("## "):
            story.append(make_heading(line[3:], styles["h2"], toc_level=1))
            continue
        if line.startswith("### "):
            story.append(Paragraph(md_inline_to_paragraph_text(line[4:]), styles["h3"]))
            continue

        stripped = line.lstrip()
        indent_spaces = len(line) - len(stripped)
        list_level = min(indent_spaces // 2, 2)

        numbered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if numbered:
            text = md_inline_to_paragraph_text(f"{numbered.group(1)}. {numbered.group(2)}")
            story.append(Paragraph(text, styles[f"list{list_level}"]))
            continue

        if stripped.startswith("- "):
            text = md_inline_to_paragraph_text(f"- {stripped[2:]}")
            story.append(Paragraph(text, styles[f"list{list_level}"]))
            continue

        # Header-like metadata lines become compact paragraphs.
        if ":" in stripped and len(stripped) < 42:
            story.append(Paragraph(md_inline_to_paragraph_text(stripped), styles["body_compact"]))
        else:
            story.append(Paragraph(md_inline_to_paragraph_text(stripped), styles["body"]))

    return story


class GuideDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, cover_title: str, font_name: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.cover_title = cover_title
        self.font_name = font_name
        self.current_chapter = ""
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal_frame",
        )
        self.addPageTemplates(
            [
                PageTemplate(
                    id="paper",
                    frames=[frame],
                    onPage=self._draw_header_footer,
                )
            ]
        )

    def _draw_header_footer(self, canvas, doc) -> None:
        page_num = canvas.getPageNumber()
        canvas.saveState()

        # Header
        if page_num >= 2:
            canvas.setStrokeColor(colors.HexColor("#dbeafe"))
            canvas.setLineWidth(0.7)
            canvas.line(self.leftMargin, A4[1] - 14 * mm, A4[0] - self.rightMargin, A4[1] - 14 * mm)

            canvas.setFont(self.font_name, 8.7)
            canvas.setFillColor(colors.HexColor("#475569"))
            canvas.drawString(self.leftMargin, A4[1] - 11.2 * mm, self.cover_title[:64])

            right_header = self.current_chapter if self.current_chapter else "학습형 제품 해설"
            canvas.drawRightString(A4[0] - self.rightMargin, A4[1] - 11.2 * mm, right_header[:40])

        # Footer
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.setLineWidth(0.6)
        canvas.line(self.leftMargin, 13 * mm, A4[0] - self.rightMargin, 13 * mm)

        canvas.setFont(self.font_name, 8.7)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(self.leftMargin, 9.6 * mm, "AI_Chatbot Buyer Guide")
        canvas.drawCentredString(A4[0] / 2, 9.6 * mm, f"{page_num}")
        canvas.drawRightString(A4[0] - self.rightMargin, 9.6 * mm, dt.datetime.now().strftime("%Y-%m-%d"))

        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return

        if not hasattr(flowable, "toc_level"):
            return

        text = flowable.getPlainText().strip()
        if not text:
            return

        level = int(flowable.toc_level)
        self.notify("TOCEntry", (level, text, self.page))

        if level == 0:
            self.current_chapter = text


def build_pdf(input_md: Path, output_pdf: Path, architecture_img: Path, cover_title: str) -> None:
    font_name = register_korean_font()
    styles = build_styles(font_name)
    md_text = input_md.read_text(encoding="utf-8")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = GuideDocTemplate(
        str(output_pdf),
        cover_title=cover_title,
        font_name=font_name,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=15 * mm,
        title=cover_title,
        author="AI_Chatbot Project",
    )

    story: list = [
        Spacer(1, 10 * mm),
        Paragraph(cover_title, styles["cover_title"]),
        Paragraph(
            "구매자/비개발 실무자를 위한 학습형 제품 해설서",
            styles["cover_subtitle"],
        ),
        Paragraph(
            f"생성일: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} (local)",
            styles["cover_meta"],
        ),
        Paragraph(f"원본 문서: {input_md.as_posix()}", styles["cover_meta"]),
        Paragraph("버전 특성: Fail-Closed / Evidence-First / Traceable", styles["cover_meta"]),
        Spacer(1, 1.2 * mm),
        HRFlowable(color=colors.HexColor("#cbd5e1"), width="100%", thickness=1.1, spaceAfter=6 * mm),
    ]

    if architecture_img.exists():
        story.append(Paragraph("시스템 개요 다이어그램", styles["h2"]))
        img = Image(str(architecture_img))
        img._restrictSize(170 * mm, 95 * mm)
        story.append(img)
        story.append(Spacer(1, 4 * mm))

    # Cover summary box
    summary_box = Table(
        [
            [
                Paragraph(
                    "<b>읽기 가이드</b><br/>"
                    "- 1장: 제품 개념 이해<br/>"
                    "- 4장: 기능 체계 심화<br/>"
                    "- 8장: 구매 전 검증 체크리스트",
                    styles["body_compact"],
                )
            ]
        ],
        colWidths=[170 * mm],
    )
    summary_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#93c5fd")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(summary_box)
    story.append(PageBreak())

    # Table of contents (auto page number, via multiBuild)
    toc = TableOfContents()
    toc.levelStyles = [styles["toc_level1"], styles["toc_level2"]]
    toc.dotsMinLevel = 0
    story.append(Paragraph("목차", styles["toc_title"]))
    story.append(Paragraph("각 장의 핵심 내용을 빠르게 찾을 수 있습니다.", styles["body_compact"]))
    story.append(Spacer(1, 1.2 * mm))
    story.append(toc)
    story.append(PageBreak())

    story.extend(markdown_to_story(md_text, styles, base_dir=input_md.parent))
    story.append(PageBreak())
    story.append(Paragraph("참고 자료", styles["h1"]))
    story.append(HRFlowable(color=colors.HexColor("#bfdbfe"), width="100%", thickness=0.8))
    story.append(
        Paragraph(
            "- docs/architecture/NOTION_System_Architecture.md<br/>"
            "- docs/review/mvp_verification_pack/01_MVP_EXPLAIN_FOR_NON_DEV.md<br/>"
            "- docs/review/mvp_verification_pack/CURRENT.md<br/>"
            "- docs/review/mvp_verification_pack/04_TEST_RESULTS.md",
            styles["body_compact"],
        )
    )

    doc.multiBuild(story)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a non-developer-friendly project blueprint PDF."
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Source markdown path (default: docs/reports/NON_DEV_PROJECT_BLUEPRINT.md)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output PDF path (default: docs/reports/NON_DEV_PROJECT_BLUEPRINT_<YYYYMMDD>.pdf)",
    )
    parser.add_argument(
        "--date-stamp",
        default=None,
        help="Date stamp in YYYYMMDD format for default output path.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional cover title override.",
    )
    parser.add_argument(
        "--architecture-image",
        default=None,
        help=(
            "Optional architecture image path for PDF cover. "
            "If omitted, uses docs/reports/assets/buyer_architecture_diagram.png when present, "
            "otherwise falls back to docs/architecture/diagrams/cs_rag_system_architecture_v1.png."
        ),
    )
    return parser.parse_args()


def infer_title(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def main() -> int:
    args = parse_args()
    root = resolve_repo_root()
    stamp = resolve_date_stamp(args.date_stamp)

    input_md = Path(args.input) if args.input else root / "docs" / "reports" / "NON_DEV_PROJECT_BLUEPRINT.md"
    output_pdf = (
        Path(args.output)
        if args.output
        else root / "docs" / "reports" / f"NON_DEV_PROJECT_BLUEPRINT_{stamp}.pdf"
    )
    preferred_arch_img = root / "docs" / "reports" / "assets" / "buyer_architecture_diagram.png"
    fallback_arch_img = root / "docs" / "architecture" / "diagrams" / "cs_rag_system_architecture_v1.png"
    architecture_img = (
        Path(args.architecture_image)
        if args.architecture_image
        else (preferred_arch_img if preferred_arch_img.exists() else fallback_arch_img)
    )

    if not input_md.exists():
        raise FileNotFoundError(f"Input markdown not found: {input_md}")

    md_text = input_md.read_text(encoding="utf-8")
    title = args.title or infer_title(md_text, "AI 챗봇 비개발자용 설계도")

    build_pdf(
        input_md=input_md,
        output_pdf=output_pdf,
        architecture_img=architecture_img,
        cover_title=title,
    )

    print(f"Using architecture image: {architecture_img}")
    print(f"Generated PDF: {output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
