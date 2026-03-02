# Spec/Notion Gate Runbook (1-Page)

## Purpose
This runbook defines the fail-closed flow for spec-file changes when Notion zero-touch sync is blocked.
The goal is to prevent merge/release from depending on human memory.

## Scope (sync targets)
- `docs/references/Summary of key features.csv`
- `docs/references/CS AI Chatbot_Requirements Statement.csv`
- `docs/references/Development environment.csv`
- `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- `docs/references/CS_AI_CHATBOT_DB.xlsx`
- `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`

## Fixed evidence paths (must not change)
- `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json`
- `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
- `spec_sync_report.md`

## One-page flow (MUST)
1. Detect change scope
- Workflow: `.github/workflows/notion-zero-touch-sync.yml`
- Script: `scripts/notion_zero_touch_gate.py`
- Result: continue only if sync targets changed.

2. Run auth preflight
- Script: `scripts/notion_ci_auth_preflight.py`
- If preflight status is `PASS`: run zero-touch sync path.
- If preflight status is not `PASS`: enter manual exception path.

3. Manual exception path (BLOCKED only)
- Create/update evidence files at fixed paths.
- `notion_blocked_status.json` must contain:
  - `status=BLOCKED_AUTOMATION`
  - `reason`
  - `detected_at_kst`
  - `preflight_ref`
- `notion_manual_patch.md` must contain metadata lines:
  - `Last synced at`
  - `Source file`
  - `Version`
  - `Change summary`
- `spec_sync_report.md` must include the BLOCKED record and both evidence file references.

4. Enforce close gate in CI
- Script: `scripts/check_notion_manual_exception_gate.py`
- If BLOCKED and any evidence file is missing or invalid: CI fails.
- If all required evidence is valid: gate passes.

5. Close condition
- Only close the exception when the manual exception gate passes.
- Keep fail-closed behavior; do not bypass with ad-hoc text.

## Fail-closed policy
- Sync target changed + preflight pass + sync marker missing -> FAIL.
- Sync target changed + preflight blocked + evidence 3-set incomplete -> FAIL.
- Sync target changed + preflight blocked + evidence valid -> PASS (manual close).
- Sync target unchanged -> skip sync flow.

## CI commands (reference)
```bash
python scripts/notion_zero_touch_gate.py \
  --base-ref origin/main \
  --head-ref HEAD \
  --output-json tmp/ci_notion_sync_context.json
```

```bash
python scripts/notion_ci_auth_preflight.py \
  --context-json tmp/ci_notion_sync_context.json \
  --output tmp/ci_notion_auth_preflight.json
```

```bash
python scripts/check_notion_manual_exception_gate.py \
  --context tmp/ci_notion_sync_context.json \
  --preflight tmp/ci_notion_auth_preflight.json \
  --status-file docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json \
  --manual-patch docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md \
  --spec-sync spec_sync_report.md \
  --output-json docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate.json \
  --output-txt docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate.txt
```

## Owner checklist
- [ ] Preflight status recorded.
- [ ] BLOCKED evidence 3-set exists with fixed filenames.
- [ ] `spec_sync_report.md` includes BLOCKED_AUTOMATION record.
- [ ] `check_notion_manual_exception_gate.py` returns PASS.
