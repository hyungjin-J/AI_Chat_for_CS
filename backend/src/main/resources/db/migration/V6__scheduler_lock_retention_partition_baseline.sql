CREATE TABLE IF NOT EXISTS tb_scheduler_lock (
    lock_key VARCHAR(120) PRIMARY KEY,
    owner_id UUID NOT NULL,
    lease_until_utc TIMESTAMP NOT NULL,
    fencing_token BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tb_data_retention_policy (
    table_name VARCHAR(120) PRIMARY KEY,
    retention_days INTEGER NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tb_data_retention_run (
    id UUID PRIMARY KEY,
    table_name VARCHAR(120) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP NULL,
    deleted_rows BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL,
    trace_id UUID NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tb_partition_plan (
    table_name VARCHAR(120) NOT NULL,
    bucket_month_utc DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PLANNED',
    executed_at TIMESTAMP NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_tb_partition_plan PRIMARY KEY (table_name, bucket_month_utc)
);

INSERT INTO tb_data_retention_policy(table_name, retention_days, enabled, updated_at)
SELECT 'tb_ops_event', 180, TRUE, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM tb_data_retention_policy WHERE table_name = 'tb_ops_event');

INSERT INTO tb_data_retention_policy(table_name, retention_days, enabled, updated_at)
SELECT 'tb_audit_log', 365, TRUE, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM tb_data_retention_policy WHERE table_name = 'tb_audit_log');

INSERT INTO tb_data_retention_policy(table_name, retention_days, enabled, updated_at)
SELECT 'tb_api_metric_hourly', 730, TRUE, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM tb_data_retention_policy WHERE table_name = 'tb_api_metric_hourly');
