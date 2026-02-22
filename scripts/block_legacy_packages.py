#!/usr/bin/env python3
"""Block reintroduction of legacy com.aichatbot.<legacy> package roots."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


IMPORT_PATTERN = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)\s*;\s*$")
PACKAGE_PATTERN = re.compile(r"^\s*package\s+([A-Za-z0-9_.]+)\s*;\s*$")


@dataclass
class Violation:
    code: str
    file: str
    detail: str


def load_contract(root: Path, contract_path: str) -> dict:
    path = Path(contract_path)
    resolved = path if path.is_absolute() else root / path
    return json.loads(resolved.read_text(encoding="utf-8", errors="strict"))


def legacy_prefixes(names: list[str]) -> tuple[str, ...]:
    return tuple(f"com.aichatbot.{name}." for name in names)


def scan_paths(root: Path, java_roots: list[str], legacy_names: list[str]) -> list[Violation]:
    violations: list[Violation] = []
    main_root = root / "backend/src/main/java/com/aichatbot"
    for name in legacy_names:
        legacy_dir = main_root / name
        if legacy_dir.exists():
            violations.append(
                Violation(
                    code="LEGACY_PACKAGE_PATH_DETECTED",
                    file=legacy_dir.relative_to(root).as_posix(),
                    detail=f"legacy root package directory is forbidden: {name}",
                )
            )

    prefixes = legacy_prefixes(legacy_names)
    for base in java_roots:
        base_path = root / base
        if not base_path.exists():
            continue
        for java_file in sorted(base_path.rglob("*.java")):
            rel = java_file.relative_to(root).as_posix()
            for line in java_file.read_text(encoding="utf-8", errors="strict").splitlines():
                import_match = IMPORT_PATTERN.match(line)
                if import_match:
                    imported = import_match.group(1)
                    if imported.startswith(prefixes):
                        violations.append(
                            Violation(
                                code="LEGACY_PACKAGE_IMPORT_DETECTED",
                                file=rel,
                                detail=imported,
                            )
                        )
                package_match = PACKAGE_PATTERN.match(line)
                if package_match:
                    package_name = package_match.group(1)
                    if package_name.startswith(prefixes):
                        violations.append(
                            Violation(
                                code="LEGACY_PACKAGE_DECLARATION_DETECTED",
                                file=rel,
                                detail=package_name,
                            )
                        )
    return violations


def render_text(payload: dict) -> str:
    lines = [
        "block_legacy_packages",
        f"status={payload['status']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(f"- [{item['code']}] file={item['file']} detail={item['detail']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Block legacy package reintroduction")
    parser.add_argument("--root", default=".")
    parser.add_argument("--contract", default="scripts/contracts/legacy_package_blocker_contract.json")
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    contract = load_contract(root=root, contract_path=args.contract)
    violations = scan_paths(
        root=root,
        java_roots=contract["java_roots"],
        legacy_names=contract["legacy_packages"],
    )
    payload = {
        "status": "PASS" if not violations else "FAIL",
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
