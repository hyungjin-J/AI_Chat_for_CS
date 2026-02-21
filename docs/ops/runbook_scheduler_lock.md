# Scheduler Lock 운영 Runbook

## 목적
`tb_scheduler_lock` 기반 분산락 장애(락 획득 실패, lease 만료, DB 오류) 시 안전하게 집계 작업을 복구한다.

## 대상 작업
- `ops_metric_hourly_aggregation`
- `data_retention_daily`
- `partition_prep_daily`

## 1) 증상
- 대시보드 수치가 갱신되지 않음
- 동일 작업이 다중 인스턴스에서 중복 실행됨
- 로그에 lock acquire 실패 반복

## 2) 즉시 점검 쿼리
```sql
SELECT lock_key, owner_id, lease_until_utc, fencing_token, updated_at
FROM tb_scheduler_lock
ORDER BY lock_key;
```

```sql
SELECT hour_bucket_utc, metric_key, metric_value, updated_at
FROM tb_api_metric_hourly
WHERE hour_bucket_utc >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '4 hours'
ORDER BY hour_bucket_utc DESC, metric_key ASC;
```

## 3) 장애 유형별 조치
### A. 락 획득 실패 반복
1. `lease_until_utc`가 현재 UTC보다 과거인지 확인
2. 과거인데도 갱신되지 않으면 앱 인스턴스 상태 점검
3. 인스턴스 1개만 남기고 재기동 후 재확인

### B. lease 만료 중 작업 중단
1. 해당 작업 trace_id 확인
2. `ops_metric_hourly_aggregation` 수동 재실행
3. `tb_api_metric_hourly` upsert 결과 중복/누락 확인

### C. DB 장애/연결 불가
1. DB 헬스 복구 전 스케줄러 자동재시도 유지
2. 복구 직후 `ops_metric_hourly_aggregation` 한 번 수동 실행
3. 최근 24h 구간 summary/series 비교 검증

## 4) 안전한 수동 집계 절차
1. 작업 시작 전 trace_id 발급
2. 단일 인스턴스에서만 집계 실행
3. 실행 후 요약 확인:
```sql
SELECT metric_key, SUM(metric_value) AS total
FROM tb_api_metric_hourly
WHERE hour_bucket_utc >= date_trunc('hour', NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
GROUP BY metric_key
ORDER BY metric_key;
```

## 5) 복구 완료 기준
- 락 테이블 갱신 시각이 최신으로 진행됨
- `dashboard/summary`, `dashboard/series` 응답이 정상
- 누락 구간 없이 시간 버킷(UTC) 연속성 유지

## 6) 사후 조치
- incident 기록에 root trace_id, 원인, 조치 시각 남김
- 반복 장애 시 `release-nightly-full`에 스케줄러 검증 스텝 강화
