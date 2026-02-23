# QA Report - 20260223_billing_spec_utf8_node22

## Validation Summary

- Scripts unit tests: PASS (`75` tests)
- Backend tests: PASS (`gradlew test`)
- Spec consistency check: PASS
- Spec sync report gate: PASS
- Domain boundary gate: PASS
- UTF-8 full-scan ratchet gate: PASS (`baseline=98`, `new=0`)
- Public API compare (reference artifact): PASS

## Frontend Repro

- Node22 + Unicode workspace `npm ci`: FAIL (`3221225477`, esbuild install)
- Node22 + ASCII workspace copy:
  - `npm ci`: PASS
  - `npm run test:run`: PASS
  - `npm run build`: PASS
- Evidence:
  - `docs/review/mvp_verification_pack/artifacts/node22_unicode_workspace_repro.txt`
  - `docs/review/mvp_verification_pack/artifacts/quality_workpack_validation_summary.txt`
