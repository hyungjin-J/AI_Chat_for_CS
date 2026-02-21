# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- document_type: Implementation and Operations Handoff Guide
- updated_at_kst: 2026-02-22 00:33:01 +09:00
- base_commit_hash: 17d758d
- release_tag: 2026.03XX-phase2.1.1-release-hygiene
- branch: main
- pr_number: N/A (local working tree)

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: explicit preflight artifacts for git status and baseline patch.
- Added: node check wrapper for compatibility with gate/runbook wording.
- Added: stable artifact filenames for PR-A/PR-B/PR-C outputs.
- Added: manual close gate parameter alignment and one-page runbook checks.
- Changed: CI Node assertion invocation to wrapper script.
- Changed: doc lint artifact outputs to stable non-date names.
- Changed: handoff docs to point to final gate artifacts.
- Fixed: metadata refresh with real timestamp and commit hash.
- Fixed: AGENTS handoff minimum content requirement reinforcement.
- Removed: ambiguity in required evidence file naming.

## 1) Execution Units
### PR-A
- Node SSOT pin maintained at .nvmrc=22.12.0.
- CI/local fail-fast wired through scripts/check_node_version.py.

### PR-B
- scripts/lint_chatgpt_handoff_docs.py enforces metadata/control-char/typo/forbidden-literal policy.
- chatGPT handoff docs normalized and updated.
- AGENTS 16.8 handoff rules reinforced.

### PR-C (MUST)
- Notion BLOCKED manual close gate script enforced.
- Runbook one-page close flow aligned to CI checks.

## 2) Validation Gate
| Gate | Status | Evidence |
|---|---|---|
| Node SSOT | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prA_node_ssot_check.txt |
| Node runtime record | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prA_node_runtime.txt |
| check_all fail-fast | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prA_check_all_failfast.txt |
| ChatGPT doc lint | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_doc_lint.txt |
| ChatGPT doc lint JSON | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_doc_lint.json |
| ChatGPT UTF-8 | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_utf8.txt |
| ChatGPT PII/token scan | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_pii_token_scan.txt |
| Notion preflight artifact | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_preflight.json |
| Notion manual gate | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate.txt |
| Notion manual gate JSON | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate.json |
| Runbook one-page check | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_runbook_onepager_check.txt |
| Backend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_backend_test_output.txt |
| Frontend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_frontend_test_output.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_frontend_build_output.txt |
| Spec consistency | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_spec_consistency.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_utf8_check.txt |

## 3) Security Notes
- Never include live secret patterns in docs; use <REDACTED> only.
- Keep trace_id naming canonical; typo forms are rejected by lint.
- Keep C0 controls out of handoff docs (LF/CR only).

## 4) Source Priority
If conflicts appear:
1. latest artifacts
2. spec_sync_report.md
3. reports/plans
