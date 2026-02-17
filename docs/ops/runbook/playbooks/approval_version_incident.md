# approval_version_incident

## Scope
- ReqID: `ADM-007`, `OPS-003`, `SYS-004`, `API-007`, `AI-009`
- ProgramID: `OPS-AUDIT-LOG-QUERY`, `OPS-AUDIT-CHANGE-DIFF`, `OPS-ROLLBACK-TRIGGER`, `OPS-PROVIDER-KILLSWITCH`, `COM-RBAC-403-RULE`, `COM-IDEMPOTENCY-RULE`
- DB: `TB_AUDIT_LOG`, `TB_POLICY_VERSION`, `TB_PROMPT_VERSION`, `TB_KB_INDEX_VERSION`, `TB_OPS_EVENT`

## Trigger
- 승인되지 않은 policy/prompt/routing/KB 버전이 운영 반영됨
- canary 실패 후 자동 롤백 미작동
- 승인자/변경 이력 누락

## Impact
- 거버넌스 위반 및 컴플라이언스 리스크
- 정책 불일치로 응답 품질/안전성 저하
- 재발 시 운영 신뢰도 하락

## Immediate Actions (exact API calls)
1. 감사로그에서 비승인 변경 조회
```bash
curl -sS -X GET "${API_BASE_URL}/v1/admin/audit-logs?resource_type=policy&from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z&page=0&size=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
2. 변경 diff로 before/after 검증
```bash
curl -sS -X GET "${API_BASE_URL}/v1/admin/audit-logs/${AUDIT_ID}/diff" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
3. 승인 버전으로 즉시 롤백
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"policy\",\"target_id\":\"${TARGET_ID}\",\"to_version\":\"${APPROVED_VERSION}\",\"reason\":\"${INCIDENT_ID}:approval_gate_violation\"}"
```
4. 영향 범위가 불명확하면 provider kill-switch로 확산 차단
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"enable\",\"reason\":\"${INCIDENT_ID}:approval_incident_containment\",\"effective_seconds\":900}"
```

## Verification
- 운영 활성 버전이 승인 버전과 일치
- 감사로그에 승인자/실행자/결과가 모두 남음
- 계약 실패/오류율이 기준치로 회복

## Rollback
- 원복 검증 후 kill-switch 해제
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/llm/providers/${PROVIDER}/kill-switch" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"disable\",\"reason\":\"${INCIDENT_ID}:approval_recovered\",\"effective_seconds\":0}"
```

## Audit requirements
- 변경 요청자, 승인자, 배포자, 복구 실행자를 모두 기록
- `before/after` diff와 승인 증적(ticket/change request) 연결
- 재발 방지 액션(승인 게이트 보강, 자동 검증 룰) 등록

## Do/Don't
### Do
- 승인 체인(Preview -> Approval -> Canary -> Gradual Rollout)을 강제한다.
- 비승인 변경 발견 즉시 롤백하고 증적을 남긴다.

### Don't
- 긴급 대응을 이유로 비승인 상태를 운영 유지하지 않는다.
- 감사로그 누락 상태에서 인시던트를 종료하지 않는다.

