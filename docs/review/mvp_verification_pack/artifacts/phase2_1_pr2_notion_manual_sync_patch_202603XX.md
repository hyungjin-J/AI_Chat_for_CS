# Phase2.1 PR2 Notion Manual Sync Patch

- generated_at_kst: 2026-02-21 22:58:08 +09:00
- source_commit: 79383ab (working tree)
- reason: Notion MCP auth required in current session

## 1) API Spec Page
- URL: https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- Last synced at: 2026-02-21 22:58:08 +09:00
- Source file: docs/references/google_ready_api_spec_v0.3_20260216.xlsx
- Version: 79383ab
- Change summary:
  1. Added async audit export APIs:
     - POST /v1/admin/audit-logs/export-jobs
     - GET /v1/admin/audit-logs/export-jobs/{job_id}
     - GET /v1/admin/audit-logs/export-jobs/{job_id}/download
  2. Marked legacy GET /v1/admin/audit-logs/export as fallback-only for small scope.
  3. Preserved ROLE taxonomy and access_level conventions.

## 2) DB Spec Page
- URL: https://www.notion.so/2ed405a3a720812180d9d508b77f31a4
- Last synced at: 2026-02-21 22:58:08 +09:00
- Source file: docs/references/CS_AI_CHATBOT_DB.xlsx
- Version: 79383ab
- Change summary:
  1. Added table specs: TB_AUDIT_EXPORT_JOB, TB_AUDIT_EXPORT_CHUNK, TB_SCHEDULER_LOCK.
  2. Refreshed 목차 count and missing table index entries.
  3. Reflected V7/V8 async export spool + scheduler self-healing schema.

## 3) UI/UX Spec Page
- URL: https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444
- Last synced at: 2026-02-21 22:58:08 +09:00
- Source file: docs/uiux/CS_RAG_UI_UX_설계서.xlsx
- Version: 79383ab
- Change summary:
  1. OPS-002 page API summary includes async export-jobs endpoints.
  2. OPS-002 table usage includes TB_AUDIT_EXPORT_JOB / TB_AUDIT_EXPORT_CHUNK / TB_SCHEDULER_LOCK.

## Notes
- This patch is generated for manual application only.
- After manual update, append evidence and result to spec_sync_report.md.
