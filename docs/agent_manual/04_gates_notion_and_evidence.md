# Agent Manual 04 - Gates, Notion, and Evidence

## Purpose
Ensure every control action leaves auditable evidence.

## Mandatory Gate Commands
- Workpack + specialized agent report contract:
  - `python scripts/assert_workpack_agent_report_contract.py --use-git-diff --git-base-ref origin/main`
- Backend:
  - `cd backend && .\gradlew.bat test --no-daemon`
- Frontend:
  - `cd frontend && npm ci && npm run test:run && npm run build`
- Spec consistency:
  - `python scripts/spec_consistency_check.py`
- UTF-8 strict check:
  - run project UTF-8 gate script or equivalent strict decode check
- Handoff docs lint:
  - `python scripts/lint_chatgpt_handoff_docs.py --files chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
- Validation Gate table lint:
  - `python scripts/lint_validation_gate_tables.py`
- Notion manual exception gate:
  - `python scripts/check_notion_manual_exception_gate.py --manual-patch docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md --spec-sync spec_sync_report.md`

## Evidence Contract
- All outputs for this control lane must use:
  - `docs/review/mvp_verification_pack/artifacts/orchestrator_control_*.txt`
  - `docs/review/mvp_verification_pack/artifacts/orchestrator_control_*.json`
- Date suffix is not used for these fixed control artifacts.

## Terminology Extension Rule
- Curated terminology checks are SSOT-driven:
  - `docs/review/mvp_verification_pack/TERMINOLOGY_SSOT.json`
- Extension process and PR checklist:
  - `docs/review/mvp_verification_pack/TERMINOLOGY_SSOT.md`

## Security and Data Rules
- Never store real tokens, secrets, or PII.
- Examples must use `<REDACTED>` only.
- If any gate fails, do not continue as green.
