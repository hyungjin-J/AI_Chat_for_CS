#!/usr/bin/env python3
"""Assert RAG quality metrics against threshold contract."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_THRESHOLDS = "eval/thresholds.yaml"
DEFAULT_ARTIFACT_DIR = "docs/review/mvp_verification_pack/artifacts"

REASON_OK = "OK"
REASON_DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
REASON_INDEXING_INCOMPLETE = "INDEXING_INCOMPLETE"
REASON_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
REASON_TARGET_UNREACHABLE = "TARGET_UNREACHABLE"
REASON_THRESHOLD_UNDERSHOOT = "THRESHOLD_UNDERSHOOT"
REASON_METRIC_COMPUTATION_BUG = "METRIC_COMPUTATION_BUG"

PRECONDITION_REASON_CODES = {
    REASON_DATA_UNAVAILABLE,
    REASON_INDEXING_INCOMPLETE,
    REASON_PROVIDER_UNAVAILABLE,
    REASON_TARGET_UNREACHABLE,
}


@dataclass
class Violation:
    code: str
    metric: str
    message: str
    actual: Any
    expected: Any


def _date_tag_local() -> str:
    return dt.datetime.now().strftime("%Y%m%d")


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def _load_thresholds(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="strict").strip()
    if not text:
        raise ValueError("threshold file is empty")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "threshold file must be JSON-compatible YAML (YAML superset): "
            f"{path.as_posix()}"
        ) from exc


def _metric_state(payload: dict[str, Any], metric_name: str) -> tuple[str, float | None]:
    metrics = payload.get("metrics", {})
    if not isinstance(metrics, dict) or metric_name not in metrics:
        return "missing", None
    item = metrics.get(metric_name)
    value = item.get("value") if isinstance(item, dict) else item
    if value is None:
        return "missing", None
    try:
        return "ok", float(value)
    except (TypeError, ValueError):
        return "invalid", None


def evaluate_thresholds(report: dict[str, Any], thresholds: dict[str, Any]) -> list[Violation]:
    violations: list[Violation] = []
    metrics_cfg = thresholds.get("metrics", {})
    if not isinstance(metrics_cfg, dict):
        raise ValueError("thresholds.metrics must be an object")

    for metric_name, rule in metrics_cfg.items():
        if not isinstance(rule, dict):
            continue
        state, actual = _metric_state(report, metric_name)
        if state == "missing":
            violations.append(
                Violation(
                    code="METRIC_MISSING",
                    metric=metric_name,
                    message="metric missing in report",
                    actual=None,
                    expected=rule,
                )
            )
            continue
        if state == "invalid":
            violations.append(
                Violation(
                    code="METRIC_INVALID",
                    metric=metric_name,
                    message="metric value is not numeric",
                    actual=None,
                    expected=rule,
                )
            )
            continue
        assert actual is not None

        min_v = rule.get("min")
        max_v = rule.get("max")
        if min_v is not None and actual < float(min_v):
            violations.append(
                Violation(
                    code="THRESHOLD_MIN_FAILED",
                    metric=metric_name,
                    message="actual value below minimum threshold",
                    actual=actual,
                    expected={"min": float(min_v)},
                )
            )
        if max_v is not None and actual > float(max_v):
            violations.append(
                Violation(
                    code="THRESHOLD_MAX_FAILED",
                    metric=metric_name,
                    message="actual value above maximum threshold",
                    actual=actual,
                    expected={"max": float(max_v)},
                )
            )

    return violations


def classify_reason(report: dict[str, Any], violations: list[Violation]) -> str:
    report_reason = str(report.get("reason_code", "")).strip().upper()
    report_status = str(report.get("status", "")).strip().upper()

    if report_status in {"SKIPPED", "FAIL"} and report_reason in PRECONDITION_REASON_CODES:
        return report_reason

    codes = [item.code for item in violations]
    if any(code in {"METRIC_MISSING", "METRIC_INVALID"} for code in codes):
        return REASON_METRIC_COMPUTATION_BUG
    if any(code.startswith("THRESHOLD_") for code in codes):
        return REASON_THRESHOLD_UNDERSHOOT
    if report_status in {"SKIPPED", "FAIL"} and report_reason:
        return report_reason
    return REASON_OK


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        "rag_regression_quality_gate",
        f"status={payload['status']}",
        f"reason_code={payload['reason_code']}",
        f"generated_at_utc={payload['generated_at_utc']}",
        f"report_path={payload['report_path']}",
        f"thresholds_path={payload['thresholds_path']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(
            f"- [{item['code']}] metric={item['metric']} "
            f"message={item['message']} actual={item['actual']} expected={item['expected']}"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert RAG regression quality gate")
    parser.add_argument("--report", required=True)
    parser.add_argument("--thresholds", default=DEFAULT_THRESHOLDS)
    parser.add_argument("--output-txt", default="")
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report)
    thresholds_path = Path(args.thresholds)
    if not report_path.exists():
        raise FileNotFoundError(f"report not found: {report_path.as_posix()}")
    if not thresholds_path.exists():
        raise FileNotFoundError(f"threshold file not found: {thresholds_path.as_posix()}")

    report = _load_json(report_path)
    thresholds = _load_thresholds(thresholds_path)

    violations: list[Violation] = []
    report_status = str(report.get("status", "")).strip().upper()
    report_reason = str(report.get("reason_code", "")).strip().upper()
    if report_status in {"SKIPPED", "FAIL"} and report_reason in PRECONDITION_REASON_CODES:
        violations.append(
            Violation(
                code=report_reason,
                metric="preflight",
                message="precondition failed before metric evaluation",
                actual=report.get("reason_detail"),
                expected="status=PASS",
            )
        )
    else:
        violations.extend(evaluate_thresholds(report=report, thresholds=thresholds))

    reason_code = classify_reason(report, violations)
    payload = {
        "status": "PASS" if reason_code == REASON_OK else "FAIL",
        "reason_code": reason_code,
        "generated_at_utc": _now_utc(),
        "report_path": report_path.as_posix(),
        "thresholds_path": thresholds_path.as_posix(),
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }
    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    output_txt = (
        Path(args.output_txt)
        if args.output_txt
        else Path(DEFAULT_ARTIFACT_DIR) / f"rag_regression_gate_{_date_tag_local()}.txt"
    )
    output_json = (
        Path(args.output_json)
        if args.output_json
        else Path(DEFAULT_ARTIFACT_DIR) / f"rag_regression_gate_{_date_tag_local()}.json"
    )
    output_txt.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_txt.write_text(text_report, encoding="utf-8")
    output_json.write_text(json_report, encoding="utf-8")

    print(text_report, end="")
    return 0 if reason_code == REASON_OK else 1


if __name__ == "__main__":
    raise SystemExit(main())
