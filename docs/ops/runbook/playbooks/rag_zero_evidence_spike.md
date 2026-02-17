# rag_zero_evidence_spike

## Scope
- ReqID: `AI-005`, `AI-009`, `OPS-003`, `PERF-001`, `SYS-004`
- ProgramID: `OPS-METRIC-SUMMARY`, `OPS-TRACE-QUERY`, `KB-REINDEX-STATUS`, `OPS-ROLLBACK-TRIGGER`, `COM-ANSWER-CONTRACT-RULE`
- DB: `TB_RAG_SEARCH_LOG`, `TB_RAG_CITATION`, `TB_VECTOR_INDEX_STATUS`, `TB_GENERATION_LOG`, `TB_OPS_EVENT`

## Trigger
- `AI-009-409-EVIDENCE` 또는 `AI-009-409-CITATION` 급증
- citation 개수 0인 응답 비율 급상승
- RAG 검색 결과 대비 인용 결합 실패율 상승

## Impact
- 근거 기반 응답 불가로 fail-closed 증가
- 답변 전송 차단 및 상담 지연
- RAG 신뢰성 하락

## Immediate Actions (exact API calls)
1. 지표 요약으로 영향도 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/metrics/summary?limit=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
2. evidence/citation 실패 trace 수집
```bash
curl -sS -X GET "${API_BASE_URL}/v1/ops/traces?page=0&size=100&keyword=AI-009-409-EVIDENCE&from=2026-02-17T00:00:00Z&to=2026-02-17T23:59:59Z" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
3. 재색인 작업 상태 확인
```bash
curl -sS -X GET "${API_BASE_URL}/v1/admin/kb/reindex/${JOB_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```
4. 문제 index/KB 버전을 승인 버전으로 롤백
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"kb\",\"target_id\":\"${KB_ID}\",\"to_version\":\"${APPROVED_INDEX_VERSION}\",\"reason\":\"${INCIDENT_ID}:zero_evidence\"}"
```
5. 필요 시 프롬프트/정책 롤백 병행
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"prompt\",\"target_id\":\"${PROMPT_ID}\",\"to_version\":\"${APPROVED_VERSION}\",\"reason\":\"${INCIDENT_ID}:citation_repair\"}"
```

## Verification
- `AI-009-409-EVIDENCE`/`AI-009-409-CITATION` 비율 하락
- citation 포함 응답 비율 회복
- fail-closed는 유지하되 정상 응답 전환율 회복

## Rollback
- 오판정 시 직전 승인 버전으로 재롤백 수행
```bash
curl -sS -X POST "${API_BASE_URL}/v1/ops/rollbacks" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"target_type\":\"kb\",\"target_id\":\"${KB_ID}\",\"to_version\":\"${PREVIOUS_APPROVED_INDEX_VERSION}\",\"reason\":\"${INCIDENT_ID}:rollback_cancel\"}"
```

## Audit requirements
- `JOB_ID`, `KB_ID`, `index_version`, `trace_id`를 incident 타임라인에 기록
- 롤백 대상과 근거 지표(실패율, 영향 tenant)를 함께 저장
- 감사로그 diff로 변경 전/후 버전을 보존

## Do/Don't
### Do
- 근거 부족은 품질 이슈가 아니라 차단 조건으로 처리한다.
- 재색인 상태와 버전 상태를 동시에 확인한다.

### Don't
- citation 없이 응답을 임시 허용하지 않는다.
- evidence 실패를 모델 재시도로만 덮지 않는다.

