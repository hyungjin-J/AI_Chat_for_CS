ALTER TABLE tb_audit_log
    ADD COLUMN IF NOT EXISTS chain_seq BIGINT NULL;

ALTER TABLE tb_audit_log
    ADD COLUMN IF NOT EXISTS hash_prev VARCHAR(128) NULL;

ALTER TABLE tb_audit_log
    ADD COLUMN IF NOT EXISTS hash_curr VARCHAR(128) NULL;

ALTER TABLE tb_audit_log
    ADD COLUMN IF NOT EXISTS hash_algo VARCHAR(20) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tb_audit_log_chain_unique
    ON tb_audit_log (tenant_id, chain_seq);

CREATE TABLE IF NOT EXISTS tb_audit_chain_state (
    tenant_id UUID PRIMARY KEY,
    last_seq BIGINT NOT NULL DEFAULT 0,
    last_hash VARCHAR(128) NOT NULL DEFAULT 'GENESIS',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_audit_chain_state_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE TABLE IF NOT EXISTS tb_audit_export_log (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    requested_by UUID NULL,
    export_format VARCHAR(20) NOT NULL,
    from_utc TIMESTAMP NULL,
    to_utc TIMESTAMP NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    trace_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_audit_export_log_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE TABLE IF NOT EXISTS tb_rbac_change_request (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    resource_key VARCHAR(120) NOT NULL,
    role_code VARCHAR(30) NOT NULL,
    admin_level VARCHAR(30) NOT NULL,
    allowed BOOLEAN NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    requested_by UUID NOT NULL,
    reason VARCHAR(400) NULL,
    applied_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_rbac_change_request_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE INDEX IF NOT EXISTS idx_tb_rbac_change_request_lookup
    ON tb_rbac_change_request (tenant_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS tb_rbac_change_approval (
    id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    approver_user_id UUID NOT NULL,
    decision VARCHAR(20) NOT NULL,
    comment VARCHAR(400) NULL,
    decided_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_rbac_change_approval_request FOREIGN KEY (request_id) REFERENCES tb_rbac_change_request(id),
    CONSTRAINT fk_tb_rbac_change_approval_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT uq_tb_rbac_change_approval UNIQUE (request_id, approver_user_id)
);

INSERT INTO tb_user (id, tenant_id, login_id, display_name, status)
SELECT '00000000-0000-0000-0000-000000000204', '00000000-0000-0000-0000-000000000001', 'admin2', 'MVP Admin 2', 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND login_id = 'admin2'
);

INSERT INTO tb_user (id, tenant_id, login_id, display_name, status)
SELECT '00000000-0000-0000-0000-000000000205', '00000000-0000-0000-0000-000000000001', 'admin3', 'MVP Admin 3', 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND login_id = 'admin3'
);

INSERT INTO tb_user_role (id, tenant_id, user_id, role_id)
SELECT '00000000-0000-0000-0000-000000000304', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000204', '00000000-0000-0000-0000-000000000102'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user_role
    WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
      AND user_id = '00000000-0000-0000-0000-000000000204'
      AND role_id = '00000000-0000-0000-0000-000000000102'
);

INSERT INTO tb_user_role (id, tenant_id, user_id, role_id)
SELECT '00000000-0000-0000-0000-000000000305', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000205', '00000000-0000-0000-0000-000000000102'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user_role
    WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
      AND user_id = '00000000-0000-0000-0000-000000000205'
      AND role_id = '00000000-0000-0000-0000-000000000102'
);

UPDATE tb_user
SET admin_level = 'SYSTEM_ADMIN'
WHERE login_id IN ('admin1', 'admin2', 'admin3');
