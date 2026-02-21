# GAP Assessment Report

- generated_at: 2026-02-21 03:25 (KST)
- scope: Post-Gap-Closure hardening evidence audit
- baseline_commands:
  - `backend\gradlew.bat test --no-daemon` PASS
  - `cd frontend && npm ci && npm run test:run && npm run build` PASS
  - `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1` PASS
  - `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1` SKIPPED (docker daemon unavailable)
  - `powershell -ExecutionPolicy Bypass -File scripts/assert_provider_regression_evidence.ps1` PASS

## Gap Matrix

| Item | AGENTS.md requirement | current evidence(path) | status | action |
|---|---|---|---|---|
| A) Answer Contract fail-closed | 4.1 Answer Contract/fail-closed 강제 | `backend/src/test/java/com/aichatbot/message/presentation/MessageAnswerContractNegativeFlowTest.java`, `backend/src/main/java/com/aichatbot/message/application/MessageGenerationService.java`, `docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt` | OK | 미인용/스키마오류/근거점수미달에서 safe_response/error/done 계약 유지 |
| B) PII masking/exclusion | 4.2 입력/로그/캐시/응답 PII 차단 | `backend/src/test/java/com/aichatbot/message/presentation/PiiEndToEndContractTest.java`, `backend/src/test/java/com/aichatbot/global/privacy/PiiMaskingServiceTest.java`, `docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt` | OK | LLM 입력 전/로그/DB 저장/SSE payload raw PII 무유출 검증 |
| C) trace_id propagation/storage | 1.2, 4.3 trace_id 전파/저장 누락 금지 | `backend/src/test/java/com/aichatbot/global/observability/TraceIdContractTest.java`, `backend/src/main/java/com/aichatbot/message/infrastructure/StreamEventRepository.java`, `backend/src/main/java/com/aichatbot/rag/infrastructure/RagSearchLogRepository.java` | OK | missing header 자동 생성, invalid format 409, message/rag/stream_event 저장 일치 검증 |
| D) Tenant isolation | 4.4 tenant 격리 서버 강제 | `backend/src/test/java/com/aichatbot/session/presentation/UuidAccessContractTest.java`, `backend/src/test/java/com/aichatbot/security/RbacTenantMatrixTest.java` | OK | 핵심 endpoint군 cross-tenant 403 검증 |
| E) RBAC matrix | 4.4 RBAC server authority | `backend/src/test/java/com/aichatbot/security/RbacTenantMatrixTest.java`, `backend/src/test/java/com/aichatbot/billing/presentation/TenantBillingRbacTest.java` | OK | no-auth=401 / wrong-role=403 일관성 확인 |
| F) SSE abuse defense | 4.5 concurrency/rate-limit 서버 강제 | `backend/src/test/java/com/aichatbot/message/presentation/SseConcurrencyLimitContractTest.java`, `backend/src/main/java/com/aichatbot/message/application/SseConcurrencyGuard.java`, `docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt` | OK | concurrency limit 유지 + leak/false-429 방지 동시 검증 |
| G) Frontend automated tests | 10.2 frontend 자동 검증 | `frontend/src/utils/uuid.test.ts`, `frontend/src/utils/sseParser.test.ts`, `frontend/src/utils/errorMapping.test.ts`, `frontend/src/App.invalid-id-guard.test.tsx` | OK | UUID 사전 차단/SSE 파서/에러 UX 자동 검증 |
| H) CI enforcement + secret scan | 10, 12 테스트·게이트 자동화 | `.github/workflows/mvp-demo-verify.yml`, `.gitleaks.toml`, `scripts/lint_uuid_params.py`, `scripts/assert_provider_regression_evidence.ps1` | OK | UUID/gitleaks/verification/provider-evidence 정합성 게이트 반영 |
| I) Provider evidence coherence | Completion 증빙 객관성 유지 | `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md`, `docs/review/mvp_verification_pack/artifacts/provider_evidence_consistency_output.txt`, `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama_PASS_20260219_003600Z.txt` | OK | 최신 local SKIPPED와 최신 PASS 근거를 분리해 모순 차단 |

## Notes
- cache/summary 전용 persistence 계층은 현재 구현 범위에 없다. 따라서 현재는 별도 PII 저장 경로가 없다.
- 해당 계층 도입 시 PII exclusion 테스트를 P0 필수 항목으로 추가한다.
