# Notion Export Snapshot Policy

## Purpose
Notion pages are part of delivery evidence, but they are outside Git-managed SSOT files.
When Notion automation is blocked, this policy preserves document durability with reproducible snapshots.

## Snapshot Rules
1. During a Notion update session, save a markdown or PDF snapshot when possible.
2. Use this path pattern:
   - `docs/notion_exports/YYYYMMDD/<page_slug>.md`
   - `docs/notion_exports/YYYYMMDD/<page_slug>.pdf`
3. Keep filenames stable and human-readable (`requirements`, `api_spec`, `db_spec`, `uiux_spec`).
4. Never include tokens, signed URLs, private endpoints, or PII.
5. Public Notion page URLs are allowed when needed for traceability.

## spec_sync_report.md Recording Rule
When a snapshot is produced, add the following to `spec_sync_report.md` in the same session:
- Export path
- Export timestamp (KST)
- Commit hash or tag
- Reason (normal sync proof or BLOCKED_AUTOMATION fallback)

## BLOCKED_AUTOMATION Minimum Procedure
If Notion auth outage blocks zero-touch sync:
1. Generate manual evidence templates (`notion_blocked_status.json`, `notion_manual_patch.md`).
2. Apply manual patch and run close gate validation.
3. Save at least one markdown/pdf snapshot under `docs/notion_exports/YYYYMMDD/`.
4. Record snapshot path and close evidence in `spec_sync_report.md`.
