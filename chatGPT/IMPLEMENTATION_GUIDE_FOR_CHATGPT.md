# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- document_type: Implementation and Operations Handoff Guide
- updated_at_kst: 2026-02-21 23:45:19 +09:00
- base_commit_hash: 98e0868
- release_tag: 2026.03XX-phase2.1.1-release-hygiene
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: explicit plan file for Phase2.1.1 release hygiene execution.
- Added: Node SSOT validator script design and CI integration path.
- Added: handoff-doc lint script design with metadata and control-char checks.
- Added: Notion manual exception gate script design for BLOCKED close criteria.
- Changed: `.nvmrc` policy from major-only to pinned patch baseline.
- Changed: workflow Node setup strategy to `node-version-file` only.
- Changed: runbook process from narrative to one-page operational flow.
- Fixed: handoff metadata standard to remove placeholders.
- Fixed: typo detection policy to enforce canonical `trace_id` naming.
- Removed: optional interpretation of PR-C; it is mandatory for release hygiene.

## 1) Core Mission
Provide implementation-ready context so ChatGPT can reason about execution details without direct repository browsing.

## 2) Completed Baseline (Before Phase2.1.1)
- PR1: Notion CI preflight fail-closed implemented.
- PR2: Async audit export (DB spool + job flow) implemented.
- PR3: Scheduler self-healing implemented.
- Key evidence is already available under `docs/review/mvp_verification_pack/artifacts/`.

## 3) Phase2.1.1 Execution Units
### PR-A
- Node 22.12.0 SSOT lock and fail-fast runtime checks.
- CI workflow alignment to `.nvmrc`.

### PR-B
- ChatGPT handoff doc linter.
- AGENTS 16.8 enforcement bridge to CI.
- ChatGPT handoff docs cleanup and metadata normalization.

### PR-C (MUST)
- Notion BLOCKED manual exception close gate.
- Fixed evidence triad enforcement.
- Runbook one-page close sequence.

## 4) Validation Gates and Evidence
| Gate | Result | Evidence |
|---|---|---|
| Backend test | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_backend_test_202603XX.txt |
| Frontend test | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_frontend_test_202603XX.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_frontend_build_202603XX.txt |
| Spec consistency | PASS (PASS=9 FAIL=0) | docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_spec_consistency_202603XX.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_utf8_check_202603XX.txt |
| Notion preflight | FAIL-CLOSED when auth missing | docs/review/mvp_verification_pack/artifacts/phase2_1_pr1_notion_auth_preflight_result_202603XX.json |

## 5) Manual Exception Gate (PR-C)
When Notion preflight fails:
1. Keep auto sync blocked.
2. Require the fixed evidence files:
   - `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json`
   - `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
   - `spec_sync_report.md` record
3. Pass `check_notion_manual_exception_gate.py` before operational close.

## 6) Immutable Constraints
1. ROLE taxonomy remains fixed.
2. Error payload schema remains fixed.
3. Hardening lock remains fixed.
4. Spec-Notion-sync DoD remains mandatory.

## 7) Source Priority
When information conflicts:
1. latest artifacts
2. `spec_sync_report.md`
3. reports/plans

## 8) Security Note for Documentation
- Do not place live secret/token examples in handoff docs.
- Use `<REDACTED>` markers for explanatory examples.
- Keep PII examples anonymized and non-production.
