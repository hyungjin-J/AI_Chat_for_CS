#!/usr/bin/env python3
"""Fail-closed contract for workpack and specialized agent reports."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path


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


def read_changed_files_from_git(root: Path, base_ref: str | None) -> list[str]:
    if base_ref:
        diff_target = f"{base_ref}...HEAD"
        command = ["git", "diff", "--name-only", diff_target]
    else:
        command = ["git", "diff", "--name-only", "HEAD"]
    proc = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return []
    return parse_changed_files(proc.stdout)


def is_high_risk(changed_files: list[str], patterns: list[str]) -> bool:
    for path in changed_files:
        for pattern in patterns:
            if fnmatch(path, pattern):
                return True
    return False


def find_complete_workpacks(root: Path, contract: dict) -> tuple[list[str], list[str], list[Violation]]:
    workpack_root = root / contract["workpack_root"]
    required = contract["required_workpack_files"]
    manual_tokens = contract["manual_hook_reference_tokens"]

    complete_dirs: list[str] = []
    manual_ref_dirs: list[str] = []
    violations: list[Violation] = []

    if not workpack_root.exists():
        violations.append(
            Violation(
                code="WORKPACK_ROOT_MISSING",
                message="required workpack root does not exist",
                details=workpack_root.as_posix(),
            )
        )
        return complete_dirs, manual_ref_dirs, violations

    for topic_dir in sorted(path for path in workpack_root.iterdir() if path.is_dir()):
        missing = [name for name in required if not (topic_dir / name).exists()]
        if missing:
            continue
        topic = topic_dir.name
        complete_dirs.append(topic)

        context_path = topic_dir / "02_context.md"
        context_text = context_path.read_text(encoding="utf-8", errors="strict")
        if any(token in context_text for token in manual_tokens):
            manual_ref_dirs.append(topic)

    if not complete_dirs:
        violations.append(
            Violation(
                code="WORKPACK_REQUIRED_SET_MISSING",
                message="at least one complete workpack(01/02/03) is required for high-risk changes",
                details=workpack_root.as_posix(),
            )
        )

    if complete_dirs and not manual_ref_dirs:
        violations.append(
            Violation(
                code="WORKPACK_MANUAL_HOOK_REFERENCE_MISSING",
                message="02_context.md must reference manual hook output evidence",
                details=f"expected one of {manual_tokens}",
            )
        )

    return complete_dirs, manual_ref_dirs, violations


def find_complete_agent_reports(root: Path, contract: dict) -> tuple[list[str], list[Violation]]:
    report_root = root / contract["agent_report_root"]
    required = contract["required_agent_reports"]
    complete_dirs: list[str] = []
    violations: list[Violation] = []

    if not report_root.exists():
        violations.append(
            Violation(
                code="AGENT_REPORT_ROOT_MISSING",
                message="required agent report root does not exist",
                details=report_root.as_posix(),
            )
        )
        return complete_dirs, violations

    for topic_dir in sorted(path for path in report_root.iterdir() if path.is_dir()):
        missing = [name for name in required if not (topic_dir / name).exists()]
        if missing:
            continue
        complete_dirs.append(topic_dir.name)

    if not complete_dirs:
        violations.append(
            Violation(
                code="AGENT_REPORT_REQUIRED_SET_MISSING",
                message="DDD/SEC/QA report files are required for high-risk changes",
                details=report_root.as_posix(),
            )
        )
    return complete_dirs, violations


def render_text(payload: dict) -> str:
    lines = [
        "assert_workpack_agent_report_contract",
        f"status={payload['status']}",
        f"high_risk_triggered={payload['high_risk_triggered']}",
        f"changed_files_count={payload['changed_files_count']}",
        f"workpack_topics={','.join(payload['complete_workpack_topics']) or '-'}",
        f"workpack_topics_with_manual_hook_ref={','.join(payload['manual_hook_workpack_topics']) or '-'}",
        f"agent_report_topics={','.join(payload['complete_agent_report_topics']) or '-'}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(f"- [{item['code']}] {item['message']} :: {item['details']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert workpack and specialized agent report contract")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument(
        "--contract",
        default="scripts/contracts/workpack_agent_report_contract.json",
        help="Contract JSON path",
    )
    parser.add_argument("--changed-files", help="Changed file list (comma or newline separated)")
    parser.add_argument("--git-base-ref", help="Optional git base ref (ex: origin/main)")
    parser.add_argument("--use-git-diff", action="store_true", help="Populate changed files from git diff")
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    contract_path = (root / args.contract) if not Path(args.contract).is_absolute() else Path(args.contract)
    contract = json.loads(contract_path.read_text(encoding="utf-8", errors="strict"))

    changed_files = parse_changed_files(args.changed_files)
    if args.use_git_diff:
        changed_files = read_changed_files_from_git(root=root, base_ref=args.git_base_ref)

    high_risk_triggered = is_high_risk(changed_files=changed_files, patterns=contract["high_risk_patterns"])
    violations: list[Violation] = []
    complete_workpacks: list[str] = []
    manual_hook_workpacks: list[str] = []
    complete_reports: list[str] = []

    if high_risk_triggered:
        complete_workpacks, manual_hook_workpacks, workpack_violations = find_complete_workpacks(root, contract)
        violations.extend(workpack_violations)
        complete_reports, report_violations = find_complete_agent_reports(root, contract)
        violations.extend(report_violations)

        if complete_workpacks and complete_reports:
            overlap = sorted(set(complete_workpacks) & set(complete_reports))
            if not overlap:
                violations.append(
                    Violation(
                        code="WORKPACK_AGENT_REPORT_TOPIC_MISMATCH",
                        message="workpack topic and specialized report topic must overlap",
                        details=f"workpacks={complete_workpacks} reports={complete_reports}",
                    )
                )
    status = "PASS" if not violations else "FAIL"
    payload = {
        "status": status,
        "high_risk_triggered": high_risk_triggered,
        "changed_files_count": len(changed_files),
        "changed_files": changed_files,
        "complete_workpack_topics": complete_workpacks,
        "manual_hook_workpack_topics": manual_hook_workpacks,
        "complete_agent_report_topics": complete_reports,
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }

    txt_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.output_txt:
        out_txt = Path(args.output_txt)
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(txt_report, encoding="utf-8")
    if args.output_json:
        out_json = Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json_report, encoding="utf-8")

    sys.stdout.write(txt_report)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
