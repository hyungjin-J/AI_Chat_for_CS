# Production Deploy Runbook (Compose SSOT)

## 1) Preflight
- Repository root: `C:\Users\hjjmj\OneDrive\바탕 화면\AI_Chatbot`
- Required tools:
  - Docker Engine + Docker Compose v2
  - Python 3.11+ (for gate scripts)
- Required files:
  - `.env` (copied from `.env.example` and filled with runtime values)
  - `infra/compose/production/docker-compose.prod.yml`

Run preflight gates:
```powershell
python scripts/validate_env_contract.py --env-example .env.example
```

SSE load/perf preflight:
- Ensure `k6` is installed and available on `PATH`.
- For deterministic SSE `429` probe behavior, run backend with:
  - `APP_BUDGET_SSE_CONCURRENCY_MAX_PER_USER=2` (or lower)
  - `APP_BUDGET_SSE_HOLD_MS=2000` (or higher)

## 2) Environment Contract
- Never commit plain secrets/tokens/keys.
- `.env.example` must keep `<REDACTED>` placeholders.
- External provider key is reference-only:
  - `LLM_PROVIDER_KEY_REF=secret://<REDACTED>`
- `X_TENANT_KEY` default must not exist in env files (tenant key is per-request header).

## 3) Deploy (One Command)
Baseline:
```powershell
docker compose -f infra/compose/production/docker-compose.prod.yml up -d
```

With optional search + local LLM:
```powershell
docker compose -f infra/compose/production/docker-compose.prod.yml --profile search --profile llm-local up -d
```

## 4) Health / Readiness / Liveness
- Application endpoints:
  - `GET /actuator/health`
  - `GET /actuator/health/liveness`
  - `GET /actuator/health/readiness`
- Spring graceful shutdown:
  - `server.shutdown=graceful`
  - `spring.lifecycle.timeout-per-shutdown-phase`
- SSE operational rules:
  - heartbeat event emitted when stream starts
  - timeout and completion handlers release concurrency guard resources
  - trace_id must remain present on stream flow

## 5) Logs / Trace Diagnostics
- Container status:
```powershell
docker compose -f infra/compose/production/docker-compose.prod.yml ps
```
- Backend logs:
```powershell
docker compose -f infra/compose/production/docker-compose.prod.yml logs -f backend
```
- Infra logs:
```powershell
docker compose -f infra/compose/production/docker-compose.prod.yml logs -f postgres redis
```

## 6) Stop / Rollback
Stop:
```powershell
docker compose -f infra/compose/production/docker-compose.prod.yml down
```

Rollback (same SSOT file, previous git tag/commit):
1. `git checkout <release_tag_or_commit>`
2. Ensure `.env` still matches contract.
3. Re-run:
```powershell
docker compose -f infra/compose/production/docker-compose.prod.yml up -d
```

## 7) Common Incident Pointers
- DB migration issue: [DB_BACKUP_RESTORE_RUNBOOK.md](../DB_BACKUP_RESTORE_RUNBOOK.md)
- Redis connectivity / lock symptoms: [scheduler_lock_incident.md](../runbook/playbooks/scheduler_lock_incident.md)
- Provider outage / key routing: [llm_provider_outage.md](../runbook/playbooks/llm_provider_outage.md)
- Audit integrity issue: [audit_chain_integrity_incident.md](../runbook/playbooks/audit_chain_integrity_incident.md)

## 8) SSE Load Gate
Run load test:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_perf_sse_gate.ps1 -RequireDocker
```

Run fail-closed gate:
```powershell
$dateTag = Get-Date -Format "yyyyMMdd"
$gateTxt = "docs/review/mvp_verification_pack/artifacts/perf_sse_gate_$dateTag.txt"
python perf/assert_perf_gate.py `
  --result perf/out/result.json `
  --thresholds perf/thresholds.yaml `
  --output-txt $gateTxt `
  --output-json "perf/out/gate_result.json"
```

Always-write guarantee:
- `perf/out/result.json` is always generated.
- If measurement cannot run, `result.json` contains `PerfGateMeta` failure metadata:
  - `reason_code`: `K6_NOT_INSTALLED`, `DOCKER_UNAVAILABLE`, `TARGET_UNREACHABLE`, `K6_EXECUTION_FAILED`, `RESULT_FILE_MISSING`
  - `reason_detail`
  - `remediation_hint`

## 9) CI Policy (Merge-block vs Monitoring-only)
- Merge-block (PR required checks): `.github/workflows/pr-smoke-contract.yml`
  - SSE perf load is excluded from PR required checks due runtime/cost and docker environment dependency.
- Monitoring-only (scheduled/manual): `.github/workflows/perf-sse-nightly.yml`
  - Runs on docker-capable Linux runner and performs real k6 SSE measurement.
  - Produces artifacts for triage even when measurement/preflight fails.
