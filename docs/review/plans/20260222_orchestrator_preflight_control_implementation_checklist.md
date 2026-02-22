# 20260222 Orchestrator Preflight Control Implementation Checklist

- baseline: existing dirty worktree snapshot required
- plan_source: `docs/review/plans/20260222_orchestrator_preflight_control_design_and_hardening_plan.md`
- declaration: 승인 전에는 코드 변경 금지

## Checklist

1. Preflight snapshot
- [ ] `git diff --name-only` captured
- [ ] control evidence file recorded

2. Manual hook bootstrap
- [ ] `scripts/agent/manual_hook.py` created
- [ ] `docs/agent_manual/01_preflight_and_baseline.md` created
- [ ] `docs/agent_manual/02_working_memory_contract.md` created
- [ ] `docs/agent_manual/03_pr_decomposition_and_agent_roles.md` created
- [ ] `docs/agent_manual/04_gates_notion_and_evidence.md` created
- [ ] hook run output captured

3. Working memory docs
- [ ] `docs/workpacks/20260222_orchestrator__preflight__control/01_plan.md`
- [ ] `docs/workpacks/20260222_orchestrator__preflight__control/02_context.md`
- [ ] `docs/workpacks/20260222_orchestrator__preflight__control/03_checklist.md`

4. 12.3 documents
- [ ] design and hardening plan exists
- [ ] implementation checklist exists

5. Gate execution
- [ ] backend test
- [ ] frontend test/build
- [ ] spec consistency
- [ ] utf8 strict
- [ ] handoff docs lint
- [ ] validation gate table lint
- [ ] notion manual exception gate

6. Evidence
- [ ] evidence files use `orchestrator_control_*` prefix
- [ ] pass/fail summary captured

