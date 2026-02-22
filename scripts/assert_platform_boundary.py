#!/usr/bin/env python3
"""Assert architecture boundary: platform/sharedkernel must not depend on contexts/channels."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


IMPORT_PATTERN = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)\s*;\s*$")

FORBIDDEN_IMPORT_PATTERNS = [
    re.compile(r"^com\.aichatbot\.contexts\.[A-Za-z0-9_]+\."),
    re.compile(r"^com\.aichatbot\.channels\.[A-Za-z0-9_]+\."),
    re.compile(r"^com\.aichatbot\.(auth|billing|message|ops|rag|session|admin|answer|llm|tool)\."),
]


@dataclass
class Violation:
    file: str
    line: int
    import_target: str
    code: str
    message: str
    remediation: str


def parse_imports(path: Path) -> list[tuple[int, str]]:
    imports: list[tuple[int, str]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8", errors="strict").splitlines(), start=1):
        match = IMPORT_PATTERN.match(line)
        if match:
            imports.append((idx, match.group(1)))
    return imports


def scan_files(root: Path, package_paths: list[Path]) -> tuple[list[Path], list[Violation]]:
    scanned: list[Path] = []
    violations: list[Violation] = []

    for package_path in package_paths:
        if not package_path.exists():
            continue
        for java_file in sorted(package_path.rglob("*.java")):
            scanned.append(java_file)
            relative = java_file.relative_to(root).as_posix()
            for line_no, target in parse_imports(java_file):
                for pattern in FORBIDDEN_IMPORT_PATTERNS:
                    if pattern.search(target):
                        violations.append(
                            Violation(
                                file=relative,
                                line=line_no,
                                import_target=target,
                                code="PLATFORM_BOUNDARY_FORBIDDEN_IMPORT",
                                message="platform/sharedkernel import from domain/channel package is forbidden",
                                remediation=(
                                    "Move dependency behind a sharedkernel interface or context ACL. "
                                    "platform/sharedkernel must stay domain-agnostic."
                                ),
                            )
                        )
                        break
    return scanned, violations


def render_text(payload: dict) -> str:
    lines = [
        "assert_platform_boundary",
        f"status={payload['status']}",
        f"root={payload['root']}",
        f"scanned_files_count={payload['scanned_files_count']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(
            f"- {item['file']}:{item['line']} [{item['code']}] "
            f"import={item['import_target']} remediation={item['remediation']}"
        )
    if payload["scanned_files_count"] == 0:
        lines.append("note=No platform/sharedkernel source files found; boundary baseline only.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert platform/sharedkernel import boundaries")
    parser.add_argument("--root", default="backend/src/main/java", help="Java source root")
    parser.add_argument(
        "--package-path",
        action="append",
        dest="package_paths",
        help=(
            "Relative package path to scan under root. "
            "Defaults: com/aichatbot/platform and com/aichatbot/sharedkernel"
        ),
    )
    parser.add_argument("--output-json", help="Optional JSON report path")
    parser.add_argument("--output-txt", help="Optional text report path")
    args = parser.parse_args()

    root = Path(args.root)
    package_paths = args.package_paths or [
        "com/aichatbot/platform",
        "com/aichatbot/sharedkernel",
    ]
    scan_roots = [root / Path(item) for item in package_paths]

    scanned, violations = scan_files(root=root, package_paths=scan_roots)
    payload = {
        "status": "PASS" if not violations else "FAIL",
        "root": root.as_posix(),
        "scan_paths": [path.as_posix() for path in scan_roots],
        "scanned_files_count": len(scanned),
        "scanned_files": [path.relative_to(root).as_posix() for path in scanned],
        "violation_count": len(violations),
        "violations": [asdict(v) for v in violations],
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
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
