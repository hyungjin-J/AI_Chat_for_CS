# 20260221 Auth/RBAC/Ops-Admin Implementation Checklist

- baseline_patch: `dirty_baseline.patch`
- policy_source: `docs/review/plans/20260221_auth_rbac_ops_admin_design_and_hardening_plan.md`

## Policy to Implementation Mapping

1. stale permission -> `401 AUTH_STALE_PERMISSION`
- backend: JWT validation + permission version check
- frontend: single refresh retry then login fallback
- tests: backend stale token + frontend retry loop guard
- status: pending

2. lockout -> `429 AUTH_LOCKED` + `Retry-After`
- backend: lockout service, response headers, audit events
- tests: lock threshold and unlock behavior
- status: pending

3. refresh CAS + reuse `409`
- backend: session token CAS update (consumed/revoked guard)
- backend: family revoke + audit
- tests: CAS row=1/row=0 paths
- status: pending

4. hourly metric UTC standard
- backend: scheduler + aggregation bucket in UTC
- tests: bucket correctness
- status: pending

5. rate-limit redis key + Retry-After
- backend: redis key schema and window-end calculation
- tests: 429 AUTH_RATE_LIMITED and header
- status: pending

6. dirty worktree baseline tracking
- docs: include baseline diff summary in final report
- status: completed

7. frontend anti-loop
- frontend: stale 401 refresh once only
- tests: stale repeated twice -> login
- status: pending

8. refresh reuse error code fixed
- backend: `AUTH_REFRESH_REUSE_DETECTED`
- tests: reuse scenario
- status: pending

9. hourly metric unique key + allowlist metric_key
- db: unique constraint `(tenant_id, hour_bucket_utc, metric_key)`
- backend: allowlist filter in aggregation
- tests: unknown key excluded
- status: pending

10. login priority `rate-limit -> lockout`
- backend: deterministic order
- tests: precedence assertions
- status: pending
