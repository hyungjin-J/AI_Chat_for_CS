# E2E Smoke Triage (2026-03-02)

- Source report: `docs/review/mvp_verification_pack/artifacts/e2e_smoke_report_20260302.json`
- Source trace: `docs/review/mvp_verification_pack/artifacts/e2e_smoke_trace_samples_20260302.txt`
- Observation: the run failed at bootstrap (`/v1/auth/login` connection refused), so `S1` and `S6` were not executed in this specific artifact.

| scenario | step | http_status | error_code | missing_event | note |
|---|---|---:|---|---|---|
| S1 | blocked_by_bootstrap (`http_connect`) | N/A | N/A | `token,citation,done` | base URL unreachable before scenario execution |
| S6 | blocked_by_bootstrap (`http_connect`) | N/A | N/A | `safe_response,error,done` | fail-closed scenario not reached due bootstrap failure |

## Bootstrap Failure Evidence

| scenario | step | http_status | error_code | missing_event | note |
|---|---|---:|---|---|---|
| BOOTSTRAP | `http_connect` | N/A | N/A | N/A | `POST /v1/auth/login` failed with connection refused (`WinError 10061`) |

## Supplemental Stability Evidence (same date, separate runs)

- `e2e_smoke_report_20260302_run1.json`: S1 PASS, S6 PASS
- `e2e_smoke_report_20260302_run2.json`: S1 PASS, S6 PASS
- `e2e_smoke_report_20260302_run3.json`: S1 PASS, S6 PASS
