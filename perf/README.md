# SSE Load Test Gate

This folder contains the reproducible SSE performance gate for go-live hygiene.

## Scope
- `perf/k6/sse_load_test.js`
  - SSE load scenario:
    - `first_token_ms` (TTFB proxy, because k6 JSON output is response-complete based)
    - `sse_done_success_rate`
    - `sse_error_rate`
    - `sse_safe_response_rate`
  - Rate-limit contract scenario:
    - `rate_limit_429_rate`
    - `rate_limit_headers_ok_rate`
    - `rate_limit_contract_ok_rate`
    - expected contract: status `429`, error code `API-008-429-SSE`, required policy headers
- `perf/assert_perf_gate.py`
  - Reads k6 JSON output and enforces thresholds with fail-closed exit code.
- `perf/thresholds.yaml`
  - Source-of-truth thresholds.

## Run
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_perf_sse_gate.ps1
```

Always-write contract:
- `perf/out/result.json` is generated on success/fail/skip paths.
- On preflight/runtime failure, `result.json` contains `PerfGateMeta` with:
  - `reason_code` (e.g., `K6_NOT_INSTALLED`, `DOCKER_UNAVAILABLE`, `TARGET_UNREACHABLE`)
  - `reason_detail`
  - `remediation_hint`
- Gate reports are written to:
  - `docs/review/mvp_verification_pack/artifacts/perf_sse_gate_YYYYMMDD.txt`
  - `docs/review/mvp_verification_pack/artifacts/perf_sse_gate_YYYYMMDD.json`
  - dashboard compatibility alias: `perf_sse_gate_YYYYMMDD_actual.json`
- `perf/assert_perf_gate.py` consumes that metadata and emits triage-friendly gate artifacts.

## Deterministic bootstrap order (Docker-capable env)
1. `docker compose down -v`
2. `docker compose up -d postgres redis`
3. `docker compose --profile db-tools run --rm flyway`
4. `docker compose --profile demo-stack up -d backend`
5. `backend /health == 200`
6. `k6 measurement start`

This sequence is enforced when running:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_perf_sse_gate.ps1 -BootstrapCompose -RequireDocker
```

## Deterministic 429 Probe Precondition
For consistent SSE concurrency rejection (`429`) in probe scenario, run backend with:
- `APP_BUDGET_SSE_CONCURRENCY_MAX_PER_USER=2` (or lower)
- `APP_BUDGET_SSE_HOLD_MS=2000` (or higher)

Without a hold window, streams may finish too quickly and reduce deterministic `429` detection.
