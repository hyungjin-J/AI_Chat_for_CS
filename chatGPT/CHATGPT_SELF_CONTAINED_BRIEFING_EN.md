# CHATGPT SELF-CONTAINED BRIEFING (EN)

- updated_at_kst: 2026-02-22 13:32:18 +09:00
- base_commit_hash: c64905b
- release_tag: 2026.03XX-phase2.1.2-open-risks-burndown
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: `scripts/bootstrap_node_from_nvmrc.ps1` for Windows Node runtime recovery from `.nvmrc`.
- Added: `scripts/bootstrap_node_from_nvmrc.sh` for macOS/Linux Node runtime recovery from `.nvmrc`.
- Added: optional retry helpers `scripts/frontend_install_retry.ps1` and `scripts/frontend_install_retry.sh`.
- Changed: `scripts/check_node_version.py` now prints 1~5 actionable recovery steps with bootstrap command.
- Changed: `scripts/check_all.ps1` fail-fast error now includes bootstrap commands and gate report path.
- Changed: `docs/dev/DEV_ENVIRONMENT.md` now points to `bootstrap_node_from_nvmrc.*` and retry helper usage.
- Changed: `docs/ops/runbook_windows_node_npm_lock.md` now includes retry helper and WSL2 fallback guidance.
- Changed: compatibility wrappers retained in `scripts/bootstrap_node_22.ps1` and `scripts/bootstrap_node_22.sh`.
- Fixed: PR1 evidence `phase2_1_2_pr1_node_bootstrap_output.txt` generated with mismatch guidance output.
- Fixed: PR1 evidence `phase2_1_2_pr1_windows_runbook_exists.txt` generated for runbook presence proof.

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
| PR1 Node mismatch bootstrap guidance | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_pr1_node_bootstrap_output.txt |
| PR1 Windows npm lock runbook presence | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_pr1_windows_runbook_exists.txt |

## 4) Notion Manual Exception Evidence (Fixed Names)
- docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json
- docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md
- spec_sync_report.md session record

## 5) Open Risks Top5 (Re-evaluated after Phase2.1.2)
1. Notion auth outage still blocks zero-touch sync by design (fail-closed risk remains intentional).
2. Manual Notion close is still human-driven before PR2 template/gate hardening is fully applied.
3. ChatGPT doc lint evidence existence is still briefing-table scoped before PR2 final lint expansion.
4. Windows endpoint security policy can still cause intermittent npm file-lock behavior.
5. Node runtime mismatch still requires nvm install on first-time developer machines.

## 6) Next PRs Top5
1. Add `scripts/gen_notion_manual_evidence_templates.py` and switch runbook to plural generator command.
2. Strengthen `scripts/check_notion_manual_exception_gate.py` with searchable spec_sync pattern output.
3. Add `docs/notion_exports/README.md` snapshot durability policy for BLOCKED_AUTOMATION sessions.
4. Extend `scripts/lint_chatgpt_handoff_docs.py` JSON output with evidence existence validation summary.
5. Regenerate full Phase2.1.2 gates and refresh final Validation Gate evidence table.

## 7) Conflict Resolution
If plan/report/evidence conflict, prioritize latest artifacts first, then spec_sync_report.md.
