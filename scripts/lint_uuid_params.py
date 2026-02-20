#!/usr/bin/env python3
"""
Fail-fast lint for MyBatis mapper interfaces:
- Flags String parameters that look like UUID identifiers (e.g., userId, tenant_id)
- Allows explicit string identifiers via allowlist (default: loginId/login_id)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PARAM_PATTERN = re.compile(
    r'(?:@Param\("(?P<annotation>[^"]+)"\)\s*)?String\s+(?P<variable>[A-Za-z_][A-Za-z0-9_]*)'
)


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    annotation: str | None
    variable: str
    snippet: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint mapper String *Id params that should be UUID.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("backend/src/main/java/com/aichatbot"),
        help="Root directory to scan",
    )
    parser.add_argument(
        "--allowlist",
        default="loginId,login_id",
        help="Comma-separated string-ID names allowed as String",
    )
    return parser.parse_args()


def is_id_like(name: str) -> bool:
    lower = name.lower()
    return lower.endswith("id") or lower.endswith("_id")


def normalize_allowlist(raw_allowlist: str) -> set[str]:
    return {item.strip().lower() for item in raw_allowlist.split(",") if item.strip()}


def mapper_files(root: Path) -> Iterable[Path]:
    return sorted(path for path in root.rglob("*Mapper.java") if "/mapper/" in path.as_posix())


def lint_file(path: Path, allowlist: set[str]) -> list[Violation]:
    violations: list[Violation] = []
    content = path.read_text(encoding="utf-8")
    for line_number, line in enumerate(content.splitlines(), start=1):
        for match in PARAM_PATTERN.finditer(line):
            annotation = match.group("annotation")
            variable = match.group("variable")
            names = [value for value in (annotation, variable) if value]
            normalized_names = [name.lower() for name in names]

            if not any(is_id_like(name) for name in names):
                continue
            if any(name in allowlist for name in normalized_names):
                continue

            violations.append(
                Violation(
                    file=path,
                    line=line_number,
                    annotation=annotation,
                    variable=variable,
                    snippet=line.strip(),
                )
            )
    return violations


def main() -> int:
    args = parse_args()
    root = args.root
    allowlist = normalize_allowlist(args.allowlist)

    if not root.exists():
        print(f"[uuid-lint] scan root not found: {root}")
        return 1

    all_violations: list[Violation] = []
    scanned = 0
    for file in mapper_files(root):
        scanned += 1
        all_violations.extend(lint_file(file, allowlist))

    if all_violations:
        print("[uuid-lint] FAIL: mapper String id-like parameters detected.")
        print(f"[uuid-lint] allowlist={sorted(allowlist)}")
        for issue in all_violations:
            annotation_info = (
                f'@Param("{issue.annotation}") '
                if issue.annotation is not None
                else ""
            )
            print(
                f"[uuid-lint] {issue.file.as_posix()}:{issue.line} -> "
                f"{annotation_info}String {issue.variable}"
            )
            print(f"[uuid-lint]   {issue.snippet}")
        print(f"[uuid-lint] checked_mapper_files={scanned} violations={len(all_violations)}")
        print("[uuid-lint] fix: use java.util.UUID in mapper params for DB UUID columns.")
        return 1

    print(f"[uuid-lint] PASS: checked_mapper_files={scanned} violations=0")
    print(f"[uuid-lint] allowlist={sorted(allowlist)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
