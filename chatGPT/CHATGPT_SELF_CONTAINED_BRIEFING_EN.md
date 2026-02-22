# CHATGPT SELF-CONTAINED BRIEFING (EN)

- updated_at_kst: 2026-02-22 14:17:28 +09:00
- base_commit_hash: e2bde0e
- release_tag: 2026.03XX-phase2.1.3-gate-regression-drift-prevention
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: `scripts/contracts/fixed_artifact_paths.json` for fixed evidence path contract locking.
- Added: `scripts/assert_fixed_artifact_paths.py` for contract validation and remediation output.
- Added: `scripts/tests/` unittest regression suite for gate scripts (lint/template/close-gate/contract).
- Added: `scripts/collect_windows_npm_lock_diag.ps1` to build sanitized Windows npm lock diagnostics bundle.
- Changed: `.github/workflows/pr-smoke-contract.yml` now enforces contract check + stdlib unittest.
- Changed: `scripts/lint_chatgpt_handoff_docs.py` now scans Validation Gate tables in both handoff docs.
- Changed: lint JSON now exposes `scanned_tables_count`, `extracted_evidence_paths_count`, `missing_paths_count`, `missing_paths`.
- Changed: `docs/ops/runbook_windows_node_npm_lock.md` now includes diagnostic bundle escalation flow.
- Fixed: `scripts/check_notion_manual_exception_gate.py` reports required spec_sync tokens/pattern in output.
- Fixed: Phase2.1.3 artifacts regenerated with stable `phase2_1_3_*` names (no date suffix).

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
| Phase2.1.3 start status snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_git_status_start.txt |
| Phase2.1.3 baseline patch snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_baseline.patch |
| Fixed artifact contract check | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_fixed_artifact_contract_check.txt |
| Gate regression unittest | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_unittest_output.txt |
| Windows diag script presence | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_windows_diag_script_exists.txt |
| Backend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_backend_test_output.txt |
| Frontend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_frontend_test_output.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_frontend_build_output.txt |
| Spec consistency | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_spec_consistency.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_utf8_check.txt |
| ChatGPT handoff doc lint | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_chatgpt_doc_lint.txt |
| ChatGPT handoff doc lint JSON | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_3_chatgpt_doc_lint.json |

## 4) Notion Manual Exception Evidence (Fixed Names)
- docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json
- docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md
- spec_sync_report.md session record

## 5) Open Risks Top5 (Re-evaluated after Phase2.1.3)
1. Notion auth outage still blocks zero-touch sync by design (fail-closed risk remains intentional).
2. Manual Notion close quality still depends on operator correctness despite stronger diagnostics.
3. Windows endpoint security policy can still trigger intermittent npm file lock behavior.
4. First-time developer machines still require nvm bootstrap prerequisites.
5. Evidence path contract currently locks Phase2.1.2 core set; future phases must append intentionally.

## 6) Next PRs Top5
1. Expand fixed artifact contract set for upcoming phase evidence groups.
2. Add CI artifact upload for `phase2_1_3_unittest_output.txt` and contract outputs.
3. Add synthetic CI fixture for Windows diag script structure checks.
4. Extend lint coverage to non-chatGPT report tables where Evidence columns exist.
5. Add policy test to reject accidental path traversal entries in contract JSON updates.

## 7) Conflict Resolution
If plan/report/evidence conflict, prioritize latest artifacts first, then spec_sync_report.md.
