# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- document_type: Implementation and Operations Handoff Guide
- updated_at_kst: 2026-02-22 14:17:28 +09:00
- base_commit_hash: e2bde0e
- release_tag: 2026.03XX-phase2.1.3-gate-regression-drift-prevention
- branch: main
- pr_number: N/A (local working tree)

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: fixed artifact path contract file `scripts/contracts/fixed_artifact_paths.json`.
- Added: contract validator `scripts/assert_fixed_artifact_paths.py` with remediation output.
- Added: stdlib gate regression tests under `scripts/tests/`.
- Added: Windows diagnostic bundle collector `scripts/collect_windows_npm_lock_diag.ps1`.
- Changed: CI workflow now enforces contract check and `python -m unittest discover`.
- Changed: handoff lint now scans both docs' Validation Gate tables for evidence paths.
- Changed: lint JSON now reports table/path coverage and missing path list.
- Changed: Windows npm lock runbook now includes diagnostics bundle escalation workflow.
- Fixed: Notion close gate output now prints required spec_sync token/pattern expectations.
- Fixed: Phase2.1.3 verification artifacts generated with stable prefix naming.

## 1) Execution Units
### Phase2.1.3 Unit A: Artifact Path Contract
- Files:
  - `scripts/contracts/fixed_artifact_paths.json`
  - `scripts/assert_fixed_artifact_paths.py`
  - `.github/workflows/pr-smoke-contract.yml`
- Goal:
  - Prevent rename drift of fixed evidence paths.
  - Fail CI when required evidence paths disappear or move out of contract scope.

### Phase2.1.3 Unit B: chatGPT Lint Coverage Expansion
- Files:
  - `scripts/lint_chatgpt_handoff_docs.py`
  - `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
  - `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
- Goal:
  - Parse Validation Gate evidence paths from both handoff documents.
  - Fail on missing local evidence and expose coverage metrics in JSON.

### Phase2.1.3 Unit C: Gate Regression Tests
- Files:
  - `scripts/tests/test_lint_chatgpt_handoff_docs.py`
  - `scripts/tests/test_notion_templates.py`
  - `scripts/tests/test_notion_manual_exception_gate.py`
  - `scripts/tests/test_fixed_artifact_contract.py`
  - `.github/workflows/pr-smoke-contract.yml`
- Goal:
  - Protect gate scripts from regressions via deterministic stdlib `unittest` execution.

### Phase2.1.3 Unit D: Windows npm Lock Diagnostics
- Files:
  - `scripts/collect_windows_npm_lock_diag.ps1`
  - `docs/ops/runbook_windows_node_npm_lock.md`
  - `docs/review/mvp_verification_pack/artifacts/phase2_1_3_windows_diag_script_exists.txt`
- Goal:
  - Provide sanitized diagnostic bundle output and escalation-ready operational flow.

## 2) Validation Gate
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

## 3) Runbook and Script Additions
- `scripts/contracts/fixed_artifact_paths.json`
- `scripts/assert_fixed_artifact_paths.py`
- `scripts/tests/test_lint_chatgpt_handoff_docs.py`
- `scripts/tests/test_notion_templates.py`
- `scripts/tests/test_notion_manual_exception_gate.py`
- `scripts/tests/test_fixed_artifact_contract.py`
- `scripts/collect_windows_npm_lock_diag.ps1`
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
1. Notion auth outage still blocks zero-touch sync by design (fail-closed risk remains intentional).
2. Manual Notion close still depends on operator quality despite stronger diagnostics.
3. Windows endpoint security policy can still cause intermittent npm file-lock behavior.
4. First-time developer machines still require nvm bootstrap prerequisites.
5. Future phase evidence paths must be intentionally appended to contract to avoid false confidence.

## 7) Next PRs Top5
1. Add CI upload/archive policy for Phase2.1.3 contract and unittest artifacts.
2. Add smoke fixtures for Windows diagnostic bundle zip structure verification.
3. Expand evidence-path lint coverage to additional report/runbook tables.
4. Add contract-review helper that proposes diff-aware path additions for new phases.
5. Add non-Windows diagnostic equivalent for npm lock anomalies on macOS/Linux.
