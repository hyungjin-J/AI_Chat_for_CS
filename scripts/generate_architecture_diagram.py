from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple
import base64
import io

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ICONS_DIR = ROOT / "docs" / "architecture" / "assets" / "icons"
DIAGRAMS_DIR = ROOT / "docs" / "architecture" / "diagrams"
PNG_OUT = DIAGRAMS_DIR / "cs_rag_system_architecture_v1.png"
SVG_OUT = DIAGRAMS_DIR / "cs_rag_system_architecture_v1.svg"

WIDTH = 2560
HEIGHT = 1440
SVG_FONT_FAMILY = "'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR','Noto Sans CJK KR','Segoe UI',sans-serif"


@dataclass
class LayerBox:
    name: str
    subtitle: str
    x: int
    y: int
    w: int
    h: int
    color: Tuple[int, int, int]


LAYERS = [
    LayerBox("클라이언트 계층", "React/TS/Vite/SSE", 50, 140, 430, 980, (34, 197, 94)),
    LayerBox("엣지/웹 계층", "Nginx + TLS", 520, 160, 340, 250, (59, 130, 246)),
    LayerBox("백엔드 계층", "Spring Boot + 보안 + RAG 오케스트레이션", 900, 120, 820, 980, (249, 115, 22)),
    LayerBox("AI/RAG 구성요소", "파서/임베딩/리랭커/LLM", 1760, 120, 420, 470, (147, 51, 234)),
    LayerBox("데이터/검색 계층", "PostgreSQL/Redis/OpenSearch", 1760, 620, 420, 500, (239, 68, 68)),
    LayerBox("외부 시스템", "LLM API / 헬프데스크 / 웹훅", 2210, 120, 300, 1000, (107, 114, 128)),
    LayerBox("관측 계층", "OpenTelemetry + ELK/메트릭/트레이싱", 520, 1160, 1710, 240, (234, 179, 8)),
]


def load_font(size: int) -> ImageFont.ImageFont:
    # Prefer Korean-capable fonts first to avoid broken Hangul glyphs.
    candidates = [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothic.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NotoSansCJKkr-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def icon_path(name: str) -> Path:
    return ICONS_DIR / f"{name}.png"


def tint_color(color: Tuple[int, int, int], toward_white: float = 0.82) -> Tuple[int, int, int]:
    # Return an opaque pastel color so layer interiors stay readable across viewers.
    r, g, b = color
    wr = int(r + (255 - r) * toward_white)
    wg = int(g + (255 - g) * toward_white)
    wb = int(b + (255 - b) * toward_white)
    return (wr, wg, wb)


def draw_layer(draw: ImageDraw.ImageDraw, layer: LayerBox, title_font: ImageFont.ImageFont, subtitle_font: ImageFont.ImageFont) -> None:
    x2 = layer.x + layer.w
    y2 = layer.y + layer.h
    draw.rounded_rectangle(
        (layer.x, layer.y, x2, y2),
        radius=24,
        fill=(*tint_color(layer.color), 255),
        outline=layer.color,
        width=4,
    )
    draw.text((layer.x + 16, layer.y + 14), layer.name, fill=(17, 24, 39), font=title_font)
    draw.text((layer.x + 16, layer.y + 48), layer.subtitle, fill=(55, 65, 81), font=subtitle_font)


def paste_icon(canvas: Image.Image, draw: ImageDraw.ImageDraw, icon_name: str, label: str, x: int, y: int, label_font: ImageFont.ImageFont) -> None:
    # Keep icon area bright regardless of layer color.
    draw.rounded_rectangle(
        (x - 8, y - 8, x + 80, y + 80),
        radius=18,
        fill=(255, 255, 255, 230),
        outline=(203, 213, 225, 255),
        width=2,
    )

    p = icon_path(icon_name)
    if p.exists():
        icon = Image.open(p).convert("RGBA").resize((72, 72))
        canvas.paste(icon, (x, y), icon)
    else:
        draw.rectangle((x, y, x + 72, y + 72), fill=(229, 231, 235), outline=(107, 114, 128), width=2)
    text_w = draw.textlength(label, font=label_font)
    draw.text((x + (72 - text_w) / 2, y + 78), label, fill=(31, 41, 55), font=label_font)


def draw_arrow(draw: ImageDraw.ImageDraw, start: Tuple[int, int], end: Tuple[int, int], color: Tuple[int, int, int], width: int = 4) -> None:
    draw.line((start, end), fill=color, width=width)
    ex, ey = end
    sx, sy = start
    dx = ex - sx
    dy = ey - sy
    if dx == 0 and dy == 0:
        return
    length = (dx * dx + dy * dy) ** 0.5
    ux = dx / length
    uy = dy / length
    left = (ex - ux * 18 - uy * 10, ey - uy * 18 + ux * 10)
    right = (ex - ux * 18 + uy * 10, ey - uy * 18 - ux * 10)
    draw.polygon([end, left, right], fill=color)


def draw_badge(canvas: Image.Image, draw: ImageDraw.ImageDraw, icon: str, text: str, x: int, y: int, font: ImageFont.ImageFont) -> None:
    draw.rounded_rectangle((x, y, x + 220, y + 50), radius=18, fill=(255, 255, 255), outline=(148, 163, 184), width=2)
    icon_img = Image.open(icon_path(icon)).convert("RGBA").resize((28, 28))
    canvas.paste(icon_img, (x + 10, y + 11), icon_img)
    draw.text((x + 48, y + 15), text, fill=(17, 24, 39), font=font)


def render_png() -> None:
    DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)

    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (237, 242, 247, 255))
    draw = ImageDraw.Draw(canvas)

    title_font = load_font(34)
    layer_title_font = load_font(26)
    subtitle_font = load_font(19)
    label_font = load_font(16)
    badge_font = load_font(16)

    draw.text((48, 36), "CS 지원 AI 챗봇(RAG) - 시스템 아키텍처", fill=(15, 23, 42), font=title_font)
    draw.text((48, 86), "한눈에 보는 계층 구성, 핵심 가드레일, 런타임 흐름", fill=(71, 85, 105), font=subtitle_font)

    for layer in LAYERS:
        draw_layer(draw, layer, layer_title_font, subtitle_font)

    # Client icons
    paste_icon(canvas, draw, "react", "React", 90, 240, label_font)
    paste_icon(canvas, draw, "typescript", "TypeScript", 190, 240, label_font)
    paste_icon(canvas, draw, "vite", "Vite", 290, 240, label_font)
    paste_icon(canvas, draw, "mui", "MUI", 90, 360, label_font)
    paste_icon(canvas, draw, "axios", "Axios", 190, 360, label_font)
    paste_icon(canvas, draw, "redux", "Redux", 290, 360, label_font)

    # Edge icons
    paste_icon(canvas, draw, "nginx", "Nginx", 610, 245, label_font)
    paste_icon(canvas, draw, "badge_trace", "TLS 보안", 710, 245, label_font)

    # Backend icons
    paste_icon(canvas, draw, "springboot", "Spring Boot", 940, 220, label_font)
    paste_icon(canvas, draw, "java", "Java 17", 1040, 220, label_font)
    paste_icon(canvas, draw, "spring", "Spring Sec", 1140, 220, label_font)
    paste_icon(canvas, draw, "badge_trace", "trace_id", 1240, 220, label_font)
    paste_icon(canvas, draw, "badge_pii", "PII 마스킹", 1340, 220, label_font)
    paste_icon(canvas, draw, "badge_rbac", "RBAC", 1440, 220, label_font)

    paste_icon(canvas, draw, "badge_budget", "예산", 940, 350, label_font)
    paste_icon(canvas, draw, "badge_fail_closed", "안전차단", 1040, 350, label_font)
    paste_icon(canvas, draw, "badge_trace", "SSE 스트림", 1140, 350, label_font)
    paste_icon(canvas, draw, "docker", "Container", 1240, 350, label_font)

    # AI icons
    paste_icon(canvas, draw, "ollama", "Ollama", 1800, 240, label_font)
    paste_icon(canvas, draw, "openai", "외부 LLM", 1900, 240, label_font)
    paste_icon(canvas, draw, "ocr", "OCR", 1800, 360, label_font)
    paste_icon(canvas, draw, "reranker", "Reranker", 1900, 360, label_font)

    # Data icons
    paste_icon(canvas, draw, "postgresql", "PostgreSQL", 1800, 740, label_font)
    paste_icon(canvas, draw, "redis", "Redis", 1900, 740, label_font)
    paste_icon(canvas, draw, "opensearch", "OpenSearch", 1800, 860, label_font)
    paste_icon(canvas, draw, "elasticsearch", "Elastic", 1900, 860, label_font)

    # Observability icons
    paste_icon(canvas, draw, "opentelemetry", "OpenTelemetry", 700, 1240, label_font)
    paste_icon(canvas, draw, "elasticsearch", "Elasticsearch", 820, 1240, label_font)
    paste_icon(canvas, draw, "kibana", "Kibana", 940, 1240, label_font)
    paste_icon(canvas, draw, "logstash", "Logstash", 1060, 1240, label_font)

    # External icons
    paste_icon(canvas, draw, "openai", "LLM API", 2240, 240, label_font)
    paste_icon(canvas, draw, "ticketing", "헬프데스크", 2340, 240, label_font)
    paste_icon(canvas, draw, "webhook", "웹훅", 2240, 360, label_font)
    paste_icon(canvas, draw, "notion", "문서", 2340, 360, label_font)

    # Main arrows
    arrow_color = (15, 23, 42)
    draw_arrow(draw, (480, 300), (520, 300), arrow_color)
    draw_arrow(draw, (860, 300), (900, 300), arrow_color)
    draw_arrow(draw, (1720, 360), (1760, 300), arrow_color)
    draw_arrow(draw, (1760, 320), (1720, 420), arrow_color)
    draw_arrow(draw, (1720, 820), (1760, 820), arrow_color)
    draw_arrow(draw, (1760, 860), (1720, 900), arrow_color)
    draw_arrow(draw, (1720, 760), (1760, 760), arrow_color)  # redis path via data

    # To observability
    obs_targets = [(780, 1160), (1120, 1160), (1500, 1160), (1940, 1160), (2340, 1160)]
    obs_sources = [(260, 1120), (690, 410), (1310, 1100), (1970, 1120), (2360, 1120)]
    for src, dst in zip(obs_sources, obs_targets):
        draw_arrow(draw, src, dst, (71, 85, 105), width=3)

    # Guardrail badges around backend
    draw_badge(canvas, draw, "badge_fail_closed", "답변 계약 검증 / 안전 차단", 1260, 500, badge_font)
    draw_badge(canvas, draw, "badge_pii", "PII 마스킹 (입력/로그/캐시/출력)", 1260, 565, badge_font)
    draw_badge(canvas, draw, "badge_trace", "trace_id 전 구간 전파", 1260, 630, badge_font)
    draw_badge(canvas, draw, "badge_rbac", "테넌트 격리 + RBAC", 1260, 695, badge_font)
    draw_badge(canvas, draw, "badge_budget", "예산/레이트리밋 가드", 1260, 760, badge_font)

    # Legend
    draw.rounded_rectangle((50, 1260, 450, 1390), radius=14, fill=(255, 255, 255), outline=(148, 163, 184), width=2)
    draw.text((66, 1278), "범례", fill=(15, 23, 42), font=layer_title_font)
    draw.line((70, 1322, 130, 1322), fill=(15, 23, 42), width=4)
    draw.polygon([(130, 1322), (116, 1314), (116, 1330)], fill=(15, 23, 42))
    draw.text((140, 1310), "요청/제어 흐름", fill=(51, 65, 85), font=label_font)
    draw.line((70, 1352, 130, 1352), fill=(71, 85, 105), width=3)
    draw.polygon([(130, 1352), (118, 1345), (118, 1359)], fill=(71, 85, 105))
    draw.text((140, 1340), "관측(텔레메트리) 흐름", fill=(51, 65, 85), font=label_font)

    canvas.save(PNG_OUT)


def svg_rect(x: int, y: int, w: int, h: int, color: Tuple[int, int, int], radius: int = 20) -> str:
    stroke = f"rgb({color[0]},{color[1]},{color[2]})"
    layer_fill = tint_color(color)
    fill = f"rgb({layer_fill[0]},{layer_fill[1]},{layer_fill[2]})"
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" ry="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="4" />'


def svg_icon(name: str, label: str, x: int, y: int) -> str:
    icon_file = icon_path(name)
    if not icon_file.exists():
        return ""
    with open(icon_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return (
        f'<rect x="{x - 8}" y="{y - 8}" width="88" height="88" rx="18" ry="18" fill="rgba(255,255,255,0.92)" '
        f'stroke="#cbd5e1" stroke-width="2" />\n'
        f'<image x="{x}" y="{y}" width="72" height="72" href="data:image/png;base64,{encoded}" />\n'
        f'<text x="{x + 36}" y="{y + 95}" text-anchor="middle" font-size="16" fill="#1f2937" font-family="{SVG_FONT_FAMILY}">{label}</text>'
    )


def render_svg() -> None:
    parts: list[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">')
    parts.append('<rect x="0" y="0" width="100%" height="100%" fill="#edf2f7" />')
    parts.append(f'<text x="48" y="74" font-size="42" fill="#0f172a" font-family="{SVG_FONT_FAMILY}" font-weight="700">CS 지원 AI 챗봇(RAG) - 시스템 아키텍처</text>')
    parts.append(f'<text x="48" y="110" font-size="24" fill="#475569" font-family="{SVG_FONT_FAMILY}">한눈에 보는 계층 구성, 핵심 가드레일, 런타임 흐름</text>')

    for layer in LAYERS:
        parts.append(svg_rect(layer.x, layer.y, layer.w, layer.h, layer.color))
        parts.append(
            f'<text x="{layer.x + 16}" y="{layer.y + 42}" font-size="30" fill="#111827" font-family="{SVG_FONT_FAMILY}" font-weight="700">{layer.name}</text>'
        )
        parts.append(f'<text x="{layer.x + 16}" y="{layer.y + 70}" font-size="20" fill="#374151" font-family="{SVG_FONT_FAMILY}">{layer.subtitle}</text>')

    icon_items = [
        ("react", "React", 90, 240),
        ("typescript", "TypeScript", 190, 240),
        ("vite", "Vite", 290, 240),
        ("mui", "MUI", 90, 360),
        ("axios", "Axios", 190, 360),
        ("redux", "Redux", 290, 360),
        ("nginx", "Nginx", 610, 245),
        ("badge_trace", "TLS 보안", 710, 245),
        ("springboot", "Spring Boot", 940, 220),
        ("java", "Java 17", 1040, 220),
        ("spring", "Spring Sec", 1140, 220),
        ("badge_trace", "trace_id", 1240, 220),
        ("badge_pii", "PII 마스킹", 1340, 220),
        ("badge_rbac", "RBAC", 1440, 220),
        ("badge_budget", "예산", 940, 350),
        ("badge_fail_closed", "안전차단", 1040, 350),
        ("badge_trace", "SSE 스트림", 1140, 350),
        ("docker", "Container", 1240, 350),
        ("ollama", "Ollama", 1800, 240),
        ("openai", "외부 LLM", 1900, 240),
        ("ocr", "OCR", 1800, 360),
        ("reranker", "Reranker", 1900, 360),
        ("postgresql", "PostgreSQL", 1800, 740),
        ("redis", "Redis", 1900, 740),
        ("opensearch", "OpenSearch", 1800, 860),
        ("elasticsearch", "Elastic", 1900, 860),
        ("opentelemetry", "OpenTelemetry", 700, 1240),
        ("elasticsearch", "Elasticsearch", 820, 1240),
        ("kibana", "Kibana", 940, 1240),
        ("logstash", "Logstash", 1060, 1240),
        ("openai", "LLM API", 2240, 240),
        ("ticketing", "헬프데스크", 2340, 240),
        ("webhook", "웹훅", 2240, 360),
        ("notion", "문서", 2340, 360),
    ]

    for item in icon_items:
        parts.append(svg_icon(*item))

    parts.append("</svg>")
    SVG_OUT.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    if not ICONS_DIR.exists():
        raise FileNotFoundError(f"Icons directory not found: {ICONS_DIR}")

    DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)
    render_png()
    render_svg()
    print(f"Generated: {PNG_OUT}")
    print(f"Generated: {SVG_OUT}")


if __name__ == "__main__":
    main()
