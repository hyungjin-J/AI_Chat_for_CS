# Tenant Cost Model & Quota Enforcement

## 1) 기준 스펙
- ReqID: `OPS-102`, `API-007`, `SEC-004`, `SYS-004`
- ProgramID:
  - `OPS-TENANT-BILLING-REPORT` (`GET /v1/admin/tenants/{tenant_id}/usage-report`)
  - `ADM-TENANT-QUOTA-UPSERT` (`PUT /v1/admin/tenants/{tenant_id}/quota`)
  - `COM-RATE-LIMIT-RULE`, `COM-BUDGET-GUARD-RULE`, `COM-TRACE-LOG-RULE`

## 2) 비용 구성요소
비용 계산은 `TB_GENERATION_LOG`의 사용량과 `TB_COST_RATE_CARD` 유효기간 요율을 조인해 산출한다.

- 입력 토큰 비용
  - `input_cost = (input_tokens / 1000) * input_token_cost_per_1k`
- 출력 토큰 비용
  - `output_cost = (output_tokens / 1000) * output_token_cost_per_1k`
- 툴 호출 비용
  - `tool_cost = tool_calls * tool_call_cost`
- 요청별 추정비용
  - `estimated_cost_per_request = input_cost + output_cost + tool_cost`

## 3) 롤업 규칙 (Daily / Monthly)
### Daily Rollup
- 대상 테이블: `TB_GENERATION_LOG -> TB_TENANT_USAGE_DAILY`
- 그룹키: `(tenant_id, usage_date)`
- 집계값:
  - `request_count`, `input_tokens`, `output_tokens`, `tool_calls`, `estimated_cost`
- 요율 조인: 요청 시각(`created_at`) 기준 `TB_COST_RATE_CARD.effective_from/effective_to` 매칭, 동시 매칭 시 최신 `effective_from` 우선

### Monthly Rollup
- 대상 테이블: `TB_TENANT_USAGE_DAILY -> TB_TENANT_USAGE_MONTHLY`
- 그룹키: `(tenant_id, usage_month)`
- 집계값:
  - 월간 `request_count`, `input_tokens`, `output_tokens`, `tool_calls`, `estimated_cost`

## 4) 데이터 소스 매핑
- `TB_GENERATION_LOG`: 원천 사용량(토큰/모델/Provider/trace_id), 프롬프트는 마스킹값만 저장
- `TB_TENANT_USAGE_DAILY`: 일별 롤업
- `TB_TENANT_USAGE_MONTHLY`: 월별 롤업
- `TB_COST_RATE_CARD`: 요율(유효기간)
- `TB_TENANT_QUOTA`: 테넌트 한도 및 breach 정책
- `TB_TENANT_PLAN`, `TB_TENANT_SUBSCRIPTION`: 플랜/구독 정보
- `TB_AUDIT_LOG`: quota 변경 감사로그(before/after diff, actor, trace_id)

## 5) 쿼터 정책
쿼터는 `TB_TENANT_QUOTA` 활성 레코드(시점 기준)를 사용한다.

- `max_daily_tokens`
- `max_monthly_cost`
- `max_qps`
- `breach_action`
  - `THROTTLE_429`: 일관된 `429` 반환
  - `BLOCK_403`: 정책 기반 `403` 반환

## 6) 초과 시 동작 (Hard Enforcement)
- 토큰/비용 초과 시 즉시 차단
- 표준 응답 헤더 강제:
  - `Retry-After`
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`
- 표준 에러 본문:
  - `error_code`, `message`, `trace_id`, `details`
- 예산 초과 코드:
  - `API-008-429-BUDGET` 또는 `API-008-403-BUDGET`

## 7) 감사/추적 규칙
- 모든 리포트/업데이트/롤업 기록에 `trace_id` 필수
- quota upsert는 `TB_AUDIT_LOG`에 아래 필드 저장
  - `actor_user_id`, `actor_role`, `trace_id`, `before_json`, `after_json`, `target_id`
- trace 누락 저장 금지 (`SYS-004`)

## 8) PII 정책
- 사용량/과금 로그는 PII 원문 저장 금지
- `TB_GENERATION_LOG.prompt` 계열 데이터는 마스킹값만 저장
- 리포트 응답도 집계 데이터만 노출(개별 고객 식별정보 제외)

## 9) 경보 임계치
- `usage >= 70%`: Warning
- `usage >= 85%`: Critical pre-breach
- `usage >= 100%`: Breach (즉시 정책 실행)
- 운영 메트릭:
  - `estimated_cost`
  - `quota_breach_count`
  - `token_budget_exceeded_count`

## 10) API 계약 요약
- `GET /v1/admin/tenants/{tenant_id}/usage-report`
  - 권한: `OPS`, `ADMIN` (서버 RBAC)
  - 응답: `daily`, `monthly`, `quota`, `trace_id`
- `PUT /v1/admin/tenants/{tenant_id}/quota`
  - 권한: `ADMIN`
  - 헤더: `Idempotency-Key` 필수
  - 감사로그: before/after diff + actor + trace_id 필수

