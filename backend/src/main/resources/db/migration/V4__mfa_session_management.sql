CREATE TABLE IF NOT EXISTS tb_user_mfa (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    mfa_type VARCHAR(30) NOT NULL,
    secret_ciphertext VARCHAR(512) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    enforced BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_user_mfa_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_user_mfa_user FOREIGN KEY (user_id) REFERENCES tb_user(id),
    CONSTRAINT uq_tb_user_mfa_user UNIQUE (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS tb_user_mfa_recovery_code (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    code_hash VARCHAR(128) NOT NULL,
    used_at TIMESTAMP NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_user_mfa_recovery_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_user_mfa_recovery_user FOREIGN KEY (user_id) REFERENCES tb_user(id),
    CONSTRAINT uq_tb_user_mfa_recovery_code UNIQUE (tenant_id, user_id, code_hash)
);

CREATE INDEX IF NOT EXISTS idx_tb_user_mfa_recovery_active
    ON tb_user_mfa_recovery_code (tenant_id, user_id, used_at, expires_at);

CREATE TABLE IF NOT EXISTS tb_auth_mfa_challenge (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    challenge_type VARCHAR(30) NOT NULL,
    totp_secret_ciphertext VARCHAR(512) NULL,
    expires_at TIMESTAMP NOT NULL,
    consumed_at TIMESTAMP NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP NULL,
    trace_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_auth_mfa_challenge_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_auth_mfa_challenge_user FOREIGN KEY (user_id) REFERENCES tb_user(id)
);

CREATE INDEX IF NOT EXISTS idx_tb_auth_mfa_challenge_lookup
    ON tb_auth_mfa_challenge (tenant_id, id, expires_at, consumed_at);

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS device_name VARCHAR(120) NULL;

ALTER TABLE tb_auth_session
    ADD COLUMN IF NOT EXISTS revoked_by_session_id UUID NULL;

CREATE INDEX IF NOT EXISTS idx_tb_auth_session_user_family_active
    ON tb_auth_session (tenant_id, user_id, session_family_id, revoked_at, expires_at);
