ALTER TABLE tb_kb_document_version
    ADD COLUMN IF NOT EXISTS raw_content_masked TEXT;

ALTER TABLE tb_kb_document_version
    ADD COLUMN IF NOT EXISTS pipeline_status VARCHAR(30);

ALTER TABLE tb_kb_document_version
    ADD COLUMN IF NOT EXISTS pipeline_error_code VARCHAR(80);

ALTER TABLE tb_kb_document_version
    ADD COLUMN IF NOT EXISTS pipeline_error_excerpt VARCHAR(500);

ALTER TABLE tb_kb_document_version
    ADD COLUMN IF NOT EXISTS pipeline_updated_at TIMESTAMP;

UPDATE tb_kb_document_version
SET raw_content_masked = COALESCE(raw_content_masked, '')
WHERE raw_content_masked IS NULL;

UPDATE tb_kb_document_version
SET pipeline_status = CASE
    WHEN LOWER(status) IN ('approved', 'archived') THEN 'INDEXED'
    ELSE 'QUEUED'
END
WHERE pipeline_status IS NULL OR pipeline_status = '';

UPDATE tb_kb_document_version
SET pipeline_updated_at = COALESCE(pipeline_updated_at, updated_at, CURRENT_TIMESTAMP)
WHERE pipeline_updated_at IS NULL;

ALTER TABLE tb_kb_reindex_job
    ADD COLUMN IF NOT EXISTS job_type VARCHAR(40);

ALTER TABLE tb_kb_reindex_job
    ADD COLUMN IF NOT EXISTS document_version_id UUID;

ALTER TABLE tb_kb_reindex_job
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(120);

ALTER TABLE tb_kb_reindex_job
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER;

ALTER TABLE tb_kb_reindex_job
    ADD COLUMN IF NOT EXISTS max_attempts INTEGER;

ALTER TABLE tb_kb_reindex_job
    ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP;

ALTER TABLE tb_kb_reindex_job
    ADD COLUMN IF NOT EXISTS error_code VARCHAR(80);

ALTER TABLE tb_kb_reindex_job
    ADD COLUMN IF NOT EXISTS error_excerpt VARCHAR(500);

ALTER TABLE tb_kb_reindex_job
    ADD COLUMN IF NOT EXISTS last_trace_id UUID;

UPDATE tb_kb_reindex_job
SET job_type = COALESCE(job_type, 'REINDEX_ALL'),
    idempotency_key = COALESCE(idempotency_key, 'AUTO-' || CAST(id AS VARCHAR)),
    attempt_count = COALESCE(attempt_count, 0),
    max_attempts = COALESCE(max_attempts, 3),
    status = UPPER(status),
    updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)
WHERE job_type IS NULL
   OR idempotency_key IS NULL
   OR attempt_count IS NULL
   OR max_attempts IS NULL
   OR status <> UPPER(status);

CREATE INDEX IF NOT EXISTS idx_tb_kb_document_version_pipeline
    ON tb_kb_document_version (tenant_id, pipeline_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_tb_kb_reindex_job_pending
    ON tb_kb_reindex_job (status, next_retry_at, requested_at);

CREATE INDEX IF NOT EXISTS idx_tb_kb_reindex_job_tenant_requested
    ON tb_kb_reindex_job (tenant_id, requested_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tb_kb_reindex_job_tenant_idempotency
    ON tb_kb_reindex_job (tenant_id, idempotency_key);
