# IMPLEMENTATION GUIDE FOR CHATGPT

- project: AI_Chatbot
- document_type: Implementation and Operations Handoff Guide
- updated_at_kst: 2026-02-22 18:47:00 +09:00
- base_commit_hash: 97f7502
- release_tag: 2026.03XX-ddd-refactor-backend-security-guard-remediation
- branch: main
- pr_number: N/A (local working tree)

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: execution baseline plan `docs/review/plans/20260222_production_continuation_gap_closing_plan.md`.
- Added: workpack/agent-report fail-closed contract gate script + contract JSON + tests.
- Added: specialized report templates and concrete DDD/SEC/QA report directories.
- Changed: AGENTS now explicitly defines trigger patterns for mandatory workpack generation.
- Added: mapper namespace drift verifier script + contract JSON + unit tests.
- Changed: `TenantResolverMapper.xml` moved under `mappers/platform` to align path and namespace context.
- Added: legacy package blocker script + contract + tests + CI wiring.
- Added: billing persistence mode switch (`app.billing.persistence.mode`) defaulting to `mybatis`.
- Added: Flyway V9 billing tables + MyBatis mapper/XML layer + mapper-backed repositories.
- Added: Testcontainers integration test for billing persistence path (`disabledWithoutDocker=true`).

## 1) Execution Units
### Unit PR1: Architecture Template + Scaffold + Gates
- Files:
  - `docs/architecture/DDD_STRUCTURE_AUDIT_AND_REFACTOR_PLAN.md`
  - `docs/architecture/bounded_context_map.md`
  - `docs/architecture/HOW_TO_ADD_NEW_DOMAIN.md`
  - `docs/architecture/templates/backend_domain_template.md`
  - `docs/architecture/templates/frontend_feature_template.md`
  - `scripts/scaffold_backend_context.py`
  - `scripts/scaffold_frontend_feature.py`
  - `scripts/contracts/domain_template_contract.json`
  - `scripts/assert_platform_boundary.py`
  - `scripts/tests/test_assert_platform_boundary.py`
  - `scripts/tests/test_scaffold_templates.py`
  - `.github/workflows/pr-smoke-contract.yml`
- Goal:
  - Lock architecture template and reproducible scaffold flow.
  - Enforce platform/sharedkernel boundary via CI lint.

### Unit PR2: Backend Domain Structure Unification
- Files:
  - `backend/src/main/java/com/aichatbot/contexts/**`
  - `backend/src/main/java/com/aichatbot/platform/**`
  - `backend/src/main/java/com/aichatbot/sharedkernel/**`
  - `backend/src/main/java/com/aichatbot/channels/backoffice/**`
  - `backend/src/main/resources/mappers/{identity,conversation,knowledge,operations}/**`
- Goal:
  - Move legacy packages into bounded contexts without runtime behavior change.
  - Keep API contract and hardening semantics intact.

### Unit PR3: Frontend Feature Structure Unification
- Files:
  - `frontend/src/features/**`
  - `frontend/src/pages/*.tsx` (thin wrappers only)
  - `frontend/src/app/README.md`
  - `frontend/src/shared/README.md`
  - `frontend/src/widgets/README.md`
- Goal:
  - Keep routing thin and move feature logic into context-scoped feature modules.
  - Preserve current routes and UI behavior.

### Unit PR4: Backend Security and Tenant Guard Remediation
- Files:
  - `backend/src/main/java/com/aichatbot/contexts/operations/application/OpsDimensionsSanitizer.java`
  - `backend/src/main/java/com/aichatbot/contexts/operations/application/OpsEventService.java`
  - `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java`
  - `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthRateLimitService.java`
  - `backend/src/main/java/com/aichatbot/contexts/identity/presentation/AuthController.java`
  - `backend/src/main/java/com/aichatbot/platform/privacy/PiiMaskingService.java`
  - `backend/src/main/java/com/aichatbot/contexts/conversation/{session,message}/**`
  - `backend/src/main/java/com/aichatbot/contexts/identity/{domain/infrastructure}/**`
  - `backend/src/main/resources/mappers/{conversation,identity}/**`
  - `backend/src/test/java/com/aichatbot/contexts/operations/application/OpsDimensionsSanitizerTest.java`
  - Header-auth test property updates in RBAC-related test classes
- Goal:
  - Remove raw PII from ops dimensions/rate-limit keying and mask session IP outputs.
  - Enforce tenant-scoped lookup contracts on cross-tenant probe and token-hash session queries.
  - Keep RBAC server-authority defaults fail-closed (`allow-header-auth=false` baseline).

## 2) Validation Gate
| Gate | Status | Evidence |
|---|---|---|
| DDD refactor start status snapshot | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_git_status_start.txt |
| DDD refactor baseline patch snapshot | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_baseline.patch |
| Platform boundary lint | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_platform_boundary_lint.txt |
| Script regression unittest | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_unittest_output.txt |
| Backend tests | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_backend_test_output.txt |
| Backend build | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_backend_build_output.txt |
| Frontend tests | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_frontend_test_output.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_frontend_build_output.txt |
| Spec consistency | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_spec_consistency.txt |
| UTF-8 strict decode | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_utf8_check.txt |
| Public API compare (before/after) | PASS | docs/review/mvp_verification_pack/artifacts/ddd_refactor_public_api_compare.txt |
| Backend security remediation test | PASS | docs/review/mvp_verification_pack/artifacts/orchestrator_control_backend_impl_test_output.txt |
| Agent system PR1 contract lint | PASS | docs/review/mvp_verification_pack/artifacts/agent_system_pr1_lint_output.txt |
| Agent system PR1 UTF-8 check | PASS | docs/review/mvp_verification_pack/artifacts/agent_system_pr1_utf8_check.txt |
| Mapper namespace drift gate | PASS | docs/review/mvp_verification_pack/artifacts/mapper_namespace_gate.txt |
| Legacy package blocker | PASS | docs/review/mvp_verification_pack/artifacts/legacy_package_blocker.txt |
| Billing persistence integration test | PASS | docs/review/mvp_verification_pack/artifacts/billing_persistence_itest.txt |
| Backend regression tests (latest) | PASS | docs/review/mvp_verification_pack/artifacts/phase2_2_3_billing_mapper_tests.txt |
| Frontend tests | PASS | docs/review/mvp_verification_pack/artifacts/phase2_2_3_frontend_test.txt |
| Frontend build | PASS | docs/review/mvp_verification_pack/artifacts/phase2_2_3_frontend_build.txt |
| Spec consistency (latest) | PASS | docs/review/mvp_verification_pack/artifacts/phase2_2_3_spec_consistency.txt |
| UTF-8 strict decode (changed files) | PASS | docs/review/mvp_verification_pack/artifacts/phase2_2_3_utf8_check.txt |
| Public API compare (latest) | PASS | docs/review/mvp_verification_pack/artifacts/phase2_2_3_public_api_compare.txt |

## 3) Runbook and Script Additions
- `docs/architecture/HOW_TO_ADD_NEW_DOMAIN.md`
- `scripts/scaffold_backend_context.py`
- `scripts/scaffold_frontend_feature.py`
- `scripts/contracts/domain_template_contract.json`
- `scripts/assert_platform_boundary.py`
- `scripts/tests/test_assert_platform_boundary.py`
- `scripts/tests/test_scaffold_templates.py`

## 4) Security Notes
- ROLE taxonomy remains fixed: AGENT/CUSTOMER/ADMIN/OPS/SYSTEM.
- `admin_level` model retained; no new ROLE introduced.
- Standard error response remains `error_code`, `message`, `trace_id`, `details`.
- Cookie/CSRF/rotation/lockout/UTC hardening behavior remains unchanged.
- No real token/secret/PII literal is documented in artifacts.

## 5) Source Priority
If conflicts appear:
1. latest artifacts
2. spec_sync_report.md
3. reports/plans

## 6) Open Risks Top5
1. [CLOSED] Billing repositories are mapper-backed with rollout/rollback mode switch.
2. [CLOSED] Mapper namespace drift now has a dedicated static verification gate.
3. [OPEN] Backoffice channel separation still requires deeper ACL boundary audit.
4. [OPEN] Frontend shared/widget extraction is not yet complete across all features.
5. [OPEN] Local Node runtime mismatch remains possible without bootstrap workflow adherence.

## 7) Next PRs Top5
1. Add domain-layer reverse reference detector (`domain -> infrastructure/application/presentation`) as CI gate.
2. Add workpack/report gate extension to bind changed-file scope and topic naming more strictly.
3. Expand billing parity regression suite for `memory` and `mybatis` mode equivalence.
4. Consolidate frontend shared API client/state helpers into `frontend/src/shared`.
5. Add scaffold smoke CI to auto-generate and verify template contract per run.
