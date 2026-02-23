#!/usr/bin/env python3
"""Fail-closed gate for spec_sync_report.md updates on canonical spec changes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path


CANONICAL_SPEC_FILES = {
    "docs/references/cs ai chatbot_requirements statement.csv",
    "docs/references/summary of key features.csv",
    "docs/references/development environment.csv",
    "docs/references/google_ready_api_spec_v0.3_20260216.xlsx",
    "docs/references/cs_ai_chatbot_db.xlsx",
}
CANONICAL_SPEC_GLOBS = [
    "docs/uiux/cs_rag_ui_ux_*.xlsx",
]
REQUIRED_METADATA_GROUPS = [
    ("Last synced at", ["last synced at"]),
    ("Source file", ["source file"]),
    ("Version/commit", ["version", "commit"]),
    ("Change summary", ["change summary"]),
]


@dataclass
class Violation:
    code: str
    message: str
    details: str


def normalize(path: str) -> str:
    return path.strip().replace("\\", "/")


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
    if normalized in CANONICAL_SPEC_FILES:
        return True
    return any(fnmatch(normalized, pattern) for pattern in CANONICAL_SPEC_GLOBS)


def find_missing_metadata_tokens(report_text: str) -> list[str]:
    lowered = report_text.lower()
    missing: list[str] = []
    for label, token_group in REQUIRED_METADATA_GROUPS:
        if not any(token in lowered for token in token_group):
            missing.append(label)
    return missing


def render_text(payload: dict) -> str:
    lines = [
        "assert_spec_sync_report_updated",
        f"status={payload['status']}",
        f"changed_files_count={payload['changed_files_count']}",
        f"spec_changed_count={payload['spec_changed_count']}",
        f"spec_sync_report_changed={payload['spec_sync_report_changed']}",
        f"require_metadata={payload['require_metadata']}",
        f"violation_count={len(payload['violations'])}",
    ]
    if payload["spec_changed_files"]:
        lines.append(f"spec_changed_files={','.join(payload['spec_changed_files'])}")
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

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "changed_files_count": len(changed_files),
        "spec_changed_count": len(spec_changed),
        "spec_changed_files": spec_changed,
        "spec_sync_report_changed": report_changed,
        "require_metadata": bool(args.require_metadata),
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
