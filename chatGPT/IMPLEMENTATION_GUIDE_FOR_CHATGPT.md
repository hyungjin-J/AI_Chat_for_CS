# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- document_type: Implementation and Operations Handoff Guide
- updated_at_kst: 2026-02-22 01:45:50 +09:00
- base_commit_hash: 8718697
- release_tag: 2026.03XX-phase2.1.2-open-risks-burndown
- branch: main
- pr_number: N/A (local working tree)

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: Node bootstrap scripts for Windows and macOS/Linux.
- Added: Notion manual evidence template generator with no-overwrite default.
- Added: Windows npm lock runbook and dev environment bootstrap guide.
- Added: Phase2.1.2 validation artifacts for backend/frontend/spec/utf8/doc-lint.
- Changed: Node check wrapper now prints actionable mismatch recovery instructions.
- Changed: Notion manual close gate reports exact missing file fields.
- Changed: Notion gate runbook to include template generation before manual patch.
- Changed: ChatGPT handoff lint to verify evidence files actually exist.
- Fixed: Notion blocked status schema (`detected_at_kst`, `preflight_ref`) and patch metadata completeness.
- Removed: reliance on manual memory for evidence triad creation order.

## 1) Execution Units
### Phase2.1.1 (baseline already completed)
- Release hygiene lock and fixed-path evidence adoption.
- ChatGPT handoff quality gate baseline.
- Notion manual close gate baseline.

### Phase2.1.2 (this run)
- W1 Node drift mitigation:
  - `scripts/bootstrap_node_22.ps1`
  - `scripts/bootstrap_node_22.sh`
  - `scripts/check_node_version.py` mismatch guidance
- W2 Windows npm lock mitigation:
  - `docs/ops/runbook_windows_node_npm_lock.md`
  - Local/CI aligned npm install flags (`--prefer-offline --no-audit --fund=false`)
- W3 Notion manual close hardening:
  - `scripts/gen_notion_manual_evidence_template.py`
  - `scripts/check_notion_manual_exception_gate.py` detailed file/field diagnostics
  - `docs/ops/runbook_spec_notion_gate.md` template-first close flow
- W4 Artifact drift prevention:
  - `scripts/lint_chatgpt_handoff_docs.py` now enforces briefing evidence file existence and scope

## 2) Validation Gate
| Gate | Status | Evidence |
|---|---|---|
| Phase2.1.2 start status snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_git_status_start.txt |
| Phase2.1.2 baseline patch snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_baseline.patch |
| Node mismatch guidance output | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_node_ssot_check.txt |
| Windows bootstrap script output | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_node_bootstrap_windows.txt |
| Notion template generator guard output | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_notion_template_generator.txt |
| Notion manual close gate | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_notion_manual_gate.txt |
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
- `scripts/bootstrap_node_22.ps1`
- `scripts/bootstrap_node_22.sh`
- `scripts/gen_notion_manual_evidence_template.py`

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
2. Node runtime mismatch still requires developer action when nvm is absent.
3. Windows endpoint security policy can still cause intermittent npm file-lock behavior.
4. Manual Notion close quality still depends on operator review even with templates.
5. Evidence existence checks are currently anchored to briefing Validation Gate rows.

## 7) Next PRs Top5
1. Add optional bootstrap auto-install path for managed developer machines.
2. Automate Windows npm lock diagnostic bundle generation.
3. Add CI fixture tests for manual close template generation and gate validation.
4. Expand lint evidence existence checks to all handoff docs with gate tables.
5. Add regression checks that prevent accidental fixed-path evidence renames.
