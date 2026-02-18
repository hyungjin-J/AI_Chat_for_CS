# Metrics Report

- generated_at: 2026-02-18 19:58:41+09:00
- source: /actuator/prometheus
- metric_unit_policy: sse_first_token_seconds exposed in seconds, reported below in ms

| metric | value |
|---|---|
| sse_first_token_ms_p50 | 0.983 |
| sse_first_token_ms_p95 | 1.999 |
| sse_first_token_sample_n | 2 |
| fail_closed_rate | 0.047619047619047616 |
| citation_coverage | 1.0 |
| idempotency_redis_fallback_total | N/A |

## Interpretation
- WARNING: sample size is below 30, interpret p95 carefully.
- idempotency_redis_fallback_total > 0 means Redis fallback occurred and distributed idempotency strength may degrade.

## Notes
- See metrics_raw.txt for raw values.
- Option: powershell -ExecutionPolicy Bypass -File scripts/generate_metrics_report.ps1 -SampleCount 30
