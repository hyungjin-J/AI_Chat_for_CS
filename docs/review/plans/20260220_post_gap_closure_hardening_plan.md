# 2026-02-20 Post Gap Closure Hardening Plan

## Why
- Completion claim 이후에도 증빙 공백(provider PASS 근거, SSE 동시성 오해, PII/trace_id 증빙)이 남아 있어 객관적 검증 속도가 떨어진다.
- 본 작업은 AGENTS.md 비협상 규칙(Fail-Closed, PII 차단, trace_id 전파, Tenant/RBAC, Budget, MyBatis/no `${}`)을 유지한 채 증빙 완결성을 높인다.

## Scope
- Provider regression 증빙 단일 진실원천 문서 신설 및 정합성 스크립트 추가
- SSE 동시성 제한 유지 증명(코드 확인 + 계약 테스트 + 문서화)
- PII E2E 증빙 강화(LLM 입력/로그/저장/응답)
- trace_id 전파/저장 강제 증빙 강화
- 검증팩/최종 보고서 최신화

## Out of Scope
- DB 스키마 변경/마이그레이션
- 스펙 CSV/XLSX 구조 변경(따라서 Notion 동기화 트리거 없음)
- API 계약 파괴적 변경

## Regression Paths
1. Provider regression 결과가 SKIPPED인데 문서가 PASS처럼 보이는 모순
2. SSE guard 누수 수정이 동시성 한도 제거로 오해될 위험
3. PII 검증이 저장/응답 경로까지 닿지 못해 정책 회귀
4. trace_id가 일부 저장 경로에서 누락될 위험
5. 검증팩 문서와 실제 아티팩트 경로 불일치

## DoD
- `backend\gradlew.bat test --no-daemon` PASS
- `cd frontend && npm ci && npm run test:run && npm run build` PASS
- `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1` PASS
- `powershell -ExecutionPolicy Bypass -File scripts/assert_provider_regression_evidence.ps1` PASS
- Provider 최신 PASS 근거를 `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md`에서 30초 내 확인 가능
- SSE 동시성 제한이 코드+테스트+문서에서 일치
- PII/trace_id P0 항목이 `docs/review/final/GAP_ASSESSMENT_REPORT.md`에서 OK
- `rg -n "CAST\\(#\\{.*\\} AS UUID\\)" backend/src/main/resources/mappers -S` 결과 NO_MATCH
- `rg -n "\\$\\{" backend/src/main/resources/mappers -S` 결과 NO_MATCH

## Commands
```powershell
backend\gradlew.bat test --no-daemon
cd frontend
npm ci
npm run test:run
npm run build
cd ..
powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1
powershell -ExecutionPolicy Bypass -File scripts/assert_provider_regression_evidence.ps1
rg -n "CAST\(#\{.*\} AS UUID\)" backend/src/main/resources/mappers -S
rg -n "\$\{" backend/src/main/resources/mappers -S
```

## Risk Register
1. Docker 미가용으로 provider PASS 로컬 생성 실패
   - Mitigation: 조건부 PR 정책 + 최신 PASS 아티팩트 링크 강제
   - Rollback: 정합성 스크립트만 임시 비활성화(기능 코드 영향 없음)
2. SSE 동시성 테스트 플래키
   - Mitigation: latch/timeout 고정, 단일 쓰레드 제어
   - Rollback: flaky 테스트 격리 후 안정화 재적용
3. trace_id strict 가드 보강으로 예상 외 4xx 증가
   - Mitigation: 테스트로 경로 선검증 후 최소 변경
   - Rollback: strict 경로를 설정 플래그로 완화
4. 문서-아티팩트 경로 불일치
   - Mitigation: 검증 스크립트로 파일 존재/필드 검증 자동화
   - Rollback: 문서 링크 복구(코드 영향 없음)

## Rollback Plan
- 모든 변경은 파일 단위(테스트/문서/스크립트)로 분리 적용한다.
- 문제 발생 시 역순으로 롤백:
  1) 문서 갱신
  2) 검증 스크립트
  3) 신규 테스트
  4) 최소 코드 보강
- DB/운영 데이터 변경이 없으므로 데이터 롤백은 필요 없다.
