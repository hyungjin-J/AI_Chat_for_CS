# Workpack Context - 20260223_billing_spec_utf8_node22

## Technical Context

- Backend domain-layer purity gate previously tracked baseline debt in billing/rbac/rag.
- Spec consistency checks were documented as recommended but not fully automated in CI.
- UTF-8 full-scan baseline tracked 118 known violations and required ratchet-safe reduction.
- Local Windows Unicode workspace path can destabilize Node22 frontend dependency install.

## Evidence Inputs

- Domain gate artifacts under `docs/review/mvp_verification_pack/artifacts/`.
- UTF-8 baseline artifacts under `docs/review/mvp_verification_pack/artifacts/`.
- Existing manual-hook reference:
  - `docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json`

## Risk Notes

- MyBatis mapper scan can accidentally bind newly introduced interfaces.
- UTF-8 normalization must avoid semantic text mutation.
- Node runtime mismatch (Node24 vs Node22) can invalidate frontend reproducibility checks.
