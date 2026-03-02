-- DB_OPERATIONS_QUERIES.sql
-- Standard PostgreSQL 16+ operations query pack (read-only).
--
-- Safety rules:
-- - SELECT-only diagnostics
-- - No DDL/DML statements
-- - Tenant safety: keep tenant filters in place for row-level inspections
--
-- Run example:
--   Get-Content docs/ops/sql/DB_OPERATIONS_QUERIES.sql -Raw |
--     docker compose -f infra/docker-compose.yml exec -T postgres \
--       psql -U aichatbot -d aichatbot

\echo 'DB_OPERATIONS_QUERIES: start'
\pset pager off
\timing on

\echo '1) Connections / active sessions summary'
SELECT
    current_database() AS database_name,
    current_setting('max_connections')::int AS max_connections,
    count(*) AS total_sessions,
    count(*) FILTER (WHERE state = 'active') AS active_sessions,
    count(*) FILTER (WHERE state = 'idle') AS idle_sessions,
    count(*) FILTER (WHERE wait_event_type IS NOT NULL) AS waiting_sessions,
    round((count(*)::numeric / current_setting('max_connections')::numeric) * 100.0, 2) AS connection_usage_pct
FROM pg_stat_activity
WHERE datname = current_database();

\echo '2) Active sessions (non-idle)'
SELECT
    pid,
    usename,
    application_name,
    backend_type,
    state,
    wait_event_type,
    wait_event,
    now() - query_start AS query_runtime,
    left(query, 220) AS query_snippet
FROM pg_stat_activity
WHERE datname = current_database()
  AND state IS DISTINCT FROM 'idle'
ORDER BY query_start ASC
LIMIT 50;

\echo '3) Locks / blockers'
SELECT
    locktype,
    mode,
    granted,
    count(*) AS lock_count
FROM pg_locks
GROUP BY locktype, mode, granted
ORDER BY lock_count DESC, locktype, mode;

SELECT
    blocked.pid AS blocked_pid,
    blocked.usename AS blocked_user,
    blocker.pid AS blocker_pid,
    blocker.usename AS blocker_user,
    now() - blocked.query_start AS blocked_duration,
    left(blocked.query, 180) AS blocked_query,
    left(blocker.query, 180) AS blocker_query
FROM pg_stat_activity blocked
JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS bpid(blocker_pid) ON true
JOIN pg_stat_activity blocker ON blocker.pid = bpid.blocker_pid
WHERE blocked.datname = current_database()
ORDER BY blocked.query_start ASC;

\echo '4) Long transactions'
SELECT
    pid,
    usename,
    application_name,
    state,
    now() - xact_start AS xact_age,
    now() - query_start AS query_age,
    left(query, 220) AS query_snippet
FROM pg_stat_activity
WHERE datname = current_database()
  AND xact_start IS NOT NULL
ORDER BY xact_start ASC
LIMIT 30;

\echo '5) Slow query candidates (pg_stat_statements preferred; fallback included)'
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')
            THEN 1
        ELSE 0
    END AS pgss_enabled
\gset

\if :pgss_enabled
SELECT
    queryid,
    calls,
    round(total_exec_time::numeric, 2) AS total_exec_time_ms,
    round(mean_exec_time::numeric, 2) AS mean_exec_time_ms,
    round(max_exec_time::numeric, 2) AS max_exec_time_ms,
    rows,
    left(query, 220) AS query_snippet
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
\else
SELECT
    pid,
    usename,
    state,
    wait_event_type,
    wait_event,
    now() - query_start AS runtime,
    left(query, 220) AS query_snippet
FROM pg_stat_activity
WHERE datname = current_database()
  AND state = 'active'
ORDER BY runtime DESC
LIMIT 20;
\endif

\echo '6) Index usage and bloat hints'
SELECT
    s.schemaname,
    s.relname AS table_name,
    s.indexrelname AS index_name,
    s.idx_scan,
    s.idx_tup_read,
    s.idx_tup_fetch,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
FROM pg_stat_user_indexes s
WHERE pg_relation_size(s.indexrelid) > 16 * 1024 * 1024
ORDER BY s.idx_scan ASC, pg_relation_size(s.indexrelid) DESC
LIMIT 30;

SELECT
    schemaname,
    relname AS table_name,
    seq_scan,
    idx_scan,
    round(seq_scan::numeric / nullif(idx_scan, 0), 2) AS seq_to_idx_scan_ratio,
    n_live_tup,
    n_dead_tup,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
ORDER BY seq_scan DESC, n_dead_tup DESC
LIMIT 30;

\echo '7) Autovacuum / analyze status'
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
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    autovacuum_count,
    autoanalyze_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC, last_autovacuum NULLS FIRST
LIMIT 30;

\echo '8) Table sizes / top growth hints'
SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pg_total_relation_size(c.oid) AS total_size_bytes,
    coalesce(s.n_tup_ins, 0) AS inserts,
    coalesce(s.n_tup_upd, 0) AS updates,
    coalesce(s.n_tup_del, 0) AS deletes,
    coalesce(s.n_mod_since_analyze, 0) AS modified_since_analyze
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 30;

\echo '9) Replication / backup indicators (may be empty on standalone local DB)'
SELECT
    name,
    setting
FROM pg_settings
WHERE name IN (
    'wal_level',
    'archive_mode',
    'archive_command',
    'max_wal_senders',
    'hot_standby'
)
ORDER BY name;

SELECT
    archived_count,
    failed_count,
    last_archived_wal,
    last_archived_time,
    last_failed_wal,
    last_failed_time,
    stats_reset
FROM pg_stat_archiver;

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

\echo '10) Tenant-aware checks (keep tenant filter; do not inspect cross-tenant rows)'
SELECT
    c.table_schema,
    c.table_name
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.column_name = 'tenant_key'
ORDER BY c.table_name;

SELECT
    CASE
        WHEN to_regclass('public.tb_message') IS NOT NULL
            THEN 1
        ELSE 0
    END AS has_tb_message
\gset

\if :has_tb_message
\set tenant_key 'REPLACE_WITH_TENANT_KEY'
SELECT
    tenant_key,
    date_trunc('day', created_at) AS day,
    count(*) AS message_count
FROM public.tb_message
WHERE tenant_key = :'tenant_key'
GROUP BY tenant_key, date_trunc('day', created_at)
ORDER BY day DESC
LIMIT 14;
\else
SELECT 'tb_message table not found; skip tenant-scoped message check' AS note;
\endif

\echo 'DB_OPERATIONS_QUERIES: end'
