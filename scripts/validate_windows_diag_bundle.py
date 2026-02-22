#!/usr/bin/env python3
"""Validate Windows npm lock diagnostic bundle structure and sanitization."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from zipfile import ZipFile


REQUIRED_FILES = {
    "summary.txt",
    "node_version.txt",
    "npm_version.txt",
    "os_info.txt",
    "path_length.txt",
    "readme.txt",
}


@dataclass
class Violation:
    code: str
    message: str
    item: str


def build_forbidden_patterns() -> list[tuple[str, re.Pattern[str]]]:
    token_key = "OPENAI" + "_" + "API" + "_" + "KEY"
    notion_key = "NOTION" + "_" + "TOKEN"
    bearer_prefix = "Bearer" + " "
    sk_prefix = "sk" + "-"
    user_home = "C:" + "\\Users\\"
    patterns = [
        ("TOKEN_KEY_EXPOSED", re.compile(re.escape(token_key), re.IGNORECASE)),
        ("NOTION_TOKEN_EXPOSED", re.compile(re.escape(notion_key), re.IGNORECASE)),
        ("BEARER_PREFIX_EXPOSED", re.compile(re.escape(bearer_prefix), re.IGNORECASE)),
        ("SK_PREFIX_EXPOSED", re.compile(re.escape(sk_prefix))),
        ("USER_HOME_PATH_EXPOSED", re.compile(re.escape(user_home), re.IGNORECASE)),
    ]
    return patterns


def validate_bundle(bundle_path: Path) -> tuple[dict, list[Violation]]:
    violations: list[Violation] = []

    if not bundle_path.exists():
        violations.append(
            Violation(
                code="BUNDLE_MISSING",
                message="diagnostic bundle zip does not exist",
                item=bundle_path.as_posix(),
            )
        )
        payload = {
            "status": "FAIL",
            "bundle_path": bundle_path.as_posix(),
            "required_files": sorted(REQUIRED_FILES),
            "zip_entries": [],
            "violation_count": len(violations),
            "violations": [asdict(v) for v in violations],
        }
        return payload, violations

    with ZipFile(bundle_path, "r") as zf:
        entries = sorted(zf.namelist())
        entry_set = set(entries)
        missing = sorted(REQUIRED_FILES - entry_set)
        for name in missing:
            violations.append(
                Violation(
                    code="REQUIRED_ENTRY_MISSING",
                    message="required file is missing in bundle",
                    item=name,
                )
            )

        forbidden_patterns = build_forbidden_patterns()
        for entry_name in entries:
            if entry_name.endswith("/"):
                continue
            try:
                text = zf.read(entry_name).decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                # Non-text content is not expected but skip binary decoding failures.
                continue

            for code, pattern in forbidden_patterns:
                if pattern.search(text):
                    violations.append(
                        Violation(
                            code=code,
                            message=f"forbidden pattern found in bundle entry {entry_name}",
                            item=entry_name,
                        )
                    )

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "bundle_path": bundle_path.as_posix(),
        "required_files": sorted(REQUIRED_FILES),
        "zip_entries": entries if bundle_path.exists() else [],
        "violation_count": len(violations),
        "violations": [asdict(v) for v in violations],
    }
    return payload, violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Windows diagnostic bundle")
    parser.add_argument(
        "--bundle",
        default="docs/review/mvp_verification_pack/artifacts/windows_npm_lock_diag_bundle.zip",
    )
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    payload, violations = validate_bundle(bundle_path=bundle_path)

    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    txt_lines = [
        "windows_npm_lock_diag_bundle_validate",
        f"status={payload['status']}",
        f"bundle_path={payload['bundle_path']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        txt_lines.append(f"- [{item['code']}] {item['message']} item={item['item']}")
    txt_report = "\n".join(txt_lines) + "\n"

    if args.output_json:
        out_json = Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json_report, encoding="utf-8")
    if args.output_txt:
        out_txt = Path(args.output_txt)
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(txt_report, encoding="utf-8")

    sys.stdout.write(txt_report)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
