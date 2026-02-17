# llm_provider_outage

## Scope
- ReqID: `OPS-003`, `PERF-001`, `SYS-004`, `AI-009`, `API-007`
- ProgramID: `LLM-PROVIDER-HEALTH`, `OPS-PROVIDER-KILLSWITCH`, `OPS-METRIC-SUMMARY`, `OPS-TRACE-QUERY`, `OPS-ROLLBACK-TRIGGER`, `COM-ERROR-FORMAT`
- DB: `TB_GENERATION_LOG`, `TB_STREAM_EVENT`, `TB_OPS_EVENT`, `TB_AUDIT_LOG`, `TB_API_METRIC_HOURLY`

## Trigger
- `/v1/ops/llm/providers/health`에서 provider 상태 `down/degraded`
- 생성/스트리밍 5xx 급증, first-token 지연 급등
- 특정 provider 경로에서 timeout/connection 오류 폭증

## Impact
- 답변 생성 실패율 증가
- 응답 지연 증가로 SLA(P95) 위반
- safe_response 비율 급증

## Immediate Actions (exact API calls)
1. provider health 즉시 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/llm/providers/health?verbose=true" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
2. 장애 provider kill-switch 활성화
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"enable\",\"reason\":\"${INCIDENT_ID}:provider_outage\",\"effective_seconds\":1800}"
```
3. 영향 지표/trace 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/metrics/summary?limit=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/traces?page=0&size=100&keyword=${PROVIDER}&from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
4. 라우팅/프롬프트 변경이 원인인 경우 승인 버전 롤백
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"policy\",\"target_id\":\"${ROUTING_POLICY_ID}\",\"to_version\":\"${APPROVED_VERSION}\",\"reason\":\"${INCIDENT_ID}:provider_route_rollback\"}"
```

## Verification
- kill-switch 적용 후 해당 provider 경로 호출 중단
- 대체 경로에서 5xx/timeout 감소
- `P95 first-token <= 2s`, `P95 E2E <= 15s` 회복

## Rollback
- provider 복구 검증 후 kill-switch 해제
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"disable\",\"reason\":\"${INCIDENT_ID}:provider_recovered\",\"effective_seconds\":0}"
```

## Audit requirements
- provider 상태 스냅샷(장애 전/중/후) 저장
- kill-switch enable/disable의 실행자와 승인자 기록
- 롤백 발생 시 `target_type`, `target_id`, `to_version` 필수 기록

## Do/Don't
### Do
- 장애가 확인되면 지연 없이 kill-switch를 먼저 적용한다.
- fail-closed 규칙을 유지하고 안전 응답을 표준화한다.

### Don't
- provider 장애 중 자유 텍스트 우회로 응답 품질을 임의 보정하지 않는다.
- 승인되지 않은 임시 라우팅 설정을 운영에 반영하지 않는다.

