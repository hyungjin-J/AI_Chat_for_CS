# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- document_type: Implementation and Operations Handoff Guide
- updated_at_kst: 2026-02-22 13:32:18 +09:00
- base_commit_hash: c64905b
- release_tag: 2026.03XX-phase2.1.2-open-risks-burndown
- branch: main
- pr_number: N/A (local working tree)

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: `scripts/bootstrap_node_from_nvmrc.ps1` and `.sh` for runtime recovery based on `.nvmrc`.
- Added: optional frontend install retry helpers for Windows/macOS/Linux.
- Added: PR1 evidence outputs for bootstrap guidance and windows runbook presence.
- Changed: `scripts/check_node_version.py` now prints 1~5 recovery steps and bootstrap command.
- Changed: `scripts/check_all.ps1` node fail-fast message now includes direct bootstrap commands.
- Changed: `docs/dev/DEV_ENVIRONMENT.md` to use new bootstrap script names.
- Changed: `docs/ops/runbook_windows_node_npm_lock.md` with retry helper and WSL2 fallback.
- Fixed: cp949/utf-8 decode instability in `scripts/check_node_version.py` subprocess capture.
- Fixed: backward compatibility by keeping `bootstrap_node_22.*` as wrappers.
- Removed: hard dependency on manual trial-and-error for local Node mismatch recovery.

## 1) Execution Units
### Phase2.1.1 (baseline already completed)
- Release hygiene lock and fixed-path evidence adoption.
- ChatGPT handoff quality gate baseline.
- Notion manual close gate baseline.

### PR1: Dev Runtime Resilience (implemented)
- Node drift mitigation:
  - `scripts/bootstrap_node_from_nvmrc.ps1`
  - `scripts/bootstrap_node_from_nvmrc.sh`
  - `scripts/check_node_version.py` mismatch guidance (1~5 action steps)
- Windows npm lock mitigation:
  - `docs/ops/runbook_windows_node_npm_lock.md`
  - `scripts/frontend_install_retry.ps1`
  - `scripts/frontend_install_retry.sh`
  - Local/CI aligned npm install flags (`--prefer-offline --no-audit --fund=false`)

### PR2: Evidence/Docs Hardening (planned next in this session)
- Notion manual evidence template generator (plural command)
- Notion close gate diagnostics hardening
- ChatGPT lint evidence-existence JSON summary
- Notion export snapshot durability policy

## 2) Validation Gate
| Gate | Status | Evidence |
|---|---|---|
| Phase2.1.2 start status snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_git_status_start.txt |
| Phase2.1.2 baseline patch snapshot | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_baseline.patch |
| PR1 node bootstrap guidance | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_pr1_node_bootstrap_output.txt |
| PR1 windows runbook presence | PASS | docs/review/mvp_verification_pack/artifacts/phase2_1_2_pr1_windows_runbook_exists.txt |

## 3) Runbook and Script Additions
- `docs/dev/DEV_ENVIRONMENT.md`
- `docs/ops/runbook_windows_node_npm_lock.md`
- `scripts/bootstrap_node_from_nvmrc.ps1`
- `scripts/bootstrap_node_from_nvmrc.sh`
- `scripts/frontend_install_retry.ps1`
- `scripts/frontend_install_retry.sh`

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
2. Manual Notion close quality still depends on operator review before PR2 hardening lands.
3. Evidence existence checks are currently anchored to briefing Validation Gate rows.
4. Windows endpoint security policy can still cause intermittent npm file-lock behavior.
5. Node runtime mismatch still requires initial nvm setup on unmanaged developer machines.

## 7) Next PRs Top5
1. Add `scripts/gen_notion_manual_evidence_templates.py` and update runbook command references.
2. Enhance `scripts/check_notion_manual_exception_gate.py` with explicit spec token/pattern reporting.
3. Add `docs/notion_exports/README.md` and tie snapshot records to `spec_sync_report.md`.
4. Extend `scripts/lint_chatgpt_handoff_docs.py` JSON with evidence existence summary.
5. Regenerate full gate artifacts and refresh final handoff docs for PR2 completion.
