# Plan

## Objective
- Implement continuation remediation gates (P0~P7) with fail-closed CI enforcement.

## Scope
- Contract gates: trigger consistency, domain purity ratchet, backoffice ACL ratchet, frontend import boundary, UTF-8 strict, scaffold smoke.
- Backend refactor for backoffice ACL.
- Frontend shared/widgets extraction and boundary enforcement.
- Node runtime bootstrap discipline and CI diagnostics.

## Non-scope
- Public API contract change (REST/SSE payload/route/method).
- ROLE taxonomy change.

## Ordered Steps
1. Add/extend scripts + contract JSON + unit tests for each gate.
2. Refactor backoffice imports to application facades.
3. Normalize UTF-16 artifacts into UTF-8 no BOM and add strict gate.
4. Wire gates into `pr-smoke-contract` and `release-nightly-full`.
5. Run backend/frontend tests and script unit tests.
6. Generate verification artifacts.

## Risk and Mitigation
- Risk: new strict topic naming breaks legacy workpack usage.
- Mitigation: enforce diff-aware topic binding so only current diff topic must comply.

## Rollback
- Revert new scripts/workflow steps and restore previous gate outputs if blocking regression appears.

## Verification
- `python -m unittest discover -s scripts/tests -p "test_*.py"`
- `cd backend && .\\gradlew.bat test --no-daemon`
- `cd frontend && npm ci && npm run test:run && npm run build`
