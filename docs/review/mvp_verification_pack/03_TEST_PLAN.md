# MVP 테스트 계획 (SSOT)

- Last synced at: 2026-02-21 03:25 (KST)
- Version(commit): `working-tree`
- Canonical results: `04_TEST_RESULTS.md`

## 실행 순서
1. `docker compose -f infra/docker-compose.yml up -d`
2. `cd backend && .\gradlew.bat test --no-daemon`
3. `cd frontend && npm ci && npm run test:run && npm run build`
4. `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
5. `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1` (조건 충족 시)

## 테스트 목록

| Test ID | 목적 | 기대 결과 | 증빙 파일 |
|---|---|---|---|
| AUTO-BE-001 | 백엔드 전체 테스트 | PASS | `artifacts/backend_gradle_test_output.txt` |
| AUTO-PY-001 | Python SSE 단위 테스트 | PASS | `artifacts/python_sse_test_output.txt` |
| AUTO-FE-001 | 프론트 의존성/테스트/빌드 | PASS | `artifacts/frontend_npm_ci_output.txt`, `artifacts/frontend_test_output.txt`, `artifacts/frontend_build_output.txt` |
| BOOT-PG-001 | Postgres+Flyway+bootRun | PASS | `artifacts/backend_bootrun_postgres_output.txt` |
| NEG-ANSWER-CONTRACT-001 | Answer Contract 음수 3종 강제 | safe_response/error + done + free-text fallback 금지 | `artifacts/backend_gradle_test_output.txt` |
| PII-E2E-001 | PII E2E 무유출 | 프롬프트/로그/DB 저장값 raw PII 미노출 | `artifacts/backend_gradle_test_output.txt` |
| TRACE-CONTRACT-001 | trace_id 계약 보장 | 자동 생성/형식 검증/SSE-DB 전파 일치 | `artifacts/backend_gradle_test_output.txt` |
| RBAC-TENANT-MATRIX-001 | RBAC + 테넌트 매트릭스 | no-auth=401, wrong-role=403, cross-tenant=403 | `artifacts/backend_gradle_test_output.txt` |
| SSE-RESUME-CONTRACT-001 | stream/resume 계약 | checkpoint 이후 이벤트만 재전송 | `artifacts/backend_gradle_test_output.txt` |
| FE-UUID-UNIT-001 | UUID 유틸 사전 검증 | invalid UUID 차단 | `artifacts/frontend_test_output.txt` |
| FE-SSE-PARSER-001 | SSE 파서 시퀀스 파싱 | token/citation/safe_response/error/done 안정 파싱 | `artifacts/frontend_test_output.txt` |
| FE-ERROR-MAP-001 | 에러 UX 매핑 | 400/403/404 구분 메시지 노출 | `artifacts/frontend_test_output.txt` |
| FE-INVALID-ID-001 | App invalid-id guard | API 호출 전 차단 + 배너 표시 | `artifacts/frontend_test_output.txt` |
| E2E-AUTH-401 | 무인증 차단 | `401 + SEC-001-401` | `artifacts/rbac_401_403_checks.txt` |
| E2E-AUTH-403 | RBAC 차단 | `403 + SEC-002-403` | `artifacts/rbac_401_403_checks.txt` |
| E2E-SESSION-001 | 세션 생성 | PASS | `artifacts/e2e_curl_transcripts.txt` |
| E2E-MSG-001 | 질문 등록 | PASS | `artifacts/e2e_curl_transcripts.txt` |
| SSE-NORMAL-001 | 정상 스트림 | `heartbeat -> tool -> citation -> token -> done` | `artifacts/sse_stream_normal.log` |
| SSE-FAIL-001 | Fail-Closed | `safe_response -> error -> done` + token leak 없음 | `artifacts/sse_stream_fail_closed.log` |
| SSE-RESUME-001 | resume 기본 | `last_event_id+1`부터 재생 | `artifacts/sse_resume_proof.log` |
| SSE-RESUME-NET-001 | fault-injection resume | 중복/누락/역순 없이 재연결 | `artifacts/sse_resume_fault_injection.log` |
| SSE-CONC-429 | 동시성 제한 | `429 + API-008-429-SSE` | `artifacts/sse_concurrency_attempts.txt` |
| SSE-CONC-CONTRACT-001 | SSE 동시성 계약 테스트(백엔드) | key(`app.budget.sse-concurrency-max-per-user`) 기준 under-limit 정상, over-limit 429(표준 JSON+trace_id), finally 해제 후 오탐 429 없음 | `artifacts/sse_concurrency_contract_test_output.txt`, `artifacts/backend_gradle_test_output.txt` |
| SSE-CONC-REAL-001 | 운영 한도 동시성 제한 | `limit=2`에서 3번째 stream이 429 | `artifacts/sse_concurrency_real_limit_proof.txt` |
| NEG-422-IDEM | idempotency key 누락 | `422 + API-003-422` | `artifacts/idempotency_negative_422.txt` |
| NEG-IDEM-409 | 동일 key 중복 | `409 + API-003-409` | `artifacts/idempotency_409_proof.txt` |
| NEG-IDEM-REDIS-001 | 재시작 후 중복 차단 | `409 + API-003-409` | `artifacts/idempotency_redis_e2e.txt` |
| NEG-TENANT-001 | 교차 테넌트 차단 | `403 + SYS-002-403 + tenant_mismatch` | `artifacts/tenant_isolation_403_checks.txt` |
| NEG-BUDGET-001 | budget 초과 방어 | `429 + API-008-429-BUDGET` | `artifacts/budget_429_checks.txt` |
| PII-REQ-001 | 요청 마스킹 | raw PII 미노출 | `artifacts/pii_masking_checks.txt` |
| PII-RESP-001 | 인용 발췌 마스킹 | `excerpt_masked`에서 raw PII 미노출 | `artifacts/citations_api_response.json`, `artifacts/pii_masking_checks.txt` |
| OBS-TRACE-001 | trace_id 종단 추적 | HTTP/SSE/DB 동일 trace_id | `artifacts/trace_id_checks.txt` |
| OBS-METRICS-001 | 운영 지표 리포트 | p50/p95 + n + 해석 경고 출력 | `artifacts/metrics_raw.txt`, `artifacts/metrics_report.md` |
| SEC-ARTIFACT-SCAN-001 | 아티팩트 비밀/PII 스캔 | 패턴 스캔 PASS | `artifacts/artifact_sanitization_scan.txt` |
| CI-UUID-LINT-001 | UUID String 회귀 게이트 | 위반 시 즉시 실패 | `artifacts/backend_gradle_test_output.txt` |
| CI-GITLEAKS-001 | 시크릿 스캔 게이트 | PR에서 leak 발견 시 실패 | `.github/workflows/mvp-demo-verify.yml`, `.gitleaks.toml` |
| LLM-PROVIDER-001 | provider 회귀 | PASS 또는 명시적 SKIPPED(+해결가이드) | `artifacts/provider_regression_ollama.log`, `artifacts/provider_regression_gap_closure_output.txt` |
| PROVIDER-EVIDENCE-001 | provider 증빙 정합성 검증 | 최신 SKIPPED일 때 최신 PASS 근거 문서/아티팩트 강제 | `artifacts/provider_evidence_consistency_output.txt`, `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md` |
| VER-CONSIST-001 | 검증팩 정합성 | SSOT 문서 충돌/증빙 누락 없음 | `artifacts/gap_closure_consistency_output.txt` |
