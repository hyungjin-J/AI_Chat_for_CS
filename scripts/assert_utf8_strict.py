#!/usr/bin/env python3
"""Fail-closed UTF-8 strict decoder gate (no BOM policy)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".csv",
    ".yml",
    ".yaml",
    ".xml",
    ".java",
    ".kt",
    ".kts",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".py",
    ".ps1",
    ".sh",
    ".sql",
    ".properties",
    ".gradle",
}

DEFAULT_EXCLUDED_DIR_NAMES = {
    ".git",
    ".gradle",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    "target",
    "out",
}


@dataclass
class Violation:
    code: str
    path: str
    details: str


def normalize(path: str) -> str:
    return path.strip().replace("\\", "/")


def parse_changed_files(raw: str | None) -> list[str]:
    if raw is None:
        return []
    items: list[str] = []
    for token in raw.replace(",", "\n").splitlines():
        value = normalize(token)
        if value:
            items.append(value)
    return sorted(set(items))


def read_changed_files_from_git(root: Path, base_ref: str | None) -> list[str]:
    if base_ref:
        target = f"{base_ref}...HEAD"
        command = ["git", "diff", "--name-only", target]
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


def collect_files(
    root: Path,
    scan_roots: list[str],
    changed_files: list[str],
    excluded_dir_names: set[str],
) -> list[Path]:
    files: list[Path] = []
    if changed_files:
        for rel in changed_files:
            target = root / rel
            if target.is_file() and target.suffix.lower() in TEXT_EXTENSIONS:
                files.append(target)
        return sorted(set(files))

    for scan_root in scan_roots:
        target_root = root / scan_root
        if not target_root.exists():
            continue
        for current_root, dir_names, file_names in os.walk(target_root):
            dir_names[:] = [
                name for name in dir_names if name not in excluded_dir_names
            ]
            current_root_path = Path(current_root)
            for file_name in file_names:
                candidate = current_root_path / file_name
                if candidate.suffix.lower() in TEXT_EXTENSIONS and candidate.is_file():
                    files.append(candidate)
    return sorted(set(files))


def detect_violation(path: Path, root: Path) -> Violation | None:
    raw = path.read_bytes()
    rel = path.relative_to(root).as_posix()

    if raw.startswith(b"\xef\xbb\xbf"):
        return Violation("UTF8_BOM_FORBIDDEN", rel, "UTF-8 with BOM is forbidden; use UTF-8 without BOM")
    if raw.startswith(b"\xff\xfe\x00\x00") or raw.startswith(b"\x00\x00\xfe\xff"):
        return Violation("UTF32_BOM_FORBIDDEN", rel, "UTF-32 BOM detected")
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return Violation("UTF16_BOM_FORBIDDEN", rel, "UTF-16 BOM detected")

    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return Violation("NON_UTF8_TEXT", rel, f"strict UTF-8 decode failed at byte {exc.start}")
    return None


def render_text(payload: dict) -> str:
    lines = [
        "assert_utf8_strict",
        f"status={payload['status']}",
        f"scanned_file_count={payload['scanned_file_count']}",
        f"violation_count={payload['violation_count']}",
    ]
    if "baseline_violation_count" in payload:
        lines.append(f"baseline_violation_count={payload['baseline_violation_count']}")
        lines.append(f"new_violation_count={payload['new_violation_count']}")
        lines.append(f"resolved_baseline_count={payload['resolved_baseline_count']}")
    if "baseline_growth_base_count" in payload:
        lines.append(f"baseline_growth_base_source={payload['baseline_growth_base_source']}")
        lines.append(f"baseline_growth_base_count={payload['baseline_growth_base_count']}")
        lines.append(f"baseline_growth_head_count={payload['baseline_growth_head_count']}")
        lines.append(f"baseline_growth_count={payload['baseline_growth_count']}")
    for violation in payload["violations"]:
        lines.append(f"- [{violation['code']}] {violation['path']} :: {violation['details']}")
    if "resolved_baseline" in payload:
        for key in payload["resolved_baseline"]:
            lines.append(f"- [RESOLVED_BASELINE] {key}")
    if "baseline_growth_items" in payload:
        for key in payload["baseline_growth_items"]:
            lines.append(f"- [BASELINE_GROWTH] {key}")
    return "\n".join(lines) + "\n"


def normalize_baseline_items(raw_items: list[dict]) -> set[str]:
    keys: set[str] = set()
    for item in raw_items:
        code = str(item.get("code", "")).strip()
        rel_path = normalize(str(item.get("path", "")).strip())
        if code and rel_path:
            keys.add(f"{code}:{rel_path}")
    return keys


def load_baseline_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    violations = payload.get("violations", []) if isinstance(payload, dict) else payload
    return normalize_baseline_items(violations if isinstance(violations, list) else [])


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
    violations = payload.get("violations", []) if isinstance(payload, dict) else payload
    return normalize_baseline_items(violations if isinstance(violations, list) else [])


def compute_baseline_growth(base_keys: set[str], head_keys: set[str]) -> dict:
    growth = sorted(head_keys - base_keys)
    return {
        "baseline_growth_base_count": len(base_keys),
        "baseline_growth_head_count": len(head_keys),
        "baseline_growth_count": len(growth),
        "baseline_growth_items": growth,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert UTF-8 strict decode without BOM")
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--scan-roots",
        nargs="*",
        default=["docs/review/mvp_verification_pack/artifacts"],
        help="Scan roots used when changed-files is not provided",
    )
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help="Scan full repository text files (changed-files and git-diff are ignored)",
    )
    parser.add_argument(
        "--exclude-dir-names",
        nargs="*",
        default=sorted(DEFAULT_EXCLUDED_DIR_NAMES),
        help="Directory names excluded during scan-roots walk",
    )
    parser.add_argument("--changed-files", help="Changed file list (comma/newline separated)")
    parser.add_argument("--git-base-ref", help="Optional git base ref for --use-git-diff")
    parser.add_argument("--use-git-diff", action="store_true")
    parser.add_argument("--baseline-file", help="Optional baseline violations JSON for ratchet mode")
    parser.add_argument(
        "--baseline-base-file",
        help="Optional baseline file path for growth comparison tests (overrides --git-base-ref for baseline guard)",
    )
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    changed_files = parse_changed_files(args.changed_files)
    if args.use_git_diff:
        changed_files = read_changed_files_from_git(root, args.git_base_ref)
    scan_roots = [normalize(item) for item in args.scan_roots]
    if args.full_scan:
        changed_files = []
        scan_roots = ["."]

    targets = collect_files(
        root=root,
        scan_roots=scan_roots,
        changed_files=changed_files,
        excluded_dir_names={str(item).strip() for item in args.exclude_dir_names if str(item).strip()},
    )
    violations: list[Violation] = []
    for path in targets:
        violation = detect_violation(path, root)
        if violation is not None:
            violations.append(violation)

    violation_items = [asdict(item) for item in violations]
    payload = {
        "status": "PASS" if not violations else "FAIL",
        "scanned_file_count": len(targets),
        "violation_count": len(violations),
        "violations": violation_items,
    }
    if args.baseline_file:
        baseline_path = (root / args.baseline_file) if not Path(args.baseline_file).is_absolute() else Path(args.baseline_file)
        baseline_keys = load_baseline_keys(baseline_path)
        baseline_growth_base_source = "head"
        if args.baseline_base_file:
            base_baseline_path = (
                root / args.baseline_base_file
                if not Path(args.baseline_base_file).is_absolute()
                else Path(args.baseline_base_file)
            )
            base_baseline_keys = load_baseline_keys(base_baseline_path)
            baseline_growth_base_source = "baseline-base-file"
        elif args.git_base_ref and baseline_path.is_relative_to(root):
            baseline_rel = baseline_path.relative_to(root).as_posix()
            if _git_has_path(root, args.git_base_ref, baseline_rel):
                base_baseline_keys = load_baseline_keys_from_git(
                    root,
                    args.git_base_ref,
                    baseline_rel,
                )
                baseline_growth_base_source = f"git:{args.git_base_ref}"
            else:
                # Bootstrap safety when baseline file is introduced on this branch.
                base_baseline_keys = set(baseline_keys)
                baseline_growth_base_source = f"head-fallback:missing-in-{args.git_base_ref}"
        else:
            base_baseline_keys = set(baseline_keys)
            baseline_growth_base_source = "head"
        baseline_growth = compute_baseline_growth(base_baseline_keys, baseline_keys)
        current_by_key = {f"{item.code}:{item.path}": asdict(item) for item in violations}
        current_keys = set(current_by_key.keys())
        new_keys = sorted(current_keys - baseline_keys)
        resolved_keys = sorted(baseline_keys - current_keys)
        baseline_growth_fail = baseline_growth["baseline_growth_count"] > 0
        payload.update(
            {
                "status": "PASS" if (not new_keys and not baseline_growth_fail) else "FAIL",
                "baseline_file": baseline_path.relative_to(root).as_posix() if baseline_path.is_relative_to(root) else baseline_path.as_posix(),
                "baseline_violation_count": len(baseline_keys),
                "new_violation_count": len(new_keys),
                "resolved_baseline_count": len(resolved_keys),
                "baseline_growth_base_source": baseline_growth_base_source,
                "baseline_growth_base_count": baseline_growth["baseline_growth_base_count"],
                "baseline_growth_head_count": baseline_growth["baseline_growth_head_count"],
                "baseline_growth_count": baseline_growth["baseline_growth_count"],
                "baseline_growth_items": baseline_growth["baseline_growth_items"],
                "new_violations": [current_by_key[key] for key in new_keys],
                "resolved_baseline": resolved_keys,
                "violations": [current_by_key[key] for key in sorted(current_keys)],
            }
        )
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
