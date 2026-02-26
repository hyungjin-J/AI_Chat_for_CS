# Workpack Context - 20260226_domain__boundary__hardening__ops__rag__admin

## Technical Context

- Existing `domain_layer_boundary_gate` baseline is already `0`; this wave preserves that invariant.
- `operations/application`, `knowledge/rag/application`, and `knowledge/rag/presentation` had infrastructure import coupling risk.
- `channels/backoffice` previously allowed domain imports in documentation and contract; policy is now tightened to application-only imports.

## Evidence Inputs

- `docs/review/mvp_verification_pack/artifacts/domain_layer_boundary_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/backoffice_acl_boundary_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/application_port_boundary_gate.txt`
- Manual hook reference: `docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json`

## Risks

- MyBatis mapper scanning can bind interface ports accidentally; implementation beans must stay explicit and primary.
- Any reintroduced `.infrastructure.` import in targeted application/presentation packages must fail immediately.
- Any reintroduced `.domain.` import in backoffice must fail immediately.
