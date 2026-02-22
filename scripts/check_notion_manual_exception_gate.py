#!/usr/bin/env python3
"""Validate Notion BLOCKED manual exception close gate evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


EXPECTED_STATUS_FILE = "notion_blocked_status.json"
EXPECTED_PATCH_FILE = "notion_manual_patch.md"
REQUIRED_PATCH_FIELDS = ("Last synced at", "Source file", "Version", "Change summary")
REQUIRED_STATUS_FIELDS = ("status", "reason", "detected_at_kst", "preflight_ref")


@dataclass
class Violation:
    code: str
    message: str


def load_json(path: Path, violations: list[Violation], name: str) -> dict:
    if not path.exists():
        violations.append(Violation(code=f"{name}_MISSING", message=f"{path.as_posix()} not found"))
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # pragma: no cover
        violations.append(
            Violation(code=f"{name}_INVALID_JSON", message=f"{path.as_posix()} parse error: {exc}")
        )
        return {}


def assert_fixed_name(path: Path, expected: str, violations: list[Violation], field: str) -> None:
    if path.name != expected:
        violations.append(
            Violation(
                code=f"{field}_INVALID_NAME",
                message=f"{field} must be {expected}, got {path.name}",
            )
        )


def require_non_empty_value(
    payload: dict,
    field_name: str,
    file_path: Path,
    violations: list[Violation],
    code: str,
) -> str:
    value = payload.get(field_name)
    if value is None:
        violations.append(
            Violation(
                code=code,
                message=f"{file_path.as_posix()} -> missing required field '{field_name}'",
            )
        )
        return ""

    normalized = str(value).strip()
    if not normalized:
        violations.append(
            Violation(
                code=code,
                message=f"{file_path.as_posix()} -> field '{field_name}' is empty",
            )
        )
    return normalized


def parse_markdown_meta_value(patch_text: str, field: str) -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.*)$", re.MULTILINE)
    match = pattern.search(patch_text)
    if not match:
        return ""
    return match.group(1).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Notion manual exception gate")
    parser.add_argument("--context")
    parser.add_argument("--preflight")
    parser.add_argument("--status-file")
    parser.add_argument("--status-json")
    parser.add_argument("--manual-patch", required=True)
    parser.add_argument("--spec-sync", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    violations: list[Violation] = []

    context_path = Path(args.context) if args.context else None
    preflight_path = Path(args.preflight) if args.preflight else None
    status_arg = args.status_json or args.status_file
    if not status_arg:
        parser.error("one of --status-json or --status-file is required")
    status_path = Path(status_arg)
    patch_path = Path(args.manual_patch)
    spec_sync_path = Path(args.spec_sync)

    assert_fixed_name(status_path, EXPECTED_STATUS_FILE, violations, "status_file")
    assert_fixed_name(patch_path, EXPECTED_PATCH_FILE, violations, "manual_patch")

    context = load_json(context_path, violations, "CONTEXT") if context_path else {}
    preflight = load_json(preflight_path, violations, "PREFLIGHT") if preflight_path else {}
    status = load_json(status_path, violations, "STATUS")

    if context_path and context:
        changed = bool(context.get("changed_targets"))
        if not changed:
            violations.append(
                Violation(
                    code="CONTEXT_NOT_CHANGED",
                    message="manual exception gate should run only when sync targets changed",
                )
            )

    if preflight_path and preflight:
        preflight_status = str(preflight.get("status", "")).upper()
        error_code = str(preflight.get("error_code", ""))
        if preflight_status != "FAIL":
            violations.append(
                Violation(code="PREFLIGHT_NOT_FAIL", message=f"preflight status must be FAIL, got {preflight_status}")
            )
        if not error_code.startswith("NOTION_AUTH_") and error_code != "OPENAI_API_KEY_MISSING":
            violations.append(
                Violation(
                    code="PREFLIGHT_ERROR_CODE_INVALID",
                    message=f"unexpected preflight error_code for manual gate: {error_code}",
                )
            )

    if status:
        for status_field in REQUIRED_STATUS_FIELDS:
            require_non_empty_value(
                payload=status,
                field_name=status_field,
                file_path=status_path,
                violations=violations,
                code="STATUS_FIELD_MISSING",
            )

        if status.get("status") != "BLOCKED_AUTOMATION":
            violations.append(
                Violation(
                    code="STATUS_INVALID",
                    message=(
                        f"{status_path.as_posix()} -> field 'status' must be "
                        f"BLOCKED_AUTOMATION, got {status.get('status')}"
                    ),
                )
            )

        if status.get("timestamp_kst") and not status.get("detected_at_kst"):
            violations.append(
                Violation(
                    code="STATUS_LEGACY_FIELD_USED",
                    message=(
                        f"{status_path.as_posix()} -> legacy field 'timestamp_kst' detected; "
                        "use 'detected_at_kst'"
                    ),
                )
            )

        preflight_ref = str(status.get("preflight_ref", "")).strip()
        if preflight_ref:
            preflight_ref_path = Path(preflight_ref)
            if not preflight_ref_path.exists():
                violations.append(
                    Violation(
                        code="STATUS_PREFLIGHT_REF_MISSING",
                        message=(
                            f"{status_path.as_posix()} -> field 'preflight_ref' points to "
                            f"missing file: {preflight_ref}"
                        ),
                    )
                )

    if not patch_path.exists():
        violations.append(Violation(code="PATCH_MISSING", message=f"{patch_path.as_posix()} not found"))
    else:
        patch_text = patch_path.read_text(encoding="utf-8", errors="strict")
        for field in REQUIRED_PATCH_FIELDS:
            value = parse_markdown_meta_value(patch_text=patch_text, field=field)
            if not value and field != "Change summary":
                violations.append(
                    Violation(
                        code="PATCH_FIELD_MISSING",
                        message=f"{patch_path.as_posix()} -> field '{field}' is missing or empty",
                    )
                )
        if not parse_markdown_meta_value(patch_text=patch_text, field="Change summary"):
            summary_has_bullet = bool(re.search(r"(?m)^\s+\d+\.\s+\S+", patch_text))
            if not summary_has_bullet:
                violations.append(
                    Violation(
                        code="PATCH_FIELD_MISSING",
                        message=(
                            f"{patch_path.as_posix()} -> field 'Change summary' is missing or empty"
                        ),
                    )
                )
        if "https://www.notion.so/" not in patch_text:
            violations.append(
                Violation(
                    code="PATCH_NOTION_URL_MISSING",
                    message=f"{patch_path.as_posix()} -> Notion target URL is missing",
                )
            )

    if not spec_sync_path.exists():
        violations.append(
            Violation(code="SPEC_SYNC_MISSING", message=f"{spec_sync_path.as_posix()} not found")
        )
    else:
        spec_text = spec_sync_path.read_text(encoding="utf-8", errors="strict")
        required_tokens = [
            EXPECTED_STATUS_FILE,
            EXPECTED_PATCH_FILE,
            "BLOCKED_AUTOMATION",
        ]
        for token in required_tokens:
            if token not in spec_text:
                violations.append(
                    Violation(
                        code="SPEC_SYNC_EVIDENCE_MISSING",
                        message=(
                            f"{spec_sync_path.as_posix()} -> missing required token '{token}'"
                        ),
                    )
                )
        if not re.search(r"Phase2\.1(?:\.\d+)?|phase2_1(?:_\d+)?", spec_text):
            violations.append(
                Violation(
                    code="SPEC_SYNC_PHASE_ENTRY_MISSING",
                    message=(
                        f"{spec_sync_path.as_posix()} -> Phase2.1 manual exception record is missing"
                    ),
                )
            )

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "violation_count": len(violations),
        "violations": [asdict(v) for v in violations],
        "checked_files": {
            "context": context_path.as_posix() if context_path else "",
            "preflight": preflight_path.as_posix() if preflight_path else "",
            "status_file": status_path.as_posix(),
            "manual_patch": patch_path.as_posix(),
            "spec_sync_report": spec_sync_path.as_posix(),
        },
    }

    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output_json:
        out_json = Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json_report, encoding="utf-8")

    txt_lines = [
        "notion_manual_exception_gate",
        f"status={payload['status']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        txt_lines.append(f"- [{item['code']}] {item['message']}")
    txt_report = "\n".join(txt_lines) + "\n"
    if args.output_txt:
        out_txt = Path(args.output_txt)
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(txt_report, encoding="utf-8")

    sys.stdout.write(txt_report)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
