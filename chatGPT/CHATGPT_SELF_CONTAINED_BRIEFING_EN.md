# CHATGPT SELF-CONTAINED BRIEFING (EN)

- updated_at_kst: 2026-02-21 23:45:19 +09:00
- base_commit_hash: 98e0868
- release_tag: 2026.03XX-phase2.1.1-release-hygiene
- branch: main
- pr_number: N/A (local working tree)
- handoff_docs_location: chatGPT/

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: Node SSOT assertion plan for `.nvmrc` + package metadata + runtime fail-fast.
- Added: ChatGPT handoff doc lint policy and CI gate integration plan.
- Added: Notion BLOCKED manual exception close gate design (MUST).
- Added: Fixed evidence filenames for manual exception handling.
- Changed: Node version policy from loose major alignment to pinned baseline alignment.
- Changed: runbook flow to one-page operational close sequence for BLOCKED state.
- Changed: AGENTS 16.8 operational rules to include lint-driven enforcement.
- Fixed: metadata placeholder usage by requiring concrete `updated_at_kst`.
- Fixed: control-character and trace identifier typo risk via dedicated lint checks.
- Removed: optional status from PR-C; promoted to mandatory release gate.

## 1) Purpose
This file is a path-independent handoff brief for ChatGPT or any assistant that cannot inspect repository files directly.

## 2) Current Snapshot
- Project: AI_Chatbot
- Stage: Phase2.1 complete, moving to Phase2.1.1 release hygiene hardening.
- Main mission: keep production hardening locks intact while removing release-process risks.

## 3) Locked Constraints
1. ROLE taxonomy remains `AGENT/CUSTOMER/ADMIN/OPS/SYSTEM`.
2. `Manager/System Admin` are `ADMIN` internal permission levels only.
3. Error payload shape remains `error_code`, `message`, `trace_id`, `details`.
4. Hardening policy lock (cookie/CSRF/rotation/lockout/UTC bucket) must not be relaxed.
5. Spec file changes require Notion sync + metadata + `spec_sync_report.md`.

## 4) Phase2.1.1 Targets
1. Node 22.12.0 single source of truth across local and CI.
2. Handoff docs quality gate (metadata, control chars, typo, sensitive literal checks).
3. Notion BLOCKED manual exception close gate with mandatory evidence triad.

## 5) Validation Gate Summary
| Gate | Status | Evidence |
|---|---|---|
| Backend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_backend_test_202603XX.txt |
| Frontend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_frontend_test_202603XX.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_frontend_build_202603XX.txt |
| Spec consistency | PASS (PASS=9 FAIL=0) | docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_spec_consistency_202603XX.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_utf8_check_202603XX.txt |
| Notion automation | BLOCKED (Auth required) | docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_notion_sync_status_202603XX.txt |

## 6) Manual Exception Evidence (Fixed Names)
- Status file: `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json`
- Manual patch: `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
- Sync report record: `spec_sync_report.md`

## 7) Open Risks Top5
1. Notion MCP auth can still block zero-touch sync in some runtimes.
2. Async audit export remains DB spool based (object storage pending).
3. WebAuthn runtime remains deferred to Phase2.2.
4. Scheduler recovery alert routing can be further automated.
5. Local runtime drift from pinned Node can break reproducibility without strict checks.

## 8) Next Actions Top5
1. Merge PR-A Node SSOT enforcement.
2. Merge PR-B doc lint + ChatGPT handoff cleanup.
3. Merge PR-C manual exception close gate and runbook one-pager.
4. Regenerate evidence artifacts for Phase2.1.1 and attach to verification pack.
5. Refresh cumulative report after PR-A/B/C completion.

## 9) Conflict Resolution Rule
If plan/report/evidence conflict, prioritize:
1. latest `docs/review/mvp_verification_pack/artifacts/*`
2. `spec_sync_report.md`
3. release report and plan documents
