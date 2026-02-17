#!/usr/bin/env python3
"""UI-API latency budget calculator and markdown writer."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_MD = ROOT / "docs" / "ops" / "Latency_Budget.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Latency budget calculator")
    parser.add_argument("--p50", type=float, default=2200.0, help="Total latency p50 (ms)")
    parser.add_argument("--p95", type=float, default=8500.0, help="Total latency p95 (ms)")
    parser.add_argument("--p99", type=float, default=14000.0, help="Total latency p99 (ms)")
    parser.add_argument("--first-token", type=float, default=1200.0, help="First token latency (ms)")
    parser.add_argument("--token-rate", type=float, default=25.0, help="Tokens per second")
    parser.add_argument("--reconnect", type=int, default=1, help="Reconnect attempts")
    return parser.parse_args()


def calc_recommended(first_token_ms: float, p95_ms: float, reconnect_count: int) -> dict[str, float]:
    request_timeout = max(15000.0, p95_ms * 1.5)
    connect_timeout = max(3000.0, first_token_ms * 2)
    retry_base = min(1500.0, max(300.0, first_token_ms * 0.4))
    retry_max = retry_base * (2 ** max(0, reconnect_count - 1))
    return {
        "request_timeout_ms": round(request_timeout, 1),
        "connect_timeout_ms": round(connect_timeout, 1),
        "retry_base_ms": round(retry_base, 1),
        "retry_max_ms": round(retry_max, 1),
    }


def write_markdown(args: argparse.Namespace, rec: dict[str, float]) -> None:
    ux_feel = "양호"
    if args.first_token > 2000 or args.p95 > 15000:
        ux_feel = "개선 필요"
    if args.first_token > 3000 or args.p95 > 20000:
        ux_feel = "위험"

    lines = [
        "# Latency Budget",
        "",
        "## 입력값",
        "| Metric | Value |",
        "|---|---|",
        f"| p50 total latency | {args.p50:.1f} ms |",
        f"| p95 total latency | {args.p95:.1f} ms |",
        f"| p99 total latency | {args.p99:.1f} ms |",
        f"| first-token | {args.first_token:.1f} ms |",
        f"| token rate | {args.token_rate:.1f} token/s |",
        f"| reconnect count | {args.reconnect} |",
        "",
        "## 권장값",
        "| Parameter | Recommended |",
        "|---|---|",
        f"| request timeout | {rec['request_timeout_ms']:.1f} ms |",
        f"| connect timeout | {rec['connect_timeout_ms']:.1f} ms |",
        f"| retry backoff base | {rec['retry_base_ms']:.1f} ms |",
        f"| retry backoff max | {rec['retry_max_ms']:.1f} ms |",
        "",
        "## 해석",
        f"- 체감 UX 상태: **{ux_feel}**",
        "- first-token 목표: 1~2초(P95)",
        "- done 이전 종료 시 재연결은 최대 3회 이내로 유지",
        "- 429 수신 시 Retry-After 우선 적용, 클라이언트 임의 재시도 금지",
        "- fail-closed 트리거(citation 누락/계약실패) 시 즉시 safe_response로 전환",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    rec = calc_recommended(args.first_token, args.p95, args.reconnect)
    write_markdown(args, rec)

    print("Latency budget generated:", OUT_MD)
    for key, value in rec.items():
        print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
