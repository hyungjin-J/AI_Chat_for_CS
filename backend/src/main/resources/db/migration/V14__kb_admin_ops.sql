CREATE TABLE IF NOT EXISTS tb_kb_reindex_job (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    status VARCHAR(30) NOT NULL,
    requested_by UUID NULL,
    requested_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    result_message VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_kb_reindex_job_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE INDEX IF NOT EXISTS idx_tb_kb_reindex_job_tenant_requested
    ON tb_kb_reindex_job (tenant_id, requested_at DESC);
