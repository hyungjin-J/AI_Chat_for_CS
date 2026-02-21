# CHATGPT SELF-CONTAINED BRIEFING (EN)

- updated_at_kst: $kst
- base_commit_hash: 79383ab
- release_tag: 2026.02.21-phase2.1-pr1-pr3
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: Notion CI auth preflight fail-closed script and workflow step.
- Added: Async audit export job APIs (create/status/download) and DB spool schema.
- Added: Scheduler lock self-healing janitor job and lock heartbeat/recovery fields.
- Added: Ops runbooks for Notion gate, scheduler lock, and audit chain incidents.
- Changed: API spec workbook to include async export endpoints and fallback note.
- Changed: DB spec workbook with TB_AUDIT_EXPORT_JOB, TB_AUDIT_EXPORT_CHUNK, TB_SCHEDULER_LOCK.
- Changed: UIUX OPS-002 sheet API/table references for async export flow.
- Fixed: ExportStorage MyBatis mapper mis-detection causing export job FAILED.
- Fixed: Audit export failure path now records both ops_event and udit_log.
- Removed: scheduler/manual-only assumptions; self-healing path is now implemented.

## 1) Purpose
This file is a path-independent handoff brief for ChatGPT (or any LLM assistant) that cannot access the repository directly.
Use this as the single context packet before asking for plan/review/implementation guidance.

## 2) Project Snapshot
- Project: AI_Chatbot
- Domain: Customer-support AI assistant with grounded responses (RAG), strong security, and operational governance.
- Current stage: Phase2.1 PR1~PR3 implementation completed in working tree.
- Overall readiness: High (Go-Live gate mostly green; Notion MCP auth remains an external blocker).

## 3) What Was Implemented in This Session
### PR1 - Notion CI Token Ops
- Added scripts/notion_ci_auth_preflight.py.
- Updated .github/workflows/notion-zero-touch-sync.yml with preflight fail-closed gate.
- Updated runbook: docs/ops/runbook_spec_notion_gate.md.

### PR2 - Async Audit Export (DB Spool)
- Added migration V7__audit_export_async_spool.sql.
- Added service/jobs/storage abstraction:
  - AuditExportJobService, AuditExportWorkerJob, AuditExportCleanupJob
  - ExportStorage, DbExportStorage
- Added APIs:
  - POST /v1/admin/audit-logs/export-jobs
  - GET /v1/admin/audit-logs/export-jobs/{job_id}
  - GET /v1/admin/audit-logs/export-jobs/{job_id}/download
- Updated AdminAudit frontend page to async create/poll/download flow.

### PR3 - Scheduler Self-Healing
- Added migration V8__scheduler_lock_self_healing.sql.
- Extended scheduler lock service/repository/mapper with heartbeat + stale recovery.
- Added SchedulerLockJanitorJob.
- Updated runbook: docs/ops/runbook_scheduler_lock.md.

## 4) Non-Negotiable Locks
1. ROLE taxonomy fixed: AGENT, CUSTOMER, ADMIN, OPS, SYSTEM.
2. Manager/System Admin are ADMIN internal levels, not roles.
3. Error payload shape fixed: error_code, message, 	race_id, details.
4. Key security code semantics fixed:
   - stale permission -> 401 AUTH_STALE_PERMISSION
   - lockout -> 429 AUTH_LOCKED
   - rate-limit -> 429 AUTH_RATE_LIMITED
   - refresh reuse -> 409 AUTH_REFRESH_REUSE_DETECTED
5. Hardening Gate cookie/CSRF/rotation/lockout/UTC policies must remain locked.
6. If spec files change, Notion sync + metadata + spec_sync_report.md entry are mandatory.

## 5) Validation Gate Summary
| Gate | Status | Evidence |
|---|---|---|
| Backend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_backend_test_202603XX.txt |
| Frontend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_frontend_test_202603XX.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_frontend_build_202603XX.txt |
| Spec consistency | PASS (PASS=9 FAIL=0) | docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_spec_consistency_202603XX.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_utf8_check_202603XX.txt |
| Notion sync automation | BLOCKED (Auth required) | docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_notion_sync_status_202603XX.txt |

## 6) Remaining Risks Top5
1. Notion MCP auth is not connected in this runtime; manual patch flow is currently required.
2. Async export currently uses DB spool only; object storage migration is pending (Phase2.2).
3. WebAuthn remains design-only (implementation pending).
4. Scheduler self-healing alert routing (Pager/Slack) is not yet automated in CI/ops.
5. Node local runtime is still v24 on this machine, while project target is Node 22.

## 7) Next PRs Top5
1. Notion MCP token lifecycle automation and self-check telemetry.
2. Export storage adapter for object storage (signed URL + KMS).
3. WebAuthn runtime endpoints and UX rollout.
4. Scheduler lock recovery alert integration and SLO dashboards.
5. Phase2.2 full regression pipeline hardening (nightly + release evidence pack).

## 8) SSOT Conflict Rule
- If report/plan/evidence conflicts, prioritize latest rtifacts/* and spec_sync_report.md.
- If mismatch remains, document an explicit addendum with rationale.
