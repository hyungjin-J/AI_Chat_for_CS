# Agent Manual 02 - Working Memory Contract

## Purpose
Force planning artifacts to exist before implementation.

## Required Files
- `docs/workpacks/YYYYMMDD_<topic>/01_plan.md`
- `docs/workpacks/YYYYMMDD_<topic>/02_context.md`
- `docs/workpacks/YYYYMMDD_<topic>/03_checklist.md`

## Trigger Patterns (Fail-Closed)
When any file matching below changes, a workpack set is mandatory:
- `backend/**`
- `frontend/**`
- `scripts/**`
- `.github/workflows/**`
- `AGENTS.md`
- `docs/architecture/**`
- `docs/agent_manual/**`
- `chatGPT/**`
- `docs/references/**`
- `docs/uiux/**`

## Mandatory Declaration
Each workpack set must explicitly contain:
- `승인 전에는 코드 변경 금지`

## Required Content
### 01_plan.md
- Objective, scope, non-scope
- Ordered execution steps with commands
- Risk and mitigation
- Rollback plan
- Verification commands

### 02_context.md
- Why this decision was made
- Alternatives considered
- Source references (local repo paths)
- Manual hook evidence path (at least one)
  - `docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json`
  - or equivalent `*manual_hook_output*.json`

### 03_checklist.md
- Checkbox process board
- Stop conditions and completion criteria

## Topic Naming Contract
- Required pattern:
  - `^20\d{6}_[a-z0-9]+(?:__[a-z0-9]+)*$`
- Example:
  - `20260222_billing__parity`
- Forbidden tokens:
  - `misc`, `etc`, `tmp`, `temp`, `update`, `fix`
- Scope binding:
  - Topic tokens must include at least one token extracted from changed files.
