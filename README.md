# AI_Chatbot (CS Support AI Chatbot)

고객센터 상담원의 답변 작성을 지원하는 RAG 기반 AI 챗봇 프로젝트입니다.

## TL;DR
- 현재 상태: **Go-Live Gap Closure 반영 완료 (2026-02-21)**
- 핵심 원칙:
  - Fail-Closed (검증 실패 시 안전응답)
  - PII 마스킹 (입력/로그/응답/인용문)
  - trace_id 종단 추적 (HTTP/SSE/DB)
  - Tenant 격리 + RBAC 서버 강제
  - 예산/레이트리밋 가드
- 최신 릴리즈 태그: `v2026.02.21-golive`
- ChatGPT 전달용 문서: `chatGPT/`

## 1) Current Status
| Item | Status | Evidence |
|---|---|---|
| Backend tests | PASS | `docs/review/mvp_verification_pack/artifacts/golive_backend_test_output.txt` |
| Frontend tests | PASS | `docs/review/mvp_verification_pack/artifacts/golive_frontend_test_output.txt` |
| Frontend build | PASS | `docs/review/mvp_verification_pack/artifacts/golive_frontend_build_output.txt` |
| Spec consistency | PASS (`PASS=9 FAIL=0`) | `docs/review/mvp_verification_pack/artifacts/golive_spec_consistency_after.txt` |
| UTF-8 check | PASS | `docs/review/mvp_verification_pack/artifacts/golive_utf8_check.txt` |
| Notion sync | DONE | `docs/review/mvp_verification_pack/artifacts/golive_notion_sync_status.txt` |

상태 SSOT:
- `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
- `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`
- `spec_sync_report.md`

## 2) What Was Implemented (Recent)
### Auth/Session
- JWT login/refresh/logout
- refresh rotation + reuse detection
- lockout/rate-limit enforcement
- session list + revoke controls
- OPS/ADMIN MFA(TOTP) path

### RBAC/Audit/Ops
- RBAC server final authority
- stale permission handling (`401 AUTH_STALE_PERMISSION`)
- RBAC approval workflow (2 approvers)
- audit chain verify path + runbooks
- ops dashboard/audit/export/block operational flow

### Reliability
- UTC hourly metric aggregation + idempotent upsert
- scheduler distributed lock (`tb_scheduler_lock`)
- CI split gates (`pr-smoke-contract`, `release-nightly-full`)

## 3) Quick Start
### Infra
```bash
docker compose -f infra/docker-compose.yml up -d
```

### Backend
```bash
cd backend
gradlew.bat bootRun
```

### Frontend
```bash
cd frontend
npm ci
npm run dev
```

## 4) Verification Commands
### Full check (recommended)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1
```

### Individual checks
```powershell
cd backend; ./gradlew.bat test --no-daemon
cd ../frontend; npm ci; npm run test:run; npm run build
python ../scripts/spec_consistency_check.py
```

Artifacts:
- `docs/review/mvp_verification_pack/artifacts/`

## 5) Non-Negotiable Policy Locks
- ROLE taxonomy fixed: `AGENT`, `CUSTOMER`, `ADMIN`, `OPS`, `SYSTEM`
- `Manager/System Admin` are `ADMIN` internal levels (not roles)
- Standard error shape fixed: `error_code`, `message`, `trace_id`, `details`
- Fixed status/error semantics:
  - stale -> `401 AUTH_STALE_PERMISSION`
  - lockout -> `429 AUTH_LOCKED`
  - rate-limit -> `429 AUTH_RATE_LIMITED`
  - refresh reuse -> `409 AUTH_REFRESH_REUSE_DETECTED`
- If spec changes: Notion sync + metadata update + `spec_sync_report.md` is mandatory

## 6) Key Documents
- Phase2 plan (SSOT): `docs/review/plans/202603XX_production_readiness_phase2_plan.md`
- Go-Live gap closure plan: `docs/review/plans/202603XX_go_live_gap_closure_plan.md`
- Full implementation report (latest): `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
- Spec sync log: `spec_sync_report.md`
- Demo runbook: `docs/DEMO_RUNBOOK.md`
- Ops runbooks:
  - `docs/ops/runbook_scheduler_lock.md`
  - `docs/ops/runbook_audit_chain.md`
  - `docs/ops/runbook_spec_notion_gate.md`
- ChatGPT handoff docs:
  - `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
  - `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`

## 7) Notion Mapping (Spec Sync Targets)
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

## 8) Security and Ops Notes
- Never commit secrets/tokens/PII in plain text.
- Enforce `X-Trace-Id` and `X-Tenant-Key`.
- On answer contract failure, do not fallback to free-text; return safe response.
