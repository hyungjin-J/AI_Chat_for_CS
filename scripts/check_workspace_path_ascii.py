#!/usr/bin/env python3
"""Warn when current workspace path contains non-ASCII characters."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check workspace path for non-ASCII characters")
    parser.add_argument("--path", default=".", help="Workspace path to inspect")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero when non-ASCII characters are found (default is warning-only).",
    )
    return parser.parse_args()


def find_non_ascii_characters(text: str) -> list[str]:
    values: list[str] = []
    for char in text:
        if ord(char) > 127:
            values.append(char)
    return sorted(set(values))


def main() -> int:
    args = parse_args()
    workspace = Path(args.path).resolve()
    workspace_str = str(workspace)
    non_ascii = find_non_ascii_characters(workspace_str)

    if not non_ascii:
        sys.stdout.write("check_workspace_path_ascii\nstatus=PASS\nnon_ascii_count=0\n")
        return 0

    lines = [
        "check_workspace_path_ascii",
        "status=WARNING",
        f"path={workspace_str}",
        f"non_ascii_count={len(non_ascii)}",
        f"non_ascii_chars={''.join(non_ascii)}",
        "recommendation=Use an ASCII-only temp workspace for Node22 frontend npm test/build runs.",
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
