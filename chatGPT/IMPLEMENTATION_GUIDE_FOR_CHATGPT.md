# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- updated_at_kst: 2026-02-22 23:12:30 +09:00
- base_commit_hash: 97f7502
- current_head_short: b6e156e
- release_tag: 2026.03XX-ddd-refactor-backend-security-guard-remediation
- branch: main

## 0) Scope
This continuation finalized:
1. Ratchet gate integrity hardening (baseline growth fail-closed)
2. SSOT handoff doc unification
3. Baseline debt burn-down updates
4. Reproducible artifact refresh and preflight sync

Primary audit entry:
- `docs/review/agent_reports/CONTINUATION_PREFLIGHT_AUDIT.md`

## 1) Implemented Changes

### 1.1 Baseline Growth Guard Hardening
Updated scripts:
- `scripts/assert_domain_layer_boundaries.py`
- `scripts/assert_backoffice_acl_boundary.py`
- `scripts/assert_utf8_strict.py`

Key behavior:
- baseline growth check compares `base_ref` vs `head` baseline counts.
- `baseline_count_head > baseline_count_base` => FAIL.
- bootstrap-safe fallback when baseline file is absent in base ref:
  - `baseline_growth_base_source=head-fallback:missing-in-<ref>`
  - avoids false failure during first introduction PR.

Tests:
- `scripts/tests/test_assert_domain_layer_boundaries.py`
- `scripts/tests/test_assert_backoffice_acl_boundary.py`
- `scripts/tests/test_assert_utf8_strict.py`
- baseline growth scenarios covered: increase FAIL / same PASS / decrease PASS.

### 1.2 Workpack/Report v2 Stability
Updated:
- `scripts/assert_workpack_agent_report_contract.py`

Fix:
- deleted/renamed legacy topic paths are filtered out from topic validation by requiring current topic directory existence.
- prevents false FAIL on removed old topic folders.

### 1.3 Baseline Burn-down
1. Domain purity:
- baseline tightened from 9 to 6.
- baseline file: `docs/review/mvp_verification_pack/artifacts/domain_layer_purity_baseline_violations.json`

2. UTF-8 full-scan:
- low-risk BOM cleanup executed for 30 files.
- baseline tightened from 148 to 118.
- baseline file: `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_baseline_violations.json`
- hash evidence:
  - `docs/review/mvp_verification_pack/artifacts/utf8_bom_normalization_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf16_normalization_report.md`

3. Backoffice ACL:
- machine baseline JSON in use:
  - `docs/review/mvp_verification_pack/artifacts/backoffice_acl_boundary_baseline_violations.json`
- current baseline count remains 0.

### 1.4 Node Runtime Discipline Evidence Refresh
PASS evidence under Node 22.12.0:
- `docs/review/mvp_verification_pack/artifacts/node_ssot_pass_on_22120.txt`
- `docs/review/mvp_verification_pack/artifacts/node_runtime_discipline_check.txt`
- `docs/review/mvp_verification_pack/artifacts/frontend_npm_ci_pass_on_22120.txt`
- `docs/review/mvp_verification_pack/artifacts/continuation_preflight_frontend_test.txt`
- `docs/review/mvp_verification_pack/artifacts/continuation_preflight_frontend_build.txt`

Note:
- on this machine, direct Node22 execution under the original Unicode workspace path was unstable for frontend tests.
- PASS evidence was generated with Node22 in an ASCII temp workspace copy to avoid path-encoding runtime issues, without changing repo code/contracts.

## 2) CI Wiring Summary
Workflows updated:
- `.github/workflows/pr-smoke-contract.yml`
- `.github/workflows/release-nightly-full.yml`

Enforced steps include:
1. workpack trigger consistency
2. workpack/report v2 gate
3. domain purity ratchet (+ baseline growth guard)
4. backoffice ACL ratchet (+ baseline growth guard)
5. frontend import boundary gate
6. UTF-8 strict diff-scope gate
7. UTF-8 full-scan ratchet gate (nightly + PR contract path)
8. scaffold contract smoke gate
9. mapper namespace + legacy package + platform boundary gates

## 3) Latest Verification Snapshot
| Check | Result | Evidence |
|---|---|---|
| Script tests | PASS (65) | `docs/review/mvp_verification_pack/artifacts/continuation_preflight_scripts_unittest.txt` |
| Trigger consistency | PASS | `docs/review/mvp_verification_pack/artifacts/continuation_trigger_consistency_gate.txt` |
| Workpack/report v2 | PASS | `docs/review/mvp_verification_pack/artifacts/workpack_agent_contract_v2.txt` |
| Domain ratchet | PASS | `docs/review/mvp_verification_pack/artifacts/domain_layer_boundary_gate.txt` |
| Backoffice ACL ratchet | PASS | `docs/review/mvp_verification_pack/artifacts/backoffice_acl_boundary_gate.txt` |
| UTF-8 diff-scope | PASS | `docs/review/mvp_verification_pack/artifacts/continuation_utf8_strict_gate.txt` |
| UTF-8 full-scan ratchet | PASS | `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.txt` |
| Scaffold smoke | PASS | `docs/review/mvp_verification_pack/artifacts/scaffold_contract_smoke.txt` |
| Backend test/build | PASS | `docs/review/mvp_verification_pack/artifacts/continuation_preflight_backend_test.txt` |
| Billing parity | PASS | `docs/review/mvp_verification_pack/artifacts/billing_parity_summary.txt` |
| Frontend npm ci/test/build (Node22) | PASS | `docs/review/mvp_verification_pack/artifacts/frontend_npm_ci_pass_on_22120.txt` |
| Public API compare | PASS (`added=0`, `removed=0`) | `docs/review/mvp_verification_pack/artifacts/continuation_preflight_public_api_compare.txt` |

## 4) Open Risk Status
1. R1 Node runtime mismatch: CLOSED
2. R2 Domain purity baseline burn-down start: CLOSED
3. R3 UTF-8 full-repo control: CLOSED
4. R4 Spec-only + Notion exception E2E path: CLOSED

## 5) Remaining Backlog
1. Domain purity baseline backlog: 6 items
2. UTF-8 historical baseline backlog: 118 items

## 6) Safety Confirmation
- No ROLE taxonomy changes.
- No error payload contract changes.
- No fail-closed answer contract relaxation.
- No hardening lock relaxation.
- No tenant/RBAC authority relaxation.
- No public API/SSE contract break.
- No secrets/tokens/raw PII in artifacts.
