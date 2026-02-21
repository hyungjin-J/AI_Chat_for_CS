#!/usr/bin/env python3
"""Lint gate for chatGPT handoff docs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


REQUIRED_META_KEYS = ("updated_at_kst", "base_commit_hash", "release_tag", "branch")
UPDATED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+09:00$")
RACE_ID_PATTERN = re.compile(r"\brace_id\b", re.IGNORECASE)
FORBIDDEN_LITERAL_PATTERNS = (
    re.compile(r"NOTION_TOKEN"),
    re.compile(r"OPENAI_API_KEY"),
    re.compile(r"ACCESS_TOKEN"),
    re.compile(r"refresh_token\s*=", re.IGNORECASE),
    re.compile(r"api_key\s*=", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"\bsk-[A-Za-z0-9]{10,}\b"),
    re.compile(r"\b01[0-9]-\d{3,4}-\d{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)


@dataclass
class Violation:
    file: str
    code: str
    message: str
    line: int | None = None


def parse_meta(lines: list[str]) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in lines:
        if not line.startswith("- "):
            continue
        if ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        meta[key.strip()] = value.strip()
    return meta


def lint_file(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    text = path.read_text(encoding="utf-8", errors="strict")
    lines = text.splitlines()

    # C0 control chars: only LF/CR allowed (tab forbidden).
    for line_idx, line in enumerate(lines, start=1):
        for ch in line:
            code = ord(ch)
            if code < 32:
                violations.append(
                    Violation(
                        file=path.as_posix(),
                        code="DOC_CONTROL_CHAR",
                        message=f"C0 control char U+{code:04X} is forbidden",
                        line=line_idx,
                    )
                )

    # Placeholder / typo checks.
    for line_idx, line in enumerate(lines, start=1):
        if "$kst" in line or "TBD" in line:
            violations.append(
                Violation(
                    file=path.as_posix(),
                    code="DOC_PLACEHOLDER",
                    message="placeholder value found",
                    line=line_idx,
                )
            )
        if RACE_ID_PATTERN.search(line):
            violations.append(
                Violation(
                    file=path.as_posix(),
                    code="DOC_TRACE_TYPO",
                    message="race_id typo detected; trace_id only",
                    line=line_idx,
                )
            )

    # Metadata checks.
    meta = parse_meta(lines)
    for key in REQUIRED_META_KEYS:
        if key not in meta or not meta[key]:
            violations.append(
                Violation(
                    file=path.as_posix(),
                    code="DOC_META_MISSING",
                    message=f"required metadata missing: {key}",
                )
            )
    if "updated_at_kst" in meta and not UPDATED_AT_PATTERN.match(meta["updated_at_kst"]):
        violations.append(
            Violation(
                file=path.as_posix(),
                code="DOC_META_INVALID",
                message="updated_at_kst must be YYYY-MM-DD HH:mm:ss +09:00",
            )
        )

    # A/C/F/R summary section and minimum 10 bullet lines.
    heading = "## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)"
    if heading not in text:
        violations.append(
            Violation(
                file=path.as_posix(),
                code="DOC_SUMMARY_MISSING",
                message="required change summary heading missing",
            )
        )
    else:
        summary_lines = text.split(heading, 1)[1].split("\n## ", 1)[0].splitlines()
        bullet_count = sum(1 for ln in summary_lines if ln.strip().startswith("- "))
        if bullet_count < 10:
            violations.append(
                Violation(
                    file=path.as_posix(),
                    code="DOC_SUMMARY_SHORT",
                    message=f"change summary requires >=10 bullets, got {bullet_count}",
                )
            )

    # Validation table and artifact evidence path.
    if "| Gate |" not in text or "|---|---|" not in text:
        violations.append(
            Violation(
                file=path.as_posix(),
                code="DOC_GATE_TABLE_MISSING",
                message="validation gate table missing",
            )
        )
    if "docs/review/mvp_verification_pack/artifacts/" not in text:
        violations.append(
            Violation(
                file=path.as_posix(),
                code="DOC_EVIDENCE_PATH_MISSING",
                message="artifact evidence path missing",
            )
        )

    # Forbidden literals (security hygiene).
    for pattern in FORBIDDEN_LITERAL_PATTERNS:
        match = pattern.search(text)
        if match:
            line = text[: match.start()].count("\n") + 1
            violations.append(
                Violation(
                    file=path.as_posix(),
                    code="DOC_FORBIDDEN_LITERAL",
                    message=f"forbidden literal found ({pattern.pattern}); use <REDACTED>",
                    line=line,
                )
            )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint chatGPT handoff documents")
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    violations: list[Violation] = []
    for file_path in args.files:
        path = Path(file_path)
        if not path.exists():
            violations.append(
                Violation(file=path.as_posix(), code="DOC_FILE_MISSING", message="file not found")
            )
            continue
        violations.extend(lint_file(path))

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "violation_count": len(violations),
        "violations": [asdict(v) for v in violations],
    }
    report_json = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(report_json, encoding="utf-8")

    lines = [
        "chatgpt_handoff_doc_lint",
        f"status={payload['status']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(
            f"- {item['file']}:{item.get('line') or '-'} [{item['code']}] {item['message']}"
        )
    report_txt = "\n".join(lines) + "\n"
    if args.output_txt:
        output_txt = Path(args.output_txt)
        output_txt.parent.mkdir(parents=True, exist_ok=True)
        output_txt.write_text(report_txt, encoding="utf-8")

    sys.stdout.write(report_txt)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
