#!/usr/bin/env python3
"""Ratchet gate for application-layer imports that must stay behind domain ports."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


IMPORT_PATTERN = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)\s*;\s*$")


@dataclass
class Violation:
    target: str
    file: str
    line: int
    import_target: str
    code: str
    details: str = ""

    def key(self) -> str:
        return f"{self.target}:{self.file}:{self.line}:{self.import_target}:{self.code}"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def _normalize_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _classify(import_target: str, forbidden_tokens: list[str]) -> str | None:
    for token in forbidden_tokens:
        if token in import_target:
            return "APP_PORT_FORBIDDEN_IMPORT"
    return None


def scan_target_violations(root: Path, target: dict) -> list[Violation]:
    target_name = str(target.get("name", "unnamed")).strip() or "unnamed"
    scan_root_rel = str(target.get("scan_root", "")).strip()
    file_glob = str(target.get("file_glob", "**/*.java")).strip() or "**/*.java"
    required_prefix = str(target.get("required_prefix", "")).strip()
    forbidden_tokens = [str(token) for token in target.get("forbidden_import_tokens", [])]

    if not scan_root_rel:
        return [
            Violation(
                target=target_name,
                file="",
                line=0,
                import_target="",
                code="APP_PORT_SCAN_ROOT_MISSING",
                details="scan_root is empty in contract target",
            )
        ]

    scan_root = root / scan_root_rel
    if not scan_root.exists():
        return [
            Violation(
                target=target_name,
                file=scan_root_rel.replace("\\", "/"),
                line=0,
                import_target="",
                code="APP_PORT_SCAN_ROOT_MISSING",
                details="scan_root does not exist",
            )
        ]

    violations: list[Violation] = []
    for java_file in sorted(scan_root.glob(file_glob)):
        if not java_file.is_file():
            continue
        rel_path = _normalize_path(java_file, root)
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
            code = _classify(import_target, forbidden_tokens)
            if code is None:
                continue
            violations.append(
                Violation(
                    target=target_name,
                    file=rel_path,
                    line=line_number,
                    import_target=import_target,
                    code=code,
                )
            )
    return violations


def scan_current_violations(root: Path, contract: dict) -> list[Violation]:
    targets = contract.get("targets", [])
    violations: list[Violation] = []
    for target in targets:
        violations.extend(scan_target_violations(root, target))
    return violations


def normalize_baseline_items(raw_items: list[dict]) -> set[str]:
    keys: set[str] = set()
    for item in raw_items:
        target = str(item.get("target", "")).strip()
        file = str(item.get("file", "")).strip()
        line = int(item.get("line", 0))
        import_target = str(item.get("import_target", "")).strip()
        code = str(item.get("code", "")).strip()
        if target and file and code:
            keys.add(f"{target}:{file}:{line}:{import_target}:{code}")
    return keys


def load_baseline_keys_from_file(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = load_json(path)
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


def load_baseline_keys_from_git(root: Path, git_ref: str, rel_path: str) -> set[str]:
    if not _git_has_path(root, git_ref, rel_path):
        return set()
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
    payload = json.loads(show.stdout)
    return normalize_baseline_items(payload.get("violations", []))


def compute_baseline_growth(base_keys: set[str], head_keys: set[str]) -> dict:
    growth = sorted(head_keys - base_keys)
    return {
        "baseline_base_count": len(base_keys),
        "baseline_head_count": len(head_keys),
        "baseline_growth_count": len(growth),
        "baseline_growth_items": growth,
    }


def render_text(payload: dict) -> str:
    lines = [
        "assert_application_port_boundaries",
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
            f"- [NEW:{item['code']}] target={item['target']} {item['file']}:{item['line']} import={item['import_target']} details={item.get('details', '')}"
        )
    for key in payload["resolved_baseline"]:
        lines.append(f"- [RESOLVED] {key}")
    for key in payload["baseline_growth_items"]:
        lines.append(f"- [BASELINE_GROWTH] {key}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert application-layer port boundaries with baseline ratchet")
    parser.add_argument("--root", default=".")
    parser.add_argument("--contract", default="scripts/contracts/application_port_boundary_contract.json")
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
    contract = load_json(contract_path)
    baseline_path = root / str(contract["baseline_file"])

    violations = scan_current_violations(root, contract)
    current_by_key = {item.key(): item for item in violations}
    current_keys = set(current_by_key.keys())

    baseline_keys = load_baseline_keys_from_file(baseline_path)
    baseline_rel = baseline_path.relative_to(root).as_posix()
    baseline_growth_base_source = "head"
    if args.baseline_base_file:
        base_baseline_path = (
            root / args.baseline_base_file
            if not Path(args.baseline_base_file).is_absolute()
            else Path(args.baseline_base_file)
        )
        base_baseline_keys = load_baseline_keys_from_file(base_baseline_path)
        baseline_growth_base_source = "baseline-base-file"
    elif args.git_base_ref:
        if _git_has_path(root, args.git_base_ref, baseline_rel):
            base_baseline_keys = load_baseline_keys_from_git(root, args.git_base_ref, baseline_rel)
            baseline_growth_base_source = f"git:{args.git_base_ref}"
        else:
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
