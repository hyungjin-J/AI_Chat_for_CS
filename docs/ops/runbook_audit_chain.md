# Audit Chain 운영 Runbook

## 목적
tenant 단위 `tb_audit_log` hash chain 위변조 의심을 조기 탐지하고, export/감사 리스크를 통제한다.

## 검증 API
- `GET /v1/admin/audit-logs/chain-verify` (OPS)

## 1) 기본 점검 절차
```bash
curl -sS -X GET "${API_BASE_URL}/v1/admin/audit-logs/chain-verify?from_utc=2026-03-01T00:00:00Z&to_utc=2026-03-01T23:59:59Z&limit=1000" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```

응답 핵심:
- `passed`
- `checked_rows`
- `failure_count`
- `failure_samples`

## 2) 실패 탐지 시 즉시 조치
1. `passed=false`면 export 요청을 임시 제한
2. `tb_ops_event`에서 `metric_key=audit_chain_verify_failed` 확인
3. 동일 tenant의 최근 변경 이벤트(trace_id, actor_user_id) 추적
4. 수동 검증 범위를 확장(24h -> 7d)

## 3) 증거 보존
- 다음 항목을 incident 아티팩트로 저장:
  - chain-verify API 원문 응답
  - 관련 `tb_audit_log` 샘플 행
  - 연관 `tb_ops_event` 행
  - 대응 작업 trace_id 목록

## 4) 금지 사항
- `before_json`/`after_json` 원문 재가공 저장 금지
- sanitizer 우회 저장 금지
- tenant 범위 없이 대량 export 금지

## 5) 복구 완료 기준
- 동일 조건 재검증에서 `passed=true`
- `failure_count=0`
- export 재개 승인(OPS 책임자 기록)
