#!/usr/bin/env python3
"""Compatibility wrapper for gen_notion_manual_evidence_templates.py."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Compatibility wrapper (deprecated)")
    parser.add_argument("--status-json")
    parser.add_argument("--manual-patch")
    parser.add_argument("--reason")
    parser.add_argument("--preflight-ref")
    parser.add_argument("--target", action="append", dest="targets")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    script_path = Path(__file__).with_name("gen_notion_manual_evidence_templates.py")
    cmd = [sys.executable, str(script_path)]
    if args.status_json:
        cmd.extend(["--status-path", args.status_json])
    if args.manual_patch:
        cmd.extend(["--patch-path", args.manual_patch])
    if args.reason:
        cmd.extend(["--reason", args.reason])
    if args.preflight_ref:
        cmd.extend(["--preflight-ref", args.preflight_ref])
    if args.targets:
        for target in args.targets:
            cmd.extend(["--target", target])
    if args.force:
        cmd.append("--force")

    print("[compat] gen_notion_manual_evidence_template.py is deprecated.")
    print("[compat] Use scripts/gen_notion_manual_evidence_templates.py instead.")
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
