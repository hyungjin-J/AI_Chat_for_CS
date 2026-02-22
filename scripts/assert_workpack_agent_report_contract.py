#!/usr/bin/env python3
"""Fail-closed contract for workpack and specialized agent reports (v2)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path


TOPIC_REGEX_DEFAULT = r"^20\d{6}_[a-z0-9]+(?:__[a-z0-9]+)*$"
FORBIDDEN_TOPIC_TOKENS_DEFAULT = ["misc", "etc", "tmp", "temp", "update", "fix"]
STOP_SCOPE_TOKENS_DEFAULT = {
    "src",
    "main",
    "test",
    "java",
    "com",
    "aichatbot",
    "contexts",
    "channels",
    "backend",
    "frontend",
    "scripts",
    "docs",
    "review",
    "workpacks",
    "agent",
    "reports",
    "presentation",
    "application",
    "domain",
    "infrastructure",
    "github",
    "workflows",
    "chatgpt",
}
SPEC_PATTERNS_DEFAULT = [
    "docs/references/*.csv",
    "docs/references/*.xlsx",
    "docs/uiux/*.xlsx",
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
        tracked = []
    else:
        tracked = parse_changed_files(proc.stdout)

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


def is_high_risk(changed_files: list[str], patterns: list[str]) -> bool:
    for path in changed_files:
        for pattern in patterns:
            if fnmatch(path, pattern):
                return True
    return False


def is_spec_file(path: str, spec_patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in spec_patterns)


def extract_topic_from_path(path: str, root_dir: str) -> str | None:
    prefix = root_dir.rstrip("/") + "/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix):]
    parts = rest.split("/")
    if len(parts) < 2:
        return None
    topic = parts[0].strip()
    return topic or None


def filter_existing_topics(root: Path, topic_root: str, topics: set[str]) -> set[str]:
    root_path = root / topic_root
    if not root_path.exists():
        return set()
    return {topic for topic in topics if (root_path / topic).exists()}


def topic_tokens(topic: str) -> list[str]:
    if "_" not in topic:
        return []
    suffix = topic.split("_", 1)[1]
    chunks = [chunk for chunk in suffix.split("__") if chunk]
    tokens: list[str] = []
    for chunk in chunks:
        tokens.extend([token for token in chunk.split("_") if token])
    return [token.lower() for token in tokens]


def extract_scope_tokens(changed_files: list[str], ignore_roots: list[str], stop_tokens: set[str]) -> set[str]:
    tokens: set[str] = set()
    for path in changed_files:
        if any(path.startswith(root.rstrip("/") + "/") for root in ignore_roots):
            continue
        parts = re.split(r"[/_.\-]+", path.lower())
        for token in parts:
            if len(token) < 3:
                continue
            if token.isdigit():
                continue
            if token in stop_tokens:
                continue
            tokens.add(token)
    return tokens


def find_complete_workpack_topics(root: Path, contract: dict, topics: set[str]) -> tuple[list[str], list[str], list[Violation]]:
    workpack_root = root / contract["workpack_root"]
    required = [str(item) for item in contract["required_workpack_files"]]
    manual_tokens = [str(item) for item in contract["manual_hook_reference_tokens"]]

    complete_topics: list[str] = []
    manual_ref_topics: list[str] = []
    violations: list[Violation] = []

    if not topics:
        return complete_topics, manual_ref_topics, violations
    if not workpack_root.exists():
        violations.append(
            Violation(
                code="WORKPACK_ROOT_MISSING",
                message="required workpack root does not exist",
                details=workpack_root.as_posix(),
            )
        )
        return complete_topics, manual_ref_topics, violations

    for topic in sorted(topics):
        topic_dir = workpack_root / topic
        if not topic_dir.exists():
            continue
        missing = [name for name in required if not (topic_dir / name).exists()]
        if missing:
            continue
        complete_topics.append(topic)
        context_path = topic_dir / "02_context.md"
        context_text = context_path.read_text(encoding="utf-8", errors="strict")
        if any(token in context_text for token in manual_tokens):
            manual_ref_topics.append(topic)
    return complete_topics, manual_ref_topics, violations


def find_complete_report_topics(root: Path, contract: dict, topics: set[str]) -> tuple[list[str], dict[str, set[str]], list[Violation]]:
    report_root = root / contract["agent_report_root"]
    required_all = [str(item) for item in contract["required_agent_reports"]]
    complete_topics: list[str] = []
    topic_to_files: dict[str, set[str]] = {}
    violations: list[Violation] = []

    if not topics:
        return complete_topics, topic_to_files, violations
    if not report_root.exists():
        violations.append(
            Violation(
                code="AGENT_REPORT_ROOT_MISSING",
                message="required agent report root does not exist",
                details=report_root.as_posix(),
            )
        )
        return complete_topics, topic_to_files, violations

    for topic in sorted(topics):
        topic_dir = report_root / topic
        if not topic_dir.exists():
            continue
        present = {name for name in required_all if (topic_dir / name).exists()}
        topic_to_files[topic] = present
        if len(present) == len(required_all):
            complete_topics.append(topic)
    return complete_topics, topic_to_files, violations


def determine_required_report_files(scope_flags: dict, contract: dict) -> set[str]:
    mapping = contract.get("required_reports_by_scope", {})
    required: set[str] = set()
    if scope_flags["backend"]:
        required.update(mapping.get("backend", []))
    if scope_flags["frontend"]:
        required.update(mapping.get("frontend", []))
    if scope_flags["security"]:
        required.update(mapping.get("security", []))
    if not required:
        required.update(contract.get("required_agent_reports", []))
    return {str(item) for item in required}


def maybe_run_notion_exception_gate(root: Path, contract: dict) -> tuple[bool, list[Violation]]:
    spec_sync = contract.get("spec_sync", {})
    gate = spec_sync.get("manual_exception_gate", {})
    if not gate:
        return False, []

    script_path = root / str(gate.get("script", "scripts/check_notion_manual_exception_gate.py"))
    status_file = root / str(gate.get("status_file", "docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json"))
    manual_patch = root / str(gate.get("manual_patch", "docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md"))
    spec_sync_report = root / str(gate.get("spec_sync_report", "spec_sync_report.md"))

    if not script_path.exists():
        return False, [Violation("NOTION_MANUAL_GATE_SCRIPT_MISSING", "notion manual gate script missing", script_path.as_posix())]
    if not status_file.exists() or not manual_patch.exists():
        return False, []

    command = [
        sys.executable,
        str(script_path),
        "--status-file",
        str(status_file),
        "--manual-patch",
        str(manual_patch),
        "--spec-sync",
        str(spec_sync_report),
    ]
    output_json = gate.get("output_json")
    output_txt = gate.get("output_txt")
    if output_json:
        command.extend(["--output-json", str(root / str(output_json))])
    if output_txt:
        command.extend(["--output-txt", str(root / str(output_txt))])

    proc = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode == 0:
        return True, []
    details = (proc.stdout + "\n" + proc.stderr).strip()
    if len(details) > 600:
        details = details[:600] + "...(truncated)"
    return True, [
        Violation(
            code="NOTION_MANUAL_EXCEPTION_GATE_FAILED",
            message="spec-only path requires passing notion manual exception gate when evidence files exist",
            details=details,
        )
    ]


def render_text(payload: dict) -> str:
    lines = [
        "assert_workpack_agent_report_contract",
        f"status={payload['status']}",
        f"high_risk_triggered={payload['high_risk_triggered']}",
        f"changed_files_count={payload['changed_files_count']}",
        f"scope_backend={payload['scope']['backend']}",
        f"scope_frontend={payload['scope']['frontend']}",
        f"scope_security={payload['scope']['security']}",
        f"scope_spec_only={payload['scope']['spec_only']}",
        f"required_report_files={','.join(payload['required_report_files']) or '-'}",
        f"changed_workpack_topics={','.join(payload['changed_workpack_topics']) or '-'}",
        f"changed_agent_report_topics={','.join(payload['changed_agent_report_topics']) or '-'}",
        f"eligible_topics={','.join(payload['eligible_topics']) or '-'}",
        f"manual_hook_workpack_topics={','.join(payload['manual_hook_workpack_topics']) or '-'}",
        f"scope_tokens={','.join(payload['scope_tokens']) or '-'}",
        f"notion_manual_exception_gate_ran={payload['notion_manual_exception_gate_ran']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(f"- [{item['code']}] {item['message']} :: {item['details']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert workpack and specialized agent report contract")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--repo-root", dest="root", help="Alias of --root (repository root override)")
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

    workpack_root = str(contract["workpack_root"])
    agent_report_root = str(contract["agent_report_root"])
    changed_workpack_topics = {
        topic
        for path in changed_files
        for topic in [extract_topic_from_path(path, workpack_root)]
        if topic
    }
    changed_agent_report_topics = {
        topic
        for path in changed_files
        for topic in [extract_topic_from_path(path, agent_report_root)]
        if topic
    }
    changed_workpack_topics = filter_existing_topics(root, workpack_root, changed_workpack_topics)
    changed_agent_report_topics = filter_existing_topics(root, agent_report_root, changed_agent_report_topics)
    changed_topics = changed_workpack_topics | changed_agent_report_topics

    spec_sync = contract.get("spec_sync", {})
    spec_patterns = [str(item) for item in spec_sync.get("patterns", SPEC_PATTERNS_DEFAULT)]
    spec_sync_report_path = str(spec_sync.get("required_report", "spec_sync_report.md"))

    non_doc_changed_files = [
        path
        for path in changed_files
        if not path.startswith(workpack_root.rstrip("/") + "/")
        and not path.startswith(agent_report_root.rstrip("/") + "/")
    ]
    spec_changed_files = [path for path in non_doc_changed_files if is_spec_file(path, spec_patterns)]
    spec_related_files = [
        path
        for path in non_doc_changed_files
        if is_spec_file(path, spec_patterns) or path == spec_sync_report_path
    ]
    spec_only = bool(spec_changed_files) and len(spec_related_files) == len(non_doc_changed_files)

    scope_security_patterns = [str(item) for item in contract.get("security_scope_patterns", [])]
    security_change = any(
        any(fnmatch(path, pattern) for pattern in scope_security_patterns)
        for path in changed_files
    )
    scope_flags = {
        "backend": any(path.startswith("backend/") for path in changed_files),
        "frontend": any(path.startswith("frontend/") for path in changed_files),
        "security": security_change,
        "spec_only": spec_only,
    }

    stop_tokens = set(str(item) for item in contract.get("scope_stop_tokens", [])) or STOP_SCOPE_TOKENS_DEFAULT
    scope_tokens = sorted(
        extract_scope_tokens(
            changed_files,
            ignore_roots=[workpack_root, agent_report_root],
            stop_tokens=stop_tokens,
        )
    )

    topic_pattern = re.compile(str(contract.get("topic_pattern", TOPIC_REGEX_DEFAULT)))
    forbidden_topic_tokens = {
        str(item).lower() for item in contract.get("forbidden_topic_tokens", FORBIDDEN_TOPIC_TOKENS_DEFAULT)
    }

    complete_workpacks: list[str] = []
    manual_hook_workpacks: list[str] = []
    report_topic_files: dict[str, set[str]] = {}
    complete_reports: list[str] = []
    eligible_topics: list[str] = []
    required_report_files: set[str] = set()
    notion_gate_ran = False

    if high_risk_triggered:
        complete_workpacks, manual_hook_workpacks, workpack_violations = find_complete_workpack_topics(
            root,
            contract,
            changed_workpack_topics,
        )
        violations.extend(workpack_violations)
        complete_reports, report_topic_files, report_violations = find_complete_report_topics(
            root,
            contract,
            changed_agent_report_topics,
        )
        violations.extend(report_violations)

        if not changed_workpack_topics:
            violations.append(
                Violation(
                    code="WORKPACK_TOPIC_NOT_IN_DIFF",
                    message="high-risk changes require a workpack topic updated in this diff",
                    details=workpack_root,
                )
            )
        if not changed_agent_report_topics:
            violations.append(
                Violation(
                    code="AGENT_REPORT_TOPIC_NOT_IN_DIFF",
                    message="high-risk changes require DDD/SEC/QA report topic updated in this diff",
                    details=agent_report_root,
                )
            )

        if not complete_workpacks:
            violations.append(
                Violation(
                    code="WORKPACK_REQUIRED_SET_MISSING",
                    message="complete workpack(01/02/03) is required for changed high-risk topic",
                    details=f"topics={sorted(changed_workpack_topics)}",
                )
            )
        if complete_workpacks and not manual_hook_workpacks:
            violations.append(
                Violation(
                    code="WORKPACK_MANUAL_HOOK_REFERENCE_MISSING",
                    message="02_context.md must reference manual hook output evidence",
                    details=f"expected one of {contract['manual_hook_reference_tokens']}",
                )
            )

        required_report_files = determine_required_report_files(scope_flags, contract)
        if required_report_files:
            for topic in sorted(changed_agent_report_topics):
                present = report_topic_files.get(topic, set())
                missing = sorted(required_report_files - present)
                if missing:
                    violations.append(
                        Violation(
                            code="AGENT_REPORT_REQUIRED_FILES_MISSING",
                            message="changed report topic does not include required report files for current scope",
                            details=f"topic={topic} missing={missing}",
                        )
                    )

        overlap = sorted(set(complete_workpacks) & set(changed_agent_report_topics))
        if not overlap:
            violations.append(
                Violation(
                    code="WORKPACK_AGENT_REPORT_TOPIC_MISMATCH",
                    message="workpack topic and specialized report topic must overlap in this diff",
                    details=f"workpack_topics={sorted(changed_workpack_topics)} report_topics={sorted(changed_agent_report_topics)}",
                )
            )
        else:
            eligible_topics = overlap

        for topic in sorted(changed_topics):
            if not topic_pattern.fullmatch(topic):
                violations.append(
                    Violation(
                        code="TOPIC_PATTERN_INVALID",
                        message="topic must match naming contract",
                        details=f"topic={topic} pattern={topic_pattern.pattern}",
                    )
                )
            tokens = topic_tokens(topic)
            for token in tokens:
                if token in forbidden_topic_tokens:
                    violations.append(
                        Violation(
                            code="TOPIC_FORBIDDEN_TOKEN",
                            message="topic contains forbidden vague token",
                            details=f"topic={topic} token={token}",
                        )
                    )
            if scope_tokens:
                if not any(token in set(scope_tokens) for token in tokens):
                    violations.append(
                        Violation(
                            code="TOPIC_SCOPE_BINDING_MISSING",
                            message="topic tokens must bind to changed-file scope tokens",
                            details=f"topic={topic} scope_tokens={scope_tokens}",
                        )
                    )

        if spec_only:
            if spec_sync_report_path not in changed_files:
                violations.append(
                    Violation(
                        code="SPEC_SYNC_REPORT_NOT_UPDATED",
                        message="spec-only changes require spec_sync_report.md update in the same diff",
                        details=spec_sync_report_path,
                    )
                )
            notion_gate_ran, notion_gate_violations = maybe_run_notion_exception_gate(root, contract)
            violations.extend(notion_gate_violations)

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "high_risk_triggered": high_risk_triggered,
        "changed_files_count": len(changed_files),
        "changed_files": changed_files,
        "scope": scope_flags,
        "required_report_files": sorted(required_report_files),
        "scope_tokens": scope_tokens,
        "changed_workpack_topics": sorted(changed_workpack_topics),
        "changed_agent_report_topics": sorted(changed_agent_report_topics),
        "complete_workpack_topics": complete_workpacks,
        "manual_hook_workpack_topics": manual_hook_workpacks,
        "complete_agent_report_topics": complete_reports,
        "eligible_topics": eligible_topics,
        "notion_manual_exception_gate_ran": notion_gate_ran,
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
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
