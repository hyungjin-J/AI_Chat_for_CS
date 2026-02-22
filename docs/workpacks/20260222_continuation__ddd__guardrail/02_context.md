# Context

## Why
- Existing evidence indicated open risks for domain purity, backoffice ACL boundary, frontend extraction, and runtime drift.
- The continuation plan requires fail-closed automation gates before additional feature work.

## Alternatives Considered
1. Keep manual review only.
- Rejected because drift recurs without deterministic CI gating.
2. Introduce soft warnings first.
- Rejected because AGENTS mandates fail-closed behavior for critical contract gates.

## Source References
- `AGENTS.md`
- `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
- `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
- `scripts/contracts/workpack_agent_report_contract.json`

## Manual Hook Evidence
- `docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json`
