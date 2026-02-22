# Backoffice ACL Boundary Audit

## Purpose
- Enforce channel boundary for `channels/backoffice`.
- Keep backoffice as orchestration layer only, not a domain-policy or infrastructure implementation layer.

## Rules
1. `channels/backoffice/**` may import:
- `contexts.*.application.*`
- `contexts.*.domain.*` (DTO/readonly model only)
- `platform.*`
- `sharedkernel.*`
2. `channels/backoffice/**` must not import:
- `contexts.*.infrastructure.*`
- `contexts.*.presentation.*`
3. Cross-context interaction must pass through application facades/ports.

## Current Baseline (Ratchet)
- Baseline file: `docs/review/mvp_verification_pack/artifacts/backoffice_acl_boundary_baseline.md`
- Gate script: `scripts/assert_backoffice_acl_boundary.py`
- Contract: `scripts/contracts/backoffice_acl_boundary_contract.json`
- Policy: no new violations are allowed; historical baseline must only decrease.

## Initial Remediation Applied
1. `AdminOpsDashboardController` no longer depends on `operations.infrastructure.OpsRepository`.
- Replaced with `operations.application.OpsDashboardQueryService`.
2. `AdminRbacController` no longer depends on `identity.rbac.infrastructure.*`.
- Replaced with `identity.rbac.application.RbacApprovalFacade`.

## Allowed vs Forbidden Examples
- Allowed:
  - `import com.aichatbot.contexts.operations.application.OpsDashboardQueryService;`
  - `import com.aichatbot.contexts.identity.rbac.application.RbacApprovalFacade;`
- Forbidden:
  - `import com.aichatbot.contexts.operations.infrastructure.OpsRepository;`
  - `import com.aichatbot.contexts.identity.rbac.infrastructure.RbacApprovalService;`
  - `import com.aichatbot.contexts.identity.presentation.AuthController;`
