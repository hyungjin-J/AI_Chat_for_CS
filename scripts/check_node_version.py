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


def build_bootstrap_guide() -> str:
    if sys.platform.startswith("win"):
        bootstrap_command = "powershell -ExecutionPolicy Bypass -File scripts/bootstrap_node_22.ps1"
    else:
        bootstrap_command = "bash scripts/bootstrap_node_22.sh"

    lines = [
        "",
        "[node-ssot] runtime mismatch detected.",
        "[node-ssot] Recovery steps:",
        "1) Verify .nvmrc target version: cat .nvmrc",
        f"2) Run bootstrap helper: {bootstrap_command}",
        "3) Re-open shell (if your version manager updated PATH).",
        (
            "4) Re-run this gate: python scripts/check_node_version.py "
            "--nvmrc .nvmrc --package-json frontend/package.json --check-runtime"
        ),
    ]
    return "\n".join(lines) + "\n"


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

    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)

    if proc.returncode != 0:
        guidance = build_bootstrap_guide()
        sys.stderr.write(guidance)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("a", encoding="utf-8") as fp:
                fp.write(guidance)

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
