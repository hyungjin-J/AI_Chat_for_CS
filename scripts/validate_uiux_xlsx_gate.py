#!/usr/bin/env python3
"""Validate UIUX workbook gate conditions and emit JSON report."""

from __future__ import annotations

import sys

from openpyxl import load_workbook

from uiux_xlsx_gate_lib import WORKBOOK_PATH, run_gate_checks, write_json_report


def main() -> int:
    if not WORKBOOK_PATH.exists():
        print(f"[Gate] workbook not found: {WORKBOOK_PATH}")
        return 1

    wb = load_workbook(WORKBOOK_PATH)
    report = run_gate_checks(wb)
    write_json_report(report)

    hard_fail = (
        len(report["missing_required"]) > 0
        or len(report["screen_id_mismatch"]) > 0
        or len(report["error_code_mismatch"]) > 0
        or len(report["missing_constraints"]) > 0
    )

    print(f"[Gate] PASS={report['pass_count']} FAIL={report['fail_count']}")
    print(f"[Gate] missing_required={len(report['missing_required'])}")
    print(f"[Gate] screen_id_mismatch={len(report['screen_id_mismatch'])}")
    print(f"[Gate] error_code_mismatch={len(report['error_code_mismatch'])}")
    print(f"[Gate] missing_constraints={len(report['missing_constraints'])}")
    print(f"[Gate] report={WORKBOOK_PATH.parent / 'reports' / 'xlsx_gate_report.json'}")

    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
