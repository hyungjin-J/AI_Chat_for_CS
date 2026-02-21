# Scheduler Lock Runbook (Self-Healing)

## 목적
`tb_scheduler_lock` 기반 분산락에서 stuck lock을 자동 감지/회복하고, 자동 회복 실패 시 수동 복구 절차로 안전하게 전환한다.

## 대상 Job Lock Key
- `ops_metric_hourly_aggregation`
- `billing_rollup_daily`
- `billing_rollup_monthly`
- `data_retention_daily`
- `partition_prep_daily`

## 감지 신호
1. 대시보드 지표가 정해진 주기보다 오래 갱신되지 않는다.
2. 동일 lock key에서 `skipped` 이벤트가 반복된다.
3. `scheduler_lock_event`에서 `self_healing_failed`가 반복된다.

## 자동 회복 정책
1. Janitor 실행 주기: 기본 `30 * * * * *` (UTC)
2. stale 조건:
   - `lease_until_utc <= now_utc` 또는
   - `last_heartbeat_utc <= now_utc - 5m`
3. Janitor 동작:
   - `forceRecoverStaleLock(lock_key)` 호출
   - 성공: `self_healing_recovered`
   - 실패: `self_healing_failed`
4. 모든 이벤트는 trace_id와 함께 운영 로그/메트릭으로 기록한다.

## 운영 확인 SQL
```sql
SELECT lock_key,
       owner_id,
       lease_until_utc,
       last_heartbeat_utc,
       last_recovered_at,
       recovery_count,
       updated_at
FROM tb_scheduler_lock
ORDER BY lock_key;
```

```sql
SELECT hour_bucket_utc, metric_key, metric_value, updated_at
FROM tb_api_metric_hourly
WHERE hour_bucket_utc >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '4 hours'
ORDER BY hour_bucket_utc DESC, metric_key;
```

## 자동 회복 실패 시 수동 조치
1. 영향 lock key를 식별한다.
2. 해당 Job 인스턴스 로그에서 최근 trace_id를 확인한다.
3. 비정상 인스턴스를 격리/재시작한다.
4. 필요 시 수동 집계를 1회 수행한다.
5. 집계 중복/누락을 SQL로 검증한다.

## 수동 집계 검증
```sql
SELECT metric_key, SUM(metric_value) AS total
FROM tb_api_metric_hourly
WHERE hour_bucket_utc >= date_trunc('hour', NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
GROUP BY metric_key
ORDER BY metric_key;
```

## 완료 기준
- lock 상태가 정상으로 회복되고(`lease_until_utc`가 미래 시각),
- `tb_api_metric_hourly` UTC 버킷이 정상 갱신되며,
- 집계 중복/누락이 없고,
- incident 기록에 trace_id, 원인, 조치, 재발방지 항목이 포함된다.
