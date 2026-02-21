ALTER TABLE tb_user
    ADD COLUMN IF NOT EXISTS permission_version BIGINT NOT NULL DEFAULT 1;

ALTER TABLE tb_user
    ADD COLUMN IF NOT EXISTS admin_level VARCHAR(30) NOT NULL DEFAULT 'MANAGER';

ALTER TABLE tb_user
    ADD COLUMN IF NOT EXISTS failed_login_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE tb_user
    ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP NULL;

ALTER TABLE tb_user
    ADD COLUMN IF NOT EXISTS last_failed_at TIMESTAMP NULL;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS session_family_id UUID;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS refresh_jti_hash VARCHAR(128);

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS parent_refresh_jti_hash VARCHAR(128);

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS consumed_at TIMESTAMP NULL;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP NULL;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS revoked_reason VARCHAR(120) NULL;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS client_type VARCHAR(60) NULL;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS created_ip VARCHAR(64) NULL;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS consumed_ip VARCHAR(64) NULL;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP NULL;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS trace_id UUID NULL;

UPDATE tb_auth_session
SET session_family_id = id
WHERE session_family_id IS NULL;

UPDATE tb_auth_session
SET refresh_jti_hash = session_token_hash
WHERE refresh_jti_hash IS NULL;

ALTER TABLE tb_auth_session
    ALTER COLUMN session_family_id SET NOT NULL;

ALTER TABLE tb_auth_session
    ALTER COLUMN refresh_jti_hash SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tb_auth_session_family
    ON tb_auth_session (tenant_id, session_family_id);

CREATE INDEX IF NOT EXISTS idx_tb_auth_session_refresh_jti
    ON tb_auth_session (refresh_jti_hash);

CREATE INDEX IF NOT EXISTS idx_tb_auth_session_user_active
    ON tb_auth_session (tenant_id, user_id, revoked_at, expires_at);

CREATE TABLE IF NOT EXISTS tb_audit_log (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    trace_id UUID NOT NULL,
    action_type VARCHAR(80) NOT NULL,
    actor_user_id UUID NULL,
    actor_role VARCHAR(80) NULL,
    target_type VARCHAR(80) NULL,
    target_id VARCHAR(200) NULL,
    before_json JSON NULL,
    after_json JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_audit_log_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE INDEX IF NOT EXISTS idx_tb_audit_log_tenant_created
    ON tb_audit_log (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tb_audit_log_action_created
    ON tb_audit_log (action_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tb_audit_log_trace
    ON tb_audit_log (trace_id);

CREATE TABLE IF NOT EXISTS tb_ops_event (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    trace_id UUID NOT NULL,
    event_time TIMESTAMP NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    metric_key VARCHAR(80) NOT NULL,
    metric_value BIGINT NOT NULL DEFAULT 1,
    dimensions_json JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_ops_event_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE INDEX IF NOT EXISTS idx_tb_ops_event_bucket
    ON tb_ops_event (tenant_id, event_time);

CREATE INDEX IF NOT EXISTS idx_tb_ops_event_metric
    ON tb_ops_event (metric_key, event_time);

CREATE TABLE IF NOT EXISTS tb_api_metric_hourly (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    hour_bucket_utc TIMESTAMP NOT NULL,
    metric_key VARCHAR(80) NOT NULL,
    metric_value BIGINT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_api_metric_hourly_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT uq_tb_api_metric_hourly UNIQUE (tenant_id, hour_bucket_utc, metric_key)
);

CREATE INDEX IF NOT EXISTS idx_tb_api_metric_hourly_range
    ON tb_api_metric_hourly (tenant_id, hour_bucket_utc);

CREATE TABLE IF NOT EXISTS tb_rbac_matrix (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    resource_key VARCHAR(120) NOT NULL,
    role_code VARCHAR(30) NOT NULL,
    admin_level VARCHAR(30) NOT NULL DEFAULT 'MANAGER',
    allowed BOOLEAN NOT NULL,
    permission_version BIGINT NOT NULL DEFAULT 1,
    updated_by UUID NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_rbac_matrix_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT uq_tb_rbac_matrix UNIQUE (tenant_id, resource_key, role_code, admin_level)
);

CREATE TABLE IF NOT EXISTS tb_ops_block (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    block_type VARCHAR(20) NOT NULL,
    block_value VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    reason VARCHAR(300) NULL,
    expires_at TIMESTAMP NULL,
    created_by UUID NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_ops_block_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT uq_tb_ops_block UNIQUE (tenant_id, block_type, block_value)
);

UPDATE tb_user
SET admin_level = 'SYSTEM_ADMIN'
WHERE login_id = 'admin1';

