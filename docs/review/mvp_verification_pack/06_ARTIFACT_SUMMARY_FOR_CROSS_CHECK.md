# 아티팩트 요약본 (교차 검증용 SSOT)

- Last synced at: 2026-02-19 00:40 (KST)
- Version(commit): `3e057a3+working-tree`
- Status source: `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`

## 상태 매트릭스 (04와 동일)

| Test ID | 상태 |
|---|---|
| AUTO-BE-001 | PASS |
| AUTO-PY-001 | PASS |
| AUTO-FE-001 | PASS |
| BOOT-PG-001 | PASS |
| E2E-AUTH-401 | PASS |
| E2E-AUTH-403 | PASS |
| E2E-SESSION-001 | PASS |
| E2E-MSG-001 | PASS |
| SSE-NORMAL-001 | PASS |
| SSE-FAIL-001 | PASS |
| SSE-RESUME-001 | PASS |
| SSE-RESUME-NET-001 | PASS |
| SSE-CONC-429 | PASS |
| SSE-CONC-REAL-001 | PASS |
| NEG-422-IDEM | PASS |
| NEG-IDEM-409 | PASS |
| NEG-IDEM-REDIS-001 | PASS |
| NEG-TENANT-001 | PASS |
| NEG-BUDGET-001 | PASS |
| PII-REQ-001 | PASS |
| PII-RESP-001 | PASS |
| OBS-TRACE-001 | PASS |
| OBS-METRICS-001 | PASS |
| SEC-ARTIFACT-SCAN-001 | PASS |
| LLM-PROVIDER-001 | PASS |
| VER-CONSIST-001 | PASS |

## 핵심 증빙 파일
- 정상 SSE: `artifacts/sse_stream_normal.log`
- Fail-Closed: `artifacts/sse_stream_fail_closed.log`
- trace_id: `artifacts/trace_id_checks.txt`
- tenant 격리: `artifacts/tenant_isolation_403_checks.txt`
- PII: `artifacts/pii_masking_checks.txt`, `artifacts/citations_api_response.json`
- Budget/SSE429: `artifacts/budget_429_checks.txt`, `artifacts/sse_concurrency_attempts.txt`
- SSE real-limit 429: `artifacts/sse_concurrency_real_limit_proof.txt`
- Idempotency: `artifacts/idempotency_negative_422.txt`, `artifacts/idempotency_409_proof.txt`, `artifacts/idempotency_redis_e2e.txt`
- Metrics: `artifacts/metrics_raw.txt`, `artifacts/metrics_report.md`
- Artifact scan: `artifacts/artifact_sanitization_scan.txt`
- Provider: `artifacts/provider_regression_ollama.log`, `artifacts/analysis_llm_provider_001.md`

## 주의
- `LLM-PROVIDER-001`은 최신 provider 회귀 로그에서 `status=PASS`가 확인된 상태다.
- 향후 상태 변경 시에도 `provider_regression_ollama.log` 실증빙 없이는 상태 변경 금지.



- consistency 게이트 로그: `artifacts/e2e_runner_stdout.txt`

