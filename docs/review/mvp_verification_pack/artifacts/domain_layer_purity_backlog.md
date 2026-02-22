# Domain Layer Purity Backlog

- Baseline reference: `docs/review/mvp_verification_pack/artifacts/domain_layer_purity_baseline_violations.json`
- Policy: ratchet mode (`No New Violations`)
- Scope: `backend/src/main/java/com/aichatbot/contexts/**/domain/**/*.java`
- Latest baseline count: `6` (reduced from `12` in this continuation step)

## Remediation Strategy
1. Mapper result row types currently located in `infrastructure` will be moved to `domain`-owned DTO namespaces, then mapper signatures will be updated.
2. Domain services importing infrastructure repositories will be inverted to domain ports (`domain.port`) + infrastructure adapters.
3. Violations are removed context-by-context; after each removal baseline file is tightened in the same commit.

## Completed In This Step
- `backend/src/main/java/com/aichatbot/contexts/conversation/message/domain/mapper/MessageMapper.java`
  - Removed forbidden import of `message.infrastructure.MessageRow`.
  - `MessageRow` moved to `message.domain.readmodel`.
- `backend/src/main/java/com/aichatbot/contexts/conversation/message/domain/mapper/StreamEventMapper.java`
  - Removed forbidden import of `message.application.StreamEventView`.
  - `StreamEventView` moved to `message.domain.readmodel`.
- `backend/src/main/java/com/aichatbot/contexts/conversation/session/domain/mapper/ConversationMapper.java`
  - Removed forbidden import of `session.infrastructure.ConversationRow`.
  - `ConversationRow` moved to `session.domain.readmodel`.
- `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/TenantQuotaMapper.java`
  - Removed forbidden import of `billing.infrastructure.TenantQuotaRow`.
  - `TenantQuotaRow` moved to `billing.domain.readmodel`.
- `backend/src/main/java/com/aichatbot/contexts/identity/rbac/domain/mapper/RbacMatrixMapper.java`
  - Removed forbidden import of `identity.rbac.infrastructure.RbacMatrixEntry`.
  - `RbacMatrixEntry` moved to `identity.rbac.domain.readmodel`.
- `backend/src/main/java/com/aichatbot/contexts/knowledge/rag/domain/mapper/CitationMapper.java`
  - Removed forbidden import of `knowledge.rag.infrastructure.CitationRow`.
  - `CitationRow` moved to `knowledge.rag.domain.readmodel`.

## Violation Plan
| File | Current Import | Planned Refactor |
|---|---|---|
| `backend/src/main/java/com/aichatbot/contexts/billing/domain/service/CostCalculator.java` | `billing.infrastructure.RateCardRepository` | Introduce `RateCardPort` in domain, implement adapter in infrastructure. |
| `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/TenantUsageMonthlyMapper.java` | `billing.infrastructure.TenantMonthlyUsageRow` | Move row type to `billing.domain.readmodel`. |
| `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/TenantUsageDailyMapper.java` | `billing.infrastructure.TenantDailyUsageRow` | Move row type to `billing.domain.readmodel`. |
| `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/GenerationLogMapper.java` | `billing.infrastructure.GenerationLogRow` | Move row type to `billing.domain.readmodel`. |
| `backend/src/main/java/com/aichatbot/contexts/knowledge/rag/domain/mapper/KbSearchMapper.java` | `knowledge.rag.infrastructure.ChunkSearchRow` | Move row type to `knowledge.rag.domain.readmodel`. |
| `backend/src/main/java/com/aichatbot/contexts/identity/rbac/domain/mapper/RbacApprovalMapper.java` | `identity.rbac.infrastructure.RbacChangeRequestRecord` | Move DTO to `identity.rbac.domain.readmodel`. |
