# answer_contract_fail_spike

## Scope
- ReqID: `AI-009`, `AI-005`, `OPS-001`, `PERF-001`, `API-007`, `SYS-004`
- ProgramID: `COM-ANSWER-CONTRACT-RULE`, `OPS-METRIC-SUMMARY`, `OPS-TRACE-QUERY`, `LLM-PROVIDER-HEALTH`, `OPS-ROLLBACK-TRIGGER`, `COM-SSE-EVENT-RULE`
- DB: `TB_GUARDRAIL_EVENT`, `TB_STREAM_EVENT`, `TB_RAG_CITATION`, `TB_GENERATION_LOG`, `TB_OPS_EVENT`

## Trigger
- `AI-009-CONTRACT_FAILED` 급증
- `AI-009-422-SCHEMA`, `AI-009-409-CITATION`, `AI-009-409-EVIDENCE` 비율 급상승
- `answer_contract_pass_rate` 급락

## Impact
- 사용자 응답 전송 차단 증가
- 상담 처리 지연 및 safe_response 비율 상승
- 근거 기반 답변 신뢰도 저하

## Immediate Actions (exact API calls)
1. 지표 요약에서 fail-closed 관련 지표 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/metrics/summary?limit=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
2. 계약 실패 trace 샘플 수집
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/traces?page=0&size=100&keyword=AI-009-CONTRACT_FAILED&from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
3. LLM provider 상태 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/llm/providers/health?verbose=true" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
4. 원인 버전(정책/프롬프트/KB) 롤백
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"prompt\",\"target_id\":\"${PROMPT_ID}\",\"to_version\":\"${APPROVED_VERSION}\",\"reason\":\"${INCIDENT_ID}:contract_fail_spike\"}"
```
5. 특정 provider 기인 시 kill-switch 활성화
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"enable\",\"reason\":\"${INCIDENT_ID}:provider_contract_error\",\"effective_seconds\":900}"
```

## Verification
- `AI-009-*` 실패 비율이 기준치 이하로 하락
- SSE 이벤트에서 `safe_response` 비중은 감소하고 `citation`/`done` 정상 비율 회복
- 자유 텍스트 fallback 노출 0건

## Rollback
- 상태 정상화 후 kill-switch 해제
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"disable\",\"reason\":\"${INCIDENT_ID}:contract_recovered\",\"effective_seconds\":0}"
```

## Audit requirements
- 실패 유형별 건수(스키마/인용/근거)와 영향 tenant를 분리 기록
- 롤백 대상/버전/사유/실행자 기록
- `TB_AUDIT_LOG`와 `TB_OPS_EVENT`에 동일 incident_id 연결

## Do/Don't
### Do
- 계약 실패는 기능 저하가 아니라 안전장치 동작으로 취급하고 원인을 즉시 제거한다.
- safe_response 노출 시 사용자 안내 문구를 표준 문구로 유지한다.

### Don't
- 계약 실패 상태에서 응답 품질을 이유로 자유 텍스트 우회를 허용하지 않는다.
- citation 누락 응답을 임시 허용하지 않는다.

