# Backoffice ACL Boundary Baseline

- Generated at (KST): 2026-02-22 20:10:00 +09:00
- Base ref: `97f7502...HEAD`
- Policy: ratchet (`No New Violations`)
- Machine baseline source: `docs/review/mvp_verification_pack/artifacts/backoffice_acl_boundary_baseline_violations.json`

## Active Baseline Violations
None (`0`).

## Historical Resolved Violations
| file | line | import | classification |
|---|---:|---|---|
| `backend/src/main/java/com/aichatbot/channels/backoffice/presentation/AdminRbacController.java` | 3 | `com.aichatbot.contexts.identity.rbac.infrastructure.RbacApprovalService` | `FORBIDDEN_INFRA_IMPORT` |
| `backend/src/main/java/com/aichatbot/channels/backoffice/presentation/AdminRbacController.java` | 4 | `com.aichatbot.contexts.identity.rbac.infrastructure.RbacChangeRequestRecord` | `FORBIDDEN_INFRA_IMPORT` |
| `backend/src/main/java/com/aichatbot/channels/backoffice/presentation/AdminOpsDashboardController.java` | 14 | `com.aichatbot.contexts.operations.infrastructure.OpsRepository` | `FORBIDDEN_INFRA_IMPORT` |
