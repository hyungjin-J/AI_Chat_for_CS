# Workpack Plan - 20260223_billing_spec_utf8_node22

## Scope

- Add automated spec consistency verification and CI wiring.
- Enforce `spec_sync_report.md` update gate when canonical specs change.
- Burn down domain-layer purity baseline violations.
- Burn down UTF-8 full-scan baseline violations without baseline growth.
- Improve local Node22 reproducibility under Unicode workspace paths.

## Constraints

- Preserve fail-closed answer contract and public REST/SSE semantics.
- Preserve RBAC and tenant isolation authority on server-side.
- Do not modify CSV/XLSX schema structures.
- Do not introduce API endpoint drift.

## Acceptance

- New scripts/tests pass.
- Domain baseline decreases.
- UTF-8 baseline decreases by at least 10.
- CI workflows include new gates.
