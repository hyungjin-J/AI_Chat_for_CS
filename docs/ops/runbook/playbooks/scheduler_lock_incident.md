# scheduler_lock_incident

## Symptoms / Detection Signals
- Repeating lock contention on same `lock_key`.
- `self_healing_failed` appears repeatedly in scheduler lock logs/events.
- Lock lease appears stale:
  - `lease_until_utc <= now_utc`
  - heartbeat stale while owner stays unchanged.
- Hourly metrics pipelines stop updating for expected buckets.

Detection query (read-only):
```sql
SELECT lock_key,
       owner_id,
       lease_until_utc,
       last_heartbeat_utc,
       fencing_token,
       recovery_count,
       last_recovered_at
FROM tb_scheduler_lock
ORDER BY lock_key;
```

## Immediate Mitigation (First Response)
1. Freeze manual retries that can duplicate jobs.
2. Confirm affected lock scope (`lock_key`, tenant impact, start time).
3. Verify janitor job activity:
   - check events tagged `self_healing_recovered` / `self_healing_failed`.
4. If stale lock persists beyond SLA, trigger controlled recovery with ops approval.

## Verification Commands (Normal vs Abnormal)
Normal criteria:
- `lease_until_utc` is in the future for active owner.
- `fencing_token` increments only on valid takeover/recovery.
- no repeated `self_healing_failed` for same key within alert window.

Abnormal criteria:
- stale lease and unchanged owner across multiple janitor intervals.
- `fencing_token` jump with missing ownership transition evidence.
- metric lag persists after recovery action.

Read-only checks:
```sql
SELECT event_time, event_type, metric_key, metric_value
FROM tb_ops_event
WHERE metric_key IN ('scheduler_lock_event', 'scheduler_lock_self_heal')
  AND event_time >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 hours'
ORDER BY event_time DESC;
```

```sql
SELECT hour_bucket_utc, metric_key, metric_value, updated_at
FROM tb_api_metric_hourly
WHERE hour_bucket_utc >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '6 hours'
ORDER BY hour_bucket_utc DESC, metric_key;
```

## Recovery Procedure (lease_until / fencing_token / janitor focus)
1. Confirm lock row is stale and not actively heartbeating.
2. Let janitor attempt recovery first (do not race manual takeover).
3. If janitor fails repeatedly:
   - isolate suspected dead owner instance,
   - run one controlled takeover/recovery action,
   - confirm `fencing_token` monotonic increment on recovered owner.
4. Validate no duplicate aggregation side effects (hourly/daily buckets).
5. Re-enable normal scheduler cadence.

## Post-Incident Actions
- Add incident timeline with `incident_id`, `root_trace_id`, `action_trace_id`.
- Attach masked SQL snapshots (no PII, no tokens, no secrets).
- Record root cause category:
  - dead worker ownership,
  - lease heartbeat bug,
  - janitor scheduling gap,
  - DB lock contention.
- Add prevention checklist:
  - janitor cadence/tuning reviewed,
  - lock TTL and heartbeat thresholds validated,
  - alert thresholds adjusted for earlier detection.

