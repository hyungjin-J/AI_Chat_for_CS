# 20260222 Orchestrator Preflight Control Design and Hardening Plan

- generated_at_kst: 2026-02-22
- scope: pre-code control orchestration
- gate: AGENTS.md 12.3 (pre-implementation mandatory)
- status: LOCKED BEFORE CODE CHANGES
- declaration: 승인 전에는 코드 변경 금지

## 1) Why
Current repository state includes broad in-progress changes. To prevent uncontrolled starts and gate bypass, this plan introduces a strict preflight control lane with fail-closed enforcement.

## 2) Scope
- Introduce `scripts/agent/manual_hook.py`.
- Bootstrap `docs/agent_manual` with required chapters.
- Create working memory pack under `docs/workpacks/20260222_orchestrator__preflight__control/`.
- Add 12.3-compatible implementation checklist for execution lock.
- Capture control evidence under fixed artifact naming.

## 3) Out of Scope
- Runtime business logic changes.
- Security hardening semantic changes.
- API contract changes.
- ROLE taxonomy / error payload schema changes.

## 4) Control Policy Locks
1. No implementation starts before successful hook execution.
2. Missing manual chapters force fail-closed exit.
3. Workpack 3-file contract is mandatory.
4. 12.3 pre-report documents are mandatory for this task.
5. Every PR DoD includes backend/frontend/spec/utf8/doc+Notion gates.
6. Evidence output path prefix is fixed:
   - `docs/review/mvp_verification_pack/artifacts/orchestrator_control_*`

## 5) PR Decomposition
### PR1
- Manual hook + agent manual bootstrap

### PR2
- Workpack memory docs + 12.3 hardening pre-report docs

### PR3
- Preflight execution contract and evidence capture wiring

## 6) Validation Plan
- Hook fail-closed behavior test (missing chapter)
- Hook pass behavior test (all chapters present)
- Required gates:
  - backend test
  - frontend test/build
  - spec consistency
  - utf8 strict
  - handoff/doc lint
  - notion manual exception gate

## 7) DoD
- Design plan exists before implementation.
- Workpack + 12.3 docs exist and include no-code-before-approval declaration.
- Hook and chapter loading process is executable and auditable.
- Mandatory gates complete with evidence files.

## 8) Rollback
- Revert by PR unit.
- Reverting this control lane does not require runtime rollback.

