# pii_leak_suspected

## Scope
- ReqID: `SEC-004`, `OPS-003`, `SYS-004`, `AI-009`, `API-007`
- ProgramID: `OPS-TRACE-QUERY`, `OPS-BLOCK-UPSERT`, `OPS-PROVIDER-KILLSWITCH`, `OPS-ROLLBACK-TRIGGER`, `OPS-AUDIT-LOG-QUERY`, `COM-ANSWER-CONTRACT-RULE`
- DB: `TB_GUARDRAIL_EVENT`, `TB_OPS_EVENT`, `TB_AUDIT_LOG`, `TB_STREAM_EVENT`, `TB_GENERATION_LOG`

## Trigger
- PII 유출 신고 접수(고객/상담사/내부 모니터링)
- `SEC-003-409-PII` 또는 PII 관련 guardrail 이벤트 급증
- 마스킹되지 않은 값이 화면/로그/내보내기에 노출된 정황

## Impact
- 개인정보보호법/내부 보안정책 위반 가능성
- 법적/재무/신뢰도 리스크
- 즉시 차단 미실행 시 확산 가능

## Immediate Actions (exact API calls)
1. 유출 추정 trace 조회
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/traces?page=0&size=100&keyword=PII&from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
2. 즉시 계정/IP 차단
```bash
curl -sS -X PUT "${API_BASE_URL}/v1/ops/blocks/${BLOCK_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"subject_type\":\"account\",\"subject_value\":\"${ACCOUNT_ID}\",\"mode\":\"temporary\",\"ttl_seconds\":7200,\"reason\":\"${INCIDENT_ID}:pii_leak\"}"
```
3. 전면 확산 시 LLM Provider kill-switch 활성화
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"enable\",\"reason\":\"${INCIDENT_ID}:pii_containment\",\"effective_seconds\":1800}"
```
4. 유출 원인 정책/프롬프트를 승인 버전으로 롤백
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"prompt\",\"target_id\":\"${PROMPT_ID}\",\"to_version\":\"${APPROVED_VERSION}\",\"reason\":\"${INCIDENT_ID}:pii_rootcause\"}"
```
5. 조치 감사로그 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/admin/audit-logs?trace_id=${TRACE_ID}&page=0&size=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```

## Verification
- 신규 응답에서 PII 노출 없음, 필요 시 `safe_response`만 반환
- 동일 유형 trace 이벤트 재발 없음
- 차단/킬스위치/롤백이 모두 감사로그에 남음

## Rollback
- 오탐/완화 후 단계적으로 kill-switch 비활성화
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"disable\",\"reason\":\"${INCIDENT_ID}:pii_recovered\",\"effective_seconds\":0}"
```

## Audit requirements
- 유출 의심 시점, 탐지 채널, 최초 trace, 영향 범위(tenant/session/message) 기록
- 모든 API 호출별 `action_trace_id`와 결과 코드 기록
- 고객 통지 필요 여부 및 의사결정자를 incident 로그에 명시

## Do/Don't
### Do
- PII 의심 시 사실 확인 전이라도 선차단 후 분석한다.
- 내보내기/스크린샷/로그 공유본에서도 마스킹을 재검증한다.

### Don't
- 민감값 원문을 티켓/채팅/문서에 복붙하지 않는다.
- 계약 실패를 자유 텍스트로 우회해 정상 응답처럼 노출하지 않는다.

