# audit_chain_integrity_incident

## Symptoms / Detection Signals
- `AUDIT_CHAIN_VERIFY_FAILED` event emitted.
- verifier output includes:
  - `chain_seq_gap`
  - `hash_link_mismatch`
  - `hash_curr_mismatch`
  - `missing_chain_fields`
- sudden spike in `audit_chain_verify_failed` metric.

Read-only detection query:
```sql
SELECT event_time, event_type, metric_key, metric_value, dimensions_json
FROM tb_ops_event
WHERE metric_key = 'audit_chain_verify_failed'
  AND event_time >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
ORDER BY event_time DESC;
```

## Immediate Mitigation (First Response)
1. Treat as integrity incident (fail-closed).
2. Pause audit export operations for affected tenant scope.
3. Capture verifier output artifact and `trace_id`.
4. Expand verification time range (for blast radius confirmation).
5. Notify security/compliance owner if tamper suspicion remains.

## Verification Commands (Normal vs Abnormal)
Primary verifier:
```bash
python scripts/verify_audit_chain_integrity.py \
  --tenant-key <tenant_key> \
  --from-utc <from_utc> \
  --to-utc <to_utc>
```

Normal criteria:
- `status=PASS`
- `failure_count=0`
- no chain gap/link/hash mismatch in samples.

Abnormal criteria:
- exit code non-zero,
- any mismatch sample returned,
- repeated failures across widened window.

## Recovery Procedure (chain scope and evidence)
1. Re-run verifier with wider time range to locate first bad sequence.
2. Confirm whether mismatch is:
   - isolated row corruption,
   - sequence gap by missing rows,
   - link/hash mismatch after code/config drift.
3. Block downstream audit export until integrity is restored.
4. Recover source data through approved backup/restore path if needed.
5. Re-run verifier on recovered range; reopen exports only after PASS.

## Post-Incident Actions
- Store masked evidence:
  - verifier txt/json,
  - incident trace references,
  - SQL snapshots without `before_json` / `after_json` raw payload leaks.
- Document root cause and prevention:
  - chain generation path regression test coverage,
  - migration/schema drift checks,
  - nightly verifier schedule and alert threshold tuning.
- Update incident review with:
  - `incident_id`, `tenant_key`, time window, failure type counts, closure approval.

