# 2026-02-20 Project Completion Plan

## 1. 요약
- 목표: 현재 상태에서 보안/검증/문서 기준을 모두 충족한 "완성 상태"를 만들고, 재현 가능한 검증팩을 남깁니다.
- 핵심 보정:
  - 삭제 문서 참조 제거
  - 레거시 `/api/v1` 비활성화
  - `check_all` 표준 진입점 도입(기존 `verify_all` 하위 호환 유지)
  - 최종 보고서/검증팩 문서 체계 생성

## 2. 작업 순서
1. consistency 스크립트에서 삭제 문서 의존 제거
2. README 및 verification pack 문서 참조 정리
3. 보안 정책 수정(`/api/v1/**` 허용 제거) + 레거시 컨트롤러 제거
4. 관련 테스트 수정/추가
5. `check_all` 스크립트 추가 및 기존 `verify_all` 호환 래핑
6. Ollama 모델 정리 + provider regression 실행
7. 최종 검증 및 최종 보고서 작성
8. Docker 종료

## 3. 검증 명령(최종)
- `backend\gradlew.bat test --no-daemon`
- `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`
- `frontend\npm run build`
- `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
- `rg -n "CAST\\(#\\{.*\\} AS UUID\\)" backend/src/main/resources/mappers`

## 4. 결과 산출물
- `docs/review/verification_pack/README.md`
- `docs/review/final/PROJECT_COMPLETION_REPORT.md`
- `docs/review/plans/20260220_project_completion_design_and_hardening_plan.md`
- `docs/review/plans/20260220_project_completion_plan.md`

## 5. 완료 기준
- 위 검증 명령이 모두 성공하고, 레거시 경로 차단 및 provider PASS 로그가 확인되면 완료로 판정합니다.

