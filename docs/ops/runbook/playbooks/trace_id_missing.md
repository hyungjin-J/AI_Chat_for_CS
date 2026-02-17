# trace_id_missing

## Scope
- ReqID: `SYS-004`, `OPS-001`, `OPS-003`, `API-007`
- ProgramID: `COM-TRACE-LOG-RULE`, `OPS-METRIC-SUMMARY`, `OPS-TRACE-QUERY`, `OPS-AUDIT-LOG-QUERY`, `OPS-AUDIT-CHANGE-DIFF`, `OPS-ROLLBACK-TRIGGER`
- DB: `TB_OPS_EVENT`, `TB_API_METRIC_HOURLY`, `TB_AUDIT_LOG`, `TB_STREAM_EVENT`

## Trigger
- `missing_trace_event_count > 0`
- `SYS-004-409-TRACE` 오류 급증
- `trace_id` 없는 API/SSE 로그 발견

## Impact
- 원인 추적 불가로 MTTR 상승
- 감사/컴플라이언스 위반 위험
- fail-closed 판정 근거 상실

## Immediate Actions (exact API calls)
1. 지표 요약으로 영향 범위 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/metrics/summary?limit=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
2. 누락 구간 추적 조회
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/traces?page=0&size=100&keyword=missing_trace&from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
3. 변경 이력 확인 (감사로그)
```bash
curl -sS -X GET "${API_BASE_URL}/v1/admin/audit-logs?from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z&page=0&size=50" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
4. 원인 변경건 diff 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/admin/audit-logs/${AUDIT_ID}/diff" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
5. 정책/프롬프트/KB 변경이 원인이면 즉시 롤백
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"policy\",\"target_id\":\"${TARGET_ID}\",\"to_version\":\"${APPROVED_VERSION}\",\"reason\":\"${INCIDENT_ID}:trace_id_missing\"}"
```

## Verification
- 신규 요청 응답/오류 JSON에 `trace_id`가 100% 포함된다.
- `/v1/ops/traces`에서 `missing_trace` 키워드 이벤트가 더 이상 증가하지 않는다.
- 감사로그에서 롤백/조치 이벤트와 `trace_id`가 연결된다.

## Rollback
- 오탐으로 판명된 경우, 검증된 승인 버전으로 재롤포워드한다.
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"policy\",\"target_id\":\"${TARGET_ID}\",\"to_version\":\"${PREVIOUS_APPROVED_VERSION}\",\"reason\":\"${INCIDENT_ID}:rollback_cancel\"}"
```

## Audit requirements
- `incident_id`, `root_trace_id`, `action_trace_id`, `audit_id`, `target_id`, `to_version` 기록
- `TB_AUDIT_LOG`에 조치/롤백 이벤트 존재 필수
- `TB_OPS_EVENT`에 심각도/컴포넌트/메시지 기록 필수

## Do/Don't
### Do
- 누락 이벤트 1건이라도 발견되면 배포 게이트를 즉시 잠근다.
- 모든 즉시조치 호출에 `X-Trace-Id`를 포함한다.

### Don't
- trace 누락을 자유 텍스트 설명으로 대체하고 운영 지속하지 않는다.
- 로그에 임의 trace 값을 덮어써서 상관관계를 위조하지 않는다.

