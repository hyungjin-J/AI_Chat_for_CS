# SEC Report - 20260226_domain__boundary__hardening__ops__rag__admin

## Security/Policy Invariants

- ROLE taxonomy unchanged: `AGENT/CUSTOMER/ADMIN/OPS/SYSTEM`.
- Error payload shape unchanged: `{error_code, message, trace_id, details}`.
- Fail-closed answer contract unchanged.
- Tenant/RBAC authority unchanged.

## ACL Tightening

- Backoffice ACL contract now explicitly forbids `.domain.` imports in addition to `.infrastructure.` and `.presentation.`.
- Classification `FORBIDDEN_DOMAIN_IMPORT` added to gate output for deterministic detection.
