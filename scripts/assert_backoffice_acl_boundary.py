#!/usr/bin/env python3
"""Ratchet gate for backoffice ACL boundary imports."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


IMPORT_PATTERN = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)\s*;\s*$")
BASELINE_ROW_PATTERN = re.compile(r"^\|\s*`?([^`|]+)`?\s*\|\s*(\d+)\s*\|\s*`?([^`|]+)`?\s*\|\s*`?([^`|]+)`?\s*\|")


@dataclass
class Violation:
    file: str
    line: int
    import_target: str
    classification: str

    def key(self) -> str:
        return f"{self.file}:{self.line}:{self.import_target}"


def load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def classify_violation(import_target: str, forbidden_tokens: list[str]) -> str | None:
    for token in forbidden_tokens:
        if token in import_target:
            if token == ".infrastructure.":
                return "FORBIDDEN_INFRA_IMPORT"
            if token == ".presentation.":
                return "FORBIDDEN_PRESENTATION_IMPORT"
            return "FORBIDDEN_IMPORT"
    return None


def parse_baseline_keys(markdown_path: Path) -> set[str]:
    if not markdown_path.exists():
        return set()
    keys: set[str] = set()
    for line in markdown_path.read_text(encoding="utf-8", errors="strict").splitlines():
        match = BASELINE_ROW_PATTERN.match(line.strip())
        if not match:
            continue
        file = match.group(1).strip()
        line_no = int(match.group(2).strip())
        import_target = match.group(3).strip()
        if file and line_no > 0 and import_target:
            keys.add(f"{file}:{line_no}:{import_target}")
    return keys


def normalize_baseline_items(raw_items: list[dict]) -> set[str]:
    keys: set[str] = set()
    for item in raw_items:
        file = str(item.get("file", "")).strip()
        line = int(item.get("line", 0))
        import_target = str(item.get("import_target", "")).strip()
        if file and line > 0 and import_target:
            keys.add(f"{file}:{line}:{import_target}")
    return keys


def load_baseline_keys_from_json(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    return normalize_baseline_items(payload.get("violations", []))


def _git_has_path(root: Path, git_ref: str, rel_path: str) -> bool:
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{git_ref}:{rel_path}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return probe.returncode == 0


def _load_text_from_git(root: Path, git_ref: str, rel_path: str) -> str | None:
    if not _git_has_path(root, git_ref, rel_path):
        return None
    show = subprocess.run(
        ["git", "show", f"{git_ref}:{rel_path}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if show.returncode != 0:
        raise RuntimeError(
            f"failed to read baseline from git ref '{git_ref}' path '{rel_path}': {show.stderr.strip()}"
        )
    return show.stdout


def load_baseline_keys_from_git_json(root: Path, git_ref: str, rel_path: str) -> set[str]:
    text = _load_text_from_git(root, git_ref, rel_path)
    if text is None:
        return set()
    payload = json.loads(text)
    return normalize_baseline_items(payload.get("violations", []))


def load_baseline_keys_from_git_markdown(root: Path, git_ref: str, rel_path: str) -> set[str]:
    text = _load_text_from_git(root, git_ref, rel_path)
    if text is None:
        return set()
    keys: set[str] = set()
    for line in text.splitlines():
        match = BASELINE_ROW_PATTERN.match(line.strip())
        if not match:
            continue
        file = match.group(1).strip()
        line_no = int(match.group(2).strip())
        import_target = match.group(3).strip()
        if file and line_no > 0 and import_target:
            keys.add(f"{file}:{line_no}:{import_target}")
    return keys


def compute_baseline_growth(base_keys: set[str], head_keys: set[str]) -> dict:
    growth = sorted(head_keys - base_keys)
    return {
        "baseline_base_count": len(base_keys),
        "baseline_head_count": len(head_keys),
        "baseline_growth_count": len(growth),
        "baseline_growth_items": growth,
    }


def scan_current_violations(root: Path, contract: dict) -> list[Violation]:
    scan_root = root / contract["scan_root"]
    if not scan_root.exists():
        return []

    file_glob = str(contract["file_glob"])
    forbidden_tokens = [str(token) for token in contract["forbidden_import_tokens"]]
    required_prefix = str(contract.get("required_prefix", ""))

    violations: list[Violation] = []
    for java_file in sorted(scan_root.glob(file_glob)):
        if not java_file.is_file():
            continue
        rel = java_file.relative_to(root).as_posix()
        for line_number, line in enumerate(
            java_file.read_text(encoding="utf-8", errors="strict").splitlines(),
            start=1,
        ):
            match = IMPORT_PATTERN.match(line)
            if not match:
                continue
            import_target = match.group(1)
            if required_prefix and not import_target.startswith(required_prefix):
                continue
            classification = classify_violation(import_target, forbidden_tokens)
            if classification is None:
                continue
            violations.append(
                Violation(
                    file=rel,
                    line=line_number,
                    import_target=import_target,
                    classification=classification,
                )
            )
    return violations


def render_text(payload: dict) -> str:
    lines = [
        "assert_backoffice_acl_boundary",
        f"status={payload['status']}",
        f"current_violation_count={payload['current_violation_count']}",
        f"baseline_violation_count={payload['baseline_violation_count']}",
        f"new_violation_count={payload['new_violation_count']}",
        f"resolved_baseline_count={payload['resolved_baseline_count']}",
        f"baseline_growth_base_source={payload['baseline_growth_base_source']}",
        f"baseline_growth_base_count={payload['baseline_growth_base_count']}",
        f"baseline_growth_head_count={payload['baseline_growth_head_count']}",
        f"baseline_growth_count={payload['baseline_growth_count']}",
    ]
    for item in payload["new_violations"]:
        lines.append(
            f"- [NEW:{item['classification']}] {item['file']}:{item['line']} import={item['import_target']}"
        )
    for key in payload["resolved_baseline"]:
        lines.append(f"- [RESOLVED] {key}")
    for key in payload["baseline_growth_items"]:
        lines.append(f"- [BASELINE_GROWTH] {key}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert backoffice ACL import boundaries")
    parser.add_argument("--root", default=".")
    parser.add_argument("--contract", default="scripts/contracts/backoffice_acl_boundary_contract.json")
    parser.add_argument("--git-base-ref", help="Optional git base ref to block baseline growth")
    parser.add_argument(
        "--baseline-base-file",
        help="Optional baseline file path for growth comparison tests (overrides --git-base-ref)",
    )
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    contract_path = (root / args.contract) if not Path(args.contract).is_absolute() else Path(args.contract)
    contract = load_contract(contract_path)

    violations = scan_current_violations(root, contract)
    current_by_key = {item.key(): item for item in violations}
    current_keys = set(current_by_key.keys())

    baseline_file = contract.get("baseline_file")
    if baseline_file:
        baseline_path = root / baseline_file
        baseline_keys = load_baseline_keys_from_json(baseline_path)
    else:
        baseline_path = root / contract["baseline_markdown"]
        baseline_keys = parse_baseline_keys(baseline_path)
    baseline_rel = baseline_path.relative_to(root).as_posix()
    baseline_growth_base_source = "head"
    if args.baseline_base_file:
        base_baseline_path = (
            root / args.baseline_base_file
            if not Path(args.baseline_base_file).is_absolute()
            else Path(args.baseline_base_file)
        )
        if baseline_file:
            base_baseline_keys = load_baseline_keys_from_json(base_baseline_path)
        else:
            base_baseline_keys = parse_baseline_keys(base_baseline_path)
        baseline_growth_base_source = "baseline-base-file"
    elif args.git_base_ref:
        if _git_has_path(root, args.git_base_ref, baseline_rel):
            if baseline_file:
                base_baseline_keys = load_baseline_keys_from_git_json(root, args.git_base_ref, baseline_rel)
            else:
                base_baseline_keys = load_baseline_keys_from_git_markdown(root, args.git_base_ref, baseline_rel)
            baseline_growth_base_source = f"git:{args.git_base_ref}"
        else:
            # Bootstrap safety when baseline file is introduced on this branch.
            base_baseline_keys = set(baseline_keys)
            baseline_growth_base_source = f"head-fallback:missing-in-{args.git_base_ref}"
    else:
        base_baseline_keys = set(baseline_keys)
        baseline_growth_base_source = "head"
    baseline_growth = compute_baseline_growth(base_baseline_keys, baseline_keys)

    new_keys = sorted(current_keys - baseline_keys)
    resolved_keys = sorted(baseline_keys - current_keys)
    baseline_growth_fail = baseline_growth["baseline_growth_count"] > 0

    payload = {
        "status": "PASS" if (not new_keys and not baseline_growth_fail) else "FAIL",
        "current_violation_count": len(current_keys),
        "baseline_violation_count": len(baseline_keys),
        "new_violation_count": len(new_keys),
        "resolved_baseline_count": len(resolved_keys),
        "baseline_growth_base_source": baseline_growth_base_source,
        "baseline_growth_base_count": baseline_growth["baseline_base_count"],
        "baseline_growth_head_count": baseline_growth["baseline_head_count"],
        "baseline_growth_count": baseline_growth["baseline_growth_count"],
        "baseline_growth_items": baseline_growth["baseline_growth_items"],
        "new_violations": [asdict(current_by_key[key]) for key in new_keys],
        "resolved_baseline": resolved_keys,
        "all_current_violations": [asdict(item) for item in violations],
    }

    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.output_txt:
        output_txt = Path(args.output_txt)
        output_txt.parent.mkdir(parents=True, exist_ok=True)
        output_txt.write_text(text_report, encoding="utf-8")
    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json_report, encoding="utf-8")

    sys.stdout.write(text_report)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
