# AI_Chatbot OPS Runbook Index

## Purpose
This runbook set defines fail-closed operational responses for Go-Live incidents.

Non-negotiables:
- Keep Answer Contract fail-closed behavior.
- Keep PII redaction in logs, artifacts, and runbook evidence.
- Keep trace propagation (`X-Trace-Id`) and tenant/RBAC boundaries.
- Do not bypass hardening gates with ad-hoc free-text responses.

## Priority Playbooks
Use this order when multiple incidents occur at the same time.

| Priority | Playbook | Primary Trigger |
|---|---|---|
| P0 | [scheduler_lock_incident.md](./playbooks/scheduler_lock_incident.md) | Scheduler lock stuck, lock starvation, janitor recovery failures |
| P0 | [audit_chain_integrity_incident.md](./playbooks/audit_chain_integrity_incident.md) | Audit chain mismatch, chain sequence gaps, tamper suspicion |
| P1 | [trace_id_missing.md](./playbooks/trace_id_missing.md) | `trace_id` missing events |
| P1 | [pii_leak_suspected.md](./playbooks/pii_leak_suspected.md) | PII leakage suspicion |
| P1 | [answer_contract_fail_spike.md](./playbooks/answer_contract_fail_spike.md) | Contract validation failure spikes |
| P1 | [kb_index_failure_incident.md](./playbooks/kb_index_failure_incident.md) | KB document ingest/index retry/dead-letter spike |
| P1 | [e2e_smoke_failure_response.md](./playbooks/e2e_smoke_failure_response.md) | E2E smoke (`S1..S6`) failure in release gate |
| P2 | [llm_provider_outage.md](./playbooks/llm_provider_outage.md) | LLM provider outage/degradation |
| P2 | [rag_zero_evidence_spike.md](./playbooks/rag_zero_evidence_spike.md) | zero-evidence/citation failure spikes |
| P2 | [sse_streaming_degradation.md](./playbooks/sse_streaming_degradation.md) | SSE latency/disconnect spikes |
| P2 | [abuse_token_drain.md](./playbooks/abuse_token_drain.md) | budget/rate-limit abuse |
| P2 | [approval_version_incident.md](./playbooks/approval_version_incident.md) | invalid approval/version activation |

## Immediate Incident Baseline
1. Assign `incident_id` and Severity.
2. Capture `root_trace_id`.
3. Run containment action with new `action_trace_id`.
4. Store only masked evidence in artifacts.
5. Record rollback/restore decisions with owner and timestamp.

## Automation Hooks
- Audit chain read-only verifier:
  - `python scripts/verify_audit_chain_integrity.py --tenant-key <tenant_key> --from-utc <from_utc> --to-utc <to_utc>`
- Operational E2E smoke:
  - `powershell -ExecutionPolicy Bypass -File scripts/run_ops_e2e_smoke.ps1`
- SSE load/perf gate:
  - `powershell -ExecutionPolicy Bypass -File scripts/run_perf_sse_gate.ps1 -RequireDocker`
  - `python perf/assert_perf_gate.py --result perf/out/result.json --thresholds perf/thresholds.yaml`
  - If preflight fails, `perf/out/result.json` still exists with `PerfGateMeta.reason_code`.
- CI workflows store verifier artifacts and fail closed on integrity mismatch.

## Release Hygiene Gates
- Spec/Notion fail-closed flow (1-page):
  - [runbook_spec_notion_gate.md](../runbook_spec_notion_gate.md)
