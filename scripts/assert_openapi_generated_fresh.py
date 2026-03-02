#!/usr/bin/env python3
"""Fail if OpenAPI/typed generation is stale versus workbook SSOT."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from generate_openapi_from_workbook import build_openapi_document, write_yaml_or_json


HASH_MARKER_RE = re.compile(r"source-openapi-sha256:\s*([0-9a-f]{64})", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert OpenAPI/generated frontend types are fresh")
    parser.add_argument("--root", default=".")
    parser.add_argument("--workbook", default="docs/references/google_ready_api_spec_v0.3_20260216.xlsx")
    parser.add_argument("--sheet", default="\uc804\uccb4API\ubaa9\ub85d")
    parser.add_argument("--openapi", default="openapi/openapi.yaml")
    parser.add_argument("--frontend-types", default="frontend/src/api/generated/openapi.ts")
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def try_parse_structured_document(text: str):
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ModuleNotFoundError:
        pass
    except Exception:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    workbook_path = root / args.workbook
    openapi_path = root / args.openapi
    frontend_types_path = root / args.frontend_types

    violations: list[str] = []
    checks: dict[str, object] = {
        "openapi_exists": openapi_path.exists(),
        "frontend_types_exists": frontend_types_path.exists(),
    }

    if not openapi_path.exists():
        violations.append(f"missing OpenAPI output: {openapi_path.as_posix()}")
    if not frontend_types_path.exists():
        violations.append(f"missing generated frontend types: {frontend_types_path.as_posix()}")

    expected_openapi_text = ""
    expected_mode = "unknown"
    if workbook_path.exists():
        document, _ = build_openapi_document(
            workbook_path=workbook_path,
            sheet_name=args.sheet,
            title="AI_Chatbot API Skeleton",
            version="0.1.0-skeleton",
            server_url="http://localhost:8080",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_output = Path(tmpdir) / "openapi.yaml"
            expected_mode = write_yaml_or_json(temp_output, document)
            expected_openapi_text = normalize_text(temp_output.read_text(encoding="utf-8"))
    else:
        violations.append(f"missing workbook: {workbook_path.as_posix()}")

    actual_openapi_text = ""
    if openapi_path.exists():
        actual_openapi_text = normalize_text(openapi_path.read_text(encoding="utf-8"))
        if expected_openapi_text:
            expected_obj = try_parse_structured_document(expected_openapi_text)
            actual_obj = try_parse_structured_document(actual_openapi_text)
            if expected_obj is not None and actual_obj is not None:
                if actual_obj != expected_obj:
                    violations.append(
                        "openapi/openapi.yaml is stale; run: "
                        "python scripts/generate_openapi_from_workbook.py --workbook docs/references/google_ready_api_spec_v0.3_20260216.xlsx --out openapi/openapi.yaml"
                    )
            elif actual_openapi_text != expected_openapi_text:
                violations.append(
                    "openapi/openapi.yaml is stale; run: "
                    "python scripts/generate_openapi_from_workbook.py --workbook docs/references/google_ready_api_spec_v0.3_20260216.xlsx --out openapi/openapi.yaml"
                )

    actual_openapi_hash = sha256_hex(actual_openapi_text) if actual_openapi_text else ""
    checks["openapi_hash"] = actual_openapi_hash
    checks["expected_write_mode"] = expected_mode

    if frontend_types_path.exists() and actual_openapi_hash:
        types_text = frontend_types_path.read_text(encoding="utf-8")
        marker = HASH_MARKER_RE.search(types_text)
        if marker is None:
            violations.append(
                "generated frontend types missing source hash marker; run: cd frontend && npm run generate:api"
            )
            checks["frontend_hash_marker"] = ""
        else:
            marker_hash = marker.group(1).lower()
            checks["frontend_hash_marker"] = marker_hash
            if marker_hash != actual_openapi_hash:
                violations.append(
                    "frontend generated types are stale versus openapi/openapi.yaml; run: cd frontend && npm run generate:api"
                )

    status = "PASS" if not violations else "FAIL"
    payload = {
        "status": status,
        "generated_at_utc": utc_now_iso(),
        "workbook": workbook_path.as_posix(),
        "openapi": openapi_path.as_posix(),
        "frontend_types": frontend_types_path.as_posix(),
        "checks": checks,
        "violation_count": len(violations),
        "violations": violations,
    }

    text_lines = [
        "openapi_generated_freshness_gate",
        f"status={status}",
        f"workbook={payload['workbook']}",
        f"openapi={payload['openapi']}",
        f"frontend_types={payload['frontend_types']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in violations:
        text_lines.append(f"- {item}")
    text = "\n".join(text_lines) + "\n"

    if args.output_json:
        out_json = (root / args.output_json) if not Path(args.output_json).is_absolute() else Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_txt:
        out_txt = (root / args.output_txt) if not Path(args.output_txt).is_absolute() else Path(args.output_txt)
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(text, encoding="utf-8")

    print(text, end="")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
