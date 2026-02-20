# 2026-02-20 Project Completion Design And Hardening Plan

## 1. 목적(Why)
- 이번 변경은 단순 기능 추가가 아니라 보안 경계(`/api/v1`), 검증 게이트, 운영 검증 흐름을 함께 다룹니다.
- AGENTS.md 12.3(사전 보고서) 기준상 고위험 변경에 해당하므로, 구현 전에 회귀 경로와 검증 기준을 고정합니다.
- 특히 의도적으로 삭제된 문서를 스크립트가 여전히 강제 참조하는 문제를 먼저 제거해 CI 회귀를 차단합니다.

## 2. 영향 범위
- Backend
  - `backend/src/main/java/com/aichatbot/global/security/SecurityConfig.java`
  - `backend/src/main/java/com/aichatbot/message/presentation/MessageStreamController.java` (삭제 예정)
  - `backend/src/test/java/com/aichatbot/billing/presentation/BudgetEnforcementHttpTest.java`
  - `backend/src/test/java/com/aichatbot/message/presentation/LegacyApiDisabledTest.java` (신규)
- Scripts
  - `scripts/assert_verification_pack_consistency.ps1`
  - `scripts/check_all.ps1` (신규)
  - `scripts/check_all.sh` (신규)
  - `scripts/verify_all.ps1` (호환 래퍼 유지)
  - `scripts/verify_all.sh` (호환 래퍼 유지)
- Docs
  - `README.md`
  - `docs/review/mvp_verification_pack/CURRENT.md`
  - `docs/review/mvp_verification_pack/_DEPRECATED/README.md`
  - `docs/review/verification_pack/README.md` (신규)
  - `docs/review/final/PROJECT_COMPLETION_REPORT.md` (신규)
  - `docs/review/plans/20260220_project_completion_plan.md` (신규)

## 3. 회귀 가능 경로
- 경로 A: 삭제 문서 의존
  - `assert_verification_pack_consistency.ps1`가 삭제된 문서를 필수로 요구하면 검증이 항상 실패합니다.
- 경로 B: 레거시 공개 API 노출
  - `/api/v1/** permitAll`가 유지되면 서버 RBAC 강제 원칙(AGENTS 4.4)과 충돌합니다.
- 경로 C: one-command 검증 분기
  - `check_all` 표준 미정렬 상태에서는 팀/CI의 검증 경로가 분산될 수 있습니다.
- 경로 D: Provider 회귀 검증 미실행
  - Docker/Ollama 미준비 상태를 놓치면 provider 상태가 PASS가 아닌데도 배포 위험이 생깁니다.

## 4. 실패 시 리스크
- 보안 리스크: 레거시 엔드포인트 우회 접근 가능성.
- 운영 리스크: consistency gate FAIL로 PR/배포 차단.
- 품질 리스크: 문서-실행 결과 불일치로 검증 신뢰도 저하.

## 5. 검증 계획
- 코드/정책 검증
  - `rg -n "PHASE2_PROGRESS_SUMMARY_FOR_CHATGPT.md|CHANGE_IMPACT_REVIEW_REPORT_FOR_CHATGPT.md" README.md docs scripts .github -S`
  - `rg -n "/api/v1/|MessageStreamController|permitAll" backend/src/main/java backend/src/test/java -S`
- 테스트/빌드
  - `backend\gradlew.bat test --no-daemon`
  - `frontend\npm run build`
  - `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
- provider 검증
  - `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`
- 모델 검증
  - `docker compose -f infra/docker-compose.ollama.yml exec ollama ollama list`

## 6. Definition of Done
- [ ] AGENTS 12.3 사전 문서가 구현 전에 존재한다.
- [ ] 삭제된 문서 참조가 스크립트/문서에서 제거되었다.
- [ ] `/api/v1/**` 레거시 경로가 비활성화되었다.
- [ ] Backend/Frontend/provider/consistency 검증이 PASS다.
- [ ] 최종 산출물 3종(plans/verification_pack/final)이 생성되었다.
- [ ] Docker 종료(`compose down`)가 실행되어 작업 종료 상태가 확인된다.

## 7. 예외/트레이드오프
- 레거시 `/api/v1`를 차단하면 과거 데모 호출 경로는 더 이상 동작하지 않습니다.
- 이 변경은 의도된 breaking change이며, 보안 일관성을 위해 우선 적용합니다.
