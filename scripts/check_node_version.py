#!/usr/bin/env python3
"""Compatibility wrapper for Node SSOT checks.

Why:
- Some gates and runbooks refer to `check_node_version.py`.
- The canonical logic lives in `assert_node_ssot.py`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Node version SSOT check wrapper")
    parser.add_argument("--nvmrc", default=".nvmrc")
    parser.add_argument("--package-json", default="frontend/package.json")
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    script_path = Path(__file__).with_name("assert_node_ssot.py")
    cmd = [
        sys.executable,
        str(script_path),
        "--nvmrc",
        args.nvmrc,
        "--package-json",
        args.package_json,
    ]
    if args.check_runtime:
        cmd.append("--check-runtime")
    if args.output:
        cmd.extend(["--output", args.output])

    proc = subprocess.run(cmd, check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
