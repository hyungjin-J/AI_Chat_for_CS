CREATE TABLE IF NOT EXISTS tb_audit_export_job (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    requested_by UUID NULL,
    status VARCHAR(20) NOT NULL,
    export_format VARCHAR(20) NOT NULL,
    from_utc TIMESTAMP NULL,
    to_utc TIMESTAMP NULL,
    row_limit INTEGER NOT NULL DEFAULT 1000,
    max_bytes INTEGER NOT NULL DEFAULT 5242880,
    max_duration_sec INTEGER NOT NULL DEFAULT 30,
    row_count INTEGER NOT NULL DEFAULT 0,
    total_bytes INTEGER NOT NULL DEFAULT 0,
    error_code VARCHAR(80) NULL,
    error_message VARCHAR(500) NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    trace_id UUID NOT NULL,
    CONSTRAINT fk_tb_audit_export_job_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE INDEX IF NOT EXISTS idx_tb_audit_export_job_tenant_status_created
    ON tb_audit_export_job (tenant_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tb_audit_export_job_expires
    ON tb_audit_export_job (expires_at, status);

CREATE TABLE IF NOT EXISTS tb_audit_export_chunk (
    job_id UUID NOT NULL,
    chunk_no INTEGER NOT NULL,
    payload_bytes BYTEA NOT NULL,
    payload_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_tb_audit_export_chunk PRIMARY KEY (job_id, chunk_no),
    CONSTRAINT fk_tb_audit_export_chunk_job FOREIGN KEY (job_id) REFERENCES tb_audit_export_job(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tb_audit_export_chunk_created
    ON tb_audit_export_chunk (created_at DESC);
