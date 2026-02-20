# 아티팩트 요약본 (교차 검증용 SSOT)

- Last synced at: 2026-02-21 01:55 (KST)
- Version(commit): `working-tree`
- Status source: `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`

## 상태 매트릭스 (04와 동일)

| Test ID | 상태 |
|---|---|
| AUTO-BE-001 | PASS |
| AUTO-PY-001 | PASS |
| AUTO-FE-001 | PASS |
| BOOT-PG-001 | PASS |
| NEG-ANSWER-CONTRACT-001 | PASS |
| PII-E2E-001 | PASS |
| TRACE-CONTRACT-001 | PASS |
| RBAC-TENANT-MATRIX-001 | PASS |
| SSE-RESUME-CONTRACT-001 | PASS |
| FE-UUID-UNIT-001 | PASS |
| FE-SSE-PARSER-001 | PASS |
| FE-ERROR-MAP-001 | PASS |
| FE-INVALID-ID-001 | PASS |
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
| CI-UUID-LINT-001 | PASS |
| CI-GITLEAKS-001 | SKIPPED |
| LLM-PROVIDER-001 | SKIPPED |
| VER-CONSIST-001 | PASS |

## 핵심 증빙 파일
- 백엔드/정적 UUID lint: `artifacts/backend_gradle_test_output.txt`
- 프론트 테스트: `artifacts/frontend_test_output.txt`
- 프론트 빌드: `artifacts/frontend_build_output.txt`
- consistency 결과: `artifacts/gap_closure_consistency_output.txt`
- provider 조건부 실행 결과: `artifacts/provider_regression_ollama.log`, `artifacts/provider_regression_gap_closure_output.txt`
- UUID CAST / MyBatis `${}` 검색 결과: `artifacts/uuid_cast_scan_output.txt`, `artifacts/mybatis_dollar_scan_output.txt`

## 주의
- `LLM-PROVIDER-001`은 현재 로컬에서 Docker daemon 미기동으로 SKIPPED이며, 실패가 아니라 조건 미충족 상태다.
- provider 상태를 PASS로 변경하려면 `provider_regression_ollama.log`에 `status=PASS`가 기록되어야 한다.
