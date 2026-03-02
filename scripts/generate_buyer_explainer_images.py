#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "reports" / "assets" / "explainers"
CANVAS_SIZE = (1600, 920)


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "C:/Windows/Fonts/malgunbd.ttf",
                "C:/Windows/Fonts/NanumGothicBold.ttf",
                "C:/Windows/Fonts/segoeuib.ttf",
            ]
        )
    candidates.extend(
        [
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/NanumGothic.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
        ]
    )
    for candidate in candidates:
        p = Path(candidate)
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def rounded_box(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int, int, int],
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
    radius: int = 26,
    width: int = 3,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_arrow(draw: ImageDraw.ImageDraw, start: Tuple[int, int], end: Tuple[int, int], color: Tuple[int, int, int], width: int = 6) -> None:
    draw.line([start, end], fill=color, width=width)
    ex, ey = end
    sx, sy = start
    dx, dy = ex - sx, ey - sy
    if dx == 0 and dy == 0:
        return
    length = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / length, dy / length
    left = (ex - ux * 20 - uy * 11, ey - uy * 20 + ux * 11)
    right = (ex - ux * 20 + uy * 11, ey - uy * 20 - ux * 11)
    draw.polygon([end, left, right], fill=color)


def title_block(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    title_font = load_font(48, bold=True)
    subtitle_font = load_font(26)
    draw.text((56, 34), title, fill=(15, 23, 42), font=title_font)
    draw.text((56, 102), subtitle, fill=(71, 85, 105), font=subtitle_font)


def save_canvas(name: str, canvas: Image.Image) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / name
    canvas.save(out)
    print(out.as_posix())


def generate_rag_pipeline() -> None:
    canvas = Image.new("RGB", CANVAS_SIZE, (246, 250, 255))
    draw = ImageDraw.Draw(canvas)
    title_block(draw, "질문 1건 처리 흐름", "비개발자용: 어떤 순서로 답변이 만들어지고 차단되는지")

    step_font = load_font(28, bold=True)
    body_font = load_font(21)

    steps = [
        ("1. 질문 입력", "상담원이 질문 전송"),
        ("2. 근거 검색", "RAG로 문서 근거 탐색"),
        ("3. 답변 초안", "AI가 구조화 답변 생성"),
        ("4. 계약 검증", "형식/근거/정책 검사"),
        ("5. 사용자 노출", "통과 시 답변 표시"),
    ]
    x = 64
    y = 220
    w = 280
    h = 220

    for idx, (title, desc) in enumerate(steps):
        fill = (232, 244, 255) if idx < 4 else (232, 255, 239)
        outline = (59, 130, 246) if idx < 4 else (22, 163, 74)
        rounded_box(draw, (x, y, x + w, y + h), fill, outline)
        draw.text((x + 18, y + 28), title, fill=(15, 23, 42), font=step_font)
        draw.text((x + 18, y + 92), desc, fill=(51, 65, 85), font=body_font)
        if idx < len(steps) - 1:
            draw_arrow(draw, (x + w + 8, y + 108), (x + w + 46, y + 108), (100, 116, 139), 5)
        x += 305

    rounded_box(draw, (90, 510, 1510, 870), (255, 255, 255), (148, 163, 184))
    draw.text((120, 548), "핵심 이해 포인트", fill=(30, 41, 59), font=step_font)
    points = [
        "• 답변보다 먼저 근거를 찾습니다.",
        "• 근거가 부족하거나 정책을 위반하면 답변을 차단합니다.",
        "• 실패 시에도 시스템은 safe_response로 안내하고 로그를 남깁니다.",
        "• 즉, '빠른 생성'보다 '안전한 노출'이 우선입니다.",
    ]
    py = 610
    for p in points:
        draw.text((130, py), p, fill=(51, 65, 85), font=body_font)
        py += 58

    save_canvas("01_rag_pipeline.png", canvas)


def generate_fail_closed_compare() -> None:
    canvas = Image.new("RGB", CANVAS_SIZE, (250, 250, 252))
    draw = ImageDraw.Draw(canvas)
    title_block(draw, "정상 경로 vs Fail-Closed 경로", "답변이 노출될 때와 차단될 때의 차이를 한눈에 비교")

    head_font = load_font(34, bold=True)
    body_font = load_font(22)
    small = load_font(20)

    rounded_box(draw, (90, 210, 760, 860), (236, 253, 245), (22, 163, 74), radius=28)
    draw.text((125, 245), "정상 경로", fill=(21, 128, 61), font=head_font)
    normal = [
        "1) 질문 입력",
        "2) 근거 검색 성공",
        "3) 계약 검증 통과",
        "4) 답변 + citation 노출",
        "5) done 이벤트 종료",
    ]
    y = 325
    for line in normal:
        draw.text((130, y), f"- {line}", fill=(31, 41, 55), font=body_font)
        y += 88

    rounded_box(draw, (840, 210, 1510, 860), (254, 242, 242), (220, 38, 38), radius=28)
    draw.text((875, 245), "Fail-Closed 경로", fill=(185, 28, 28), font=head_font)
    blocked = [
        "1) 질문 입력",
        "2) 근거 부족/정책 위반 감지",
        "3) 일반 답변 차단",
        "4) safe_response만 노출",
        "5) done 이벤트 종료",
    ]
    y = 325
    for line in blocked:
        draw.text((880, y), f"- {line}", fill=(31, 41, 55), font=body_font)
        y += 88

    rounded_box(draw, (420, 770, 1180, 890), (255, 255, 255), (148, 163, 184), radius=22)
    draw.text(
        (450, 808),
        "핵심: '틀릴 수 있는 답변'을 내보내는 대신, 안내문으로 안전하게 멈춥니다.",
        fill=(51, 65, 85),
        font=small,
    )

    save_canvas("02_fail_closed_compare.png", canvas)


def generate_tenant_rbac() -> None:
    canvas = Image.new("RGB", CANVAS_SIZE, (246, 248, 252))
    draw = ImageDraw.Draw(canvas)
    title_block(draw, "테넌트 격리 + RBAC 차단 구조", "비개발자용: 왜 같은 화면이어도 접근 결과가 다른가")

    head = load_font(30, bold=True)
    body = load_font(21)

    rounded_box(draw, (70, 250, 470, 680), (224, 242, 254), (2, 132, 199), radius=22)
    draw.text((105, 290), "사용자 요청", fill=(12, 74, 110), font=head)
    draw.text((110, 362), "- 로그인 토큰", fill=(30, 41, 59), font=body)
    draw.text((110, 418), "- ROLE 정보", fill=(30, 41, 59), font=body)
    draw.text((110, 474), "- Tenant Key", fill=(30, 41, 59), font=body)

    rounded_box(draw, (580, 210, 1030, 720), (255, 251, 235), (245, 158, 11), radius=22)
    draw.text((625, 250), "서버 정책 게이트", fill=(120, 53, 15), font=head)
    draw.text((620, 330), "1) 인증 확인", fill=(51, 65, 85), font=body)
    draw.text((620, 386), "2) ROLE 권한 확인", fill=(51, 65, 85), font=body)
    draw.text((620, 442), "3) Tenant 경계 확인", fill=(51, 65, 85), font=body)
    draw.text((620, 498), "4) 정책/예산 확인", fill=(51, 65, 85), font=body)
    draw.text((620, 574), "통과: 200 + 데이터", fill=(21, 128, 61), font=body)
    draw.text((620, 630), "실패: 403/429 + 표준 오류", fill=(185, 28, 28), font=body)

    rounded_box(draw, (1140, 250, 1530, 680), (240, 253, 244), (34, 197, 94), radius=22)
    draw.text((1175, 290), "응답 결과", fill=(20, 83, 45), font=head)
    draw.text((1180, 362), "- 허용된 데이터만", fill=(30, 41, 59), font=body)
    draw.text((1180, 418), "- 권한 외 접근 차단", fill=(30, 41, 59), font=body)
    draw.text((1180, 474), "- 오류 형식 표준화", fill=(30, 41, 59), font=body)

    draw_arrow(draw, (480, 470), (570, 470), (71, 85, 105), 6)
    draw_arrow(draw, (1040, 470), (1130, 470), (71, 85, 105), 6)

    rounded_box(draw, (90, 760, 1510, 875), (255, 255, 255), (148, 163, 184), radius=20)
    draw.text(
        (120, 802),
        "핵심: 보안은 '화면에서 숨김'이 아니라 '서버에서 차단'으로 완성됩니다.",
        fill=(51, 65, 85),
        font=body,
    )

    save_canvas("03_tenant_rbac.png", canvas)


def generate_traceid_flow() -> None:
    canvas = Image.new("RGB", CANVAS_SIZE, (245, 250, 255))
    draw = ImageDraw.Draw(canvas)
    title_block(draw, "trace_id 전파와 운영 추적", "요청 1건을 끝까지 추적하는 방법")

    head = load_font(30, bold=True)
    body = load_font(20)

    items = [
        ("상담 화면", "질문 전송"),
        ("API 서버", "인증/권한/정책"),
        ("RAG 검색", "근거 탐색"),
        ("LLM 생성", "답변 후보"),
        ("SSE 응답", "token/citation/done"),
        ("운영 로그", "추적/분석"),
    ]
    x = 70
    y = 280
    w = 230
    h = 220
    for i, (title, desc) in enumerate(items):
        rounded_box(draw, (x, y, x + w, y + h), (255, 255, 255), (59, 130, 246), radius=20)
        draw.text((x + 20, y + 36), title, fill=(30, 64, 175), font=head)
        draw.text((x + 20, y + 110), desc, fill=(51, 65, 85), font=body)
        draw.text((x + 20, y + 160), "trace_id 동일", fill=(22, 163, 74), font=body)
        if i < len(items) - 1:
            draw_arrow(draw, (x + w + 8, y + 108), (x + w + 30, y + 108), (100, 116, 139), 5)
        x += 250

    rounded_box(draw, (120, 570, 1480, 865), (239, 246, 255), (96, 165, 250), radius=24)
    draw.text((160, 610), "운영팀이 얻는 이점", fill=(30, 64, 175), font=head)
    points = [
        "• 고객 문의 1건을 '감'이 아니라 데이터로 분석할 수 있습니다.",
        "• 장애 원인(검색 실패/검증 실패/권한 차단)을 빠르게 구분할 수 있습니다.",
        "• 재발 방지 항목을 문서화하고, 운영 기준을 표준화할 수 있습니다.",
    ]
    py = 680
    for p in points:
        draw.text((170, py), p, fill=(51, 65, 85), font=body)
        py += 62

    save_canvas("04_traceid_observability.png", canvas)


def main() -> int:
    generate_rag_pipeline()
    generate_fail_closed_compare()
    generate_tenant_rbac()
    generate_traceid_flow()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
