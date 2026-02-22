# CHATGPT SELF-CONTAINED BRIEFING (EN)

- updated_at_kst: 2026-02-22 01:45:50 +09:00
- base_commit_hash: 8718697
- release_tag: 2026.03XX-phase2.1.2-open-risks-burndown
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: `scripts/bootstrap_node_22.ps1` for Windows Node runtime auto-recovery.
- Added: `scripts/bootstrap_node_22.sh` for macOS/Linux Node runtime auto-recovery.
- Added: `scripts/gen_notion_manual_evidence_template.py` for fixed-path evidence generation.
- Added: `docs/dev/DEV_ENVIRONMENT.md` for Node bootstrap and fallback runtime setup.
- Added: `docs/ops/runbook_windows_node_npm_lock.md` for Windows npm lock incident handling.
- Changed: `scripts/check_node_version.py` now emits step-by-step bootstrap guidance on mismatch.
- Changed: `scripts/check_notion_manual_exception_gate.py` now reports file/field-level failures.
- Changed: `scripts/lint_chatgpt_handoff_docs.py` now enforces evidence path existence in briefing gate table.
- Fixed: `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json` now uses `detected_at_kst` and `preflight_ref`.
- Fixed: `docs/ops/runbook_spec_notion_gate.md` now includes template-first close flow and fixed evidence paths.

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

## 4) Notion Manual Exception Evidence (Fixed Names)
- docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json
- docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md
- spec_sync_report.md session record

## 5) Open Risks Top5 (Re-evaluated after Phase2.1.2)
1. Notion auth outage still blocks zero-touch sync by design (fail-closed risk remains intentional).
2. Node runtime mismatch still requires developer action when nvm is absent, even with bootstrap guidance.
3. Windows endpoint security policy can still cause intermittent npm file-lock behavior.
4. Manual Notion close still depends on human patch quality after template generation.
5. Evidence existence lint currently uses briefing Validation Gate as source; missing references outside that table can bypass the check.

## 6) Next PRs Top5
1. Add optional `--attempt-install` mode to bootstrap scripts for enterprise-standard Node installers.
2. Add Windows lock diagnostics collector script and map it into the runbook escalation template.
3. Add CI job for `scripts/check_notion_manual_exception_gate.py` with template-generated fixtures.
4. Expand handoff lint evidence existence checks to implementation guide tables as well.
5. Add a small policy test pack that verifies fixed evidence path constants remain unchanged.

## 7) Conflict Resolution
If plan/report/evidence conflict, prioritize latest artifacts first, then spec_sync_report.md.
