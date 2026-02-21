# 202603XX Phase2.1.1 Release Hygiene & ChatGPT Handoff Hardening Plan

- status: `PLAN_LOCK_DRAFT`
- mode: `EXECUTION_BASELINE_LOCKED`
- references:
  1. `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
  2. `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
  3. `AGENTS.md` (16.8)
  4. `docs/ops/runbook_spec_notion_gate.md`
  5. `spec_sync_report.md`
  6. `docs/review/mvp_verification_pack/artifacts/*` (Phase2.1 evidence)

## Summary
Phase2.1.1 targets release hygiene hardening, not new business features.
This plan closes three release blockers:
1. Node 22 LTS SSOT/CI alignment with fail-fast.
2. Automated quality gate for ChatGPT handoff docs.
3. Formalized Notion BLOCKED manual exception close gate.

## Why
1. ChatGPT handoff docs contain placeholder metadata and control-character corruption.
2. Node policy is partially standardized, but CI and local policy are not fully locked to one source.
3. Notion preflight fail-closed exists, but BLOCKED manual close path is not formally gate-enforced.

## Scope
1. Lock Node SSOT and synchronize CI/runtime checks.
2. Add ChatGPT doc lint automation (metadata/control chars/forbidden terms).
3. Add Notion manual exception gate with required evidence triad.
4. Add one-page runbook flow: `BLOCKED -> Manual Patch -> Evidence -> Close`.

## Out of Scope
1. ROLE taxonomy changes (`AGENT/CUSTOMER/ADMIN/OPS/SYSTEM` fixed).
2. Runtime business feature changes (MFA/WebAuthn/RBAC model redesign).
3. Hardening policy relaxations.
4. Error payload schema changes.

## Decisions (Locked)
1. Node SSOT is `.nvmrc` and pinned to `22.12.0`.
2. CI Node setup uses only `node-version-file: .nvmrc`.
3. Node mismatch is fail-fast in local and CI checks.
4. ChatGPT doc quality gate is standardized via `scripts/lint_chatgpt_handoff_docs.py`.
5. Notion preflight `NOTION_AUTH_*` failure always blocks auto sync (fail-closed).
6. Notion manual exception close requires evidence triad:
   - blocked status
   - manual patch document
   - `spec_sync_report.md` entry
7. Node pin policy is unified: keep `.nvmrc=22.12.0` and synchronize `package.json` `engines`/`volta` (if present) to the same baseline.
8. C0 control character policy is locked: only `\n` and `\r` allowed; all other C0 (including `\t`) are forbidden.
9. `trace_id` typo detection is enforced by regex (`\brace_id\b` forbidden; `trace_id` only).
10. Forbidden-term examples in documentation must use `<REDACTED>` placeholder, not live pattern literals.
11. Notion manual exception evidence filenames are fixed under `docs/review/mvp_verification_pack/artifacts/`:
    - `notion_blocked_status.json`
    - `notion_manual_patch.md`
12. PR-C is promoted from recommended to MUST; Notion BLOCKED needs an official operational close gate.

## PR Plan

## PR-A Node 22 Standardization
### Files
1. `.nvmrc`
2. `frontend/package.json`
3. `.github/workflows/pr-smoke-contract.yml`
4. `.github/workflows/release-nightly-full.yml`
5. `.github/workflows/mvp-demo-verify.yml`
6. `.github/workflows/provider-regression-nightly.yml`
7. `.github/workflows/notion-zero-touch-sync.yml`
8. `scripts/check_all.ps1`
9. `scripts/assert_node_ssot.py` (new)

### DoD
1. `.nvmrc` pinned to `22.12.0`.
2. All listed workflows use `node-version-file: .nvmrc`.
3. Node mismatch fails fast via script and `check_all.ps1`.

## PR-B ChatGPT Handoff Doc Hardening
### Files
1. `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
2. `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
3. `AGENTS.md` (16.8 hardening clauses)
4. `scripts/lint_chatgpt_handoff_docs.py` (new)
5. `.github/workflows/pr-smoke-contract.yml` (lint step)
6. `.github/workflows/release-nightly-full.yml` (lint step)

### DoD
1. Placeholder metadata removed.
2. C0 control chars removed (except LF/CR).
3. `race_id` typo blocked by lint.
4. Token/PII leakage scan for ChatGPT docs passes.

## PR-C (MUST) Notion BLOCKED Exception Gate + Runbook
### Files
1. `scripts/check_notion_manual_exception_gate.py` (new)
2. `.github/workflows/notion-zero-touch-sync.yml`
3. `docs/ops/runbook_spec_notion_gate.md`
4. `spec_sync_report.md`
5. `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json` (template/evidence)
6. `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md` (template/evidence)

### DoD
1. Preflight failure blocks auto sync.
2. Manual exception close passes only with evidence triad.
3. Runbook one-page flow and commands match CI gate behavior.

## Validation Commands
1. `python scripts/assert_node_ssot.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime`
2. `python scripts/lint_chatgpt_handoff_docs.py --files chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md --output-json docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_doc_lint_202603XX.json`
3. `python scripts/check_notion_manual_exception_gate.py --context tmp/ci_notion_sync_context.json --preflight tmp/ci_notion_auth_preflight.json --status-file docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json --manual-patch docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md --spec-sync spec_sync_report.md --output-json docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate_202603XX.json`
4. `python scripts/spec_consistency_check.py`
5. `cd backend && ./gradlew.bat test --no-daemon`
6. `cd frontend && npm ci && npm run test:run && npm run build`

## Evidence Artifacts
1. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prA_node_ssot_check_202603XX.txt`
2. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prA_node_runtime_202603XX.txt`
3. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prA_check_all_failfast_202603XX.txt`
4. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_doc_lint_202603XX.txt`
5. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_doc_lint_202603XX.json`
6. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_utf8_202603XX.txt`
7. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_pii_token_scan_202603XX.txt`
8. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate_202603XX.txt`
9. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate_202603XX.json`
10. `docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_runbook_onepager_check_202603XX.txt`

## Global DoD
1. Node SSOT/CI/runtime checks are aligned and fail-fast.
2. ChatGPT docs lint/UTF-8/security scan passes.
3. Notion BLOCKED manual exception close gate is enforced in CI.
4. AGENTS 16.8 requirements are operationalized by scripts/workflows.
5. Hardening locks and error schema constraints remain unchanged.

## Rollback
1. PR-A/B/C remain independently revertible.
2. Fail-closed behavior is non-negotiable and not rolled back.
3. If rollback is needed, preserve evidence and append rollback rationale to `spec_sync_report.md`.
