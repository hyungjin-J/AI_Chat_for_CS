# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- purpose: ChatGPT가 현재 코드베이스의 구조와 Gap Closure 구현 내용을 빠르게 이해하도록 제공하는 최종 핸드오프 문서
- updated_at: 2026-02-21 01:55 (KST)

## 1) Completion 상태 요약

현재 구현은 Completion 증빙 강화를 목표로 한 Gap Closure 작업을 반영한 상태다.

검증 요약:
- backend test: PASS (`docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt`)
- frontend test/build: PASS (`docs/review/mvp_verification_pack/artifacts/frontend_test_output.txt`, `docs/review/mvp_verification_pack/artifacts/frontend_build_output.txt`)
- verification consistency: PASS (`docs/review/mvp_verification_pack/artifacts/gap_closure_consistency_output.txt`)
- provider regression: SKIPPED (Docker daemon unavailable) (`docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`)
- UUID CAST 검색: NO_MATCH (`docs/review/mvp_verification_pack/artifacts/uuid_cast_scan_output.txt`)
- MyBatis `${}` 검색: NO_MATCH (`docs/review/mvp_verification_pack/artifacts/mybatis_dollar_scan_output.txt`)

## 2) Plan Mode 초반 기초 설정 (필수 기록)

이번 작업은 코드 수정 전에 아래 베이스라인 절차를 먼저 고정했다.

1. `AGENTS.md` 최신 규칙 확인
- Fail-Closed, PII 차단, trace_id 전파, tenant/RBAC, budget 정책을 구현 기준으로 재확인

2. Hardening Gate 문서 선작성
- `docs/review/plans/20260220_gap_closure_design_and_hardening_plan.md` 생성
- Why/Scope/Regression/DoD/명령/리스크/롤백을 먼저 명시

3. 비파괴 상태 점검(Evidence Audit)
- `docs/review/final/GAP_ASSESSMENT_REPORT.md` 작성
- A~G 항목을 `Item | requirement | evidence | status | action` 매트릭스로 고정

4. 베이스라인 검증 실행
- `backend\gradlew.bat test --no-daemon`
- `cd frontend && npm run build`
- `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`

## 3) 전체 구조도 (Repository Map)

```text
AI_Chatbot/
├─ backend/
│  ├─ src/main/java/com/aichatbot/
│  │  ├─ global/          # security/error/trace/tenant/privacy/mybatis
│  │  ├─ auth/            # login/refresh/logout
│  │  ├─ session/         # session + message entry
│  │  ├─ message/         # generation + SSE stream
│  │  ├─ rag/             # retrieval/citation/logging
│  │  ├─ answer/          # answer contract validation
│  │  ├─ billing/         # quota/rate/budget
│  │  └─ llm/tool/        # provider abstraction + tools
│  ├─ src/main/resources/mappers/   # MyBatis XML
│  └─ src/test/java/com/aichatbot/  # contract/integration/security tests
├─ frontend/
│  └─ src/
│     ├─ App.tsx
│     ├─ utils/uuid.ts
│     ├─ utils/sseParser.ts
│     ├─ utils/errorMapping.ts
│     └─ *.test.ts(x)
├─ scripts/               # lint/check/provider/consistency
├─ .github/workflows/     # PR gate CI
└─ docs/review/           # plans/final/mvp_verification_pack/verification_pack
```

## 4) Gap Closure 구현 내역 (핵심)

### 4.1 Backend P0 테스트/가드 보강
- Answer Contract 음수 시나리오 추가
  - `backend/src/test/java/com/aichatbot/message/presentation/MessageAnswerContractNegativeFlowTest.java`
- PII E2E 계약 테스트 추가
  - `backend/src/test/java/com/aichatbot/message/presentation/PiiEndToEndContractTest.java`
- trace_id 계약 테스트 추가
  - `backend/src/test/java/com/aichatbot/global/observability/TraceIdContractTest.java`
- RBAC + tenant 매트릭스 테스트 추가
  - `backend/src/test/java/com/aichatbot/security/RbacTenantMatrixTest.java`
- SSE resume 계약 테스트 추가
  - `backend/src/test/java/com/aichatbot/message/presentation/SseResumeContractTest.java`

### 4.2 Backend 동작 보강
- safe_response payload에 `trace_id` 보장
  - `backend/src/main/java/com/aichatbot/message/application/MessageGenerationService.java`
- SSE error payload에 `trace_id` 보장
  - `backend/src/main/java/com/aichatbot/message/application/SseStreamService.java`
- SSE 연결 가드 해제를 `finally + 중복방지`로 보강
  - 테스트 간 429 누적 회귀 방지
- PII 마스킹 패턴 보강(주소 패턴)
  - `backend/src/main/java/com/aichatbot/global/privacy/PiiMaskingService.java`

### 4.3 Frontend 테스트 체계 도입
- Vitest/RTL 설정
  - `frontend/package.json`
  - `frontend/vite.config.ts`
  - `frontend/src/test/setup.ts`
  - `frontend/tsconfig.app.json`
- 에러 매핑 분리
  - `frontend/src/utils/errorMapping.ts`
  - `frontend/src/App.tsx` 적용
- 테스트 추가
  - `frontend/src/utils/uuid.test.ts`
  - `frontend/src/utils/sseParser.test.ts`
  - `frontend/src/utils/errorMapping.test.ts`
  - `frontend/src/App.invalid-id-guard.test.tsx`

### 4.4 CI 게이트 강화
- PR 워크플로우 확장
  - `backend test`
  - `frontend test + build`
  - `uuid lint`
  - `verification pack consistency`
  - `gitleaks secret scan`
  - `provider regression conditional`
- 관련 파일
  - `.github/workflows/mvp-demo-verify.yml`
  - `.gitleaks.toml`

## 5) 증빙 문서/아티팩트 구조

### 5.1 최종 보고서
- `docs/review/final/GAP_ASSESSMENT_REPORT.md`
- `docs/review/final/PROJECT_COMPLETION_REPORT.md`
- `docs/review/final/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md` (본 문서)

### 5.2 검증팩
- `docs/review/verification_pack/README.md`
- SSOT
  - `docs/review/mvp_verification_pack/03_TEST_PLAN.md`
  - `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`
  - `docs/review/mvp_verification_pack/00_EXEC_SUMMARY.md`
  - `docs/review/mvp_verification_pack/06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md`
  - `docs/review/mvp_verification_pack/CHANGELOG.md`

## 6) 운영/재실행 가이드

핵심 명령:
1. `cd backend && .\gradlew.bat test --no-daemon`
2. `cd frontend && npm ci && npm run test:run && npm run build`
3. `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
4. `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`

주의:
- provider regression은 Docker Desktop/Ollama 준비 여부에 따라 SKIPPED가 가능하다.
- Node 표준은 22.x이지만, 현재 로컬은 24.x로 엔진 경고가 출력될 수 있다.
- 시크릿/PII는 로그/문서/예시에 포함하지 않는다.
