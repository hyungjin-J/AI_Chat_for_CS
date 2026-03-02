# RAG Regression Analysis (2026-03-02)

Source files:
- `eval/out/latest/report.json`
- `eval/out/latest/summary.csv`
- `eval/thresholds.yaml`

Snapshot:
- `report.status=PASS`
- `report.reason_code=OK`
- `execution_summary: executed=6, passed=6, failed=0, skipped=0`

## Metric Threshold Check

| Metric | Actual | Threshold | Result |
| --- | ---: | ---: | --- |
| `citation_coverage_rate` | `1.000000` | `>= 0.80` | PASS |
| `fail_closed_rate` | `0.333333` | `0.10 <= x <= 0.80` | PASS |
| `policy_violation_rate` | `0.000000` | `<= 0.00` | PASS |
| `answer_contract_pass_rate` | `0.666667` | `>= 0.50` | PASS |
| `latency_p95_ms` | `26.932` | `<= 5000.0` | PASS |
| `case_pass_rate` | `1.000000` | `>= 0.80` | PASS |

## Failed Case Summary

| case_id | expected_outcome | status | reason_code | note |
| --- | --- | --- | --- | --- |
| *(none)* | - | - | - | all cases passed |

## Root Cause Fix Summary

- Preflight reason-code contract added: `DATA_UNAVAILABLE`, `INDEXING_INCOMPLETE`, `PROVIDER_UNAVAILABLE`.
- `always-write` report contract enforced (`report.json`/`summary.csv` are produced on success/fail/skip).
- KB seed prerequisite added (`eval/seed_kb_minimal.py`) with index completion polling.
- False-positive policy violations removed by narrowing PII patterns and scanning user-visible text fields only.
- Fail-closed case (`RAG-REG-006`) changed to deterministic no-evidence probe.
- Determinism check: `run + assert` 3 consecutive runs all PASS.
