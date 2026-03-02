# e2e_smoke_failure_response

## Scope
- Goal: keep Go-Live gate fail-closed when operational E2E smoke fails.
- Entry points:
  - `scripts/run_ops_e2e_smoke.ps1`
  - `e2e/api_smoke/run_e2e_smoke.py`
- Evidence:
  - `docs/review/mvp_verification_pack/artifacts/e2e_smoke_report_YYYYMMDD.json`
  - `docs/review/mvp_verification_pack/artifacts/e2e_smoke_trace_samples_YYYYMMDD.txt`

## Trigger
- `e2e_smoke_report_*.json` has `status=FAIL`
- any scenario `S1..S6` fails
- smoke runner exits with non-zero code

## Detection Signals
- Missing SSE contract events: `token/citation/done`, `safe_response/error`
- `trace_id` mismatch across request, DB, or SSE payload
- raw PII pattern detected in stream/citation/log/DB masked field
- cross-tenant session read not blocked by `403` or `404`
- unauthorized admin access not blocked by `403`

## Immediate Actions
1. Freeze release promotion and keep fail-closed behavior enabled.
2. Open latest smoke artifacts and identify first failed stage.
3. Copy failing `trace_id` and inspect correlated logs/events before rerun.
4. Execute scenario-specific playbook:
   - `S2` -> `playbooks/sse_streaming_degradation.md`
   - `S3` -> `playbooks/pii_leak_suspected.md`
   - `S4/S5` -> `playbooks/trace_id_missing.md`
   - `S6` -> `playbooks/answer_contract_fail_spike.md`

## Verification Commands
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_ops_e2e_smoke.ps1 `
  -BaseUrl http://localhost:8080 `
  -TenantKey demo-tenant `
  -CrossTenantKey tenant-a
```

```powershell
python e2e/api_smoke/run_e2e_smoke.py `
  --base-url http://localhost:8080 `
  --tenant-key demo-tenant `
  --role AGENT
```

```powershell
python e2e/api_smoke/run_e2e_smoke.py `
  --base-url http://localhost:8080 `
  --tenant-key tenant-a `
  --auth-tenant-key demo-tenant `
  --role AGENT `
  --cross-tenant-key tenant-a
```

## Recovery Criteria
- Latest E2E report status is `PASS`
- All required scenarios `S1..S6` are `PASS`
- Trace sample file contains one end-to-end flow trace (`request -> search -> tool -> done/safe_response`)
- No raw PII string appears in artifacts/log excerpts

## Post-Incident Checklist
- Record incident owner, detection time, failing stage, and root cause.
- Link failing and recovery artifacts in verification pack.
- Add preventive action in gate/test if failure mode was not previously covered.
