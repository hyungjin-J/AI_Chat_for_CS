# MVP 테스트 결과 (SSOT)

- Last synced at: 2026-02-21 01:55 (KST)
- Version(commit): `working-tree`
- Status: Gap Closure Evidence Updated

## 실행 환경
- OS: Windows 11
- Java: 17
- Node: v24.11.1 (프로젝트 표준은 22.x)
- Python: 3.11

## 실행 명령
1. `cd backend && .\gradlew.bat test --no-daemon`
2. `cd frontend && npm ci && npm run test:run && npm run build`
3. `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
4. `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`
5. `rg -n "CAST\(#\{.*\} AS UUID\)" backend/src/main/resources/mappers -S`
6. `rg -n "\$\{" backend/src/main/resources/mappers -S`

## 결과표

| Test ID | 상태 | 근거 파일 |
|---|---|---|
| AUTO-BE-001 | PASS | `artifacts/backend_gradle_test_output.txt` |
| AUTO-PY-001 | PASS | `artifacts/python_sse_test_output.txt` |
| AUTO-FE-001 | PASS | `artifacts/frontend_npm_ci_output.txt`, `artifacts/frontend_test_output.txt`, `artifacts/frontend_build_output.txt` |
| BOOT-PG-001 | PASS | `artifacts/backend_bootrun_postgres_output.txt` |
| NEG-ANSWER-CONTRACT-001 | PASS | `artifacts/backend_gradle_test_output.txt` |
| PII-E2E-001 | PASS | `artifacts/backend_gradle_test_output.txt` |
| TRACE-CONTRACT-001 | PASS | `artifacts/backend_gradle_test_output.txt` |
| RBAC-TENANT-MATRIX-001 | PASS | `artifacts/backend_gradle_test_output.txt` |
| SSE-RESUME-CONTRACT-001 | PASS | `artifacts/backend_gradle_test_output.txt` |
| FE-UUID-UNIT-001 | PASS | `artifacts/frontend_test_output.txt` |
| FE-SSE-PARSER-001 | PASS | `artifacts/frontend_test_output.txt` |
| FE-ERROR-MAP-001 | PASS | `artifacts/frontend_test_output.txt` |
| FE-INVALID-ID-001 | PASS | `artifacts/frontend_test_output.txt` |
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
| OBS-METRICS-001 | PASS | `artifacts/metrics_raw.txt`, `artifacts/metrics_report.md` |
| SEC-ARTIFACT-SCAN-001 | PASS | `artifacts/artifact_sanitization_scan.txt` |
| CI-UUID-LINT-001 | PASS | `artifacts/backend_gradle_test_output.txt` |
| CI-GITLEAKS-001 | SKIPPED (local) | CI workflow only (`.github/workflows/mvp-demo-verify.yml`) |
| LLM-PROVIDER-001 | SKIPPED (docker unavailable) | `artifacts/provider_regression_ollama.log`, `artifacts/provider_regression_gap_closure_output.txt`, `artifacts/provider_regression_exit_code.txt` |
| VER-CONSIST-001 | PASS | `artifacts/gap_closure_consistency_output.txt` |

## 정책 확인 포인트
- UUID CAST 검색: `artifacts/uuid_cast_scan_output.txt` => `NO_MATCH`
- MyBatis `${}` 검색: `artifacts/mybatis_dollar_scan_output.txt` => `NO_MATCH`
- trace_id 정책: UUID 형식만 허용 (`SYS-004-409-TRACE`)
- tenant mismatch: `403 + SYS-002-403 + details=["tenant_mismatch"]`
- provider는 PR에서 조건부 실행, nightly는 강제 실행
