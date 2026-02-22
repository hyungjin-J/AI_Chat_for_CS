# Orchestrator Preflight Control Plan

- date_kst: 2026-02-22
- topic: orchestrator_preflight_control
- mode: pre-code control
- declaration: 승인 전에는 코드 변경 금지

## 1) Goal
Establish a fail-closed control sequence before any implementation work starts.

## 2) Scope
- Add manual hook script and agent manual chapters.
- Create workpack memory files.
- Create 12.3 hardening pre-report files.
- Execute required gates and collect evidence under fixed artifact paths.

## 3) Out of Scope
- Runtime feature behavior changes.
- Security policy/hardening semantic changes.
- API contract changes.

## 4) Ordered Steps
1. Preflight snapshot:
   - collect `git diff --name-only`
   - save changed-file evidence
2. Run manual hook:
   - `python scripts/agent/manual_hook.py --task "<request>" --changed-files "<files>"`
3. Load and summarize returned chapters from `docs/agent_manual`.
4. Confirm/create workpack files:
   - `01_plan.md`, `02_context.md`, `03_checklist.md`
5. Confirm/create AGENTS 12.3 pre-report documents in `docs/review/plans/`.
6. Run mandatory gates and persist evidence.

## 5) PR Breakdown and Agent Assignment
### PR1 - Manual Hook + Agent Manual Bootstrap
- owner: Control-Plane Agent
- scope:
  - `scripts/agent/manual_hook.py`
  - `docs/agent_manual/01_*.md` to `04_*.md`
  - `scripts/tests/test_manual_hook.py`
- DoD:
  - backend test
  - frontend build/test
  - spec consistency
  - utf8 strict
  - document and notion gates

### PR2 - Working Memory + 12.3 Pre-Report
- owner: Documentation Architect Agent
- scope:
  - `docs/workpacks/20260222_orchestrator_preflight_control/01_plan.md`
  - `docs/workpacks/20260222_orchestrator_preflight_control/02_context.md`
  - `docs/workpacks/20260222_orchestrator_preflight_control/03_checklist.md`
  - `docs/review/plans/20260222_orchestrator_preflight_control_design_and_hardening_plan.md`
  - `docs/review/plans/20260222_orchestrator_preflight_control_implementation_checklist.md`
- DoD:
  - backend test
  - frontend build/test
  - spec consistency
  - utf8 strict
  - document and notion gates

### PR3 - Execution Contract + Evidence Wiring
- owner: QA/Gate Agent
- scope:
  - preflight sequence documentation
  - gate evidence path contract using `orchestrator_control_*`
- DoD:
  - backend test
  - frontend build/test
  - spec consistency
  - utf8 strict
  - document and notion gates

## 6) Risks and Mitigation
- Risk: existing dirty worktree creates trace ambiguity.
  - Mitigation: fixed artifact prefix and explicit preflight snapshot.
- Risk: hook or manuals missing leads to bypass.
  - Mitigation: hook fail-closed with exit code `1`.
- Risk: docs-only process drifts from gates.
  - Mitigation: run actual gate commands and store outputs.

## 7) Rollback
- PR1 rollback: revert hook and manual files only.
- PR2 rollback: revert workpack and plan docs only.
- PR3 rollback: revert evidence wiring docs/scripts only.
- No runtime migration rollback required for this lane.

## 8) Verification Commands
- `cd backend && .\gradlew.bat test --no-daemon`
- `cd frontend && npm ci && npm run test:run && npm run build`
- `python scripts/spec_consistency_check.py`
- `python scripts/lint_chatgpt_handoff_docs.py --files chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
- `python scripts/lint_validation_gate_tables.py`
- `python scripts/check_notion_manual_exception_gate.py --manual-patch docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md --spec-sync spec_sync_report.md`
