# CHATGPT SELF-CONTAINED BRIEFING (EN)

- updated_at_kst: 2026-02-22 13:44:40 +09:00
- base_commit_hash: 763c3f4
- release_tag: 2026.03XX-phase2.1.2-open-risks-burndown
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: `scripts/bootstrap_node_from_nvmrc.ps1` and `.sh` for actionable Node recovery from `.nvmrc`.
- Added: `scripts/frontend_install_retry.ps1` and `.sh` to reduce npm lock/transient install failures.
- Added: `scripts/gen_notion_manual_evidence_templates.py` with no-overwrite default and next-action guidance.
- Added: `docs/notion_exports/README.md` for outage-time snapshot durability policy.
- Changed: `scripts/check_node_version.py` now prints 1~5 recovery steps and bootstrap command path.
- Changed: `scripts/check_all.ps1` now keeps fail-fast while showing bootstrap commands in the error message.
- Changed: `scripts/check_notion_manual_exception_gate.py` now prints required `spec_sync_report.md` tokens/pattern.
- Changed: `scripts/lint_chatgpt_handoff_docs.py` now emits evidence existence validation summary in JSON output.
- Fixed: `docs/ops/runbook_spec_notion_gate.md` now references plural template generator command.
- Fixed: Phase2.1.2 PR1/PR2 evidence artifacts regenerated with stable `phase2_1_2_*` naming.

## 1) Purpose
Path-independent briefing for assistants that cannot browse local files directly.

## 2) Locked Constraints
1. ROLE taxonomy remains AGENT/CUSTOMER/ADMIN/OPS/SYSTEM.
2. Manager/System Admin are admin-level permissions only.
3. Error payload shape remains error_code, message, trace_id, details.
4. Hardening lock (cookie/CSRF/rotation/lockout/UTC) must not be relaxed.
5. Spec change requires Notion sync metadata and spec_sync_report.md entry.

## 3) Validation Gate
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

## 4) Notion Manual Exception Evidence (Fixed Names)
- docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json
- docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md
- spec_sync_report.md session record

## 5) Open Risks Top5 (Re-evaluated after PR1+PR2)
1. Notion auth outage still blocks zero-touch sync by design (fail-closed risk remains intentional).
2. Manual Notion close still depends on operator quality even with template and improved gate messages.
3. Evidence existence lint enforces briefing table paths; wider document coverage can be extended later.
4. Windows endpoint security policy can still cause intermittent npm file-lock behavior.
5. First-time developer machines still need nvm installation before bootstrap can auto-heal runtime.

## 6) Next PRs Top5
1. Add optional managed-environment installer mode for Node bootstrap scripts.
2. Add Windows lock diagnostic bundle script and connect it to runbook escalation.
3. Extend evidence existence lint to additional handoff/report tables beyond briefing gate.
4. Add CI fixture tests for notion template generator + close gate failure diagnostics.
5. Add regression checks preventing accidental renaming of fixed evidence paths.

## 7) Conflict Resolution
If plan/report/evidence conflict, prioritize latest artifacts first, then spec_sync_report.md.
