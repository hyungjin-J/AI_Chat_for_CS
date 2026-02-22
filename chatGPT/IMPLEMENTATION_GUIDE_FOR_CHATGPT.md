# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- document_type: Implementation and Operations Handoff Guide
- updated_at_kst: 2026-02-22 13:44:40 +09:00
- base_commit_hash: 763c3f4
- release_tag: 2026.03XX-phase2.1.2-open-risks-burndown
- branch: main
- pr_number: N/A (local working tree)

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: PR1 Node bootstrap scripts `bootstrap_node_from_nvmrc.ps1/.sh`.
- Added: PR1 npm lock mitigation scripts `frontend_install_retry.ps1/.sh`.
- Added: PR2 Notion template generator `gen_notion_manual_evidence_templates.py`.
- Added: PR2 Notion export snapshot policy `docs/notion_exports/README.md`.
- Changed: `check_node_version.py` mismatch output now provides 1~5 action steps.
- Changed: `check_all.ps1` fail-fast node error now includes bootstrap commands.
- Changed: `check_notion_manual_exception_gate.py` now prints required spec tokens/pattern.
- Changed: `lint_chatgpt_handoff_docs.py` now reports evidence existence stats in JSON.
- Fixed: `runbook_spec_notion_gate.md` now references plural template generator command.
- Fixed: Phase2.1.2 artifacts updated under stable fixed names without date suffix.

## 1) Execution Units
### PR1: Dev Runtime Resilience
- Files:
  - `scripts/bootstrap_node_from_nvmrc.ps1`
  - `scripts/bootstrap_node_from_nvmrc.sh`
  - `scripts/frontend_install_retry.ps1`
  - `scripts/frontend_install_retry.sh`
  - `scripts/check_node_version.py`
  - `scripts/check_all.ps1`
  - `docs/dev/DEV_ENVIRONMENT.md`
  - `docs/ops/runbook_windows_node_npm_lock.md`
- Goal:
  - Recover quickly from Node drift with actionable bootstrap path.
  - Standardize Windows npm lock response with runbook and retry helper.

### PR2: Evidence/Docs Hardening
- Files:
  - `scripts/gen_notion_manual_evidence_templates.py`
  - `scripts/gen_notion_manual_evidence_template.py` (compat wrapper)
  - `scripts/check_notion_manual_exception_gate.py`
  - `scripts/lint_chatgpt_handoff_docs.py`
  - `docs/ops/runbook_spec_notion_gate.md`
  - `docs/notion_exports/README.md`
  - `spec_sync_report.md`
- Goal:
  - Reduce manual evidence mistakes with template generation and stronger diagnostics.
  - Enforce evidence existence from handoff docs and preserve outage-time export durability.

## 2) Validation Gate
| Gate | Status | Evidence |
|---|---|---|
| Phase2.1.2 start status snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_git_status_start.txt |
| Phase2.1.2 baseline patch snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_baseline.patch |
| PR1 node bootstrap guidance | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_pr1_node_bootstrap_output.txt |
| PR1 windows runbook presence | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_pr1_windows_runbook_exists.txt |
| PR2 notion template generator guard | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_pr2_notion_template_gen.txt |
| PR2 notion close gate error message | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_pr2_notion_gate_error_message.txt |
| PR2 notion export policy readme presence | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_pr2_notion_exports_readme_exists.txt |
| Backend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_backend_test_output.txt |
| Frontend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_frontend_test_output.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_frontend_build_output.txt |
| Spec consistency | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_spec_consistency.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_utf8_check.txt |
| ChatGPT handoff doc lint | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_chatgpt_doc_lint.txt |
| ChatGPT handoff doc lint JSON | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_chatgpt_doc_lint.json |

## 3) Runbook and Script Additions
- `docs/dev/DEV_ENVIRONMENT.md`
- `docs/ops/runbook_windows_node_npm_lock.md`
- `docs/ops/runbook_spec_notion_gate.md`
- `docs/notion_exports/README.md`
- `scripts/bootstrap_node_from_nvmrc.ps1`
- `scripts/bootstrap_node_from_nvmrc.sh`
- `scripts/frontend_install_retry.ps1`
- `scripts/frontend_install_retry.sh`
- `scripts/gen_notion_manual_evidence_templates.py`

## 4) Security Notes
- Never include live secret patterns in docs; use `<REDACTED>` only.
- Keep trace_id naming canonical; typo forms are rejected by lint.
- Keep C0 controls out of handoff docs (LF/CR only).
- Hardening lock, ROLE taxonomy, and standard error shape remain unchanged.

## 5) Source Priority
If conflicts appear:
1. latest artifacts
2. spec_sync_report.md
3. reports/plans

## 6) Open Risks Top5
1. Notion auth outage still blocks zero-touch sync by design (fail-closed risk remains intentional).
2. Manual Notion close still depends on operator quality even with improved templates and diagnostics.
3. Evidence existence lint currently enforces briefing gate rows; wider table coverage can be expanded.
4. Windows endpoint security policy can still cause intermittent npm file-lock behavior.
5. First-time developer machines still need nvm installation before automatic bootstrap recovery.

## 7) Next PRs Top5
1. Add optional managed-environment installer mode for Node bootstrap scripts.
2. Automate Windows npm lock diagnostic bundle generation and attach to escalation.
3. Expand evidence existence lint to additional handoff/report validation tables.
4. Add CI fixture tests for notion template generator + close gate diagnostics.
5. Add regression checks to prevent fixed evidence path rename drift.
