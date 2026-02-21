# PROJECT COMPLETION REPORT

- generated_at: 2026-02-21 03:25 (KST)
- project: AI_Chatbot
- scope: Post-Gap-Closure Hardening (completion evidence closure)

## 1) 결과 요약
- P0 항목(Answer Contract fail-closed, PII 차단, trace_id 전파/저장, tenant/RBAC)은 테스트로 재검증했다.
- provider 회귀 최신 로컬 결과는 `SKIPPED`이며, PASS 근거는 SSOT 문서 `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md`로 분리 고정했다.
- SSE 동시성 제한은 유지된다. 이번 변경은 가드 해제 누수/오탐(불필요 429) 방지 보강이며, 한도 자체를 완화한 변경이 아니다.
- CI 게이트는 `assert_provider_regression_evidence.ps1`까지 포함해 증빙 모순을 차단한다.

## 2) 핵심 구현 내역

### 2.1 Provider 증빙 정합성
- 신규 SSOT 문서
  - `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md`
- 신규 정합성 스크립트
  - `scripts/assert_provider_regression_evidence.ps1`
- 신규 PASS 아티팩트(커밋 가능 형식)
  - `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama_PASS_20260219_003600Z.txt`
- CI 반영
  - `.github/workflows/mvp-demo-verify.yml`에 provider evidence consistency 단계 추가

### 2.2 SSE 동시성/Abuse Defense
- 신규 계약 테스트
  - `backend/src/test/java/com/aichatbot/message/presentation/SseConcurrencyLimitContractTest.java`
- 보강 내용
  - under-limit 정상 스트림(`token/citation/done`)
  - over-limit `429 + API-008-429-SSE + trace_id`
  - 완료 후 재요청 허용(가드 release 확인)

### 2.3 PII/trace_id 증빙 보강
- `backend/src/test/java/com/aichatbot/message/presentation/PiiEndToEndContractTest.java`
  - LLM 프롬프트/로그/DB 저장 + SSE payload raw PII 무유출 검증
- `backend/src/test/java/com/aichatbot/global/observability/TraceIdContractTest.java`
  - `safe_response/error/done` trace_id 일치
  - `tb_message`, `tb_rag_search_log`, `tb_stream_event(payload)` trace_id 일치
- 저장 경로 fail-closed 가드
  - `backend/src/main/java/com/aichatbot/message/infrastructure/StreamEventRepository.java`
  - stream event payload의 `trace_id` 누락 시 저장 차단

### 2.4 trace_id 일관성 코드 보강
- `backend/src/main/java/com/aichatbot/message/application/MessageGenerationService.java`
  - `token/citation` 이벤트 payload에 `trace_id` 추가
- `backend/src/main/java/com/aichatbot/message/application/SseStreamService.java`
  - `heartbeat/error` payload에 `trace_id` 보장
  - release dedupe/finally 유지(누수 방지)
- `backend/src/main/java/com/aichatbot/message/infrastructure/MessageRepository.java`
- `backend/src/main/java/com/aichatbot/session/infrastructure/ConversationRepository.java`
- `backend/src/main/java/com/aichatbot/rag/infrastructure/RagSearchLogRepository.java`
  - ingress trace context 기반 저장 강제

## 3) 실행 검증 결과

1. Backend tests
- command: `backend\gradlew.bat test --no-daemon`
- result: PASS
- evidence: `docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt`

2. Frontend tests/build
- command: `cd frontend && npm ci && npm run test:run && npm run build`
- result: PASS
- evidence:
  - `docs/review/mvp_verification_pack/artifacts/frontend_npm_ci_output.txt`
  - `docs/review/mvp_verification_pack/artifacts/frontend_test_output.txt`
  - `docs/review/mvp_verification_pack/artifacts/frontend_build_output.txt`

3. Verification pack consistency
- command: `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
- result: PASS
- evidence: `docs/review/mvp_verification_pack/artifacts/gap_closure_consistency_output.txt`

4. Provider regression (local)
- command: `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`
- result: SKIPPED (docker daemon unavailable)
- evidence:
  - `docs/review/mvp_verification_pack/artifacts/provider_regression_gap_closure_output.txt`
  - `docs/review/mvp_verification_pack/artifacts/provider_regression_exit_code.txt`
  - `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`

5. Provider evidence consistency
- command: `powershell -ExecutionPolicy Bypass -File scripts/assert_provider_regression_evidence.ps1`
- result: PASS
- evidence:
  - `docs/review/mvp_verification_pack/artifacts/provider_evidence_consistency_output.txt`
  - `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md`

6. UUID/MyBatis 정책 스캔
- command: `rg -n "CAST\(#\{.*\} AS UUID\)" backend/src/main/resources/mappers -S`
- result: `NO_MATCH`
- evidence: `docs/review/mvp_verification_pack/artifacts/uuid_cast_scan_output.txt`

- command: `rg -n "\$\{" backend/src/main/resources/mappers -S`
- result: `NO_MATCH`
- evidence: `docs/review/mvp_verification_pack/artifacts/mybatis_dollar_scan_output.txt`

## 4) 남은 제한사항 / 운영 주의점
- provider 회귀는 PR에서 조건부 실행이며, local Docker/Ollama 미준비 시 SKIPPED가 가능하다.
- SKIPPED는 PASS 근거가 아니며, 항상 `PROVIDER_REGRESSION_EVIDENCE.md`의 최신 PASS 항목으로 판단한다.
- cache/summary 전용 persistence 계층은 현재 구현 범위에 없다. 도입 시 PII exclusion 테스트를 의무 추가한다.
- Node 표준은 22.x이며, 로컬 Node 24.x에서는 엔진 경고가 출력될 수 있다.

## 5) SSE Concurrency Contract (명시 고정)
- key name: `app.budget.sse-concurrency-max-per-user`
- default: `2`
- enforcement unit: `user` (실제 키 구성은 `tenant_id:user_id`, 즉 테넌트 내부 사용자 단위)
- session 단위 별도 키: 없음(현재는 사용자 단위로 강제)

제한 초과 시 표준 응답 고정:
```json
{
  "error_code": "API-008-429-SSE",
  "message": "human readable message",
  "trace_id": "uuid",
  "details": ["quota_exceeded"]
}
```

증빙:
- 계약 테스트: `backend/src/test/java/com/aichatbot/message/presentation/SseConcurrencyLimitContractTest.java`
- 실행 로그: `docs/review/mvp_verification_pack/artifacts/sse_concurrency_contract_test_output.txt`
- finally 해제(오탐 429/락 누수 제거) 검증: `shouldNotProduceFalse429AfterCompletedStreamFinallyRelease`
