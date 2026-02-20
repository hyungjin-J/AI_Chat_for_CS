# GAP Assessment Report

- generated_at: 2026-02-21
- scope: Completion 주장에 대한 증빙/테스트/CI 게이트 갭 클로저 결과
- baseline_commands:
  - `backend\gradlew.bat test --no-daemon` PASS
  - `cd frontend && npm ci && npm run test:run && npm run build` PASS
  - `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1` PASS
  - `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1` SKIPPED (docker daemon unavailable)

## Gap Matrix

| Item | AGENTS.md requirement | current evidence(path) | status | action |
|---|---|---|---|---|
| A) Answer Contract fail-closed | 4.1 Answer Contract/fail-closed 강제 | `backend/src/test/java/com/aichatbot/message/presentation/MessageAnswerContractNegativeFlowTest.java`, `backend/src/main/java/com/aichatbot/message/application/MessageGenerationService.java`, `docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt` | OK | 음수 3종(미인용/스키마오류/근거점수미달)과 safe_response/error/done 계약 검증 완료 |
| B) PII masking/exclusion | 4.2 입력/로그/캐시/응답 PII 차단 | `backend/src/test/java/com/aichatbot/message/presentation/PiiEndToEndContractTest.java`, `backend/src/test/java/com/aichatbot/global/privacy/PiiMaskingServiceTest.java`, `backend/src/main/java/com/aichatbot/global/privacy/PiiMaskingService.java` | OK | LLM 입력 전/로그/DB 저장값(raw PII) 무유출 검증 완료 |
| C) trace_id propagation | 1.2, 4.3 trace_id 전파/누락 방지 | `backend/src/test/java/com/aichatbot/global/observability/TraceIdContractTest.java`, `backend/src/main/java/com/aichatbot/message/application/SseStreamService.java`, `backend/src/main/java/com/aichatbot/message/application/MessageGenerationService.java` | OK | 헤더 누락 자동생성, invalid format 409, SSE/DB trace 일치 검증 완료 |
| D) Tenant isolation | 4.4 tenant 격리 서버 강제 | `backend/src/test/java/com/aichatbot/session/presentation/UuidAccessContractTest.java`, `backend/src/test/java/com/aichatbot/security/RbacTenantMatrixTest.java` | OK | 핵심 endpoint군 cross-tenant 접근 403 매트릭스 검증 완료 |
| E) RBAC matrix | 4.4 RBAC server authority | `backend/src/test/java/com/aichatbot/security/RbacTenantMatrixTest.java`, `backend/src/test/java/com/aichatbot/billing/presentation/TenantBillingRbacTest.java` | OK | no-auth=401 / wrong-role=403 일관성 검증 완료 |
| F) Frontend automated tests | 10.2 frontend 자동 검증 | `frontend/src/utils/uuid.test.ts`, `frontend/src/utils/sseParser.test.ts`, `frontend/src/utils/errorMapping.test.ts`, `frontend/src/App.invalid-id-guard.test.tsx`, `docs/review/mvp_verification_pack/artifacts/frontend_test_output.txt` | OK | UUID 사전 검증, SSE 파싱, 오류 UX 자동 테스트 구축 |
| G) CI enforcement + secret scan | 10, 12 테스트·게이트 자동화 | `.github/workflows/mvp-demo-verify.yml`, `.gitleaks.toml`, `scripts/lint_uuid_params.py` | OK | PR 게이트에 frontend test/uuid lint/gitleaks/consistency 반영, provider는 조건부 실행 |

## Notes
- cache/summary 별도 저장 계층은 현재 구현 범위에 없음. 해당 저장 계층 도입 시 PII exclusion 테스트를 추가하는 후속 항목으로 관리한다.
- provider regression은 AGENTS 규칙에 맞춰 조건부 실행 정책으로 유지한다. 현재 로컬 실행은 Docker daemon 미기동으로 SKIPPED이며, CI/nightly 경로에서 강제 가능하다.
