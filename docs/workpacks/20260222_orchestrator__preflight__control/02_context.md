# Orchestrator Preflight Control Context

- date_kst: 2026-02-22
- topic: orchestrator_preflight_control
- declaration: No code changes before approval

## Manual-based review baseline
Hook result (`docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json`) loaded:
- `docs/agent_manual/01_preflight_and_baseline.md`
- `docs/agent_manual/02_working_memory_contract.md`
- `docs/agent_manual/03_pr_decomposition_and_agent_roles.md`
- `docs/agent_manual/04_gates_notion_and_evidence.md`

DDD/security/db constraints were evaluated with:
- `AGENTS.md` section `6.1-A` through `6.1-D` (domain template, dependency rule, backoffice channel, naming policy)
- `AGENTS.md` section `6.8` (MyBatis boundary and `tenant_key` rule)
- `AGENTS.md` section `7.1` (frontend features structure as de facto mandatory)

## DDD review scorecard (current changes)
1. Domain-centered separation: `PARTIAL`
- Positive: package migration to `contexts/*`, `channels/backoffice`, `platform`, `sharedkernel` is largely in place.
- Evidence: `backend/src/main/java/com/aichatbot/contexts`, `backend/src/main/java/com/aichatbot/channels/backoffice`.
- Risk: cross-context direct imports remain and create hidden coupling.

2. Role clarity inside domain (`presentation/application/domain/infrastructure`): `PARTIAL`
- Positive: layer folders are present per context.
- Violations found:
  - `application -> presentation`: `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java:10`, `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java:11`
  - `domain -> infrastructure`: `backend/src/main/java/com/aichatbot/contexts/billing/domain/service/CostCalculator.java:5`
  - `infrastructure -> application`: `backend/src/main/java/com/aichatbot/contexts/conversation/message/infrastructure/MessageRepository.java:4`
  - `presentation -> infrastructure`: `backend/src/main/java/com/aichatbot/contexts/knowledge/rag/presentation/CitationController.java:7`

3. Ubiquitous Language and ambiguous naming control: `PARTIAL`
- Positive: most old `global/*` names were replaced by `platform/*` and `contexts/*`.
- Remaining ambiguous hubs:
  - `backend/src/main/java/com/aichatbot/sharedkernel/util`
  - `frontend/src/utils`
- Recommendation:
  - `sharedkernel/util/UuidParser` -> `sharedkernel/identity/UuidParser` or `sharedkernel/id/UuidParser`
  - `frontend/src/utils` -> `frontend/src/shared/lib` with explicit domain-neutral names

4. Pattern consistency and copyability: `GOOD with gaps`
- Positive:
  - backend scaffold exists: `scripts/scaffold_backend_context.py`
  - frontend scaffold exists: `scripts/scaffold_frontend_feature.py`
  - contract exists: `scripts/contracts/domain_template_contract.json`
- Gap:
  - mapper/resource consistency is incomplete for billing (`backend/src/main/resources/mappers` has no `billing` directory).
  - cross-layer imports still break template purity.

5. Context independence (fix bug within one context): `LOW-PARTIAL`
- Cross-context dependency edges detected:
  - `conversation -> knowledge` and `knowledge -> conversation` (bidirectional cycle)
  - `identity -> operations` and `operations -> identity` (bidirectional cycle)
  - `billing -> operations`
- Representative evidence:
  - `backend/src/main/java/com/aichatbot/contexts/conversation/message/application/MessageGenerationService.java:15`
  - `backend/src/main/java/com/aichatbot/contexts/knowledge/rag/application/RagAnswerService.java:3`
  - `backend/src/main/java/com/aichatbot/contexts/identity/security/SecurityConfig.java:7`
  - `backend/src/main/java/com/aichatbot/contexts/operations/audit/AuditLogService.java:6`

## Boundary invasion findings, alternatives, and PR split proposal
### Finding A: identity and operations are directly coupled in both directions
- Problem:
  - `identity` imports operations services for auth flow events.
  - `operations` imports identity principal classes.
- Evidence:
  - `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java:12`
  - `backend/src/main/java/com/aichatbot/contexts/operations/audit/AuditLogService.java:6`
- Alternative:
  - Introduce `sharedkernel` event/actor abstractions and context-local adapters.
  - Convert direct service calls to ACL interface (`identity` emits event, `operations` subscribes/handles).

### Finding B: conversation and knowledge are cyclic
- Problem:
  - `conversation` application depends on `knowledge` retrieval/application + infra classes.
  - `knowledge` application depends on `conversation` answer contract + llm classes.
- Evidence:
  - `backend/src/main/java/com/aichatbot/contexts/conversation/message/application/MessageGenerationService.java:18`
  - `backend/src/main/java/com/aichatbot/contexts/knowledge/rag/application/RagAnswerService.java:10`
- Alternative:
  - Move shared answer contract/validator to `sharedkernel` (or a dedicated kernel module).
  - Expose `KnowledgeQueryPort` and `AnswerComposePort` interfaces to remove direct context-to-context service imports.

### Finding C: layer inversion inside same context
- Problem:
  - application imports presentation DTO.
  - domain mapper imports infrastructure row types.
  - infrastructure repository imports application view types.
- Evidence:
  - `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java:10`
  - `backend/src/main/java/com/aichatbot/contexts/conversation/message/domain/mapper/MessageMapper.java:3`
  - `backend/src/main/java/com/aichatbot/contexts/conversation/message/infrastructure/MessageRepository.java:4`
- Alternative:
  - Keep DTO mapping in presentation adapter.
  - Introduce domain-owned persistence model (or infrastructure-owned mapper DTO package) without domain->infra dependency.
  - application should expose use case response models, not presentation DTOs.

### Proposed separate structure-change PRs
1. PR-Structure-1: Context ACL and cycle break
- target: identity<->operations, conversation<->knowledge decoupling
- non-goal: runtime behavior/security policy changes

2. PR-Structure-2: Layer purity cleanup
- target: remove application->presentation, domain->infrastructure, infrastructure->application imports
- add architecture tests for forbidden layer imports

3. PR-Structure-3: Mapper/resource contract completion
- target: billing mapper strategy normalization (MyBatis adoption or explicit non-MyBatis exception doc)
- ensure mapper location/namespace checks remain green

## Builder handoff rules (backend/frontend)
### Backend builder rules
1. Build strictly under `contexts/<context>/{presentation,application,domain,infrastructure}`.
2. Do not import another context implementation class directly.
- allowed: sharedkernel primitives/interfaces, ACL ports.
- forbidden: `contexts.<other>.application|infrastructure|presentation` direct imports.
3. Keep `platform` and `sharedkernel` domain-agnostic.
- no imports from `contexts/*` or `channels/*` into `platform/*` or `sharedkernel/*`.
4. Keep MyBatis boundary clear.
- mapper interface under domain mapper package.
- XML under `backend/src/main/resources/mappers/<context>/`.
- maintain `tenant_key` filter coverage.

### Frontend builder rules
1. Route layer stays thin.
- `frontend/src/pages/*` should only compose feature views.
2. New functionality must be created in `frontend/src/features/<context>/<feature>/`.
3. Avoid generic utility sinks.
- no new business logic in `frontend/src/utils`.
- use `frontend/src/shared/lib` for truly cross-feature helpers.
4. Preserve backoffice as channel, not business domain.
- admin orchestration UI goes to `features/backoffice/*`.

## References
- `AGENTS.md`
- `docs/agent_manual/01_preflight_and_baseline.md`
- `docs/agent_manual/02_working_memory_contract.md`
- `docs/agent_manual/03_pr_decomposition_and_agent_roles.md`
- `docs/agent_manual/04_gates_notion_and_evidence.md`
- `scripts/scaffold_backend_context.py`
- `scripts/scaffold_frontend_feature.py`
- `scripts/contracts/domain_template_contract.json`
- `scripts/assert_platform_boundary.py`

## Implementation Update (Backend Security/Operations Guard)
Applied remediation scope in this workpack execution:
1. PII/log/cache hardening for auth and ops dimensions.
- `backend/src/main/java/com/aichatbot/contexts/operations/application/OpsDimensionsSanitizer.java`
- `backend/src/main/java/com/aichatbot/contexts/operations/application/OpsEventService.java`
- `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java`
- `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthRateLimitService.java`
- `backend/src/main/java/com/aichatbot/platform/privacy/PiiMaskingService.java`
- `backend/src/main/java/com/aichatbot/contexts/identity/presentation/AuthController.java`

2. Tenant query scope hardening in mapper/repository contracts.
- `backend/src/main/resources/mappers/conversation/MessageMapper.xml`
- `backend/src/main/resources/mappers/conversation/ConversationMapper.xml`
- `backend/src/main/resources/mappers/identity/AuthMapper.xml`
- `backend/src/main/java/com/aichatbot/contexts/conversation/message/domain/mapper/MessageMapper.java`
- `backend/src/main/java/com/aichatbot/contexts/conversation/session/domain/mapper/ConversationMapper.java`
- `backend/src/main/java/com/aichatbot/contexts/identity/domain/mapper/AuthMapper.java`

3. RBAC default hardening.
- `backend/src/main/resources/application.properties` (`app.security.allow-header-auth=false` default)
- Header-auth dependent test classes were updated to explicit opt-in only.

4. Regression test added.
- `backend/src/test/java/com/aichatbot/contexts/operations/application/OpsDimensionsSanitizerTest.java`

5. Verification evidence.
- Backend gate output: `docs/review/mvp_verification_pack/artifacts/orchestrator_control_backend_impl_test_output.txt`
