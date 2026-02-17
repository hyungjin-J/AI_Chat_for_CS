# sse_streaming_degradation

## Scope
- ReqID: `PERF-001`, `API-007`, `SYS-004`, `OPS-001`, `AI-009`
- ProgramID: `COM-SSE-EVENT-RULE`, `OPS-METRIC-SUMMARY`, `OPS-TRACE-QUERY`, `LLM-PROVIDER-HEALTH`, `OPS-PROVIDER-KILLSWITCH`, `OPS-ROLLBACK-TRIGGER`
- DB: `TB_STREAM_EVENT`, `TB_API_METRIC_HOURLY`, `TB_GENERATION_LOG`, `TB_OPS_EVENT`

## Trigger
- `P95 first-token > 2s`
- SSE 재연결/`Last-Event-ID` resume 실패율 증가
- `done` 이전 끊김, `error` 이벤트 급증

## Impact
- 사용자 체감 지연 증가
- 스트리밍 중단으로 상담 작업 단절
- SLA 위반 및 운영 비용 증가

## Immediate Actions (exact API calls)
1. 운영 지표 요약 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/metrics/summary?limit=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
2. 스트리밍 오류 trace 수집
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/traces?page=0&size=100&keyword=sse_resume_failed&from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
3. provider 상태 점검
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/llm/providers/health?verbose=true" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
4. 문제 provider kill-switch 활성화
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"enable\",\"reason\":\"${INCIDENT_ID}:sse_degradation\",\"effective_seconds\":1200}"
```
5. 과도한 출력/지연 유발 프롬프트가 원인이면 롤백
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"prompt\",\"target_id\":\"${PROMPT_ID}\",\"to_version\":\"${APPROVED_VERSION}\",\"reason\":\"${INCIDENT_ID}:sse_latency\"}"
```

## Verification
- `P95 first-token <= 2s`, `P95 E2E <= 15s` 회복
- resume 실패율 하락, `done` 이벤트 비율 정상화
- 계약 실패 시에도 `safe_response` 이벤트만 노출

## Rollback
- 안정화 후 kill-switch 해제
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"disable\",\"reason\":\"${INCIDENT_ID}:sse_recovered\",\"effective_seconds\":0}"
```

## Audit requirements
- first-token, resume failure, timeout 지표를 incident 로그에 시점별 기록
- kill-switch/rollbacks 실행 trace를 모두 저장
- 영향 테넌트와 채널을 분리 기록

## Do/Don't
### Do
- SSE 표준 이벤트(`token/tool/citation/done/error/heartbeat/safe_response`) 준수 여부를 함께 점검한다.
- 재연결 실패를 네트워크 문제로 단정하지 않고 provider/정책/버전을 함께 확인한다.

### Don't
- 지연을 숨기기 위해 완료 전 임의 종료를 정상 완료처럼 표시하지 않는다.
- 계약 실패 응답을 일반 token 스트림으로 바꾸지 않는다.

