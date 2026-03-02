CREATE TABLE IF NOT EXISTS tb_admin_resource (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_key VARCHAR(150) NOT NULL,
    status VARCHAR(40) NOT NULL,
    payload_json VARCHAR(12000) NULL,
    active_flag BOOLEAN NOT NULL DEFAULT FALSE,
    last_rotated_at TIMESTAMP NULL,
    created_by UUID NULL,
    updated_by UUID NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_admin_resource_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT uq_tb_admin_resource UNIQUE (tenant_id, resource_type, resource_key)
);

CREATE INDEX IF NOT EXISTS idx_tb_admin_resource_tenant_type
    ON tb_admin_resource (tenant_id, resource_type, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_tb_admin_resource_tenant_type_active
    ON tb_admin_resource (tenant_id, resource_type, active_flag);

CREATE TABLE IF NOT EXISTS tb_ops_rollback (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(150) NOT NULL,
    status VARCHAR(40) NOT NULL,
    reason VARCHAR(500) NULL,
    requested_by UUID NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_ops_rollback_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE INDEX IF NOT EXISTS idx_tb_ops_rollback_tenant_created
    ON tb_ops_rollback (tenant_id, created_at DESC);
