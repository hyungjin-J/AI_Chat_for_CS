# AI_Chatbot (CS Support AI Chatbot)

고객센터 상담원을 위한 RAG 기반 AI 챗봇 프로젝트입니다.  
핵심 목표는 빠른 응답이 아니라, **근거 기반 답변 + 보안 + 운영 추적성**을 동시에 만족하는 운영형 시스템입니다.

## TL;DR
- 현재 기준: **Phase2.1.3 (Gate Regression & Drift Prevention) 반영 완료**
- 최신 기준 문서(SSOT):
  - `docs/review/plans/202603XX_phase2_1_1_release_hygiene_plan.md`
  - `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
  - `spec_sync_report.md`
- 핵심 잠금 정책:
  - ROLE 고정: `AGENT`, `CUSTOMER`, `ADMIN`, `OPS`, `SYSTEM`
  - 표준 에러 포맷 고정: `error_code`, `message`, `trace_id`, `details`
  - Hardening Gate 완화 금지(쿠키/CSRF/락아웃/리프레시 회전/UTC 버킷)
  - 스펙 변경 시 Notion 동기화 + 메타 갱신 + `spec_sync_report.md` 필수

## Current Status (Phase2.1.3)
| Item | Status | Evidence |
|---|---|---|
| Start status snapshot | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_git_status_start.txt` |
| Baseline patch snapshot | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_baseline.patch` |
| Fixed artifact contract | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_fixed_artifact_contract_check.txt` |
| Gate regression unittest | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_unittest_output.txt` |
| ChatGPT doc lint | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_chatgpt_doc_lint.txt` |
| Backend tests | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_backend_test_output.txt` |
| Frontend tests | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_frontend_test_output.txt` |
| Frontend build | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_frontend_build_output.txt` |
| Spec consistency | PASS (`FAIL=0`) | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_spec_consistency.txt` |
| UTF-8 strict decode | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_3_utf8_check.txt` |

## What Changed in Phase2.1.3

### A) Artifact Path Contract + CI
- 고정 경로 계약 파일 추가:
  - `scripts/contracts/fixed_artifact_paths.json`
- 계약 검사 스크립트 추가:
  - `scripts/assert_fixed_artifact_paths.py`
- CI smoke gate에 계약 검사 단계 추가:
  - `.github/workflows/pr-smoke-contract.yml`

### B) chatGPT Doc Lint Coverage 확장
- Validation Gate Evidence 경로 검증을 두 문서로 확장:
  - `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
  - `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
- lint JSON 출력에 coverage 메트릭 추가:
  - `scanned_tables_count`
  - `extracted_evidence_paths_count`
  - `missing_paths_count`
  - `missing_paths`

### C) Gate Regression Test + CI
- stdlib `unittest` 회귀 테스트 추가:
  - `scripts/tests/test_lint_chatgpt_handoff_docs.py`
  - `scripts/tests/test_notion_templates.py`
  - `scripts/tests/test_notion_manual_exception_gate.py`
  - `scripts/tests/test_fixed_artifact_contract.py`
- CI smoke gate에 unittest 단계 추가:
  - `.github/workflows/pr-smoke-contract.yml`

### D) Windows npm lock Runbook 격상
- 진단 번들 수집 스크립트 추가:
  - `scripts/collect_windows_npm_lock_diag.ps1`
- runbook에 진단 번들 생성/에스컬레이션 절차 추가:
  - `docs/ops/runbook_windows_node_npm_lock.md`

## Quick Start

### 1) Infra
```bash
docker compose -f infra/docker-compose.yml up -d
```

### 2) Backend
```bash
cd backend
gradlew.bat bootRun
```

### 3) Frontend
```bash
cd frontend
npm ci --prefer-offline --no-audit --fund=false
npm run dev
```

## Verification Commands

### Full Check (recommended)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1
```

### Individual Checks
```powershell
python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime
cd backend; ./gradlew.bat test --no-daemon
cd ../frontend; npm ci --prefer-offline --no-audit --fund=false; npm run test:run; npm run build
python ../scripts/spec_consistency_check.py
python ../scripts/assert_fixed_artifact_paths.py
python -m unittest discover -s ../scripts/tests -p "test_*.py"
python ../scripts/lint_chatgpt_handoff_docs.py --files ../chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md ../chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md
```

## Policy Locks (Non-Negotiable)
- ROLE taxonomy fixed: `AGENT`, `CUSTOMER`, `ADMIN`, `OPS`, `SYSTEM`
- `Manager/System Admin`는 ROLE이 아니라 `ADMIN` 내부 권한 레벨
- 표준 에러 포맷 고정: `error_code`, `message`, `trace_id`, `details`
- 상태/에러 의미 고정:
  - stale permission -> `401 AUTH_STALE_PERMISSION`
  - lockout -> `429 AUTH_LOCKED`
  - rate-limit -> `429 AUTH_RATE_LIMITED`
  - refresh reuse -> `409 AUTH_REFRESH_REUSE_DETECTED`
- 스펙 변경 시 Notion 동기화 + 메타 갱신 + `spec_sync_report.md` 기록 없으면 실패

## Key Documents
- Phase2.1.1 plan: `docs/review/plans/202603XX_phase2_1_1_release_hygiene_plan.md`
- Full report: `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
- Spec sync report: `spec_sync_report.md`
- Dev guide: `docs/dev/DEV_ENVIRONMENT.md`
- Notion export policy: `docs/notion_exports/README.md`
- Ops runbooks:
  - `docs/ops/runbook_scheduler_lock.md`
  - `docs/ops/runbook_audit_chain.md`
  - `docs/ops/runbook_spec_notion_gate.md`
  - `docs/ops/runbook_windows_node_npm_lock.md`
- ChatGPT handoff docs:
  - `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
  - `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`

## Notion Mapping (Spec Sync Targets)
- Summary of key features.csv  
  https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149
- CS AI Chatbot_Requirements Statement.csv  
  https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- Development environment.csv  
  https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7
- google_ready_api_spec_v0.3_20260216.xlsx  
  https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- CS_AI_CHATBOT_DB.xlsx  
  https://www.notion.so/2ed405a3a720812180d9d508b77f31a4
- CS_RAG_UI_UX_설계서.xlsx  
  https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444

## Security Notes
- 민감정보/토큰/시크릿/PII 평문 커밋 금지
- `X-Trace-Id`, `X-Tenant-Key` 전파 강제
- Answer Contract 실패 시 자유 텍스트 우회 금지(safe response 또는 차단)
