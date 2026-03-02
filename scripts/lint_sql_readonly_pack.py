#!/usr/bin/env python3
"""Lint SQL packs to keep them read-only and non-destructive."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SQL_FILE = "docs/ops/sql/DB_OPERATIONS_QUERIES.sql"
FORBIDDEN_KEYWORDS = (
    "DROP",
    "TRUNCATE",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "REINDEX",
    "VACUUM",
    "ANALYZE",
    "GRANT",
    "REVOKE",
    "CALL",
    "DO",
)


@dataclass(frozen=True)
class Violation:
    line: int
    keyword: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint read-only SQL packs")
    parser.add_argument("--sql-file", default=DEFAULT_SQL_FILE)
    parser.add_argument("--output-txt")
    return parser.parse_args()


def sanitize_sql(text: str) -> str:
    result: list[str] = []
    index = 0
    length = len(text)

    in_single_quote = False
    in_line_comment = False
    in_block_comment = False

    while index < length:
        ch = text[index]
        nxt = text[index + 1] if index + 1 < length else ""

        if in_single_quote:
            if ch == "'":
                if nxt == "'":
                    result.append("  ")
                    index += 2
                    continue
                in_single_quote = False
                result.append(" ")
                index += 1
                continue
            result.append("\n" if ch == "\n" else " ")
            index += 1
            continue

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                result.append("\n")
            else:
                result.append(" ")
            index += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                result.append("  ")
                index += 2
                continue
            result.append("\n" if ch == "\n" else " ")
            index += 1
            continue

        if ch == "-" and nxt == "-":
            in_line_comment = True
            result.append("  ")
            index += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            result.append("  ")
            index += 2
            continue

        if ch == "'":
            in_single_quote = True
            result.append(" ")
            index += 1
            continue

        result.append(ch)
        index += 1

    return "".join(result)


def find_violations(text: str) -> list[Violation]:
    sanitized = sanitize_sql(text)
    patterns = {
        keyword: re.compile(rf"(?<![A-Za-z0-9_]){keyword}(?![A-Za-z0-9_])", re.IGNORECASE)
        for keyword in FORBIDDEN_KEYWORDS
    }

    violations: list[Violation] = []
    for line_no, line in enumerate(sanitized.splitlines(), start=1):
        for keyword, pattern in patterns.items():
            if pattern.search(line):
                violations.append(Violation(line=line_no, keyword=keyword))
    return sorted(violations, key=lambda item: (item.line, item.keyword))


def render_report(sql_file: Path, violations: list[Violation]) -> str:
    lines = [
        "lint_sql_readonly_pack",
        f"status={'PASS' if not violations else 'FAIL'}",
        f"sql_file={sql_file.as_posix()}",
        f"violation_count={len(violations)}",
    ]
    for item in violations:
        lines.append(
            f"- [READONLY_SQL_FORBIDDEN_KEYWORD] line={item.line} keyword={item.keyword}"
        )
    return "\n".join(lines) + "\n"


def write_output(path: Path | None, content: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    sql_file = Path(args.sql_file).resolve()
    if not sql_file.exists():
        raise FileNotFoundError(f"sql file not found: {sql_file}")

    text = sql_file.read_text(encoding="utf-8", errors="replace")
    violations = find_violations(text)
    report = render_report(sql_file=sql_file, violations=violations)

    output_txt = Path(args.output_txt).resolve() if args.output_txt else None
    write_output(output_txt, report)

    sys.stdout.write(report)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
