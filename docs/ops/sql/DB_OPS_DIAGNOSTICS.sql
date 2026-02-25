-- Operational diagnostics SQL set for local/prod triage.
-- Run (docker local):
--   Get-Content docs/ops/sql/DB_OPS_DIAGNOSTICS.sql -Raw |
--     docker compose -f infra/docker-compose.yml exec -T postgres psql -U aichatbot -d aichatbot
--
-- Notes:
-- - Queries are read-only.
-- - Some sections can return zero rows in local single-node setups.

-- 1) Connection saturation and session state distribution.
SELECT
    current_database() AS database_name,
    count(*) AS total_sessions,
    count(*) FILTER (WHERE state = 'active') AS active_sessions,
    count(*) FILTER (WHERE state = 'idle') AS idle_sessions,
    count(*) FILTER (WHERE wait_event_type IS NOT NULL) AS waiting_sessions,
    current_setting('max_connections')::int AS max_connections,
    round((count(*)::numeric / current_setting('max_connections')::numeric) * 100.0, 2) AS connection_usage_pct
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY current_database(), current_setting('max_connections');

-- 2) Active sessions (non-idle) with runtime and wait details.
SELECT
    pid,
    usename,
    application_name,
    backend_type,
    client_addr,
    state,
    wait_event_type,
    wait_event,
    now() - query_start AS query_runtime,
    left(query, 300) AS query_snippet
FROM pg_stat_activity
WHERE datname = current_database()
  AND state IS DISTINCT FROM 'idle'
ORDER BY query_start ASC
LIMIT 50;

-- 3) Lock inventory summary.
SELECT
    locktype,
    mode,
    granted,
    count(*) AS lock_count
FROM pg_locks
GROUP BY locktype, mode, granted
ORDER BY lock_count DESC, locktype, mode;

-- 4) Blocking tree (blocked <-> blocker).
SELECT
    blocked.pid AS blocked_pid,
    blocked.usename AS blocked_user,
    blocker.pid AS blocker_pid,
    blocker.usename AS blocker_user,
    blocked.wait_event_type AS blocked_wait_type,
    blocked.wait_event AS blocked_wait_event,
    now() - blocked.query_start AS blocked_duration,
    left(blocked.query, 200) AS blocked_query,
    left(blocker.query, 200) AS blocker_query
FROM pg_stat_activity blocked
JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS bpid(blocker_pid) ON true
JOIN pg_stat_activity blocker ON blocker.pid = bpid.blocker_pid
WHERE blocked.datname = current_database()
ORDER BY blocked.query_start ASC;

-- 5) Long-running queries (> 30 seconds).
SELECT
    pid,
    usename,
    application_name,
    state,
    now() - query_start AS runtime,
    wait_event_type,
    wait_event,
    left(query, 300) AS query_snippet
FROM pg_stat_activity
WHERE datname = current_database()
  AND state = 'active'
  AND now() - query_start > interval '30 seconds'
ORDER BY runtime DESC;

-- 6) Slow-query candidates without pg_stat_statements (runtime/wait proxy).
SELECT
    pid,
    backend_type,
    state,
    wait_event_type,
    wait_event,
    now() - query_start AS runtime,
    left(query, 200) AS query_snippet
FROM pg_stat_activity
WHERE datname = current_database()
  AND state = 'active'
ORDER BY (now() - query_start) DESC
LIMIT 20;

-- 7) Table bloat candidates (dead tuples and dead tuple ratio proxy).
SELECT
    schemaname,
    relname AS table_name,
    n_live_tup,
    n_dead_tup,
    round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 2) AS dead_tuple_ratio_pct,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    last_vacuum,
    last_autovacuum,
    vacuum_count,
    autovacuum_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC, dead_tuple_ratio_pct DESC NULLS LAST
LIMIT 30;

-- 8) Index efficiency / possible index-bloat candidates.
SELECT
    s.schemaname,
    s.relname AS table_name,
    s.indexrelname AS index_name,
    s.idx_scan,
    s.idx_tup_read,
    s.idx_tup_fetch,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
FROM pg_stat_user_indexes s
WHERE pg_relation_size(s.indexrelid) > 50 * 1024 * 1024
ORDER BY s.idx_scan ASC, pg_relation_size(s.indexrelid) DESC
LIMIT 30;

-- 9) Autovacuum state: progress + stale-vacuum candidates.
SELECT
    p.pid,
    p.relid::regclass AS relation_name,
    p.phase,
    p.heap_blks_total,
    p.heap_blks_scanned,
    p.heap_blks_vacuumed,
    p.index_vacuum_count,
    p.max_dead_tuples,
    p.num_dead_tuples
FROM pg_stat_progress_vacuum p
ORDER BY p.pid;

SELECT
    schemaname,
    relname AS table_name,
    n_dead_tup,
    last_autovacuum,
    now() - coalesce(last_autovacuum, 'epoch'::timestamp) AS since_last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC, last_autovacuum NULLS FIRST
LIMIT 30;

-- 10) Replication and slot health (may be empty on local standalone DB).
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    sync_state,
    pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS wal_lag_bytes
FROM pg_stat_replication
ORDER BY application_name;

SELECT
    slot_name,
    slot_type,
    active,
    temporary,
    restart_lsn,
    confirmed_flush_lsn,
    pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS retained_wal_bytes
FROM pg_replication_slots
ORDER BY slot_name;

-- 11) Tenant isolation schema checks.
-- 11-a) Tables that do not have tenant discriminator column (tenant_id/tenant_key).
SELECT
    t.table_schema,
    t.table_name
FROM information_schema.tables t
WHERE t.table_schema = 'public'
  AND t.table_type = 'BASE TABLE'
  AND NOT EXISTS (
      SELECT 1
      FROM information_schema.columns c
      WHERE c.table_schema = t.table_schema
        AND c.table_name = t.table_name
        AND c.column_name IN ('tenant_id', 'tenant_key')
  )
ORDER BY t.table_name;

-- 11-b) Tables where tenant discriminator exists but is nullable.
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.is_nullable
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.column_name IN ('tenant_id', 'tenant_key')
  AND c.is_nullable = 'YES'
ORDER BY c.table_name, c.column_name;

