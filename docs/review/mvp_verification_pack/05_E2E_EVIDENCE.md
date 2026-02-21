# E2E 증빙 (민감정보 마스킹)

- Last synced at: 2026-02-18 19:35 (KST)
- Version(commit): `3e057a3+working-tree`
- Status source: `04_TEST_RESULTS.md`

## 핵심 증빙
1. 정상 SSE + citation: `artifacts/sse_stream_normal.log`
2. Fail-Closed(토큰 누출 없음): `artifacts/sse_stream_fail_closed.log`
3. tenant 격리: `artifacts/tenant_isolation_403_checks.txt`
4. trace_id 종단 일치: `artifacts/trace_id_checks.txt`
5. PII 요청/응답 마스킹: `artifacts/pii_masking_checks.txt`, `artifacts/citations_api_response.json`

## 네거티브 증빙
- 인증/권한: `artifacts/rbac_401_403_checks.txt`
- budget 429: `artifacts/budget_429_checks.txt`
- SSE concurrency 429: `artifacts/sse_concurrency_attempts.txt`
- idempotency 누락 422: `artifacts/idempotency_negative_422.txt`
- idempotency 중복 409: `artifacts/idempotency_409_proof.txt`
- Redis 재시작 멱등성: `artifacts/idempotency_redis_e2e.txt`

## SSE resume fault-injection 강화 검증
- 파일: `artifacts/sse_resume_fault_injection.log`
- 포함 시나리오:
1. 중간 `last_event_id`에서 재연결(2회)
2. 과거 ID(`0`) 재연결
3. 미래 ID(`999`) 재연결
4. 이벤트 ID 중복/누락/순서 검증

## 관측/정합성 증빙
- metrics raw/report: `artifacts/metrics_raw.txt`, `artifacts/metrics_report.md`
- consistency gate 로그: `artifacts/e2e_runner_stdout.txt`

## Provider 회귀
- 파일: `artifacts/provider_regression_ollama.log`
- 최신 로컬 결과: SKIPPED (`status=SKIPPED`)
- 최신 PASS 근거: `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md`의 `latest_pass_artifact`

