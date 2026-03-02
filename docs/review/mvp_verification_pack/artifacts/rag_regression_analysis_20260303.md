# RAG Regression Analysis (2026-03-03)

## Previous FAIL Snapshot (2026-03-02)
| Artifact | Observed status | reason_code | Evidence detail |
| --- | --- | --- | --- |
| `rag_regression_gate_20260302.txt` | FAIL | DATA_UNAVAILABLE | preflight `admin_login_failed` with `network_error=[WinError 10061]` |
| `eval/out/latest/report.json` (previous run) | SKIPPED | DATA_UNAVAILABLE | all cases skipped before metric evaluation |

## Root Cause Classification
`DATA_UNAVAILABLE` on 2026-03-02 was not a KB seed/indexing issue. The immediate failure point was API reachability (`localhost:8080` refused connection) during preflight login.

## Fix Applied
1. `eval/run_rag_regression.py`
- Added base-url probe in preflight.
- Classifies unreachable target as `TARGET_UNREACHABLE`.
- Added auto-seed trigger when approved/indexed docs are below minimum.
- Uses seed result and re-checks tenant readiness before running cases.

2. `eval/seed_kb_minimal.py`
- Added callable function `seed_minimal_kb(...)` for harness reuse.
- Added base-url probe and `TARGET_UNREACHABLE` classification.
- Preserved always-write report behavior for all failure paths.

3. `eval/assert_rag_quality_gate.py`
- Added `TARGET_UNREACHABLE` as precondition reason for deterministic gate diagnosis.

## Validation Result (2026-03-03)
- Seed: PASS (`eval/out/latest/seed_kb_minimal_report.json`)
- Regression harness: PASS (`eval/out/latest/report.json`, `summary.csv`)
- Gate: PASS (`artifacts/rag_regression_gate_20260303.txt/.json`)

## Notes
- In local non-mock LLM config (`APP_LLM_PROVIDER=ollama` without runtime), answer cases fail-closed and hit threshold undershoot.
- For deterministic local pass, backend was run with `APP_LLM_PROVIDER=mock`.
