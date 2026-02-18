# MVP 테스트 결과 (SSOT)

- Last synced at: 2026-02-18 20:00 (KST)
- Version(commit): `3e057a3+working-tree`
- Status: Demo Ready

## 실행 환경
- OS: Windows 11
- Java: 17
- Node: v24.11.1 (로컬 실행은 `APP_VERIFY_ALLOW_NON_22_NODE=true` 오버라이드, 기본 정책은 22 강제)
- Python: 3.11

## 실행 명령
1. `docker compose -f infra/docker-compose.yml up -d`
2. `cd backend && .\gradlew.bat test --no-daemon`
3. `cd frontend && npm ci && npm run build`
4. `powershell -ExecutionPolicy Bypass -File scripts/verify_all.ps1`
5. `python tests/sse_stream_basic_test.py`
6. `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`

## 결과표

| Test ID | 상태 | 근거 파일 |
|---|---|---|
| AUTO-BE-001 | PASS | `artifacts/backend_gradle_test_output.txt` |
| AUTO-PY-001 | PASS | `artifacts/python_sse_test_output.txt` |
| AUTO-FE-001 | PASS | `artifacts/frontend_npm_ci_output.txt`, `artifacts/frontend_build_output.txt` |
| BOOT-PG-001 | PASS | `artifacts/backend_bootrun_postgres_output.txt` |
| E2E-AUTH-401 | PASS | `artifacts/rbac_401_403_checks.txt` |
| E2E-AUTH-403 | PASS | `artifacts/rbac_401_403_checks.txt` |
| E2E-SESSION-001 | PASS | `artifacts/e2e_curl_transcripts.txt` |
| E2E-MSG-001 | PASS | `artifacts/e2e_curl_transcripts.txt` |
| SSE-NORMAL-001 | PASS | `artifacts/sse_stream_normal.log` |
| SSE-FAIL-001 | PASS | `artifacts/sse_stream_fail_closed.log` |
| SSE-RESUME-001 | PASS | `artifacts/sse_resume_proof.log` |
| SSE-RESUME-NET-001 | PASS | `artifacts/sse_resume_fault_injection.log` |
| SSE-CONC-429 | PASS | `artifacts/sse_concurrency_attempts.txt` |
| SSE-CONC-REAL-001 | PASS | `artifacts/sse_concurrency_real_limit_proof.txt` |
| NEG-422-IDEM | PASS | `artifacts/idempotency_negative_422.txt` |
| NEG-IDEM-409 | PASS | `artifacts/idempotency_409_proof.txt` |
| NEG-IDEM-REDIS-001 | PASS | `artifacts/idempotency_redis_e2e.txt` |
| NEG-TENANT-001 | PASS | `artifacts/tenant_isolation_403_checks.txt` |
| NEG-BUDGET-001 | PASS | `artifacts/budget_429_checks.txt` |
| PII-REQ-001 | PASS | `artifacts/pii_masking_checks.txt` |
| PII-RESP-001 | PASS | `artifacts/citations_api_response.json`, `artifacts/pii_masking_checks.txt` |
| OBS-TRACE-001 | PASS | `artifacts/trace_id_checks.txt` |
| OBS-METRICS-001 | PASS (n=2, 경고표시) | `artifacts/metrics_raw.txt`, `artifacts/metrics_report.md` |
| SEC-ARTIFACT-SCAN-001 | PASS | `artifacts/artifact_sanitization_scan.txt` |
| LLM-PROVIDER-001 | SKIPPED | `artifacts/provider_regression_ollama.log` |
| VER-CONSIST-001 | PASS | `artifacts/e2e_runner_stdout.txt` |

## SKIPPED 사유 및 해결법
- `LLM-PROVIDER-001` 사유: ollama endpoint 미준비 또는 환경변수 미설정
- 해결 순서:
1. `docker compose -f infra/docker-compose.ollama.yml up -d`
2. `set APP_OLLAMA_BASE_URL=http://localhost:11434`
3. `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`

## 정책 확인 포인트
- trace_id 정책: UUID 형식만 허용 (`SYS-004-409-TRACE`)
- tenant mismatch: `403 + SYS-002-403 + details=["tenant_mismatch"]`
- Node 정책: 기본은 22.12.0 강제이며, 로컬 임시 진단 시에만 APP_VERIFY_ALLOW_NON_22_NODE=true 오버라이드 허용 (`artifacts/node_version_check.txt`)


