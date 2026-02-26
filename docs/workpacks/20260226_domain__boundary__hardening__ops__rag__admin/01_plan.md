# Workpack Plan - 20260226_domain__boundary__hardening__ops__rag__admin

## Scope

- Add a new ratchet gate for application-layer port boundaries.
- Refactor `operations` and `knowledge/rag` application services to consume domain ports instead of infrastructure classes.
- Remove `channels/backoffice` domain imports and tighten ACL boundary policy to block `.domain.` imports.
- Keep all boundary baselines at `0` with fail-closed ratchet behavior.

## Constraints

- No REST/SSE public contract changes.
- No ROLE taxonomy or error payload shape changes.
- Domain boundary and backoffice ACL gates must remain `PASS` with `new_violation_count=0`.

## Acceptance

- `domain_layer_boundary_gate`: `PASS` with baseline `0`.
- `application_port_boundary_gate`: `PASS` with baseline `0`.
- `backoffice_acl_boundary_gate`: `PASS` with baseline `0` and `.domain.` enforcement.
- Backend test suite passes after refactoring.
