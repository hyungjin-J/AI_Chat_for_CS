# Terminology SSOT Guide

## Purpose
`docs/review/mvp_verification_pack/TERMINOLOGY_SSOT.json` is the single source of truth for curated terminology checks used by `scripts/spec_consistency_check.py`.

This gate is curated-only. Do not add broad regex or arbitrary token scans.

## SSOT Schema
The JSON file must keep these top-level keys:
- `required_exact_tokens`
- `forbidden_variants`
- `required_headers`
- `sse_event_types`
- `error_payload_fields`

Current mapping to checks:
- `required_exact_tokens.secret_ref` -> `TERMINOLOGY_SECRET_REF_*`
- `error_payload_fields` + `forbidden_variants.error_payload` -> `TERMINOLOGY_ERROR_PAYLOAD_*`
- `sse_event_types` + `forbidden_variants.sse_event_types` -> `TERMINOLOGY_SSE_EVENT_*`
- `required_headers.required` / `required_headers.optional` -> `TERMINOLOGY_TRACE_TENANT_HEADER_*`
- `required_exact_tokens.snake_case_contract_fields` + `forbidden_variants.snake_case_contract_fields` -> `TERMINOLOGY_SNAKE_CASE_*`

## Change Approval Process
1. Propose the exact token/variant change in PR description with rationale.
2. Confirm the change is already approved in AGENTS.md or spec docs.
3. Get reviewer approval from at least:
   - spec owner (requirements/API workbook)
   - backend owner (contract compatibility)
4. Attach gate evidence from local run:
   - `python scripts/spec_consistency_check.py`

## PR Checklist
- [ ] Updated `TERMINOLOGY_SSOT.json` only for approved curated terms.
- [ ] Did not add arbitrary/non-curated token scans in code.
- [ ] `scripts/tests/test_spec_consistency_check.py` updated or still passing deterministically.
- [ ] `python scripts/spec_consistency_check.py` PASS/expected FAIL verified with evidence.
- [ ] No output contract change in `spec_consistency_check` txt/json reports.
