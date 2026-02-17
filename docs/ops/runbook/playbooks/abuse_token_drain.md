# abuse_token_drain

## Scope
- ReqID: `SEC-004`, `API-007`, `OPS-003`, `SYS-004`, `PERF-001`
- ProgramID: `COM-BUDGET-GUARD-RULE`, `COM-RATE-LIMIT-RULE`, `OPS-METRIC-SUMMARY`, `OPS-TRACE-QUERY`, `OPS-BLOCK-UPSERT`, `OPS-AUDIT-LOG-QUERY`
- DB: `TB_TENANT_USAGE_DAILY`, `TB_TENANT_USAGE_MONTHLY`, `TB_TENANT_QUOTA`, `TB_GENERATION_LOG`, `TB_TOOL_CALL_LOG`, `TB_OPS_EVENT`

## Trigger
- `API-008-429-BUDGET` 급증
- 토큰/툴콜/세션 예산 소진 속도 비정상 증가
- 특정 계정/IP의 rapid-fire 요청 탐지

## Impact
- 정상 사용자 자원 고갈
- 비용 급증
- 서비스 품질 저하 및 차단 정책 남용 위험

## Immediate Actions (exact API calls)
1. 운영 지표에서 소진 패턴 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/metrics/summary?limit=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
2. 예산 초과 trace 조회
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/traces?page=0&size=100&keyword=API-008-429-BUDGET&from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
3. 공격 계정/IP 즉시 차단
```bash
curl -sS -X PUT "${API_BASE_URL}/v1/ops/blocks/${BLOCK_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"subject_type\":\"ip\",\"subject_value\":\"${SOURCE_IP}\",\"mode\":\"temporary\",\"ttl_seconds\":3600,\"reason\":\"${INCIDENT_ID}:token_drain\"}"
```
4. 조치 감사로그 조회
```bash
curl -sS -X GET "${API_BASE_URL}/v1/admin/audit-logs?from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z&page=0&size=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
5. 필요 시 상위 차단(영구) 반영
```bash
curl -sS -X PUT "${API_BASE_URL}/v1/ops/blocks/${BLOCK_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"subject_type\":\"ip\",\"subject_value\":\"${SOURCE_IP}\",\"mode\":\"permanent\",\"ttl_seconds\":0,\"reason\":\"${INCIDENT_ID}:repeat_abuse\"}"
```

## Verification
- 토큰 소진 속도와 429 발생률이 정상 범위로 복귀
- 우회 시도(계정/IP 변경 패턴) 감소
- 정상 사용자 트래픽의 오류율/지연이 회복

## Rollback
- 오탐 시 차단을 최소 TTL로 재업데이트하여 자동 해제 유도
```bash
curl -sS -X PUT "${API_BASE_URL}/v1/ops/blocks/${BLOCK_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"subject_type\":\"ip\",\"subject_value\":\"${SOURCE_IP}\",\"mode\":\"temporary\",\"ttl_seconds\":1,\"reason\":\"${INCIDENT_ID}:false_positive_release\"}"
```

## Audit requirements
- 차단 대상(`subject_type`, `subject_value`), 기간, 사유, 승인자 기록
- 예산 초과 지표(토큰/툴콜/세션/SSE 동시성)를 분리 저장
- 차단 전후 서비스 지표 변화 기록

## Do/Don't
### Do
- 차단은 단계적으로 적용하고 재평가 시간을 명시한다.
- `429`와 `Retry-After` 계약을 일관되게 유지한다.

### Don't
- UI 단 차단만 적용하고 서버 강제를 생략하지 않는다.
- 특정 테넌트 이슈를 전역 차단으로 과잉 확장하지 않는다.

