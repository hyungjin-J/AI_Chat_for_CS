#!/usr/bin/env python3
"""Assert Node.js SSOT alignment across .nvmrc/package metadata/runtime."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


EXPECTED_VERSION = "22.12.0"


def read_nvmrc(path: Path) -> str:
    text = path.read_text(encoding="utf-8").splitlines()
    for line in text:
        value = line.strip()
        if value and not value.startswith("#"):
            return value
    raise ValueError("empty .nvmrc")


def load_frontend_package(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_runtime_node_version() -> str:
    proc = subprocess.run(
        ["node", "-v"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"node -v failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def normalize_semver(value: str) -> str:
    return value.strip().lstrip("v")


def assert_valid_semver(value: str, field_name: str, violations: list[str]) -> None:
    if not re.match(r"^\d+\.\d+\.\d+$", value):
        violations.append(f"{field_name} must be exact semver (x.y.z), got: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Node SSOT assertion")
    parser.add_argument("--nvmrc", default=".nvmrc")
    parser.add_argument("--package-json", default="frontend/package.json")
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument("--output", help="Optional text report path")
    args = parser.parse_args()

    violations: list[str] = []

    nvmrc_path = Path(args.nvmrc)
    pkg_path = Path(args.package_json)
    nvmrc_version = normalize_semver(read_nvmrc(nvmrc_path))
    package = load_frontend_package(pkg_path)
    engines_node = str(package.get("engines", {}).get("node", "")).strip()
    volta_node = str(package.get("volta", {}).get("node", "")).strip()

    assert_valid_semver(nvmrc_version, ".nvmrc", violations)
    assert_valid_semver(engines_node, "frontend.package.engines.node", violations)
    assert_valid_semver(volta_node, "frontend.package.volta.node", violations)

    if nvmrc_version != EXPECTED_VERSION:
        violations.append(f".nvmrc must be {EXPECTED_VERSION}, got: {nvmrc_version}")
    if engines_node and normalize_semver(engines_node) != nvmrc_version:
        violations.append(
            "frontend.package.engines.node must match .nvmrc "
            f"({nvmrc_version}), got: {engines_node}"
        )
    if volta_node and normalize_semver(volta_node) != nvmrc_version:
        violations.append(
            "frontend.package.volta.node must match .nvmrc "
            f"({nvmrc_version}), got: {volta_node}"
        )

    runtime_node = ""
    if args.check_runtime:
        runtime_node = get_runtime_node_version()
        runtime_normalized = normalize_semver(runtime_node)
        if runtime_normalized != nvmrc_version:
            violations.append(
                f"runtime node version must match .nvmrc ({nvmrc_version}), got: {runtime_node}"
            )

    report_lines = [
        "node_ssot_assertion",
        f"expected={EXPECTED_VERSION}",
        f"nvmrc={nvmrc_version}",
        f"engines_node={engines_node}",
        f"volta_node={volta_node}",
        f"runtime_node={runtime_node or 'SKIPPED'}",
        f"status={'PASS' if not violations else 'FAIL'}",
    ]
    if violations:
        report_lines.append("violations:")
        report_lines.extend([f"- {v}" for v in violations])
    report_text = "\n".join(report_lines) + "\n"

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")

    sys.stdout.write(report_text)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
