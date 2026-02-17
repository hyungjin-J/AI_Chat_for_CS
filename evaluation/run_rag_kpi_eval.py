#!/usr/bin/env python3
"""RAG KPI evaluation runner outline.

This script is intentionally an outline:
- No secrets in repository
- Read DB connection only from environment
- Evaluate pass/fail gate from measurable KPIs
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any


@dataclasses.dataclass(slots=True)
class EvalCase:
    case_id: str
    tenant_id: str
    scenario: str
    from_ts: dt.datetime
    to_ts: dt.datetime
    expected_contract_pass_rate_min: float
    expected_citation_coverage_min: float
    expected_zero_evidence_rate_max: float
    expected_fail_closed_rate_max: float
    expected_fallback_leak_count_max: int
    expected_trace_coverage_min: float
    expected_pii_leak_count_max: int
    expected_p95_e2e_ms_max: float
    expected_p95_first_token_ms_max: float
    expected_stream_completion_rate_min: float
    expected_tool_success_rate_min: float
    expected_feedback_positive_rate_min: float
    notes: str


@dataclasses.dataclass(slots=True)
class KpiResult:
    kpi_id: str
    value: float
    unit: str
    target: str
    passed: bool
    severity: str
    detail: str


@dataclasses.dataclass(slots=True)
class CaseResult:
    case_id: str
    tenant_id: str
    scenario: str
    from_ts: str
    to_ts: str
    kpis: list[KpiResult]
    passed: bool
    failed_kpis: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate RAG KPI gates from dataset template.")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to dataset CSV.")
    parser.add_argument("--out", type=Path, default=Path("evaluation/report.json"), help="Output JSON report.")
    parser.add_argument(
        "--db-dsn-env",
        default="DATABASE_URL",
        help="Environment variable that stores DB DSN. No DSN is stored in repository.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate structure only without DB query execution.",
    )
    return parser.parse_args()


def parse_iso8601(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            cases.append(
                EvalCase(
                    case_id=row["case_id"],
                    tenant_id=row["tenant_id"],
                    scenario=row["scenario"],
                    from_ts=parse_iso8601(row["from_ts"]),
                    to_ts=parse_iso8601(row["to_ts"]),
                    expected_contract_pass_rate_min=float(row["expected_contract_pass_rate_min"]),
                    expected_citation_coverage_min=float(row["expected_citation_coverage_min"]),
                    expected_zero_evidence_rate_max=float(row["expected_zero_evidence_rate_max"]),
                    expected_fail_closed_rate_max=float(row["expected_fail_closed_rate_max"]),
                    expected_fallback_leak_count_max=int(row["expected_fallback_leak_count_max"]),
                    expected_trace_coverage_min=float(row["expected_trace_coverage_min"]),
                    expected_pii_leak_count_max=int(row["expected_pii_leak_count_max"]),
                    expected_p95_e2e_ms_max=float(row["expected_p95_e2e_ms_max"]),
                    expected_p95_first_token_ms_max=float(row["expected_p95_first_token_ms_max"]),
                    expected_stream_completion_rate_min=float(row["expected_stream_completion_rate_min"]),
                    expected_tool_success_rate_min=float(row["expected_tool_success_rate_min"]),
                    expected_feedback_positive_rate_min=float(row["expected_feedback_positive_rate_min"]),
                    notes=row.get("notes", ""),
                )
            )
    return cases


def query_kpis_from_db(dsn: str, case: EvalCase) -> dict[str, float]:
    """Return computed KPI values from DB.

    TODO:
    - Implement SQL execution with psycopg (or approved DB client)
    - Use only masked columns for text-based checks
    - Do not log query parameters that can contain sensitive data
    - Map SQL outputs to KPI IDs defined in docs/ops/rag-kpi.md
    """
    raise NotImplementedError("Connect DB and implement KPI SQL queries before production use.")


def build_mock_kpis_for_dry_run(case: EvalCase) -> dict[str, float]:
    """Produce deterministic mock values to validate pipeline structure."""
    return {
        "KPI-AC-001": case.expected_contract_pass_rate_min,
        "KPI-CT-001": case.expected_citation_coverage_min,
        "KPI-EV-001": case.expected_zero_evidence_rate_max,
        "KPI-FC-001": case.expected_fail_closed_rate_max,
        "KPI-FF-001": float(case.expected_fallback_leak_count_max),
        "KPI-TR-001": case.expected_trace_coverage_min,
        "KPI-PII-001": float(case.expected_pii_leak_count_max),
        "KPI-LAT-001": case.expected_p95_e2e_ms_max,
        "KPI-LAT-002": case.expected_p95_first_token_ms_max,
        "KPI-SSE-001": case.expected_stream_completion_rate_min,
        "KPI-TOOL-001": case.expected_tool_success_rate_min,
        "KPI-FB-001": case.expected_feedback_positive_rate_min,
    }


def evaluate_gate(case: EvalCase, metrics: dict[str, float]) -> CaseResult:
    kpis: list[KpiResult] = []

    def add(kpi_id: str, value: float, target: str, passed: bool, detail: str, unit: str = "pct") -> None:
        severity = "ok" if passed else "fail"
        kpis.append(KpiResult(kpi_id=kpi_id, value=value, target=target, passed=passed, severity=severity, detail=detail, unit=unit))

    add(
        "KPI-AC-001",
        metrics["KPI-AC-001"],
        f">= {case.expected_contract_pass_rate_min}",
        metrics["KPI-AC-001"] >= case.expected_contract_pass_rate_min,
        "Answer Contract pass rate",
    )
    add(
        "KPI-CT-001",
        metrics["KPI-CT-001"],
        f">= {case.expected_citation_coverage_min}",
        metrics["KPI-CT-001"] >= case.expected_citation_coverage_min,
        "Citation coverage",
    )
    add(
        "KPI-EV-001",
        metrics["KPI-EV-001"],
        f"<= {case.expected_zero_evidence_rate_max}",
        metrics["KPI-EV-001"] <= case.expected_zero_evidence_rate_max,
        "Zero evidence rate",
    )
    add(
        "KPI-FC-001",
        metrics["KPI-FC-001"],
        f"<= {case.expected_fail_closed_rate_max}",
        metrics["KPI-FC-001"] <= case.expected_fail_closed_rate_max,
        "Fail-closed conversion rate",
    )
    add(
        "KPI-FF-001",
        metrics["KPI-FF-001"],
        f"<= {case.expected_fallback_leak_count_max}",
        metrics["KPI-FF-001"] <= case.expected_fallback_leak_count_max,
        "Free-text fallback leakage count",
        unit="count",
    )
    add(
        "KPI-TR-001",
        metrics["KPI-TR-001"],
        f">= {case.expected_trace_coverage_min}",
        metrics["KPI-TR-001"] >= case.expected_trace_coverage_min,
        "Trace coverage",
    )
    add(
        "KPI-PII-001",
        metrics["KPI-PII-001"],
        f"<= {case.expected_pii_leak_count_max}",
        metrics["KPI-PII-001"] <= case.expected_pii_leak_count_max,
        "PII suspected count",
        unit="count",
    )
    add(
        "KPI-LAT-001",
        metrics["KPI-LAT-001"],
        f"<= {case.expected_p95_e2e_ms_max}",
        metrics["KPI-LAT-001"] <= case.expected_p95_e2e_ms_max,
        "E2E latency p95",
        unit="ms",
    )
    add(
        "KPI-LAT-002",
        metrics["KPI-LAT-002"],
        f"<= {case.expected_p95_first_token_ms_max}",
        metrics["KPI-LAT-002"] <= case.expected_p95_first_token_ms_max,
        "First-token latency p95",
        unit="ms",
    )
    add(
        "KPI-SSE-001",
        metrics["KPI-SSE-001"],
        f">= {case.expected_stream_completion_rate_min}",
        metrics["KPI-SSE-001"] >= case.expected_stream_completion_rate_min,
        "SSE completion rate",
    )
    add(
        "KPI-TOOL-001",
        metrics["KPI-TOOL-001"],
        f">= {case.expected_tool_success_rate_min}",
        metrics["KPI-TOOL-001"] >= case.expected_tool_success_rate_min,
        "Tool success rate",
    )
    add(
        "KPI-FB-001",
        metrics["KPI-FB-001"],
        f">= {case.expected_feedback_positive_rate_min}",
        metrics["KPI-FB-001"] >= case.expected_feedback_positive_rate_min,
        "Positive feedback rate",
    )

    failed = [item.kpi_id for item in kpis if not item.passed]
    return CaseResult(
        case_id=case.case_id,
        tenant_id=case.tenant_id,
        scenario=case.scenario,
        from_ts=case.from_ts.isoformat(),
        to_ts=case.to_ts.isoformat(),
        kpis=kpis,
        passed=not failed,
        failed_kpis=failed,
    )


def write_report(path: Path, results: list[CaseResult], dry_run: bool) -> None:
    payload: dict[str, Any] = {
        "generated_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "mode": "dry_run" if dry_run else "live",
        "summary": {
            "total_cases": len(results),
            "passed_cases": sum(1 for item in results if item.passed),
            "failed_cases": sum(1 for item in results if not item.passed),
        },
        "results": [
            {
                "case_id": item.case_id,
                "tenant_id": item.tenant_id,
                "scenario": item.scenario,
                "from_ts": item.from_ts,
                "to_ts": item.to_ts,
                "passed": item.passed,
                "failed_kpis": item.failed_kpis,
                "kpis": [
                    {
                        "kpi_id": kpi.kpi_id,
                        "value": kpi.value,
                        "unit": kpi.unit,
                        "target": kpi.target,
                        "passed": kpi.passed,
                        "severity": kpi.severity,
                        "detail": kpi.detail,
                    }
                    for kpi in item.kpis
                ],
            }
            for item in results
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    cases = load_cases(args.dataset)
    dsn = os.getenv(args.db_dsn_env)
    results: list[CaseResult] = []

    for case in cases:
        if args.dry_run:
            metrics = build_mock_kpis_for_dry_run(case)
        else:
            if not dsn:
                raise RuntimeError(
                    f"Environment variable {args.db_dsn_env} is required in live mode. "
                    "Do not hardcode secrets in repository."
                )
            metrics = query_kpis_from_db(dsn, case)
        results.append(evaluate_gate(case, metrics))

    write_report(args.out, results, args.dry_run)
    return 0 if all(result.passed for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())

