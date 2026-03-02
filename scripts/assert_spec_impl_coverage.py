#!/usr/bin/env python3
"""Fail-closed gate for Spec -> Implementation coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DEFAULT_REPORT_JSON = "docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_report.json"
DEFAULT_OUTPUT_TXT = "docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_gate.txt"
DEFAULT_OUTPUT_JSON = "docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_gate.json"
IMPORTANCE_MUST = "Must"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert Must API coverage gate")
    parser.add_argument("--report-json", default=DEFAULT_REPORT_JSON)
    parser.add_argument("--output-txt", default=DEFAULT_OUTPUT_TXT)
    parser.add_argument("--output-json", default=DEFAULT_OUTPUT_JSON)
    parser.add_argument(
        "--require-tests-for-must",
        action="store_true",
        help="Fail if Must API rows have tests_present=false",
    )
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else Path.cwd() / candidate


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_text(payload: dict) -> str:
    lines = [
        "assert_spec_impl_coverage",
        f"status={payload['status']}",
        f"require_tests_for_must={payload['require_tests_for_must']}",
        f"must_api_rows={payload['must_api_rows']}",
        f"must_backend_missing_count={payload['must_backend_missing_count']}",
        f"must_tests_missing_count={payload['must_tests_missing_count']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(
            f"- [{item['code']}] program_id={item['program_id']} method={item['method']} "
            f"endpoint={item['endpoint']} details={item['details']}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    report_json_path = resolve_path(args.report_json)
    output_txt_path = resolve_path(args.output_txt)
    output_json_path = resolve_path(args.output_json)

    if not report_json_path.exists():
        payload = {
            "status": "FAIL",
            "require_tests_for_must": bool(args.require_tests_for_must),
            "must_api_rows": 0,
            "must_backend_missing_count": 0,
            "must_tests_missing_count": 0,
            "violation_count": 1,
            "violations": [
                {
                    "code": "COVERAGE_REPORT_MISSING",
                    "program_id": "-",
                    "method": "-",
                    "endpoint": "-",
                    "details": str(report_json_path),
                }
            ],
        }
        text_report = render_text(payload)
        json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        write_output(output_txt_path, text_report)
        write_output(output_json_path, json_report)
        sys.stdout.write(text_report)
        return 1

    try:
        report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = {
            "status": "FAIL",
            "require_tests_for_must": bool(args.require_tests_for_must),
            "must_api_rows": 0,
            "must_backend_missing_count": 0,
            "must_tests_missing_count": 0,
            "violation_count": 1,
            "violations": [
                {
                    "code": "COVERAGE_REPORT_INVALID_JSON",
                    "program_id": "-",
                    "method": "-",
                    "endpoint": "-",
                    "details": str(report_json_path),
                }
            ],
        }
        text_report = render_text(payload)
        json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        write_output(output_txt_path, text_report)
        write_output(output_json_path, json_report)
        sys.stdout.write(text_report)
        return 1

    rows = report_payload.get("rows", [])
    if not isinstance(rows, list):
        rows = []

    must_rows = [item for item in rows if isinstance(item, dict) and item.get("importance") == IMPORTANCE_MUST]

    violations: list[dict] = []
    must_backend_missing_count = 0
    must_tests_missing_count = 0

    for row in must_rows:
        program_id = str(row.get("program_id", ""))
        method = str(row.get("method", ""))
        endpoint = str(row.get("endpoint", ""))
        req_ids = row.get("req_ids", [])
        req_id_display = ",".join(req_ids) if isinstance(req_ids, list) and req_ids else "-"

        if not bool(row.get("backend_implemented")):
            must_backend_missing_count += 1
            violations.append(
                {
                    "code": "MUST_BACKEND_IMPLEMENTATION_MISSING",
                    "program_id": program_id,
                    "method": method,
                    "endpoint": endpoint,
                    "details": f"req_ids={req_id_display}",
                }
            )

        if args.require_tests_for_must and not bool(row.get("tests_present")):
            must_tests_missing_count += 1
            violations.append(
                {
                    "code": "MUST_TEST_COVERAGE_MISSING",
                    "program_id": program_id,
                    "method": method,
                    "endpoint": endpoint,
                    "details": f"req_ids={req_id_display}",
                }
            )

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "require_tests_for_must": bool(args.require_tests_for_must),
        "must_api_rows": len(must_rows),
        "must_backend_missing_count": must_backend_missing_count,
        "must_tests_missing_count": must_tests_missing_count,
        "violation_count": len(violations),
        "violations": violations,
    }

    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_output(output_txt_path, text_report)
    write_output(output_json_path, json_report)
    sys.stdout.write(text_report)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
