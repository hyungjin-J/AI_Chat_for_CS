# 20260222 Production Continuation Gap Closing Plan
- target_file: `docs/review/plans/20260222_production_continuation_gap_closing_plan.md`
- generated_at_kst: 2026-02-22
- base_commit_hash: `97f7502`
- mode: plan-only (non-mutating revalidation)
- absolute_locks: AGENTS.md 준수, 보안/PII/Notion fail-closed 정책 완화 금지

## Summary
본 계획은 `DDD + 4대 작업효율 시스템(Manual Hook / Working Memory / Auto QA / Specialized Agents)`의 반영 상태를 증거 기반으로 재검증하고, 상용화 지속 가능성을 위한 Gap Closing을 PR-1~PR-3으로 결정완료 수준으로 설계한다.  
핵심 결론은 다음과 같다.
1. DDD 구조 자체(`contexts/platform/sharedkernel/channels/backoffice`)는 실코드에 반영됨.
2. 레거시 top-level 패키지(`com.aichatbot.auth` 등)는 소스 기준 제거됨.
3. 그러나 레이어 규칙/namespace drift/workpack-selfcheck-specialized report는 “문서 규칙 대비 CI 강제성 부족”이 핵심 갭임.
4. billing persistence는 여전히 in-memory 중심이며 MyBatis 표준(AGENTS 6.8)과 불일치.

## 1) 반영 여부 감사 (Evidence-based Audit)

| 영역 | 항목 | 판정 | 근거 파일 경로 | 판단 근거 |
|---|---|---|---|---|
| DDD | bounded context 구조(`contexts/platform/sharedkernel/backoffice`) 존재 | 있다 | `backend/src/main/java/com/aichatbot`, `backend/src/main/java/com/aichatbot/contexts`, `backend/src/main/java/com/aichatbot/platform`, `backend/src/main/java/com/aichatbot/sharedkernel`, `backend/src/main/java/com/aichatbot/channels/backoffice/presentation/AdminOpsDashboardController.java` | 실제 디렉터리/클래스 존재 |
| DDD | 레거시 패키지(`com.aichatbot.auth` 등) 잔존 | 없다(소스 기준) | `backend/src/main/java/com/aichatbot`, `backend/src/test/java/com/aichatbot` | 루트 하위가 `channels/contexts/platform/sharedkernel`로 정리되어 있음 |
| DDD | 도메인 내부 레이어 규칙(도메인→infra 역참조 금지) CI 강제 | 부분 | `AGENTS.md`(6.1-B), `scripts/assert_platform_boundary.py`, `.github/workflows/pr-smoke-contract.yml`, `backend/src/main/java/com/aichatbot/contexts/billing/domain/service/CostCalculator.java`, `backend/src/main/java/com/aichatbot/contexts/conversation/message/domain/mapper/MessageMapper.java` | 규칙 문서화는 되어 있으나 CI는 platform/sharedkernel 경계 위주, domain→infra 위반 코드 존재 |
| 4대 시스템-1 | manual hook 스크립트 존재 | 있다 | `scripts/agent/manual_hook.py`, `scripts/tests/test_manual_hook.py` | 스크립트 + 테스트 존재 |
| 4대 시스템-1 | `docs/agent_manual` 챕터 분리 + hook 출력 기반 최소 로딩 | 있다 | `docs/agent_manual/01_preflight_and_baseline.md`, `docs/agent_manual/02_working_memory_contract.md`, `docs/agent_manual/03_pr_decomposition_and_agent_roles.md`, `docs/agent_manual/04_gates_notion_and_evidence.md`, `docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json` | 4챕터 + hook output에 chapter summary 기록 |
| 4대 시스템-1 | hook 결과를 workpack/보고서에 기록하는 규칙 | 부분 | `docs/agent_manual/04_gates_notion_and_evidence.md`, `docs/review/mvp_verification_pack/artifacts/orchestrator_control_gate_summary.txt`, `docs/workpacks/20260222_orchestrator__preflight__control/02_context.md` | 규칙/샘플은 있으나 CI 강제 없음 |
| 4대 시스템-2 | Working Memory 3문서 표준(`01/02/03`) | 있다 | `docs/agent_manual/02_working_memory_contract.md`, `docs/workpacks/20260222_orchestrator__preflight__control/01_plan.md`, `docs/workpacks/20260222_orchestrator__preflight__control/02_context.md`, `docs/workpacks/20260222_orchestrator__preflight__control/03_checklist.md` | 표준 + 실사용 예시 존재 |
| 4대 시스템-2 | 어떤 변경에서 workpack 강제되는지 규칙/게이트 | 부분 | `AGENTS.md`(12.3), `docs/agent_manual/02_working_memory_contract.md`, `.github/workflows/pr-smoke-contract.yml` | 규칙은 있으나 CI에 workpack 존재 강제 step 없음 |
| 4대 시스템-3 | check_all/테스트/빌드/utf8/spec 일괄 실행 경로 | 부분 | `scripts/check_all.ps1`, `scripts/check_all.sh`, `.github/workflows/pr-smoke-contract.yml`, `.github/workflows/release-nightly-full.yml` | check_all은 테스트/빌드 중심, spec/utf8 one-path 강제 부재. spec은 CI에만 존재 |
| 4대 시스템-3 | self-check 질문(JSON)+checklist 기록 강제 | 부분 | `docs/workpacks/20260222_orchestrator__preflight__control/03_checklist.md`, `docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json` | checklist/JSON 샘플은 존재하나 self-check JSON 스키마/CI 게이트 없음 |
| 4대 시스템-3 | mapper namespace drift 검증(전체 XML 커버리지) | 없다 | `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`, `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`, `.github/workflows/pr-smoke-contract.yml`, `scripts` | handoff 문서에 “follow-up risk”로 남아 있고 전용 게이트 스크립트/CI step 부재 |
| 4대 시스템-4 | Specialized Agents 역할별 산출물 템플릿/경로 | 부분 | `docs/agent_manual/03_pr_decomposition_and_agent_roles.md`, `docs/workpacks/20260222_orchestrator__preflight__control/04_agent_prompts.md` | 역할 모델/프롬프트는 있으나 공용 템플릿 체계와 강제 게이트 없음 |
| 4대 시스템-4 | 최소 보고서(DDD/SEC/QA) 작성 규칙 | 부분 | `docs/workpacks/20260222_orchestrator__preflight__control/02_context.md`, `docs/workpacks/20260222_orchestrator__preflight__control/03_checklist.md` | 단일 workpack에는 존재하나 전사 표준 규칙/게이트로 고정되지 않음 |

## 2) 문서 SSOT 정합성 검사 (Mismatch + Fix)

| 불일치 항목 | 근거 파일 경로 | 수정안 |
|---|---|---|
| 아키텍처 문서의 “Current Structure Snapshot”이 구구조(`global/auth/admin/...`) 기준 | `docs/architecture/DDD_STRUCTURE_AUDIT_AND_REFACTOR_PLAN.md` | 2.x 섹션을 현행 구조(`channels/contexts/platform/sharedkernel`)로 교체하고, 존재하지 않는 경로 참조 제거 |
| 문서 규칙(레이어 금지)과 실코드 불일치가 방치됨 | `AGENTS.md`(6.1-B), `backend/src/main/java/com/aichatbot/contexts/billing/domain/service/CostCalculator.java`, `backend/src/main/java/com/aichatbot/contexts/conversation/message/domain/mapper/MessageMapper.java` | PR-1에서 “정책 선언 vs 현재 예외”를 명시하고 PR-3 이후 정리 일정/게이트를 AGENTS에 고정 |
| MyBatis 표준(AGENTS 6.8)과 billing in-memory 저장소 불일치 | `AGENTS.md`(6.8), `backend/src/main/java/com/aichatbot/contexts/billing/infrastructure/*.java` | PR-3에서 billing mapper-backed 전환 |
| mapper 리소스 폴더와 namespace context 불일치(`identity` 폴더에 platform mapper) | `backend/src/main/resources/mappers/identity/TenantResolverMapper.xml`, `backend/src/main/java/com/aichatbot/platform/tenancy/domain/mapper/TenantResolverMapper.java` | PR-2에서 `mappers/platform/TenantResolverMapper.xml`로 이동 + drift gate 추가 |
| workpack/manual/self-check가 “권고” 중심이고 CI fail-closed 강제 약함 | `AGENTS.md`(12.3/12.6), `docs/agent_manual/02_working_memory_contract.md`, `.github/workflows/pr-smoke-contract.yml` | PR-1에서 계약 스크립트 + CI 게이트 추가, AGENTS 문구를 강제 규칙으로 명확화 |

## 3) PR 설계 (최소 3개, Decision-complete)

## PR-1: AGENTS/문서 SSOT 최신화 + workpack/manual hook/agent report 규칙 고정
### 목표
문서-프로세스 SSOT를 현재 코드 구조와 일치시키고, workpack/manual hook/specialized report(DDD/SEC/QA)를 CI로 fail-closed 강제한다.

### 예상 변경 파일
1. `AGENTS.md`
2. `docs/architecture/DDD_STRUCTURE_AUDIT_AND_REFACTOR_PLAN.md`
3. `docs/architecture/HOW_TO_ADD_NEW_DOMAIN.md`
4. `docs/agent_manual/02_working_memory_contract.md`
5. `docs/agent_manual/03_pr_decomposition_and_agent_roles.md`
6. `docs/agent_manual/04_gates_notion_and_evidence.md`
7. `docs/review/templates/agent_reports/DDD_report_template.md` (신규)
8. `docs/review/templates/agent_reports/SEC_report_template.md` (신규)
9. `docs/review/templates/agent_reports/QA_report_template.md` (신규)
10. `scripts/assert_workpack_agent_report_contract.py` (신규)
11. `scripts/tests/test_assert_workpack_agent_report_contract.py` (신규)
12. `.github/workflows/pr-smoke-contract.yml`

### 구현 결정
1. 고위험 변경 감지 조건은 `AGENTS.md` 12.3 대상과 동일하게 고정한다.
2. 고위험 변경 PR에서 필수 파일을 강제한다.
3. 필수 파일은 `docs/workpacks/YYYYMMDD_<topic>/01_plan.md`, `02_context.md`, `03_checklist.md`, `docs/review/agent_reports/YYYYMMDD_<topic>/DDD_report.md`, `SEC_report.md`, `QA_report.md`.
4. `02_context.md`에 manual hook output 경로(`.../orchestrator_control_manual_hook_output.json` 또는 동등 산출물) 참조가 없으면 실패시킨다.
5. AGENTS 12.6의 one-command 최소 항목과 agent manual 04의 mandatory gate 목록을 동일 기준으로 정합화한다.

### DoD (필수 게이트/증적 파일명)
1. 계약 스크립트 단위테스트 PASS.
2. PR CI에서 계약 스크립트가 fail-closed 동작.
3. 증적 파일 생성: `docs/review/mvp_verification_pack/artifacts/phase2_2_1_workpack_agent_contract.txt`
4. 증적 파일 생성: `docs/review/mvp_verification_pack/artifacts/phase2_2_1_workpack_agent_contract.json`
5. 문서 lint/기존 게이트 PASS.

### 롤백 전략
1. PR-1 단독 revert.
2. CI false-positive 시 `scripts/contracts/workpack_agent_report_allowlist.json` 임시 예외 파일로 단기 완화하고 만료일을 강제한다.
3. 템플릿/문서 변경과 게이트 변경은 같은 PR에서만 롤백한다.

### 위험 요인 및 완화
1. 위험: 문서-only PR까지 과잉 차단.
2. 완화: 변경경로 매트릭스 기반으로 고위험 범위만 강제.
3. 위험: topic 명 규칙 충돌.
4. 완화: `orchestrator_preflight_control__<suffix>` 규칙을 스크립트 정규식으로 통일.

---

## PR-2: MyBatis namespace drift 정적 검증 게이트 + 테스트 + 증적
### 목표
`backend/src/main/resources/mappers/**/*.xml` 전수에 대해 namespace drift를 CI에서 차단한다.

### 예상 변경 파일
1. `scripts/assert_mapper_namespace_drift.py` (신규)
2. `scripts/tests/test_assert_mapper_namespace_drift.py` (신규)
3. `scripts/contracts/mapper_namespace_contract.json` (신규)
4. `backend/src/main/resources/mappers/platform/TenantResolverMapper.xml` (신규/이동)
5. `backend/src/main/resources/mappers/identity/TenantResolverMapper.xml` (삭제/이동)
6. `scripts/check_all.ps1`
7. `scripts/check_all.sh`
8. `.github/workflows/pr-smoke-contract.yml`
9. `.github/workflows/release-nightly-full.yml`
10. `docs/architecture/HOW_TO_ADD_NEW_DOMAIN.md`
11. `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
12. `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`

### 구현 결정
1. XML마다 namespace 필수.
2. namespace FQCN이 실제 mapper interface `.java` 파일과 1:1 일치해야 함.
3. 모든 mapper interface(`**/domain/**/mapper/*Mapper.java`)는 대응 XML이 있어야 함.
4. XML 폴더 컨텍스트(`conversation|identity|knowledge|operations|billing|platform`)와 namespace context가 일치해야 함.
5. duplicate namespace는 실패.
6. 리포트는 txt/json 동시 출력.
7. check_all과 PR/nightly CI 모두에서 실행한다.

### DoD (필수 게이트/증적 파일명)
1. `scripts/tests/test_assert_mapper_namespace_drift.py` PASS.
2. PR CI 게이트 PASS.
3. 증적 파일 생성: `docs/review/mvp_verification_pack/artifacts/phase2_2_2_mapper_namespace_drift.txt`
4. 증적 파일 생성: `docs/review/mvp_verification_pack/artifacts/phase2_2_2_mapper_namespace_drift.json`
5. 증적 파일 생성: `docs/review/mvp_verification_pack/artifacts/phase2_2_2_mapper_namespace_drift_unittest.txt`

### 롤백 전략
1. PR-2 단독 revert.
2. 경로 이동 실패 시 XML 파일을 원복하되 drift gate는 임시 allowlist로 제한 운용.
3. CI step는 revert 시 함께 원복한다.

### 위험 요인 및 완화
1. 위험: namespace 파싱 오검출.
2. 완화: XML parser 기반 구현 + fixture 단위테스트.
3. 위험: platform mapper 같은 비-context 케이스 누락.
4. 완화: contract 파일에 허용 context를 명시하고 테스트에 포함.

---

## PR-3: billing in-memory → mapper-backed persistence 확장 (계약/동작 불변) + 테스트
### 목표
billing 저장소를 MyBatis mapper 기반으로 전환하고 외부 API 계약과 동작을 유지한다.

### 예상 변경 파일
1. `backend/src/main/resources/db/migration/V9__billing_mapper_persistence.sql` (신규)
2. `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/TenantQuotaMapper.java` (신규)
3. `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/TenantPlanMapper.java` (신규)
4. `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/TenantSubscriptionMapper.java` (신규)
5. `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/TenantUsageDailyMapper.java` (신규)
6. `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/TenantUsageMonthlyMapper.java` (신규)
7. `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/GenerationLogMapper.java` (신규)
8. `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/RateCardMapper.java` (신규)
9. `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/BillingAuditLogMapper.java` (신규)
10. `backend/src/main/resources/mappers/billing/*.xml` (신규 다수)
11. `backend/src/main/java/com/aichatbot/contexts/billing/infrastructure/*.java` (기존 in-memory 구현을 mapper 호출형으로 교체)
12. `backend/src/main/resources/application.properties` (필요 시 `app.billing.persistence.mode` 추가)
13. `backend/src/test/java/com/aichatbot/contexts/billing/application/UsageRollupServiceIntegrationTest.java`
14. `backend/src/test/java/com/aichatbot/contexts/billing/presentation/TenantBillingRbacTest.java`
15. `backend/src/test/java/com/aichatbot/contexts/billing/presentation/BudgetEnforcementHttpTest.java`
16. `backend/src/test/java/com/aichatbot/contexts/billing/domain/service/CostCalculatorTest.java`
17. `backend/src/test/java/com/aichatbot/contexts/billing/infrastructure/BillingMapperPersistenceIntegrationTest.java` (신규)

### 구현 결정
1. 외부 API(`GET /v1/admin/tenants/{tenant_id}/usage-report`, `PUT /v1/admin/tenants/{tenant_id}/quota`)의 path/JSON/error_code는 변경하지 않는다.
2. 현재 런타임 계약 보존을 위해 billing 내부 식별자는 우선 `tenant_key` 문자열 기준으로 저장한다.
3. V9에서 billing 전용 테이블(`tb_tenant_quota`, `tb_tenant_plan`, `tb_tenant_subscription`, `tb_tenant_usage_daily`, `tb_tenant_usage_monthly`, `tb_generation_log`, `tb_cost_rate_card`, `tb_billing_audit_log`)을 생성한다.
4. 모든 쿼리에 `tenant_key` 조건을 강제한다.
5. repository `clear()`는 테스트 호환을 위해 유지하되 테스트 프로파일에서만 사용한다.
6. 롤백 민첩성을 위해 `app.billing.persistence.mode=memory|mybatis` 스위치를 제공한다. 기본값은 `mybatis`로 설정한다.
7. memory 구현은 즉시 삭제하지 않고 `memory` 모드 fallback으로 유지한다.
8. PR-3 완료 후 memory 모드는 운영 비상용으로만 문서화한다.

### DoD (필수 게이트/증적 파일명)
1. billing 관련 테스트 PASS(HTTP/RBAC/rollup/cost).
2. Flyway V9 적용 후 애플리케이션 기동 및 mapper scan PASS.
3. 증적 파일 생성: `docs/review/mvp_verification_pack/artifacts/phase2_2_3_billing_mapper_tests.txt`
4. 증적 파일 생성: `docs/review/mvp_verification_pack/artifacts/phase2_2_3_billing_http_regression.txt`
5. 증적 파일 생성: `docs/review/mvp_verification_pack/artifacts/phase2_2_3_billing_rollup_regression.txt`
6. 증적 파일 생성: `docs/review/mvp_verification_pack/artifacts/phase2_2_3_flyway_v9_apply.txt`
7. `${}` 사용 0건 유지, tenant_key 누락 쿼리 0건 리뷰 통과.

### 롤백 전략
1. 즉시 롤백: `APP_BILLING_PERSISTENCE_MODE=memory`.
2. 코드 롤백: PR-3 단독 revert.
3. DB 롤백: V9는 additive migration으로 설계하여 즉시 다운마이그레이션 없이도 코드 롤백 가능.
4. 장애 시 data consistency 우선순위: DB write 실패 시 fail-closed 에러로 종료하고 free-text 우회 금지.

### 위험 요인 및 완화
1. 위험: H2/Postgres SQL 차이로 테스트 실패.
2. 완화: V9 SQL을 H2 호환 문법으로 작성하고 통합테스트에 H2+Testcontainers(Postgres) 분리 검증.
3. 위험: memory/mybatis 모드 분기에서 동작 불일치.
4. 완화: 동일 시나리오를 두 모드로 회귀 테스트.
5. 위험: tenant_key/string 기반이 UUID 정책(6.9)과 긴장.
6. 완화: PR-3 범위를 “계약 불변 전환”으로 고정하고, UUID 정규화는 후속 PR에서 API/도메인 식별자 정리로 분리.

## 4) Public API / Interface / Type 영향
1. 외부 REST/SSE 계약 변경 없음.
2. 내부 인터페이스 추가.
3. 신규 스크립트 CLI 추가.
4. 신규 앱 설정 추가.
5. 신규 MyBatis mapper 인터페이스/SQL XML 추가.

## 5) 테스트 시나리오 (필수)
1. DDD 경계: platform/sharedkernel import 금지 + mapper namespace drift 전수검사.
2. Workpack/Agent report 강제: 고위험 변경 PR에서 누락 시 CI 실패.
3. Billing HTTP 회귀: 기존 상태코드/에러코드/trace_id 유지.
4. Billing rollup 회귀: 일별/월별 집계 수치 동일.
5. Billing quota/audit 회귀: upsert 후 감사로그 생성 동일.
6. Flyway/V9: clean DB에서 기동 가능.
7. Security 회귀: PII/trace_id/tenant scope 정책 유지.

## 6) 명시적 가정과 기본값
1. 기준일은 2026-02-22이며 본 문서 경로는 `docs/review/plans/20260222_production_continuation_gap_closing_plan.md`로 고정한다.
2. 현재 워크트리는 dirty 상태이므로 PR 단위로 증적 파일명을 명확히 분리한다.
3. PR merge 순서는 PR-1 → PR-2 → PR-3으로 고정한다.
4. Notion fail-closed 정책은 완화하지 않는다.
5. 본 문서는 계획 산출물이며 코드/문서 실제 수정은 일반 모드에서 수행한다.

## 7) Prompt B (일반 모드, 즉시 실행용)
```text
[MODE: PLAN MODE = OFF]
[ABSOLUTE: AGENTS.md 준수, 보안/PII/Notion fail-closed 정책 완화 금지]

작업 목표:
`docs/review/plans/20260222_production_continuation_gap_closing_plan.md`를 기준으로 PR-1, PR-2, PR-3을 순차 구현하라.
반드시 증거 기반으로 진행하고, 각 PR 완료 시 DoD 증적 파일을 생성하라.

고정 입력:
- AGENTS.md
- chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md
- chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md
- docs/architecture/*
- scripts/*
- .github/workflows/*

실행 순서:
1) 먼저 위 계획 문서를 정확한 본문으로 파일에 생성/갱신한다.
2) PR-1 구현:
   - AGENTS/architecture/agent_manual SSOT 정합화
   - workpack + agent report(DDD/SEC/QA) 계약 스크립트 + 테스트 + PR CI 연동
   - 증적:
     - docs/review/mvp_verification_pack/artifacts/phase2_2_1_workpack_agent_contract.txt
     - docs/review/mvp_verification_pack/artifacts/phase2_2_1_workpack_agent_contract.json
3) PR-2 구현:
   - mapper namespace drift 전수 게이트 스크립트 + 테스트
   - TenantResolverMapper XML 위치 정합화(mappers/platform)
   - check_all + PR/nightly workflow 연동
   - 증적:
     - docs/review/mvp_verification_pack/artifacts/phase2_2_2_mapper_namespace_drift.txt
     - docs/review/mvp_verification_pack/artifacts/phase2_2_2_mapper_namespace_drift.json
     - docs/review/mvp_verification_pack/artifacts/phase2_2_2_mapper_namespace_drift_unittest.txt
4) PR-3 구현:
   - billing in-memory 저장소를 mapper-backed로 전환(계약/동작 불변)
   - V9 migration 추가
   - 필요 시 app.billing.persistence.mode(memory|mybatis) 롤백 스위치 도입
   - billing 테스트 회귀 통과
   - 증적:
     - docs/review/mvp_verification_pack/artifacts/phase2_2_3_billing_mapper_tests.txt
     - docs/review/mvp_verification_pack/artifacts/phase2_2_3_billing_http_regression.txt
     - docs/review/mvp_verification_pack/artifacts/phase2_2_3_billing_rollup_regression.txt
     - docs/review/mvp_verification_pack/artifacts/phase2_2_3_flyway_v9_apply.txt
5) 각 PR마다 다음을 보고:
   - 변경 파일 목록
   - 실행한 명령과 핵심 결과
   - DoD 충족 여부
   - 롤백 방법
   - 잔여 리스크

주의:
- 기존 사용자 변경(더티 워크트리)을 임의로 되돌리지 마라.
- destructive git 명령 사용 금지.
- Notion/spec 관련 fail-closed 규칙은 유지한다.
- PII/secret/token은 어떤 산출물에도 평문으로 남기지 마라.
```
