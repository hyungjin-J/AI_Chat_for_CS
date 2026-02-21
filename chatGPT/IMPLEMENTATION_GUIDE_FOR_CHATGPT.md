# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- document_type: Implementation and Operations Handoff Guide
- updated_at_kst: $kst
- base_commit_hash: 79383ab
- release_tag: 2026.02.21-phase2.1-pr1-pr3
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: Notion auth preflight fail-closed step in CI workflow.
- Added: 
otion_ci_auth_preflight.py with explicit NOTION_AUTH_* error mapping.
- Added: Async audit export endpoints and service/job/storage components.
- Added: DB migrations V7/V8 for export spool and scheduler self-healing.
- Changed: API/DB/UIUX spec workbooks to match PR2/PR3 runtime behavior.
- Changed: Ops runbooks for spec/notion gate, audit chain, scheduler lock incidents.
- Changed: Report and sync documents to include Phase2.1 evidence paths.
- Fixed: Export job failure due MyBatis mapper scan collision on ExportStorage.
- Fixed: Export failure paths now write both ops_event and udit_log.
- Removed: assumption that sync export is the primary export path (now fallback-only).

## 1) Core Mission
Provide a complete context package for ChatGPT so it can reason about this repository without direct path/file access.
The guide contains architecture state, locked constraints, gate evidence, and remaining risk items.

## 2) Current Completion Status
- PR1 (Notion CI token ops): Implemented
- PR2 (Async audit export): Implemented
- PR3 (Scheduler self-healing): Implemented
- PR4 (WebAuthn): Design-only, not runtime implemented

## 3) Validation Gates and Evidence
| Gate | Result | Evidence |
|---|---|---|
| Backend full test | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_backend_test_202603XX.txt |
| Frontend test | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_frontend_test_202603XX.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_frontend_build_202603XX.txt |
| Spec consistency | PASS (PASS=9 FAIL=0) | docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_spec_consistency_202603XX.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_utf8_check_202603XX.txt |
| Notion automation | BLOCKED (Auth required) | docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_notion_sync_status_202603XX.txt |

## 4) What Was Changed (Technical Scope)
### Backend
- Added export spool schema and APIs for async audit export.
- Added export worker/cleanup scheduled jobs.
- Added scheduler stale-lock recovery job.
- Extended scheduler lock model with heartbeat and recovery counters.

### Frontend
- Changed Admin Audit page export behavior from direct sync download to async job flow:
  1. Create export job
  2. Poll status
  3. Download on DONE

### CI and Ops Docs
- Notion sync workflow now requires preflight pass before Codex sync.
- Updated runbooks:
  - docs/ops/runbook_spec_notion_gate.md
  - docs/ops/runbook_audit_chain.md
  - docs/ops/runbook_scheduler_lock.md

### Spec and Traceability
- API workbook now includes export-jobs endpoints.
- DB workbook now includes export/scheduler tables for V7/V8.
- UIUX workbook OPS-002 sheet updated to reflect async export interactions.
- spec_sync_report.md section 11 added for Phase2.1 records.

## 5) Immutable Constraints (Do Not Relax)
1. ROLE taxonomy: AGENT/CUSTOMER/ADMIN/OPS/SYSTEM only.
2. Manager/System Admin are ADMIN internal levels only.
3. Error payload: error_code, message, 	race_id, details.
4. State/security semantics:
   - stale permission => 401 AUTH_STALE_PERMISSION
   - lockout => 429 AUTH_LOCKED
   - rate-limit => 429 AUTH_RATE_LIMITED
   - refresh reuse => 409 AUTH_REFRESH_REUSE_DETECTED
5. Hardening gate policy lock (cookie/CSRF/rotation/lockout/UTC) must stay unchanged.
6. Spec change requires Notion sync + metadata update + spec_sync_report.md record.

## 6) Current Limitations / Residual Risks
1. Notion MCP auth is unavailable in current runtime; manual patch workflow is active.
2. Async export currently DB spool only; object storage target is Phase2.2.
3. WebAuthn is still design-only.
4. Scheduler self-healing alert routing is not fully automated.
5. Local machine Node version mismatch (24) vs project target (22).

## 7) Suggested Prompt Pattern for ChatGPT
Use this minimal packet:
1. Current scope (PR1/PR2/PR3 status)
2. Immutable constraints section
3. Validation gate table
4. Specific output format request (plan/review/implementation checklist)

## 8) Source Priority Rule
When docs conflict:
1. docs/review/mvp_verification_pack/artifacts/* (latest evidence)
2. spec_sync_report.md
3. docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md
4. plan docs under docs/review/plans/*

## 9) Latest Notion Manual Sync Patch
- docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_notion_manual_sync_patch_202603XX.md
- Apply manually when MCP auth is unavailable, then record outcome in spec_sync_report.md.
