#!/usr/bin/env python3
"""Lint gate for chatGPT handoff documents."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath


REQUIRED_META_KEYS = ("updated_at_kst", "base_commit_hash", "release_tag", "branch")
UPDATED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+09:00$")
RACE_ID_PATTERN = re.compile(r"\brace_id\b", re.IGNORECASE)
ARTIFACT_ROOT = "docs/review/mvp_verification_pack/artifacts/"
ALLOWED_NON_ARTIFACT_EVIDENCE = {"spec_sync_report.md"}
ARTIFACT_PATH_PATTERN = re.compile(r"docs/review/mvp_verification_pack/artifacts/[A-Za-z0-9._/\-]+")
PLAIN_EVIDENCE_PATTERN = re.compile(r"(?:docs/review/mvp_verification_pack/artifacts/[A-Za-z0-9._/\-]+|spec_sync_report\.md)")
UNSTABLE_EVIDENCE_NAME_PATTERN = re.compile(r"_(?:20\d{6}|20\d{2}XX)(?=\.)")
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


@dataclass
class WarningItem:
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


def normalize_path(path: str) -> str:
    return path.strip().strip("`").strip().replace("\\", "/")


def extract_paths_from_evidence_cell(cell: str) -> set[str]:
    candidates: set[str] = set()

    # Inline code snippets.
    for match in re.findall(r"`([^`]+)`", cell):
        normalized = normalize_path(match)
        if normalized:
            candidates.add(normalized)

    # Markdown links: [label](path)
    for match in re.findall(r"\[[^\]]+\]\(([^)]+)\)", cell):
        normalized = normalize_path(match)
        if normalized:
            candidates.add(normalized)

    # Plain path tokens.
    for match in PLAIN_EVIDENCE_PATTERN.findall(cell):
        normalized = normalize_path(match)
        if normalized:
            candidates.add(normalized)

    return candidates


def parse_validation_gate_tables(path: Path, lines: list[str]) -> tuple[int, list[tuple[int, str]]]:
    scanned_tables = 0
    evidence_entries: list[tuple[int, str]] = []

    idx = 0
    while idx < len(lines):
        stripped = lines[idx].strip().lower()
        if stripped == "| gate | status | evidence |":
            scanned_tables += 1
            idx += 1
            while idx < len(lines):
                row = lines[idx].strip()
                if not row.startswith("|"):
                    break

                cells = [cell.strip() for cell in row.split("|")[1:-1]]
                if len(cells) < 3:
                    idx += 1
                    continue

                # Skip header/separator rows.
                if cells[0].lower() == "gate" and cells[1].lower() == "status":
                    idx += 1
                    continue
                if all(cell and set(cell) <= {"-"} for cell in cells):
                    idx += 1
                    continue

                evidence_cell = cells[2]
                for extracted in extract_paths_from_evidence_cell(evidence_cell):
                    evidence_entries.append((idx + 1, extracted))

                idx += 1
            continue
        idx += 1

    return scanned_tables, evidence_entries


def lint_file(path: Path) -> tuple[list[Violation], list[WarningItem], dict]:
    violations: list[Violation] = []
    warnings: list[WarningItem] = []
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

    # Validation table presence.
    if "| Gate |" not in text or "|---|---|" not in text:
        violations.append(
            Violation(
                file=path.as_posix(),
                code="DOC_GATE_TABLE_MISSING",
                message="validation gate table missing",
            )
        )

    scanned_tables, evidence_entries = parse_validation_gate_tables(path=path, lines=lines)
    if scanned_tables == 0:
        violations.append(
            Violation(
                file=path.as_posix(),
                code="DOC_GATE_EVIDENCE_MISSING",
                message="validation gate evidence table was not parsed",
            )
        )

    missing_paths: set[str] = set()
    extracted_unique: set[str] = set()

    for line_idx, evidence_path in evidence_entries:
        normalized = normalize_path(evidence_path)
        if not normalized:
            continue

        extracted_unique.add(normalized)

        if normalized.startswith(("http://", "https://")):
            warnings.append(
                WarningItem(
                    file=path.as_posix(),
                    code="DOC_EVIDENCE_EXTERNAL_PATH",
                    message=f"external evidence path detected (local path preferred): {normalized}",
                    line=line_idx,
                )
            )
            continue

        if ".." in PurePosixPath(normalized).parts:
            warnings.append(
                WarningItem(
                    file=path.as_posix(),
                    code="DOC_EVIDENCE_PATH_TRAVERSAL",
                    message=f"path traversal detected in evidence path: {normalized}",
                    line=line_idx,
                )
            )
            continue

        is_artifact = normalized.startswith(ARTIFACT_ROOT)
        is_allowlisted = normalized in ALLOWED_NON_ARTIFACT_EVIDENCE
        if not is_artifact and not is_allowlisted:
            warnings.append(
                WarningItem(
                    file=path.as_posix(),
                    code="DOC_EVIDENCE_SCOPE_WARNING",
                    message=(
                        "evidence path should be under artifacts root or spec_sync_report.md: "
                        f"{normalized}"
                    ),
                    line=line_idx,
                )
            )
            continue

        evidence_file = Path(normalized)
        if not evidence_file.exists():
            missing_paths.add(normalized)
            violations.append(
                Violation(
                    file=path.as_posix(),
                    code="DOC_EVIDENCE_NOT_FOUND",
                    message=f"evidence file does not exist: {normalized}",
                    line=line_idx,
                )
            )
            continue

        if is_artifact and UNSTABLE_EVIDENCE_NAME_PATTERN.search(evidence_file.name):
            violations.append(
                Violation(
                    file=path.as_posix(),
                    code="DOC_EVIDENCE_UNSTABLE_NAME",
                    message=(
                        "evidence filename appears date-suffixed; use stable prefix naming: "
                        f"{evidence_file.name}"
                    ),
                    line=line_idx,
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

    evidence_stats = {
        "file": path.as_posix(),
        "scanned_tables_count": scanned_tables,
        "extracted_evidence_paths_count": len(extracted_unique),
        "missing_paths_count": len(missing_paths),
        "missing_paths": sorted(missing_paths),
    }
    return violations, warnings, evidence_stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint chatGPT handoff documents")
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    violations: list[Violation] = []
    warnings: list[WarningItem] = []
    evidence_scan_by_file: list[dict] = []

    for file_path in args.files:
        path = Path(file_path)
        if not path.exists():
            violations.append(
                Violation(file=path.as_posix(), code="DOC_FILE_MISSING", message="file not found")
            )
            continue

        file_violations, file_warnings, file_evidence_stats = lint_file(path)
        violations.extend(file_violations)
        warnings.extend(file_warnings)
        evidence_scan_by_file.append(file_evidence_stats)

    scanned_tables_count = sum(item["scanned_tables_count"] for item in evidence_scan_by_file)
    extracted_evidence_paths_count = sum(
        item["extracted_evidence_paths_count"] for item in evidence_scan_by_file
    )
    missing_paths_set = {
        path
        for item in evidence_scan_by_file
        for path in item["missing_paths"]
    }
    missing_paths = sorted(missing_paths_set)

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "violation_count": len(violations),
        "violations": [asdict(v) for v in violations],
        "warning_count": len(warnings),
        "warnings": [asdict(w) for w in warnings],
        "scanned_tables_count": scanned_tables_count,
        "extracted_evidence_paths_count": extracted_evidence_paths_count,
        "missing_paths_count": len(missing_paths),
        "missing_paths": missing_paths,
        "evidence_scan_by_file": evidence_scan_by_file,
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
        f"warning_count={payload['warning_count']}",
        f"scanned_tables_count={payload['scanned_tables_count']}",
        f"extracted_evidence_paths_count={payload['extracted_evidence_paths_count']}",
        f"missing_paths_count={payload['missing_paths_count']}",
    ]
    for missing in payload["missing_paths"]:
        lines.append(f"- missing_path={missing}")
    for item in payload["violations"]:
        lines.append(
            f"- {item['file']}:{item.get('line') or '-'} [{item['code']}] {item['message']}"
        )
    for item in payload["warnings"]:
        lines.append(
            f"- {item['file']}:{item.get('line') or '-'} [WARN:{item['code']}] {item['message']}"
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
