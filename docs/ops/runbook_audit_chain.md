# Audit Chain Integrity Runbook

## 목적
tenant 범위 `tb_audit_log` hash chain의 무결성을 검증하고, 이상 탐지 시 export 제한 및 증거 보존 절차를 표준화한다.

## 검증 API
- `GET /v1/admin/audit-logs/chain-verify` (OPS)

## 기본 점검 호출
```bash
curl -sS -X GET "${API_BASE_URL}/v1/admin/audit-logs/chain-verify?from_utc=2026-03-01T00:00:00Z&to_utc=2026-03-01T23:59:59Z&limit=1000" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Trace-Id: ${TRACE_ID}" \
  -H "X-Tenant-Key: ${TENANT_KEY}"
```

핵심 응답 필드:
- `passed`
- `checked_rows`
- `failure_count`
- `failure_samples`

## 실패 시 즉시 조치
1. `passed=false`이면 대량 export를 즉시 제한한다.
2. `tb_ops_event`에서 `metric_key=audit_chain_verify_failed` 발생 여부를 확인한다.
3. 동일 tenant의 최근 변경 이벤트(trace_id, actor_user_id)를 추적한다.
4. 검증 범위를 24h에서 7d로 확장해 재검증한다.

## 증거 보존
incident 아티팩트에 아래를 포함한다.
- chain-verify API 요청/응답 원문
- 관련 `tb_audit_log` 샘플 레코드
- 관련 `tb_ops_event` 레코드
- 연관 작업 trace_id 목록

## 금지 사항
- `before_json`/`after_json` 원문 유출 금지
- sanitizer 우회 금지
- tenant 범위 검증 없는 export 금지

## 복구 완료 기준
- 동일 조건 재검증에서 `passed=true`
- `failure_count=0`
- export 재개 결정과 책임자 기록 완료
