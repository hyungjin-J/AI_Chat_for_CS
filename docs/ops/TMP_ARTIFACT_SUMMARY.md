# TMP Artifact Summary

## Why this file exists
- `tmp/` has been converted to a local-only workspace.
- Raw dumps are no longer tracked in git.
- Only `tmp/.gitkeep` remains in repository history.

## Removed Tracked/Untracked Temp Dumps (converted to local-only)
- `tmp/analysis_data.json`
- `tmp/api_rows_compact.csv`
- `tmp/notion_api_db_map.json`
- `tmp/notion_db_catalog_map.json`
- `tmp/notion_db_layout.md`
- `tmp/notion_db_page_content.md`
- `tmp/notion_rest_api_content.md`
- `tmp/requirements_ac_logs_security.csv`
- `tmp/requirements_compact.csv`
- `tmp/spec_extract.json`
- `tmp/spec_summary.json`
- `tmp/template_uiux_analysis.json`
- `tmp/uiux_input_summary.json`

## Policy
- Keep sensitive/intermediate data local.
- Commit only durable, curated outputs under `docs/**` when needed.
