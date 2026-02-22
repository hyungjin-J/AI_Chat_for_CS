# Orchestrator Manual Chapter Summary

- status: PASS
- changed_files_count: 237

## 01_preflight_and_baseline.md
- Lock a reproducible baseline before any code implementation starts.
- 1. Collect changed targets first:
- - `git diff --name-only`

## 02_working_memory_contract.md
- Force planning artifacts to exist before implementation.
- - `docs/workpacks/YYYYMMDD_<topic>/01_plan.md`
- - `docs/workpacks/YYYYMMDD_<topic>/02_context.md`

## 03_pr_decomposition_and_agent_roles.md
- Split work into rollback-safe and ownership-clear units.
- - At least 2 PRs are required.
- - Preferred: 3 PRs (control plane, documentation, QA gate wiring).

## 04_gates_notion_and_evidence.md
- Ensure every control action leaves auditable evidence.
- - Backend:
- - `cd backend && .\gradlew.bat test --no-daemon`

