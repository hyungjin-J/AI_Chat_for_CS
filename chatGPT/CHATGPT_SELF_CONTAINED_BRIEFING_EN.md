# CHATGPT SELF-CONTAINED BRIEFING (EN)

- updated_at_kst: 2026-02-22 14:56:27 +09:00
- base_commit_hash: 7ac802f
- release_tag: 2026.03XX-phase2.1.4-ci-evidence-archive-contract-safety-diagnostics-evidence-lint
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: `scripts/validate_windows_diag_bundle.py` for fixed-structure and sanitization checks on Windows diagnostic bundle zip.
- Added: `scripts/lint_validation_gate_tables.py` to lint Validation Gate evidence paths in reports/runbooks/plans.
- Added: `scripts/tests/test_lint_validation_gate_tables.py` for regression lock on non-chatGPT docs evidence lint.
- Changed: `.github/workflows/pr-smoke-contract.yml` now runs docs evidence lint and a dedicated windows diag smoke job.
- Changed: CI artifact upload policy now archives gate evidence on both `pr-smoke-contract` and `release-nightly-full`.
- Changed: `scripts/assert_fixed_artifact_paths.py` now blocks absolute paths, backslash paths, and traversal paths.
- Changed: `scripts/collect_windows_npm_lock_diag.ps1` now supports `DIAG_SMOKE=1` and fixed zip entry contract.
- Changed: `docs/ops/runbook_windows_node_npm_lock.md` now documents zip structure + validator + escalation sequence.
- Fixed: Phase2.1.4 artifacts generated under stable `phase2_1_4_*` naming without date suffix.
- Fixed: Contract safety and docs evidence lint regression tests now pass under stdlib `unittest`.

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
| Phase2.1.4 start status snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_git_status_start.txt |
| Phase2.1.4 baseline patch snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_baseline.patch |
| PR1 CI artifact upload policy | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr1_ci_artifact_upload_policy.txt |
| Fixed artifact contract check | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_fixed_artifact_contract_check.txt |
| PR2 contract safety unittest | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr2_contract_safety_test_output.txt |
| PR3 windows diag smoke output | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr3_windows_diag_smoke.txt |
| PR3 windows diag validate JSON | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr3_windows_diag_validate.json |
| PR4 docs evidence lint | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr4_docs_evidence_lint.txt |
| PR4 docs evidence lint JSON | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr4_docs_evidence_lint.json |
| Gate regression unittest | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_unittest_output.txt |
| Backend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_backend_test_output.txt |
| Frontend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_frontend_test_output.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_frontend_build_output.txt |
| Spec consistency | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_spec_consistency.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_utf8_check.txt |
| ChatGPT handoff doc lint | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_chatgpt_doc_lint.txt |
| ChatGPT handoff doc lint JSON | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_4_chatgpt_doc_lint.json |

## 4) Notion Manual Exception Evidence (Fixed Names)
- docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json
- docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md
- spec_sync_report.md session record

## 5) Open Risks Top5 (Re-evaluated after Phase2.1.4)
1. Notion auth outage still blocks zero-touch sync by design (fail-closed remains intentional and documented).
2. Non-chatGPT docs currently have zero Validation Gate tables, so PR4 lint coverage is structural-ready but data-light.
3. Windows diag smoke bundle is sanitized/minimal; deep forensic needs controlled manual follow-up.
4. Fixed artifact contract still requires explicit updates when new phase-critical artifacts are introduced.
5. CI artifact retention is 30 days; long-horizon audit retention requires separate storage policy.

## 6) Next PRs Top5
1. Extend fixed artifact contract entries to include stabilized Phase2.1.4 mandatory evidence paths.
2. Add a non-Windows diagnostic collector/validator pair for npm lock anomalies on macOS/Linux.
3. Add a fixture markdown set under docs to keep non-chatGPT Validation Gate lint coverage non-zero.
4. Add CI summary artifact index markdown generation for faster audit navigation by run_id.
5. Add allowlist governance workflow for intentional contract path additions with reviewer ack.

## 7) Conflict Resolution
If plan/report/evidence conflict, prioritize latest artifacts first, then spec_sync_report.md.
