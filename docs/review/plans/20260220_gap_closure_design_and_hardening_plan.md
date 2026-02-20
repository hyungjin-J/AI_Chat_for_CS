# 2026-02-20 Gap Closure Design and Hardening Plan

- generated_at: 2026-02-20
- scope: Completion 증빙 강화 + 회귀 방지 게이트 보강
- risk_level: high (보안/정책/CI 거버넌스 포함)

## 1) Why
- 현재 구현은 핵심 기능이 동작하지만, AGENTS.md의 P0 정책(Answer Contract fail-closed, trace_id, tenant/RBAC, PII 차단)을 회귀 없이 증명하는 자동 근거가 부족하다.
- 테스트/CI/문서 증빙을 강화해 "완성" 판정을 코드와 로그로 재현 가능하게 만든다.

## 2) Scope
- backend: P0 정책 보강 테스트 추가 + 최소 비파괴 코드 보강
- frontend: uuid/sse/error mapping 자동 테스트 추가
- CI: PR 게이트에 frontend test + uuid lint + gitleaks 추가
- docs: gap audit/완료 보고/verification pack 최신화

Out of scope:
- 스펙 CSV/XLSX 구조 변경
- DB 스키마 파괴적 변경
- 레거시 복원

## 3) Regression Paths
1. Answer Contract 음수 경로에서 free-text fallback 회귀
2. trace_id 누락/불일치(HTTP/SSE/DB)
3. cross-tenant 접근 차단 회귀
4. RBAC 경계 누락으로 401/403 정책 흔들림
5. 프론트 입력 검증/에러 UX 회귀
6. CI 게이트에서 시크릿/UUID/검증팩 일관성 누락

## 4) Implementation Strategy
1. 증빙 갭 문서화(GAP_ASSESSMENT_REPORT) 선행
2. P0 backend 테스트와 최소 보강 코드 동시 적용
3. frontend test 체계 추가(vitest/rtl)
4. CI 게이트 확장(mvp-demo-verify)
5. verification pack/final docs 동기화

## 5) Non-destructive Principle
- 변경은 additive 중심으로 수행한다.
- 기존 API/이벤트 필드 제거 금지.
- 롤백은 커밋 단위로 가능하게 기능군 별로 분리한다.

## 6) DoD
- backend: `backend\gradlew.bat test --no-daemon` PASS
- frontend: `cd frontend && npm run test:run && npm run build` PASS
- consistency: `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1` PASS
- provider regression: 조건 충족 시 PASS, 미충족 시 SKIPPED 근거 문서화
- GAP_ASSESSMENT_REPORT에서 P0(A,B,C,D,E) 항목 상태가 모두 OK
- CI workflow에 frontend test/uuid lint/gitleaks가 PR 게이트로 반영

## 7) Validation Commands
1. `backend\gradlew.bat test --no-daemon`
2. `cd frontend && npm ci && npm run test:run && npm run build`
3. `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
4. `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1` (조건부)
5. `rg -n "CAST\\(#\\{.*\\} AS UUID\\)" backend/src/main/resources/mappers -S`
6. `rg -n "\\$\\{" backend/src/main/resources/mappers -S`

## 8) Risks / Mitigations
- SSE payload 추가로 프론트 파서 영향 가능
  - mitigation: additive field만 추가 + parser test 보강
- gitleaks false positive
  - mitigation: 최소 allowlist 정책 파일로 제어
- provider 회귀 환경 의존성
  - mitigation: PR 조건부 실행 + nightly 강제 유지
- 새 테스트가 flaky 가능
  - mitigation: deterministic 입력/고정 trace/id 사용

## 9) Rollback
- 테스트 추가로 실패 시 해당 테스트/보강 코드만 선택 롤백 가능하도록 파일 단위 분리 유지
- CI 게이트 문제 시 workflow 변경만 별도 롤백 가능
- 문서는 코드 상태에 맞춰 즉시 재동기화
