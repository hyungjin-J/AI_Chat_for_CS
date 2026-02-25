#!/usr/bin/env python3
"""Fail-closed gate for spec_sync_report.md updates on canonical spec changes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from fnmatch import fnmatch
from pathlib import Path

CANONICAL_SPEC_FILES_TO_NOTION = {
    "docs/references/cs ai chatbot_requirements statement.csv": "https://www.notion.so/2ed405a3a720816594e4dc34972174ec",
    "docs/references/summary of key features.csv": "https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149",
    "docs/references/development environment.csv": "https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7",
    "docs/references/google_ready_api_spec_v0.3_20260216.xlsx": "https://www.notion.so/2ed405a3a720816594e4dc34972174ec",
    "docs/references/cs_ai_chatbot_db.xlsx": "https://www.notion.so/2ed405a3a720812180d9d508b77f31a4",
}
CANONICAL_SPEC_GLOBS_TO_NOTION = [
    ("docs/uiux/cs_rag_ui_ux_*.xlsx", "https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444"),
]
REQUIRED_METADATA_GROUPS = [
    ("Last synced at", ["last synced at"]),
    ("Source file", ["source file"]),
    ("Version/commit", ["version", "commit"]),
    ("Change summary", ["change summary"]),
]
STRICT_CODE_MESSAGES = {
    "SPEC_SYNC_EVIDENCE_BLOCK_MISSING": "spec_sync_report.md is missing source-specific evidence block",
    "SPEC_SYNC_LAST_SYNCED_AT_INVALID_KST": "Last synced at must be KST format YYYY-MM-DD HH:MM:SS +09:00",
    "SPEC_SYNC_VERSION_COMMIT_MISSING": "Version/commit must contain a commit hash (7~40 hex chars)",
    "SPEC_SYNC_VERSION_HEAD_MISMATCH": "Version/commit hash must include current HEAD commit hash",
    "SPEC_SYNC_NOTION_URL_MISSING": "Notion URL is missing in matched source evidence section",
    "SPEC_SYNC_NOTION_URL_MISMATCH": "Notion URL does not match canonical source-to-Notion mapping",
    "SPEC_SYNC_CHANGE_SUMMARY_COUNT_INVALID": "Change summary must contain 3~10 lines",
}
KST_SYNC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+09:00$")
COMMIT_HASH_PATTERN = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
NOTION_URL_PATTERN = re.compile(r"https://www\.notion\.so/[^\s`)>]+")
SOURCE_FILE_LINE_PATTERN = re.compile(r"^\s*-\s*source file(?:s)?\s*:\s*(.*)$", re.IGNORECASE)
LAST_SYNCED_AT_LINE_PATTERN = re.compile(r"^\s*-\s*last synced at\s*:\s*(.*)$", re.IGNORECASE)
VERSION_LINE_PATTERN = re.compile(r"^\s*-\s*version[^:]*:\s*(.*)$", re.IGNORECASE)
CHANGE_SUMMARY_LINE_PATTERN = re.compile(r"^\s*-\s*change summary\s*:\s*(.*)$", re.IGNORECASE)
SECTION_HEADING_PATTERN = re.compile(r"^\s*##\s+\S")
METADATA_BULLET_PATTERN = re.compile(r"^\s*-\s+[^:]{1,80}:\s*")


@dataclass
class Violation:
    code: str
    message: str
    details: str


@dataclass
class SectionEvidence:
    title: str
    line_start: int
    source_files: list[str] = field(default_factory=list)
    last_synced_at: str = ""
    version_raw: str = ""
    notion_urls: list[str] = field(default_factory=list)
    change_summary_line_count: int = 0


@dataclass
class SectionCheckResult:
    section: str
    last_synced_valid: bool
    version_has_hash: bool
    version_head_match: bool
    notion_url_present: bool
    notion_url_match: bool
    change_summary_line_count: int
    change_summary_valid: bool
    version_hashes: list[str] = field(default_factory=list)


@dataclass
class SourceEvidenceResult:
    source_file: str
    expected_notion_url: str
    status: str
    matched_section_count: int
    matched_sections: list[str] = field(default_factory=list)
    passed_sections: list[str] = field(default_factory=list)
    failed_check_codes: list[str] = field(default_factory=list)
    section_checks: list[SectionCheckResult] = field(default_factory=list)


def normalize(path: str) -> str:
    return path.strip().replace("\\", "/")


def normalize_notion_url(value: str) -> str:
    return value.strip().strip("`").rstrip("/")


def normalize_source_token(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"^(?:-|\d+\.)\s+", "", cleaned)
    cleaned = cleaned.strip("`").strip()
    cleaned = cleaned.strip("()")
    return normalize(cleaned)


def parse_changed_files(raw: str | None) -> list[str]:
    if raw is None:
        return []
    values: list[str] = []
    for token in raw.replace(",", "\n").splitlines():
        normalized = normalize(token)
        if normalized:
            values.append(normalized)
    return sorted(set(values))


def read_changed_files_from_git(root: Path, base_ref: str | None, head_ref: str) -> list[str]:
    if base_ref:
        diff_range = f"{base_ref}..{head_ref}"
        command = ["git", "diff", "--name-only", diff_range]
    else:
        command = ["git", "diff", "--name-only", head_ref]

    proc = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tracked = parse_changed_files(proc.stdout) if proc.returncode == 0 else []

    untracked_proc = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    untracked = parse_changed_files(untracked_proc.stdout) if untracked_proc.returncode == 0 else []
    return sorted(set(tracked + untracked))


def is_canonical_spec(path: str) -> bool:
    normalized = normalize(path).lower()
    if normalized in CANONICAL_SPEC_FILES_TO_NOTION:
        return True
    return any(fnmatch(normalized, pattern) for pattern, _ in CANONICAL_SPEC_GLOBS_TO_NOTION)


def expected_notion_url(path: str) -> str:
    normalized = normalize(path).lower()
    mapped = CANONICAL_SPEC_FILES_TO_NOTION.get(normalized)
    if mapped:
        return mapped
    for pattern, url in CANONICAL_SPEC_GLOBS_TO_NOTION:
        if fnmatch(normalized, pattern):
            return url
    return ""


def find_missing_metadata_tokens(report_text: str) -> list[str]:
    lowered = report_text.lower()
    missing: list[str] = []
    for label, token_group in REQUIRED_METADATA_GROUPS:
        if not any(token in lowered for token in token_group):
            missing.append(label)
    return missing


def strip_wrapping_backticks(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("`") and cleaned.endswith("`") and len(cleaned) >= 2:
        return cleaned[1:-1].strip()
    return cleaned


def extract_source_files(section_lines: list[str]) -> list[str]:
    source_files: list[str] = []
    for index, line in enumerate(section_lines):
        match = SOURCE_FILE_LINE_PATTERN.match(line)
        if not match:
            continue

        inline_value = strip_wrapping_backticks(match.group(1))
        if inline_value:
            source_files.extend(extract_source_file_tokens(inline_value))

        probe = index + 1
        while probe < len(section_lines):
            follow_line = section_lines[probe]
            if re.match(r"^\s*#{2,}\s+\S", follow_line):
                break
            if METADATA_BULLET_PATTERN.match(follow_line):
                break
            nested_match = re.match(r"^\s{2,}(?:-|\d+\.)\s+(.+)$", follow_line)
            if nested_match:
                source_files.extend(extract_source_file_tokens(nested_match.group(1)))
            probe += 1

    dedup: list[str] = []
    seen: set[str] = set()
    for item in source_files:
        normalized = normalize_source_token(item)
        lower = normalized.lower()
        if not normalized:
            continue
        if lower in seen:
            continue
        if not lower.endswith(".csv") and not lower.endswith(".xlsx"):
            continue
        dedup.append(normalized)
        seen.add(lower)
    return dedup


def extract_source_file_tokens(raw_value: str) -> list[str]:
    parts = [raw_value]
    if "," in raw_value:
        parts = [token for token in raw_value.split(",")]
    values: list[str] = []
    for token in parts:
        normalized = normalize_source_token(token)
        if normalized:
            values.append(normalized)
    return values


def extract_last_synced_at(section_lines: list[str]) -> str:
    for line in section_lines:
        match = LAST_SYNCED_AT_LINE_PATTERN.match(line)
        if match:
            return strip_wrapping_backticks(match.group(1))
    return ""


def extract_version_raw(section_lines: list[str]) -> str:
    for line in section_lines:
        match = VERSION_LINE_PATTERN.match(line)
        if match:
            return strip_wrapping_backticks(match.group(1))
    return ""


def extract_notion_urls(section_lines: list[str]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    joined = "\n".join(section_lines)
    for match in NOTION_URL_PATTERN.findall(joined):
        cleaned = normalize_notion_url(match)
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        urls.append(cleaned)
        seen.add(cleaned)
    return urls


def extract_change_summary_line_count(section_lines: list[str]) -> int:
    for index, line in enumerate(section_lines):
        match = CHANGE_SUMMARY_LINE_PATTERN.match(line)
        if not match:
            continue

        count = 0
        inline_value = strip_wrapping_backticks(match.group(1))
        if inline_value:
            count += 1

        probe = index + 1
        while probe < len(section_lines):
            follow_line = section_lines[probe]
            if re.match(r"^\s*#{2,}\s+\S", follow_line):
                break
            if METADATA_BULLET_PATTERN.match(follow_line):
                break
            if re.match(r"^\s*\d+\.\s+\S", follow_line):
                count += 1
            elif re.match(r"^\s*-\s+\S", follow_line):
                count += 1
            probe += 1
        return count
    return 0


def parse_spec_sync_sections(report_text: str) -> list[SectionEvidence]:
    lines = report_text.splitlines()
    if not lines:
        return []

    section_start_indexes = [index for index, line in enumerate(lines) if SECTION_HEADING_PATTERN.match(line)]
    if not section_start_indexes:
        section_start_indexes = [0]

    sections: list[SectionEvidence] = []
    for index, start in enumerate(section_start_indexes):
        end = section_start_indexes[index + 1] if index + 1 < len(section_start_indexes) else len(lines)
        section_lines = lines[start:end]
        first_line = section_lines[0] if section_lines else ""
        first_line_stripped = first_line.lstrip()
        title = first_line_stripped[2:].strip() if first_line_stripped.startswith("##") else first_line_stripped.strip()
        evidence = SectionEvidence(
            title=title or "<untitled>",
            line_start=start + 1,
            source_files=extract_source_files(section_lines),
            last_synced_at=extract_last_synced_at(section_lines),
            version_raw=extract_version_raw(section_lines),
            notion_urls=extract_notion_urls(section_lines),
            change_summary_line_count=extract_change_summary_line_count(section_lines),
        )
        sections.append(evidence)
    return sections


def section_label(section: SectionEvidence) -> str:
    return f"{section.title}@L{section.line_start}"


def section_contains_source(section: SectionEvidence, source_file: str) -> bool:
    source_lower = normalize(source_file).lower()
    return any(normalize(item).lower() == source_lower for item in section.source_files)


def extract_commit_hashes(version_raw: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in COMMIT_HASH_PATTERN.findall(version_raw):
        lowered = item.lower()
        if lowered in seen:
            continue
        values.append(lowered)
        seen.add(lowered)
    return values


def resolve_head_commit(root: Path, head_ref: str) -> tuple[str, str]:
    full_proc = subprocess.run(
        ["git", "rev-parse", head_ref],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    short_proc = subprocess.run(
        ["git", "rev-parse", "--short", head_ref],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    full_value = full_proc.stdout.strip().lower() if full_proc.returncode == 0 else ""
    short_value = short_proc.stdout.strip().lower() if short_proc.returncode == 0 else ""
    return full_value, short_value


def evaluate_source_evidence(
    source_file: str,
    expected_url: str,
    sections: list[SectionEvidence],
    head_commit: str,
    head_commit_short: str,
) -> SourceEvidenceResult:
    matched = [section for section in sections if section_contains_source(section, source_file)]
    matched_labels = [section_label(section) for section in matched]
    result = SourceEvidenceResult(
        source_file=source_file,
        expected_notion_url=expected_url,
        status="FAIL",
        matched_section_count=len(matched),
        matched_sections=matched_labels,
    )

    if not matched:
        result.failed_check_codes.append("SPEC_SYNC_EVIDENCE_BLOCK_MISSING")
        return result

    section_checks: list[SectionCheckResult] = []
    passed_sections: list[str] = []
    normalized_expected_url = normalize_notion_url(expected_url)
    for section in matched:
        version_hashes = extract_commit_hashes(section.version_raw)
        has_hash = bool(version_hashes)
        head_match = bool(
            has_hash
            and (
                (head_commit and head_commit in version_hashes)
                or (head_commit_short and head_commit_short in version_hashes)
            )
        )
        notion_url_present = bool(section.notion_urls)
        notion_url_match = bool(
            normalized_expected_url and normalized_expected_url in section.notion_urls
        )
        summary_valid = 3 <= section.change_summary_line_count <= 10
        last_synced_valid = bool(KST_SYNC_PATTERN.fullmatch(section.last_synced_at))

        check = SectionCheckResult(
            section=section_label(section),
            last_synced_valid=last_synced_valid,
            version_has_hash=has_hash,
            version_head_match=head_match,
            notion_url_present=notion_url_present,
            notion_url_match=notion_url_match,
            change_summary_line_count=section.change_summary_line_count,
            change_summary_valid=summary_valid,
            version_hashes=version_hashes,
        )
        section_checks.append(check)

        if (
            check.last_synced_valid
            and check.version_has_hash
            and check.version_head_match
            and check.notion_url_match
            and check.change_summary_valid
        ):
            passed_sections.append(check.section)

    result.section_checks = section_checks
    result.passed_sections = passed_sections

    if passed_sections:
        result.status = "PASS"
        return result

    if not any(item.last_synced_valid for item in section_checks):
        result.failed_check_codes.append("SPEC_SYNC_LAST_SYNCED_AT_INVALID_KST")
    if not any(item.version_has_hash for item in section_checks):
        result.failed_check_codes.append("SPEC_SYNC_VERSION_COMMIT_MISSING")
    elif not any(item.version_head_match for item in section_checks):
        result.failed_check_codes.append("SPEC_SYNC_VERSION_HEAD_MISMATCH")
    if not any(item.notion_url_present for item in section_checks):
        result.failed_check_codes.append("SPEC_SYNC_NOTION_URL_MISSING")
    elif not any(item.notion_url_match for item in section_checks):
        result.failed_check_codes.append("SPEC_SYNC_NOTION_URL_MISMATCH")
    if not any(item.change_summary_valid for item in section_checks):
        result.failed_check_codes.append("SPEC_SYNC_CHANGE_SUMMARY_COUNT_INVALID")
    return result


def build_strict_violation(
    code: str,
    source_file: str,
    expected_url: str,
    matched_sections: list[str],
) -> Violation:
    matched_display = ",".join(matched_sections) if matched_sections else "none"
    return Violation(
        code=code,
        message=STRICT_CODE_MESSAGES[code],
        details=f"source_file={source_file}; expected_notion_url={expected_url}; matched_sections={matched_display}",
    )


def render_text(payload: dict) -> str:
    lines = [
        "assert_spec_sync_report_updated",
        f"status={payload['status']}",
        f"changed_files_count={payload['changed_files_count']}",
        f"spec_changed_count={payload['spec_changed_count']}",
        f"spec_sync_report_changed={payload['spec_sync_report_changed']}",
        f"require_metadata={payload['require_metadata']}",
        f"require_notion_evidence_format={payload['require_notion_evidence_format']}",
        f"head_commit={payload['head_commit']}",
        f"head_commit_short={payload['head_commit_short']}",
        f"evidence_section_count={payload['evidence_section_count']}",
        f"violation_count={len(payload['violations'])}",
    ]
    if payload["spec_changed_files"]:
        lines.append(f"spec_changed_files={','.join(payload['spec_changed_files'])}")
    for result in payload["source_evidence_results"]:
        lines.append(
            "source_evidence="
            f"{result['source_file']} status={result['status']} "
            f"expected_notion_url={result['expected_notion_url']} "
            f"matched_section_count={result['matched_section_count']}"
        )
        if result["matched_sections"]:
            lines.append(f"  matched_sections={','.join(result['matched_sections'])}")
        if result["passed_sections"]:
            lines.append(f"  passed_sections={','.join(result['passed_sections'])}")
        if result["failed_check_codes"]:
            lines.append(f"  failed_check_codes={','.join(result['failed_check_codes'])}")
    for violation in payload["violations"]:
        lines.append(f"- [{violation['code']}] {violation['message']} :: {violation['details']}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Require spec_sync_report.md update when canonical specs change")
    parser.add_argument("--root", default=".")
    parser.add_argument("--base-ref", help="Base git ref for diff (for example origin/main)")
    parser.add_argument("--head-ref", default="HEAD", help="Head git ref (default: HEAD)")
    parser.add_argument("--changed-files", help="Optional changed-files list (comma/newline separated)")
    parser.add_argument("--spec-sync-report", default="spec_sync_report.md")
    parser.add_argument("--require-metadata", action="store_true")
    parser.add_argument("--require-notion-evidence-format", action="store_true")
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    return parser.parse_args()


def write_output(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()

    changed_files = parse_changed_files(args.changed_files)
    if not changed_files:
        changed_files = read_changed_files_from_git(root, args.base_ref, args.head_ref)

    spec_changed = sorted(path for path in changed_files if is_canonical_spec(path))
    spec_sync_report_path = normalize(args.spec_sync_report)
    normalized_changed = {normalize(path).lower() for path in changed_files}
    report_changed = spec_sync_report_path.lower() in normalized_changed

    violations: list[Violation] = []
    head_commit = ""
    head_commit_short = ""
    evidence_section_count = 0
    source_evidence_results: list[SourceEvidenceResult] = []
    if spec_changed and not report_changed:
        violations.append(
            Violation(
                code="SPEC_SYNC_REPORT_NOT_UPDATED",
                message="canonical spec files changed but spec_sync_report.md was not updated",
                details=",".join(spec_changed),
            )
        )

    if spec_changed and report_changed and args.require_metadata:
        report_file = root / spec_sync_report_path
        if not report_file.exists():
            violations.append(
                Violation(
                    code="SPEC_SYNC_REPORT_MISSING",
                    message="spec_sync_report.md is listed as changed but file was not found",
                    details=report_file.as_posix(),
                )
            )
        else:
            report_text = report_file.read_text(encoding="utf-8", errors="strict")
            missing_metadata = find_missing_metadata_tokens(report_text)
            if missing_metadata:
                violations.append(
                    Violation(
                        code="SPEC_SYNC_REPORT_METADATA_MISSING",
                        message="spec_sync_report.md is missing required metadata tokens",
                        details=",".join(missing_metadata),
                    )
                )

            if args.require_notion_evidence_format:
                sections = parse_spec_sync_sections(report_text)
                evidence_section_count = len(sections)
                head_commit, head_commit_short = resolve_head_commit(root=root, head_ref=args.head_ref)
                for source_file in spec_changed:
                    expected_url = expected_notion_url(source_file)
                    source_result = evaluate_source_evidence(
                        source_file=source_file,
                        expected_url=expected_url,
                        sections=sections,
                        head_commit=head_commit,
                        head_commit_short=head_commit_short,
                    )
                    source_evidence_results.append(source_result)
                    if source_result.status == "FAIL":
                        for code in source_result.failed_check_codes:
                            violations.append(
                                build_strict_violation(
                                    code=code,
                                    source_file=source_file,
                                    expected_url=expected_url,
                                    matched_sections=source_result.matched_sections,
                                )
                            )

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "changed_files_count": len(changed_files),
        "spec_changed_count": len(spec_changed),
        "spec_changed_files": spec_changed,
        "spec_sync_report_changed": report_changed,
        "require_metadata": bool(args.require_metadata),
        "require_notion_evidence_format": bool(args.require_notion_evidence_format),
        "head_commit": head_commit,
        "head_commit_short": head_commit_short,
        "evidence_section_count": evidence_section_count,
        "source_evidence_results": [asdict(item) for item in source_evidence_results],
        "violations": [asdict(item) for item in violations],
    }

    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    output_txt = Path(args.output_txt) if args.output_txt else None
    output_json = Path(args.output_json) if args.output_json else None
    write_output(output_txt, text_report)
    write_output(output_json, json_report)

    sys.stdout.write(text_report)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
