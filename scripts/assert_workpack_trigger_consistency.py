#!/usr/bin/env python3
"""Fail-closed lint: AGENTS/manual trigger patterns must match contract JSON."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Violation:
    code: str
    message: str
    details: str


def normalize_pattern(raw: str) -> str:
    return raw.strip().strip("`").replace("\\", "/")


def extract_bullets_after_heading(text: str, heading_token: str) -> list[str]:
    lines = text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        if heading_token in line:
            start_index = index + 1
            break
    if start_index is None:
        return []

    bullets: list[str] = []
    started = False
    for line in lines[start_index:]:
        stripped = line.strip()
        if stripped.startswith("#### ") and started:
            break
        if stripped.startswith("## ") and started:
            break
        if stripped.startswith("- "):
            bullets.append(normalize_pattern(stripped[2:]))
            started = True
            continue
        if started and stripped == "":
            continue
        if started and not stripped.startswith("- "):
            break
    return bullets


def render_text(payload: dict) -> str:
    lines = [
        "assert_workpack_trigger_consistency",
        f"status={payload['status']}",
        f"agents_pattern_count={len(payload['agents_patterns'])}",
        f"manual_pattern_count={len(payload['manual_patterns'])}",
        f"contract_pattern_count={len(payload['contract_patterns'])}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(f"- [{item['code']}] {item['message']} :: {item['details']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert workpack trigger consistency")
    parser.add_argument("--root", default=".")
    parser.add_argument("--agents", default="AGENTS.md")
    parser.add_argument("--manual", default="docs/agent_manual/02_working_memory_contract.md")
    parser.add_argument("--contract", default="scripts/contracts/workpack_agent_report_contract.json")
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    agents_path = root / args.agents
    manual_path = root / args.manual
    contract_path = root / args.contract

    violations: list[Violation] = []

    if not agents_path.exists():
        violations.append(Violation("AGENTS_FILE_MISSING", "AGENTS file missing", agents_path.as_posix()))
        agents_patterns: list[str] = []
    else:
        agents_text = agents_path.read_text(encoding="utf-8", errors="strict")
        agents_patterns = extract_bullets_after_heading(agents_text, "12.3-A Working Memory")
        if not agents_patterns:
            violations.append(
                Violation(
                    "AGENTS_TRIGGER_SECTION_MISSING",
                    "could not extract trigger patterns from AGENTS",
                    "missing heading or bullet list",
                )
            )

    if not manual_path.exists():
        violations.append(Violation("MANUAL_FILE_MISSING", "agent manual file missing", manual_path.as_posix()))
        manual_patterns: list[str] = []
    else:
        manual_text = manual_path.read_text(encoding="utf-8", errors="strict")
        manual_patterns = extract_bullets_after_heading(manual_text, "Trigger Patterns (Fail-Closed)")
        if not manual_patterns:
            violations.append(
                Violation(
                    "MANUAL_TRIGGER_SECTION_MISSING",
                    "could not extract trigger patterns from agent manual",
                    "missing heading or bullet list",
                )
            )

    if not contract_path.exists():
        violations.append(Violation("CONTRACT_FILE_MISSING", "contract file missing", contract_path.as_posix()))
        contract_patterns: list[str] = []
    else:
        contract_json = json.loads(contract_path.read_text(encoding="utf-8", errors="strict"))
        raw_patterns = contract_json.get("high_risk_patterns", [])
        if not isinstance(raw_patterns, list):
            violations.append(
                Violation(
                    "CONTRACT_INVALID",
                    "high_risk_patterns must be a list",
                    contract_path.as_posix(),
                )
            )
            raw_patterns = []
        contract_patterns = [normalize_pattern(str(item)) for item in raw_patterns]

    if agents_patterns and contract_patterns and agents_patterns != contract_patterns:
        violations.append(
            Violation(
                "AGENTS_CONTRACT_MISMATCH",
                "AGENTS trigger patterns must match contract high_risk_patterns",
                f"agents={agents_patterns} contract={contract_patterns}",
            )
        )

    if manual_patterns and contract_patterns and manual_patterns != contract_patterns:
        violations.append(
            Violation(
                "MANUAL_CONTRACT_MISMATCH",
                "agent manual trigger patterns must match contract high_risk_patterns",
                f"manual={manual_patterns} contract={contract_patterns}",
            )
        )

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "agents_patterns": agents_patterns,
        "manual_patterns": manual_patterns,
        "contract_patterns": contract_patterns,
        "violation_count": len(violations),
        "violations": [asdict(v) for v in violations],
    }

    report_txt = render_text(payload)
    report_json = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output_txt:
        output_txt = Path(args.output_txt)
        output_txt.parent.mkdir(parents=True, exist_ok=True)
        output_txt.write_text(report_txt, encoding="utf-8")
    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(report_json, encoding="utf-8")

    sys.stdout.write(report_txt)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
