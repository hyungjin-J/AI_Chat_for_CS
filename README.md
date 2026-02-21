# AI_Chatbot (CS Support AI Chatbot)

고객센터 상담원을 위한 RAG 기반 AI 챗봇 프로젝트입니다.  
핵심 목표는 빠른 응답이 아니라, **근거 기반 답변 + 보안 + 운영 추적성**을 동시에 만족하는 운영형 시스템입니다.

## TL;DR
- 현재 기준: **Phase2.1.1 (Release Hygiene & ChatGPT Handoff Hardening) 반영 완료**
- 최신 기준 문서(SSOT):
  - `docs/review/plans/202603XX_phase2_1_1_release_hygiene_plan.md`
  - `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
  - `spec_sync_report.md`
- 핵심 잠금 정책:
  - ROLE 고정: `AGENT`, `CUSTOMER`, `ADMIN`, `OPS`, `SYSTEM`
  - 표준 에러 포맷 고정: `error_code`, `message`, `trace_id`, `details`
  - Hardening Gate 완화 금지(쿠키/CSRF/락아웃/리프레시 회전/UTC 버킷)
  - 스펙 변경 시 Notion 동기화 + 메타 갱신 + `spec_sync_report.md` 필수

## Current Status (Phase2.1.1)
| Item | Status | Evidence |
|---|---|---|
| Backend tests | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_1_backend_test_202603XX.txt` |
| Frontend npm ci | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_1_frontend_npm_ci_202603XX.txt` |
| Frontend tests | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_1_frontend_test_202603XX.txt` |
| Frontend build | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_1_frontend_build_202603XX.txt` |
| ChatGPT doc lint | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_doc_lint_202603XX.txt` |
| Spec consistency | PASS (`FAIL=0`) | `docs/review/mvp_verification_pack/artifacts/phase2_1_1_spec_consistency_202603XX.txt` |
| UTF-8 strict decode | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_1_utf8_check_202603XX.txt` |
| Notion manual exception gate | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate_202603XX.txt` |

## What Changed in Phase2.1.1

### PR-A: Node 22 SSOT + CI Fail-Fast
- Node SSOT를 `.nvmrc=22.12.0`으로 고정
- `frontend/package.json`의 `engines`/`volta`를 동일 기준으로 동기화
- CI 워크플로우 Node 설정을 `node-version-file: .nvmrc`로 통일
- Node 불일치 시 즉시 실패:
  - `scripts/assert_node_ssot.py`
  - `scripts/check_all.ps1`

### PR-B: ChatGPT Handoff Docs Quality Gate
- 신규 린터:
  - `scripts/lint_chatgpt_handoff_docs.py`
- 강제 검증:
  - `updated_at_kst` 실제 값 필수
  - `base_commit_hash`/`release_tag`/`branch` 필수
  - C0 제어문자 금지(`\n`, `\r`만 허용)
  - `race_id` 오탈자 금지(`trace_id`만 허용)
  - 문서 내 민감 패턴 금지(`<REDACTED>` 표기 사용)
- 대상 문서:
  - `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
  - `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`

### PR-C (MUST): Notion BLOCKED Manual Exception Close Gate
- Notion preflight 실패 시 자동 동기화는 fail-closed 유지
- 수동 예외 닫기(close) 공식 게이트 추가:
  - `scripts/check_notion_manual_exception_gate.py`
- 고정 증적 파일:
  - `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json`
  - `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
- 운영 절차 원페이지:
  - `docs/ops/runbook_spec_notion_gate.md`

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
npm ci
npm run dev
```

## Verification Commands

### Full Check (recommended)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1
```

### Individual Checks
```powershell
cd backend; ./gradlew.bat test --no-daemon
cd ../frontend; npm ci; npm run test:run; npm run build
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
- Ops runbooks:
  - `docs/ops/runbook_scheduler_lock.md`
  - `docs/ops/runbook_audit_chain.md`
  - `docs/ops/runbook_spec_notion_gate.md`
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
