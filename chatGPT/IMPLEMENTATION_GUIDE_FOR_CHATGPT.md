# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- document_type: Implementation and Operations Handoff Guide
- updated_at_kst: 2026-02-22 14:56:27 +09:00
- base_commit_hash: 7ac802f
- release_tag: 2026.03XX-phase2.1.4-ci-evidence-archive-contract-safety-diagnostics-evidence-lint
- branch: main
- pr_number: N/A (local working tree)

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: `scripts/validate_windows_diag_bundle.py` for deterministic zip-structure/sanitization checks.
- Added: `scripts/lint_validation_gate_tables.py` for non-chatGPT docs Validation Gate evidence lint.
- Added: `scripts/tests/test_lint_validation_gate_tables.py` regression tests for docs evidence lint behavior.
- Changed: `pr-smoke-contract.yml` now adds windows diag smoke job (`DIAG_SMOKE=1`) and PR4 docs lint step.
- Changed: CI artifact archive now includes gate evidence patterns plus Windows diag zip, with `if: always()`.
- Changed: `release-nightly-full.yml` upload policy now mirrors PR smoke archive policy.
- Changed: `scripts/assert_fixed_artifact_paths.py` blocks backslash/absolute/traversal contract entries.
- Changed: `scripts/collect_windows_npm_lock_diag.ps1` enforces fixed zip entry set and redacted path output.
- Fixed: Phase2.1.4 evidence artifacts emitted with stable `phase2_1_4_*` naming.
- Fixed: Gate regression suite passes with contract safety and docs evidence lint tests included.

## 1) Execution Units
### Phase2.1.4 Unit A: CI Evidence Archive
- Files:
  - `.github/workflows/pr-smoke-contract.yml`
  - `.github/workflows/release-nightly-full.yml`
  - `docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr1_ci_artifact_upload_policy.txt`
- Goal:
  - Upload gate evidence even on failed runs (`if: always()`).
  - Keep 30-day retention and non-blocking missing-file behavior (`if-no-files-found: warn`).

### Phase2.1.4 Unit B: Contract Safety Lock
- Files:
  - `scripts/assert_fixed_artifact_paths.py`
  - `scripts/tests/test_fixed_artifact_contract.py`
  - `docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr2_contract_safety_test_output.txt`
- Goal:
  - Reject path traversal, absolute path, and Windows backslash entries in contract JSON.
  - Emit remediation-oriented failures for 3-minute operator recovery.

### Phase2.1.4 Unit C: Windows Diagnostics Fixture and Smoke
- Files:
  - `scripts/collect_windows_npm_lock_diag.ps1`
  - `scripts/validate_windows_diag_bundle.py`
  - `docs/ops/runbook_windows_node_npm_lock.md`
  - `docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr3_windows_diag_smoke.txt`
  - `docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr3_windows_diag_validate.json`
  - `.github/workflows/pr-smoke-contract.yml`
- Goal:
  - Validate fixed zip structure and sanitization in `windows-latest` CI smoke job.
  - Keep diagnostics bundle useful while excluding sensitive path/token patterns.

### Phase2.1.4 Unit D: Evidence Lint Expansion (Non-chatGPT Docs)
- Files:
  - `scripts/lint_validation_gate_tables.py`
  - `scripts/tests/test_lint_validation_gate_tables.py`
  - `docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr4_docs_evidence_lint.txt`
  - `docs/review/mvp_verification_pack/artifacts/phase2_1_4_pr4_docs_evidence_lint.json`
- Goal:
  - Scan docs reports/runbooks/plans for Validation Gate Evidence local-path drift.
  - Fail CI on missing local evidence paths while warning external links.

## 2) Validation Gate
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

## 3) Runbook and Script Additions
- `scripts/collect_windows_npm_lock_diag.ps1`
- `scripts/validate_windows_diag_bundle.py`
- `scripts/lint_validation_gate_tables.py`
- `scripts/tests/test_lint_validation_gate_tables.py`
- `.github/workflows/pr-smoke-contract.yml` (windows diag smoke + docs lint + archive)
- `.github/workflows/release-nightly-full.yml` (archive parity)
- `docs/ops/runbook_windows_node_npm_lock.md`

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
1. Notion auth outage still blocks zero-touch sync by design (fail-closed remains intentional).
2. Non-chatGPT docs currently expose no Validation Gate tables, so PR4 lint runs as preventive contract.
3. Windows diagnostics smoke remains intentionally minimal and may omit rare forensic hints.
4. Fixed artifact contract still needs explicit governance when introducing new mandatory evidence files.
5. Artifact retention in GitHub Actions (30 days) may be insufficient for extended audits.

## 7) Next PRs Top5
1. Add non-Windows diagnostics fixture and validator for npm lock parity across macOS/Linux.
2. Expand fixed contract set to include selected Phase2.1.4 mandatory artifacts.
3. Seed docs fixtures with Validation Gate tables to keep PR4 lint exercised continuously.
4. Add CI comment summary with key artifact links (`run_id`, failed gates, remediation hints).
5. Introduce reviewer-ack workflow for contract JSON modifications (safety governance).
