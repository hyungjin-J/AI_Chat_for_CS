# Verification Pack CURRENT

- Last synced at: 2026-02-18 20:20 (KST)
- Git commit hash: `working-tree`
- Execution environment:
  - OS: Windows 11
  - Java: 17
  - Node: v24.11.1 (표준 22.12.0, 로컬 임시 오버라이드 사용)
  - Python: 3.11
- Canonical status source: `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`
- Final status: Demo Ready + Phase2.1 운영 게이트 잠금 반영

## 실행 커맨드
1. `docker compose -f infra/docker-compose.yml up -d`
2. `cd backend && .\gradlew.bat test --no-daemon`
3. `cd frontend && npm ci && npm run build`
4. `powershell -ExecutionPolicy Bypass -File scripts/verify_all.ps1`
5. `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`

## SSOT 규칙
- PASS/FAIL/SKIPPED의 진실은 `04_TEST_RESULTS.md` 1곳으로 고정한다.
- `00_EXEC_SUMMARY.md`, `03_TEST_PLAN.md`, `06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md`, `PHASE2_PROGRESS_SUMMARY_FOR_CHATGPT.md`, `CHANGELOG.md`는 04 기준으로 관리한다.
- consistency 게이트: `scripts/assert_verification_pack_consistency.ps1`
