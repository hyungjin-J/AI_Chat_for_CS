#!/usr/bin/env python3
"""Fail-closed gate for SSE load/performance results."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


SUPPORTED_RULE_KEYS = {
    "min",
    "max",
    "avg_min",
    "avg_max",
    "p95_min",
    "p95_max",
    "sample_count_min",
    "sample_count_max",
}

REASON_OK = "OK"
REASON_RESULT_FILE_MISSING = "RESULT_FILE_MISSING"
REASON_RESULT_POINTS_MISSING = "RESULT_POINTS_MISSING"
REASON_RESULT_PARSE_ERROR = "RESULT_PARSE_ERROR"


@dataclass
class AssertionResult:
    metric: str
    rule: str
    expected: float
    actual: float | None
    passed: bool
    message: str


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def load_thresholds(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise ValueError(
                "threshold file must be JSON, or install PyYAML for YAML parsing"
            ) from exc
        payload = yaml.safe_load(raw)

    if not isinstance(payload, dict):
        raise ValueError("threshold file root must be an object")
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError("threshold file must include non-empty 'metrics' object")
    return payload


def parse_result_points(result_path: Path) -> tuple[dict[str, list[float]], int, dict | None]:
    metric_points: dict[str, list[float]] = {}
    point_count = 0
    meta: dict | None = None
    with result_path.open("r", encoding="utf-8", errors="strict") as handle:
        for line_no, line in enumerate(handle, start=1):
            row = line.strip()
            if row == "":
                continue
            try:
                payload = json.loads(row)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON line at {line_no}") from exc

            payload_type = payload.get("type")
            if payload_type == "PerfGateMeta" and isinstance(payload, dict):
                meta = payload
                continue

            if payload.get("type") != "Point":
                continue
            data = payload.get("data")
            if not isinstance(data, dict):
                continue
            metric_name = data.get("metric")
            if not isinstance(metric_name, str):
                metric_name = payload.get("metric")
            metric_value = data.get("value")
            if not isinstance(metric_name, str):
                continue
            if not isinstance(metric_value, (int, float)):
                continue

            metric_points.setdefault(metric_name, []).append(float(metric_value))
            point_count += 1

    return metric_points, point_count, meta


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if pct <= 0:
        return min(values)
    if pct >= 100:
        return max(values)

    ordered = sorted(values)
    pos = (len(ordered) - 1) * (pct / 100.0)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    frac = pos - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


def metric_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "sample_count": 0,
            "avg": None,
            "p95": None,
            "min": None,
            "max": None,
        }
    return {
        "sample_count": len(values),
        "avg": sum(values) / len(values),
        "p95": percentile(values, 95),
        "min": min(values),
        "max": max(values),
    }


def as_float(raw: object, label: str) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    raise ValueError(f"{label} must be numeric")


def evaluate_rule(rule: str, expected: float, summary: dict[str, float | int | None]) -> tuple[bool, float | None]:
    sample_count = summary["sample_count"]
    avg = summary["avg"]
    p95 = summary["p95"]

    if rule in ("min", "avg_min"):
        actual = avg if isinstance(avg, (int, float)) else None
        return (actual is not None and actual >= expected, actual)
    if rule in ("max", "avg_max"):
        actual = avg if isinstance(avg, (int, float)) else None
        return (actual is not None and actual <= expected, actual)
    if rule == "p95_min":
        actual = p95 if isinstance(p95, (int, float)) else None
        return (actual is not None and actual >= expected, actual)
    if rule == "p95_max":
        actual = p95 if isinstance(p95, (int, float)) else None
        return (actual is not None and actual <= expected, actual)
    if rule == "sample_count_min":
        actual = float(sample_count)
        return (actual >= expected, actual)
    if rule == "sample_count_max":
        actual = float(sample_count)
        return (actual <= expected, actual)

    raise ValueError(f"unsupported threshold rule: {rule}")


def render_text(payload: dict) -> str:
    lines = [
        "perf_gate",
        f"status={payload['status']}",
        f"reason_code={payload.get('reason_code', '')}",
        f"reason_detail={payload.get('reason_detail', '')}",
        f"remediation_hint={payload.get('remediation_hint', '')}",
        f"generated_at_utc={payload['generated_at_utc']}",
        f"result_file={payload['result_file']}",
        f"thresholds_file={payload['thresholds_file']}",
        f"point_count={payload['point_count']}",
        f"metric_count={payload['metric_count']}",
        f"assertion_count={payload['assertion_count']}",
        f"violation_count={payload['violation_count']}",
    ]

    lines.append("metrics:")
    metrics = payload.get("metrics", {})
    for metric_name in sorted(metrics):
        item = metrics[metric_name]
        lines.append(
            f"- {metric_name}: sample_count={item.get('sample_count')} "
            f"avg={item.get('avg')} p95={item.get('p95')} min={item.get('min')} max={item.get('max')}"
        )

    lines.append("assertions:")
    for assertion in payload.get("assertions", []):
        lines.append(
            f"- {'PASS' if assertion.get('passed') else 'FAIL'} "
            f"{assertion.get('metric')}.{assertion.get('rule')} "
            f"actual={assertion.get('actual')} expected={assertion.get('expected')} "
            f"message={assertion.get('message')}"
        )

    lines.append("violations:")
    for violation in payload.get("violations", []):
        lines.append(f"- {violation}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert SSE perf gate from k6 JSON output")
    parser.add_argument("--result", required=True, help="k6 result JSON path")
    parser.add_argument("--thresholds", required=True, help="threshold YAML/JSON path")
    parser.add_argument("--output-json", help="optional gate report JSON path")
    parser.add_argument("--output-txt", help="optional gate report TXT path")
    args = parser.parse_args()

    result_path = Path(args.result)
    threshold_path = Path(args.thresholds)

    try:
        thresholds = load_thresholds(threshold_path)
        metric_points, point_count, meta = parse_result_points(result_path)
        if point_count == 0:
            reason_code = REASON_RESULT_POINTS_MISSING
            reason_detail = "result did not include any Point samples"
            remediation_hint = "Run k6 load test and ensure json output includes Point entries."
            if isinstance(meta, dict):
                reason_code = str(meta.get("reason_code", reason_code))
                reason_detail = str(meta.get("reason_detail", reason_detail))
                remediation_hint = str(meta.get("remediation_hint", remediation_hint))
            payload = {
                "status": "FAIL",
                "reason_code": reason_code,
                "reason_detail": reason_detail,
                "remediation_hint": remediation_hint,
                "generated_at_utc": utc_now_iso(),
                "result_file": result_path.as_posix(),
                "thresholds_file": threshold_path.as_posix(),
                "point_count": 0,
                "metric_count": 0,
                "assertion_count": 0,
                "violation_count": 1,
                "metrics": {},
                "assertions": [],
                "violations": [f"{reason_code}: {reason_detail}"],
            }
            report = render_text(payload)
            if args.output_json:
                out_json = Path(args.output_json)
                out_json.parent.mkdir(parents=True, exist_ok=True)
                out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if args.output_txt:
                out_txt = Path(args.output_txt)
                out_txt.parent.mkdir(parents=True, exist_ok=True)
                out_txt.write_text(report, encoding="utf-8")
            sys.stdout.write(report)
            return 1
    except Exception as exc:
        reason_code = REASON_RESULT_PARSE_ERROR
        if isinstance(exc, FileNotFoundError):
            reason_code = REASON_RESULT_FILE_MISSING
        payload = {
            "status": "FAIL",
            "reason_code": reason_code,
            "reason_detail": str(exc),
            "remediation_hint": "Check perf runner preflight and regenerate result.json.",
            "generated_at_utc": utc_now_iso(),
            "result_file": result_path.as_posix(),
            "thresholds_file": threshold_path.as_posix(),
            "point_count": 0,
            "metric_count": 0,
            "assertion_count": 0,
            "violation_count": 1,
            "metrics": {},
            "assertions": [],
            "violations": [str(exc)],
        }
        report = render_text(payload)
        if args.output_json:
            out_json = Path(args.output_json)
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.output_txt:
            out_txt = Path(args.output_txt)
            out_txt.parent.mkdir(parents=True, exist_ok=True)
            out_txt.write_text(report, encoding="utf-8")
        sys.stdout.write(report)
        return 1

    assertions: list[AssertionResult] = []
    violations: list[str] = []
    summary_map: dict[str, dict[str, float | int | None]] = {}
    metric_rules = thresholds["metrics"]

    for metric_name, raw_rules in metric_rules.items():
        if not isinstance(metric_name, str):
            violations.append("metric name must be string")
            continue
        if not isinstance(raw_rules, dict):
            violations.append(f"threshold rules for '{metric_name}' must be object")
            continue

        unknown_keys = sorted(set(raw_rules.keys()) - SUPPORTED_RULE_KEYS)
        if unknown_keys:
            violations.append(f"{metric_name} includes unsupported keys: {','.join(unknown_keys)}")
            continue

        points = metric_points.get(metric_name, [])
        summary = metric_summary(points)
        summary_map[metric_name] = summary

        if not points:
            violations.append(f"missing metric points: {metric_name}")

        for rule, raw_expected in raw_rules.items():
            expected = as_float(raw_expected, f"{metric_name}.{rule}")
            passed, actual = evaluate_rule(rule, expected, summary)
            message = "ok" if passed else "threshold_not_met"
            assertions.append(
                AssertionResult(
                    metric=metric_name,
                    rule=rule,
                    expected=expected,
                    actual=actual,
                    passed=passed,
                    message=message,
                )
            )
            if not passed:
                violations.append(
                    f"{metric_name}.{rule} failed: actual={actual} expected={expected}"
                )

    status = "PASS" if not violations else "FAIL"
    payload = {
        "status": status,
        "reason_code": REASON_OK if status == "PASS" else "THRESHOLD_UNDERSHOOT",
        "reason_detail": "" if status == "PASS" else "one or more metric thresholds were not met",
        "remediation_hint": "" if status == "PASS" else "Tune service/perf settings and rerun the load test.",
        "generated_at_utc": utc_now_iso(),
        "result_file": result_path.as_posix(),
        "thresholds_file": threshold_path.as_posix(),
        "point_count": point_count,
        "metric_count": len(summary_map),
        "assertion_count": len(assertions),
        "violation_count": len(violations),
        "metrics": summary_map,
        "assertions": [asdict(item) for item in assertions],
        "violations": violations,
    }
    report = render_text(payload)

    if args.output_json:
        out_json = Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_txt:
        out_txt = Path(args.output_txt)
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(report, encoding="utf-8")

    sys.stdout.write(report)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
