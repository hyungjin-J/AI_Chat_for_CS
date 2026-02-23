# IMPLEMENTATION GUIDE FOR CHATGPT

- updated_at_kst: 2026-02-24 00:56:11 +09:00
- base_commit_hash: 97f7502
- current_head_short: 0115add
- release_tag: 2026.03XX-quality-hardening-workpack
- branch: main

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: `scripts/spec_consistency_check.py` with CSV/XLSX ReqID integrity checks and terminology validation.
- Added: `scripts/tests/test_spec_consistency_check.py` for deterministic PASS/FAIL regression coverage.
- Added: `scripts/assert_spec_sync_report_updated.py` to enforce report update on canonical spec changes.
- Added: `scripts/tests/test_assert_spec_sync_report_updated.py` to verify fail-closed spec sync behavior.
- Added: `scripts/check_workspace_path_ascii.py` and unit tests for local unicode-path warning behavior.
- Added: `docs/ops/NODE22_UNICODE_WORKSPACE_GUIDE.md` for reproducible frontend execution guidance.
- Changed: `.github/workflows/pr-smoke-contract.yml` and `.github/workflows/release-nightly-full.yml` to run new gates.
- Changed: ChatGPT handoff update gate default mode to `core-only` (fail on core changes, warn on non-core).
- Changed: UTF-8 Wave2 conservative conversion batch lowered full-scan baseline from 98 to 78.
- Changed: domain boundary refactors in billing/identity/knowledge to reduce purity debt without relaxing security invariants.
- Fixed: full-scan UTF-8 baseline artifacts and normalization reports after safe BOM-focused conversion batch.
- Removed: undocumented handoff gap by aligning this guide and briefing to AGENTS 16.8 mandatory handoff content.

## 1) Scope Implemented
This continuation covers:
1. Automated spec consistency verification
2. Spec sync report fail-closed enforcement
3. Domain purity debt burn-down
4. UTF-8 baseline debt burn-down
5. Node22 unicode workspace reproducibility hardening
6. CI integration and evidence refresh

Primary audit entry:
- `docs/review/agent_reports/CONTINUATION_PREFLIGHT_AUDIT.md`

## 2) Implementation Details

### 2.1 Spec Consistency Gate
Files:
- `scripts/spec_consistency_check.py`
- `scripts/tests/test_spec_consistency_check.py`

Behavior:
- Builds ReqID SSOT from requirements CSV.
- Validates ReqID references in Summary CSV.
- Parses API workbook `전체API목록` `비고` field for `ReqID:` and `ReqID+:` tokens.
- Scans UIUX/DB workbooks for ReqID-like tokens and validates against SSOT.
- Verifies minimal terminology consistency: `secret_ref`, ROLE taxonomy, SSE event set.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/spec_consistency_check_report.txt`
- `docs/review/mvp_verification_pack/artifacts/spec_consistency_check_report.json`
- `docs/review/mvp_verification_pack/artifacts/spec_consistency_check_pass.txt`

### 2.2 Spec Sync Report Update Gate
Files:
- `scripts/assert_spec_sync_report_updated.py`
- `scripts/tests/test_assert_spec_sync_report_updated.py`

Behavior:
- Detects canonical spec file changes via git diff.
- Requires `spec_sync_report.md` change when canonical spec changes are present.
- Optionally validates metadata tokens: Last synced at / Source file / Version or commit / Change summary.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/spec_sync_report_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/spec_sync_report_gate.json`

### 2.3 Domain Purity Burn-down
Highlights:
- Boundary violations addressed by moving row/record types to domain model package.
- Billing cost dependency path refactored through domain port style.
- Ratchet gate evidence refreshed with reduced baseline.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/domain_layer_boundary_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/domain_layer_purity_burndown_summary.txt`
- `docs/review/mvp_verification_pack/artifacts/domain_layer_purity_baseline_violations.json`

### 2.4 UTF-8 Baseline Burn-down
Files:
- `scripts/normalize_utf8.py`

Highlights:
- Safe BOM-focused normalization batch with evidence reporting.
- Baseline reduced while ratchet remained fail-closed.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_current.txt`
- `docs/review/mvp_verification_pack/artifacts/utf8_bom_normalization_report.md`
- `docs/review/mvp_verification_pack/artifacts/utf16_normalization_report.md`

### 2.5 Node22 Unicode Workspace Mitigation
Files:
- `scripts/check_workspace_path_ascii.py`
- `scripts/bootstrap_node_from_nvmrc.ps1`
- `docs/ops/NODE22_UNICODE_WORKSPACE_GUIDE.md`

Highlights:
- Local warning-only guard to avoid CI noise.
- Repro evidence documents unicode-path failure and ASCII workspace success path.

Output:
- `docs/review/mvp_verification_pack/artifacts/node22_unicode_workspace_repro.txt`

### 2.6 ChatGPT Handoff Update Gate Tuning
Files:
- `scripts/assert_chatgpt_handoff_updated.py`
- `scripts/tests/test_assert_chatgpt_handoff_updated.py`

Policy:
- Default mode is `core-only`.
- `core-only` blocks merge only for core implementation changes without both handoff docs updates.
- Non-core changes produce warning only to reduce developer friction.
- `strict-all` remains available for temporary hard lock if needed.

Output:
- `docs/review/mvp_verification_pack/artifacts/chatgpt_handoff_update_gate.txt`

## 3) Validation Gates
| Gate | Status | Evidence |
|---|---|---|
| Workpack/report v2 contract | PASS | `docs/review/mvp_verification_pack/artifacts/workpack_agent_contract_v2.txt` |
| Workpack trigger consistency | PASS | `docs/review/mvp_verification_pack/artifacts/continuation_trigger_consistency_gate.txt` |
| Domain purity ratchet | PASS | `docs/review/mvp_verification_pack/artifacts/domain_layer_boundary_gate.txt` |
| Backoffice ACL ratchet | PASS | `docs/review/mvp_verification_pack/artifacts/backoffice_acl_boundary_gate.txt` |
| Frontend import boundary | PASS | `docs/review/mvp_verification_pack/artifacts/frontend_import_boundary_gate.txt` |
| UTF-8 strict diff-scope | PASS | `docs/review/mvp_verification_pack/artifacts/continuation_utf8_strict_gate.txt` |
| UTF-8 full-scan ratchet | PASS | `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.txt` |
| Scaffold smoke | PASS | `docs/review/mvp_verification_pack/artifacts/scaffold_contract_smoke.txt` |
| Spec consistency check | PASS | `docs/review/mvp_verification_pack/artifacts/spec_consistency_check_report.txt` |
| Spec sync report update gate | PASS | `docs/review/mvp_verification_pack/artifacts/spec_sync_report_gate.txt` |
| ChatGPT handoff update gate | PASS | `docs/review/mvp_verification_pack/artifacts/chatgpt_handoff_update_gate.txt` |
| Quality validation summary | PASS | `docs/review/mvp_verification_pack/artifacts/quality_workpack_validation_summary.txt` |

## 4) Baseline Delta
- Domain purity baseline: 6 -> 0
- UTF-8 full-scan baseline: 118 -> 78
- API compare: added=0, removed=0

## 5) Remaining Risks Top5
1. UTF-8 residual baseline remains non-trivial and should be reduced in controlled waves.
2. Node22 unicode-path instability can still impact developers who skip ASCII workspace mitigation.
3. Spec terminology checks are intentionally minimal and should be expanded gradually.
4. Notion synchronization traceability still depends on explicit report discipline.
5. Large artifact inventory can hide regressions without periodic curation.

## 6) Next PRs Top5
1. Add broader terminology checks to spec consistency gate with curated allowlist.
2. Continue UTF-8 burn-down toward sub-80 baseline while preserving ratchet strictness.
3. Extend Node workspace guide with one-command mirror-and-run helper.
4. Tighten evidence curation for stale artifact cleanup and easier gate reading.
5. Incrementally strengthen automation around sync and handoff completeness checks.

## 7) Safety Confirmation
- No ROLE taxonomy change.
- No error payload shape change.
- No fail-closed answer contract relaxation.
- No hardening lock relaxation.
- No tenant/RBAC authority relaxation.
- No public API/SSE contract break.
- No secrets/tokens/raw PII in committed artifacts.

## 8) Conflict Resolution Note (SSOT)
- In conflict, latest artifacts under `docs/review/mvp_verification_pack/artifacts/*` take precedence.
- `spec_sync_report.md` remains the sync log precedence target for spec/document synchronization conflicts.
