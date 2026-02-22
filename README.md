# AI_Chatbot (CS Support AI Chatbot)

고객센터 상담원을 위한 RAG 기반 AI 챗봇 프로젝트입니다.  
핵심 목표는 빠른 응답이 아니라, **근거 기반 답변 + 보안 + 운영 추적성**을 동시에 만족하는 운영형 시스템입니다.

## TL;DR
- 현재 기준: **Phase2.1.2 (Open Risks Burn-down) 반영 완료**
- 최신 기준 문서(SSOT):
  - `docs/review/plans/202603XX_phase2_1_1_release_hygiene_plan.md`
  - `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
  - `spec_sync_report.md`
- 핵심 잠금 정책:
  - ROLE 고정: `AGENT`, `CUSTOMER`, `ADMIN`, `OPS`, `SYSTEM`
  - 표준 에러 포맷 고정: `error_code`, `message`, `trace_id`, `details`
  - Hardening Gate 완화 금지(쿠키/CSRF/락아웃/리프레시 회전/UTC 버킷)
  - 스펙 변경 시 Notion 동기화 + 메타 갱신 + `spec_sync_report.md` 필수

## Current Status (Phase2.1.2)
| Item | Status | Evidence |
|---|---|---|
| Start status snapshot | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_git_status_start.txt` |
| Baseline patch snapshot | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_baseline.patch` |
| Node SSOT guidance check | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_node_ssot_check.txt` |
| Backend tests | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_backend_test_output.txt` |
| Frontend tests | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_frontend_test_output.txt` |
| Frontend build | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_frontend_build_output.txt` |
| ChatGPT doc lint | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_chatgpt_doc_lint.txt` |
| Spec consistency | PASS (`FAIL=0`) | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_spec_consistency.txt` |
| UTF-8 strict decode | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_utf8_check.txt` |
| Notion manual exception gate | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_2_notion_manual_gate.txt` |

## What Changed in Phase2.1.2

### W1: Node 런타임 드리프트 완화
- 플랫폼별 부트스트랩 스크립트 추가:
  - `scripts/bootstrap_node_22.ps1`
  - `scripts/bootstrap_node_22.sh`
- Node 버전 불일치 시 복구 가이드 자동 출력:
  - `scripts/check_node_version.py`
  - `docs/dev/DEV_ENVIRONMENT.md`

### W2: Windows npm lock 대응 강화
- npm 설치 표준 플래그를 로컬/CI 동일하게 적용:
  - `npm ci --prefer-offline --no-audit --fund=false`
- 운영 런북 추가:
  - `docs/ops/runbook_windows_node_npm_lock.md`
- CI/로컬 검사 스크립트 반영:
  - `.github/workflows/pr-smoke-contract.yml`
  - `scripts/check_all.ps1`

### W3: Notion 수동 예외 Close 게이트 고도화
- 수동 증적 템플릿 생성 스크립트 추가:
  - `scripts/gen_notion_manual_evidence_template.py`
- 파일/필드 단위로 상세 진단하도록 검증기 강화:
  - `scripts/check_notion_manual_exception_gate.py`
- 운영 절차 업데이트:
  - `docs/ops/runbook_spec_notion_gate.md`
- 고정 증적 경로 유지:
  - `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json`
  - `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
  - `spec_sync_report.md`

### W4: ChatGPT handoff 증적 경로 검증 강화
- 브리핑 문서의 Validation Gate에서 참조한 증적 파일 존재/범위를 자동 검사:
  - `scripts/lint_chatgpt_handoff_docs.py`
- 대상 문서:
  - `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
  - `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`

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
