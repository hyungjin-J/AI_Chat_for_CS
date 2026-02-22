# Orchestrator Preflight Control Checklist

- date_kst: 2026-02-22
- topic: orchestrator_preflight_control
- declaration: No code changes before approval

## Process Board
- [x] Preflight changed-files snapshot captured
- [x] `scripts/agent/manual_hook.py` exists and is executable
- [x] Manual hook run completed
- [x] Hook output chapters loaded and summarized
- [x] `docs/agent_manual` required 4 chapters present
- [x] Workpack files (`01_plan`, `02_context`, `03_checklist`) present
- [x] AGENTS 12.3 pre-report documents present
- [x] PR split defined (minimum 2 PRs)
- [x] Agent ownership assigned per PR
- [x] Backend test command executed
- [ ] Frontend build/test command executed
- [ ] Spec consistency command executed
- [x] UTF-8 strict check executed
- [ ] Document and Notion gate commands executed
- [x] Evidence files saved with `orchestrator_control_*` prefix

## Stop Conditions
- [x] Stop if hook status is `FAIL`
- [x] Stop if required manuals/workpacks are missing
- [x] Stop if Notion/doc gate violations exist

## Completion Criteria
- [ ] All mandatory gates are PASS
- [x] Evidence artifacts are present and readable
- [ ] Control process is handoff-ready

## 보안 셀프 체크 답변 (Security Self-check)

### 1) PII 차단(입력/로그/캐시/응답) 위반 가능성은 없는가?
- Answer: `Yes`
- Evidence:
  - Ops event dimensions now sanitized before persistence:
    - `backend/src/main/java/com/aichatbot/contexts/operations/application/OpsEventService.java:73`
    - `backend/src/main/java/com/aichatbot/contexts/operations/application/OpsDimensionsSanitizer.java`
  - Auth event payload uses hashed fields (`tenant_key_hash`, `ip_hash`, `login_id_hash`):
    - `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java:133`
    - `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java:175`
    - `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java:634`
  - Rate-limit cache/log context now hashed:
    - `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthRateLimitService.java:44`
    - `backend/src/main/java/com/aichatbot/contexts/identity/application/AuthRateLimitService.java:59`
  - Session response IP values are masked:
    - `backend/src/main/java/com/aichatbot/contexts/identity/presentation/AuthController.java:227`
    - `backend/src/main/java/com/aichatbot/platform/privacy/PiiMaskingService.java:12`

### 2) trace_id 전파가 전 구간 유지되는가?
- Answer: `Yes`
- Evidence:
  - Ingress enforcement and normalization:
    - `backend/src/main/java/com/aichatbot/platform/observability/TraceIdFilter.java:38`
    - `backend/src/main/java/com/aichatbot/platform/observability/TraceIdFilter.java:55`
  - Missing trace guard blocks with `SYS-004-409-TRACE`:
    - `backend/src/main/resources/application.properties:30`
    - `backend/src/main/java/com/aichatbot/platform/observability/TraceGuard.java:13`
  - Stream event repository rejects payloads without trace field:
    - `backend/src/main/java/com/aichatbot/contexts/conversation/message/infrastructure/StreamEventRepository.java:26`

### 3) 테넌트 격리(tenant_key 누락)가 없는가?
- Answer: `Yes`
- Evidence:
  - Tenant ingress gate still fail-closed:
    - `backend/src/main/java/com/aichatbot/platform/tenancy/TenantKeyFilter.java:43`
  - Cross-tenant probes now explicitly tenant-scoped (`tenant_id != #{tenantId}`):
    - `backend/src/main/resources/mappers/conversation/MessageMapper.xml:49`
    - `backend/src/main/resources/mappers/conversation/ConversationMapper.xml:48`
  - Token-hash auth session queries now tenant-scoped:
    - `backend/src/main/resources/mappers/identity/AuthMapper.xml:142`
    - `backend/src/main/resources/mappers/identity/AuthMapper.xml:151`
    - `backend/src/main/resources/mappers/identity/AuthMapper.xml:171`

### 4) RBAC/권한 검증은 서버가 최종 권위인가?
- Answer: `Yes`
- Evidence:
  - Header-role fallback is disabled by default:
    - `backend/src/main/resources/application.properties:28`
  - Server-side endpoint RBAC matrix remains enforced in security config:
    - `backend/src/main/java/com/aichatbot/contexts/identity/security/SecurityConfig.java:63`
    - `backend/src/main/java/com/aichatbot/contexts/identity/security/SecurityConfig.java:94`
  - Header-auth dependent tests now explicitly opt-in (`app.security.allow-header-auth=true`) and no longer rely on default:
    - `backend/src/test/java/com/aichatbot/contexts/identity/security/RbacTenantMatrixTest.java:28`
    - `backend/src/test/java/com/aichatbot/contexts/conversation/session/presentation/UuidAccessContractTest.java:23`

### 5) 실패 시 fail-closed/safe_response 경로가 자유 텍스트로 우회되지 않는가?
- Answer: `Yes`
- Evidence:
  - Contract validation and evidence/citation threshold gating remain strict:
    - `backend/src/main/java/com/aichatbot/contexts/conversation/answer/application/AnswerContractValidator.java:44`
    - `backend/src/main/java/com/aichatbot/contexts/conversation/message/application/MessageGenerationService.java:154`
    - `backend/src/main/java/com/aichatbot/contexts/conversation/message/application/MessageGenerationService.java:292`
  - LLM fallback still returns safe contract rather than free-text answer:
    - `backend/src/main/java/com/aichatbot/contexts/conversation/llm/application/LlmService.java:39`
    - `backend/src/main/java/com/aichatbot/contexts/conversation/llm/application/LlmService.java:60`

## PR Blocking Summary
- Blocked: `No`
- Blocking items: `None`

## Backend Verification Evidence
- `./gradlew test --no-daemon`: `docs/review/mvp_verification_pack/artifacts/orchestrator_control_backend_impl_test_output.txt`
- Added regression test:
  - `backend/src/test/java/com/aichatbot/contexts/operations/application/OpsDimensionsSanitizerTest.java`

## 재검증 명령
1. `cd backend && .\gradlew.bat test --no-daemon`
2. `rg -n "tenant_id != #\{tenantId\}|tenant_id = #\{tenantId\}\s+AND\s+session_token_hash" backend/src/main/resources/mappers`
3. `rg -n "tenant_key_hash|ip_hash|login_id_hash" backend/src/main/java/com/aichatbot/contexts/identity/application/AuthService.java`
4. `rg -n "allow-header-auth" backend/src/main/resources/application.properties`
5. `rg -n "OpsDimensionsSanitizer|sanitize\(" backend/src/main/java/com/aichatbot/contexts/operations/application`
