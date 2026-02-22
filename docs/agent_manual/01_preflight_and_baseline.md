# Agent Manual 01 - Preflight and Baseline

## Purpose
Lock a reproducible baseline before any code implementation starts.

## Required Actions
1. Collect changed targets first:
   - `git diff --name-only`
2. Save a baseline snapshot for later diff isolation:
   - changed files list
   - optional baseline patch
3. Run `scripts/agent/manual_hook.py` before coding.

## Fail-Closed Criteria
- If manual chapters are missing, stop immediately.
- If changed files cannot be collected, stop immediately.
- If hook status is `FAIL`, do not start implementation.

## Baseline Tracking Notes
- Existing dirty worktree must be treated as external baseline context.
- New work for this control lane should be trackable by dedicated evidence files.
- Evidence path prefix for this lane:
  - `docs/review/mvp_verification_pack/artifacts/orchestrator_control_*`

