# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- purpose: ChatGPT 인수인계를 위한 구조/검증/증빙 가이드
- updated_at: 2026-02-21 03:25 (KST)

## 1) Completion 상태
- backend test: PASS (`docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt`)
- frontend test/build: PASS (`docs/review/mvp_verification_pack/artifacts/frontend_test_output.txt`, `docs/review/mvp_verification_pack/artifacts/frontend_build_output.txt`)
- verification consistency: PASS (`docs/review/mvp_verification_pack/artifacts/gap_closure_consistency_output.txt`)
- provider regression latest local: SKIPPED (`docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`)
- provider PASS 근거 SSOT: `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md`

## 2) Plan Mode 초반 기초 설정(필수 기록)
1. `AGENTS.md` 최신 규칙 재확인
- Fail-Closed, PII 차단, trace_id, tenant/RBAC, budget, MyBatis/no `${}`를 작업 기준으로 고정

2. Hardening Gate 선행 문서 작성
- `docs/review/plans/20260220_post_gap_closure_hardening_plan.md`
- Why/Scope/Regression/DoD/검증 명령/리스크/롤백을 코드 변경 전에 먼저 고정

3. 베이스라인 점검 실행
- `backend\gradlew.bat test --no-daemon`
- `cd frontend && npm ci && npm run test:run && npm run build`
- `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`

4. 증빙 갭 우선순위 확정
- Provider PASS 근거 분리
- SSE 동시성 오해 제거(한도 유지 증명)
- PII/trace_id 테스트 증빙 보강

## 3) 전체 구조도
```text
AI_Chatbot/
├─ backend/
│  ├─ src/main/java/com/aichatbot/
│  │  ├─ global/      # security, error, observability, tenant, privacy
│  │  ├─ auth/
│  │  ├─ session/
│  │  ├─ message/
│  │  ├─ rag/
│  │  ├─ billing/
│  │  └─ tool/
│  ├─ src/main/resources/mappers/   # MyBatis XML
│  └─ src/test/java/com/aichatbot/  # 계약/통합 테스트
├─ frontend/src/       # App + utils + vitest tests
├─ scripts/            # check/lint/provider/assert scripts
├─ .github/workflows/  # PR/nightly gates
└─ docs/review/        # plans/final/mvp_verification_pack
```

## 4) 이번 하드닝 구현 요약

### 4.1 Provider 증빙 SSOT
- 신규 문서: `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md`
- 신규 스크립트: `scripts/assert_provider_regression_evidence.ps1`
- 신규 PASS 아티팩트: `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama_PASS_20260219_003600Z.txt`
- 목적: 최신 local 결과가 SKIPPED여도 최신 PASS 근거를 빠르게 추적 가능하게 유지

### 4.2 SSE 동시성 제한 증명
- 신규 테스트: `backend/src/test/java/com/aichatbot/message/presentation/SseConcurrencyLimitContractTest.java`
- 보강 코드:
  - `backend/src/main/java/com/aichatbot/message/application/SseStreamService.java`
  - `backend/src/main/java/com/aichatbot/message/application/SseConcurrencyGuard.java` (기존 정책 유지)
- 명시: 동시성 한도는 그대로 유지되고, 누수/오탐(불필요 429)만 수정했다.
- 핵심 문구: 동시성 한도는 유지되며, 누수/오탐 429만 보정됨

### 4.3 PII/trace_id 증빙 강화
- PII E2E 강화:
  - `backend/src/test/java/com/aichatbot/message/presentation/PiiEndToEndContractTest.java`
  - prompt/log/db + SSE payload에서 raw PII 무유출 검증
- trace_id 강화:
  - `backend/src/test/java/com/aichatbot/global/observability/TraceIdContractTest.java`
  - safe_response/error/done + message/rag/stream_event 저장 일치
- 이벤트 payload trace 보강:
  - `backend/src/main/java/com/aichatbot/message/application/MessageGenerationService.java`
  - `backend/src/main/java/com/aichatbot/message/infrastructure/StreamEventRepository.java`

### 4.4 저장 경로 trace 강제
- `backend/src/main/java/com/aichatbot/message/infrastructure/MessageRepository.java`
- `backend/src/main/java/com/aichatbot/session/infrastructure/ConversationRepository.java`
- `backend/src/main/java/com/aichatbot/rag/infrastructure/RagSearchLogRepository.java`
- 목적: ingress trace context 누락 시 저장을 fail-closed로 차단

### 4.5 CI/one-command 연동
- CI 업데이트: `.github/workflows/mvp-demo-verify.yml`
  - `assert_provider_regression_evidence.ps1` 단계 추가
- one-command 업데이트: `scripts/check_all.ps1`
  - provider evidence consistency 단계 추가

## 5) 테스트 목록(핵심)
- `MessageAnswerContractNegativeFlowTest`
- `PiiEndToEndContractTest`
- `TraceIdContractTest`
- `RbacTenantMatrixTest`
- `SseResumeContractTest`
- `SseConcurrencyLimitContractTest`
- frontend:
  - `uuid.test.ts`
  - `sseParser.test.ts`
  - `errorMapping.test.ts`
  - `App.invalid-id-guard.test.tsx`

## 6) 실행 명령
1. `cd backend && .\gradlew.bat test --no-daemon`
2. `cd frontend && npm ci && npm run test:run && npm run build`
3. `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
4. `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`
5. `powershell -ExecutionPolicy Bypass -File scripts/assert_provider_regression_evidence.ps1`

## 7) 운영 주의사항
- provider latest local 결과가 SKIPPED여도 Completion 보고 시 PASS로 표기하면 안 된다.
- PASS 여부는 `PROVIDER_REGRESSION_EVIDENCE.md`의 최신 PASS 항목으로 판단한다.
- cache/summary persistence 계층은 아직 별도 구현이 없다(도입 시 PII 테스트 필수 추가).
- Node 표준은 22.x이며 로컬 24.x에서는 엔진 경고가 발생할 수 있다.

## 8) SSE 동시성 정책 고정값
- key name: `app.budget.sse-concurrency-max-per-user`
- default value: `2`
- enforcement unit: `user` (내부적으로 `tenant_id:user_id` 조합 키)
- session 전용 동시성 키: 없음

제한 초과 정책:
- HTTP `429`
- 표준 에러 JSON(`error_code`, `message`, `trace_id`, `details`) 유지
- `trace_id` 필드 누락 금지

회귀 방지 증빙:
- `SseConcurrencyLimitContractTest#shouldEnforceSseConcurrencyLimitAndReleaseAfterCompletion`
- `SseConcurrencyLimitContractTest#shouldNotProduceFalse429AfterCompletedStreamFinallyRelease`
- 실행 로그: `docs/review/mvp_verification_pack/artifacts/sse_concurrency_contract_test_output.txt`
