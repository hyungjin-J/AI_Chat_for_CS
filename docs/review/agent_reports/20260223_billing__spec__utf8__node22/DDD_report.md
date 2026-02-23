# DDD Report - 20260223_billing_spec_utf8_node22

## Domain Boundary Changes

- Moved data row models from infrastructure to domain model packages:
  - billing usage/generation rows
  - rbac change request record
  - rag chunk search row
- Updated mapper XML `resultMap` targets to new domain model FQCNs.
- Introduced domain port abstraction `RateCardLookup` and wired `RateCardRepository` through it.

## Domain Purity Result

- Baseline before: 6
- Baseline after: 0
- Evidence:
  - `docs/review/mvp_verification_pack/artifacts/domain_layer_purity_baseline_violations.json`
  - `docs/review/mvp_verification_pack/artifacts/domain_layer_purity_burndown_summary.txt`
