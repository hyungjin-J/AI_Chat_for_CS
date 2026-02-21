# CHATGPT SELF-CONTAINED BRIEFING (EN)

- updated_at_kst: 2026-02-22 00:32:43 +09:00
- base_commit_hash: 17d758d
- release_tag: 2026.03XX-phase2.1.1-release-hygiene
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: Node SSOT wrapper script for CI/local fail-fast checks.
- Added: PR-A evidence files without date suffix for stable handoff paths.
- Added: PR-B lint rules for token-like and key assignment literals.
- Added: PR-C manual exception close gate evidence paths.
- Changed: Node gate calls to use scripts/check_node_version.py.
- Changed: workflow lint output paths to stable artifact names.
- Changed: AGENTS 16.8 handoff minimum content lock.
- Fixed: chatGPT docs metadata and gate table to current run.
- Fixed: evidence naming consistency across plan and runbook.
- Removed: ambiguity around optional PR-C status (MUST close gate).

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
| PR-A Node SSOT check | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prA_node_ssot_check.txt |
| PR-A Node runtime record | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prA_node_runtime.txt |
| PR-A check_all fail-fast proof | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prA_check_all_failfast.txt |
| PR-B handoff doc lint | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_doc_lint.txt |
| PR-B lint detail JSON | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_doc_lint.json |
| PR-B UTF-8 check | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_utf8.txt |
| PR-B PII/token scan | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prB_chatgpt_pii_token_scan.txt |
| PR-C preflight snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_preflight.json |
| PR-C manual close gate | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate.txt |
| PR-C runbook one-page check | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_runbook_onepager_check.txt |
| Backend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_backend_test_output.txt |
| Frontend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_frontend_test_output.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_frontend_build_output.txt |
| Spec consistency | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_spec_consistency.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_1_utf8_check.txt |

## 4) Notion Manual Exception Evidence (Fixed Names)
- docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json
- docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md
- spec_sync_report.md session record

## 5) Open Risks Top5
1. Local runtime drift from pinned Node can still block developers until runtime is switched.
2. Manual close gate depends on complete evidence triad discipline.
3. Notion auth outages still block zero-touch sync path by design.
4. Windows file lock may intermittently affect package install speed/stability.
5. Artifact naming drift can reappear if future PRs bypass lint/runbook.

## 6) Conflict Resolution
If plan/report/evidence conflict, prioritize latest artifacts first, then spec_sync_report.md.
