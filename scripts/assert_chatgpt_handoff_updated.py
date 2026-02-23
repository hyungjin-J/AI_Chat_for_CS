#!/usr/bin/env python3
"""Fail-closed gate for chatGPT handoff doc updates with beginner-friendly trigger scope."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


REQUIRED_HANDOFF_DOCS = (
    "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md",
    "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md",
)
CORE_TRIGGER_PREFIXES = (
    "backend/src/",
    "frontend/src/",
    "scripts/",
    ".github/workflows/",
    "docs/references/",
    "docs/uiux/",
)
CORE_TRIGGER_EXACT = {
    "agents.md",
    "spec_sync_report.md",
}
NON_BLOCKING_PREFIXES = (
    "docs/review/mvp_verification_pack/artifacts/",
    "docs/review/agent_reports/",
    "docs/workpacks/",
    "tmp/",
)


@dataclass
class Violation:
    code: str
    message: str
    details: str


@dataclass
class WarningItem:
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
        command = ["git", "diff", "--name-only", f"{base_ref}..{head_ref}"]
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


def render_text(payload: dict) -> str:
    lines = [
        "assert_chatgpt_handoff_updated",
        f"status={payload['status']}",
        f"mode={payload['mode']}",
        f"changed_files_count={payload['changed_files_count']}",
        f"trigger_changed_count={payload['trigger_changed_count']}",
        f"core_changed_count={payload['core_changed_count']}",
        f"non_core_changed_count={payload['non_core_changed_count']}",
        f"non_blocking_changed_count={payload['non_blocking_changed_count']}",
        f"handoff_docs_changed_count={payload['handoff_docs_changed_count']}",
        f"required_handoff_docs_changed={payload['required_handoff_docs_changed']}",
        f"violation_count={len(payload['violations'])}",
        f"warning_count={len(payload['warnings'])}",
    ]
    if payload["missing_handoff_docs"]:
        lines.append(f"missing_handoff_docs={','.join(payload['missing_handoff_docs'])}")
    if payload["trigger_changed_files"]:
        lines.append(f"trigger_changed_files={','.join(payload['trigger_changed_files'])}")
    if payload["core_changed_files"]:
        lines.append(f"core_changed_files={','.join(payload['core_changed_files'])}")
    if payload["non_core_changed_files"]:
        lines.append(f"non_core_changed_files={','.join(payload['non_core_changed_files'])}")
    if payload["non_blocking_changed_files"]:
        lines.append(f"non_blocking_changed_files={','.join(payload['non_blocking_changed_files'])}")
    for violation in payload["violations"]:
        lines.append(f"- [{violation['code']}] {violation['message']} :: {violation['details']}")
    for warning in payload["warnings"]:
        lines.append(f"- [WARN:{warning['code']}] {warning['message']} :: {warning['details']}")
    return "\n".join(lines) + "\n"


def write_output(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Require chatGPT handoff docs updates when non-handoff files change"
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--base-ref", help="Base git ref for diff (for example origin/main)")
    parser.add_argument("--head-ref", default="HEAD", help="Head git ref (default: HEAD)")
    parser.add_argument("--changed-files", help="Optional changed-files list (comma/newline separated)")
    parser.add_argument(
        "--mode",
        choices=("core-only", "strict-all"),
        default="core-only",
        help="core-only: fail only on core implementation changes; strict-all: fail on any non-handoff change",
    )
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    return parser.parse_args()


def is_core_trigger(path_lower: str) -> bool:
    if path_lower in CORE_TRIGGER_EXACT:
        return True
    return any(path_lower.startswith(prefix) for prefix in CORE_TRIGGER_PREFIXES)


def is_non_blocking_path(path_lower: str) -> bool:
    return any(path_lower.startswith(prefix) for prefix in NON_BLOCKING_PREFIXES)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()

    changed_files = parse_changed_files(args.changed_files)
    if not changed_files:
        changed_files = read_changed_files_from_git(root=root, base_ref=args.base_ref, head_ref=args.head_ref)

    required_docs_norm = {normalize(path).lower() for path in REQUIRED_HANDOFF_DOCS}
    changed_norm_map = {normalize(path).lower(): normalize(path) for path in changed_files}
    changed_norm_set = set(changed_norm_map.keys())

    handoff_changed = sorted(path for path in changed_files if normalize(path).lower() in required_docs_norm)
    non_handoff_changed = sorted(
        path for path in changed_files if normalize(path).lower() not in required_docs_norm
    )
    core_changed = sorted(
        path for path in non_handoff_changed if is_core_trigger(normalize(path).lower())
    )
    non_blocking_changed = sorted(
        path
        for path in non_handoff_changed
        if not is_core_trigger(normalize(path).lower()) and is_non_blocking_path(normalize(path).lower())
    )
    non_core_changed = sorted(
        path
        for path in non_handoff_changed
        if not is_core_trigger(normalize(path).lower()) and not is_non_blocking_path(normalize(path).lower())
    )

    if args.mode == "strict-all":
        trigger_changed = non_handoff_changed
    else:
        trigger_changed = core_changed

    missing_handoff_docs = sorted(
        path
        for path in REQUIRED_HANDOFF_DOCS
        if normalize(path).lower() not in changed_norm_set
    )

    violations: list[Violation] = []
    warnings: list[WarningItem] = []
    if trigger_changed and missing_handoff_docs:
        if args.mode == "strict-all":
            message = (
                "non-handoff changes detected but required chatGPT handoff docs were not both updated"
            )
        else:
            message = (
                "core implementation changes detected but required chatGPT handoff docs were not both updated"
            )
        violations.append(
            Violation(
                code="CHATGPT_HANDOFF_NOT_UPDATED",
                message=message,
                details="missing=" + ",".join(missing_handoff_docs),
            )
        )
    elif args.mode == "core-only" and non_core_changed and missing_handoff_docs:
        warnings.append(
            WarningItem(
                code="CHATGPT_HANDOFF_RECOMMENDED",
                message=(
                    "non-core changes were detected; handoff docs update is recommended but not mandatory"
                ),
                details="non_core=" + ",".join(non_core_changed),
            )
        )

    required_handoff_docs_changed = not missing_handoff_docs
    payload = {
        "status": "PASS" if not violations else "FAIL",
        "mode": args.mode,
        "changed_files_count": len(changed_files),
        "trigger_changed_count": len(trigger_changed),
        "trigger_changed_files": trigger_changed,
        "core_changed_count": len(core_changed),
        "core_changed_files": core_changed,
        "non_core_changed_count": len(non_core_changed),
        "non_core_changed_files": non_core_changed,
        "non_blocking_changed_count": len(non_blocking_changed),
        "non_blocking_changed_files": non_blocking_changed,
        "handoff_docs_changed_count": len(handoff_changed),
        "required_handoff_docs_changed": required_handoff_docs_changed,
        "missing_handoff_docs": missing_handoff_docs,
        "violations": [asdict(item) for item in violations],
        "warnings": [asdict(item) for item in warnings],
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
