CREATE TABLE IF NOT EXISTS tb_tenant (
    id UUID PRIMARY KEY,
    tenant_key VARCHAR(100) NOT NULL UNIQUE,
    tenant_name VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    plan_tier VARCHAR(20) NOT NULL DEFAULT 'standard',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tb_user (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    login_id VARCHAR(120) NOT NULL,
    display_name VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_user_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT uq_tb_user_tenant_login UNIQUE (tenant_id, login_id)
);

CREATE TABLE IF NOT EXISTS tb_role (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    role_code VARCHAR(60) NOT NULL,
    role_name VARCHAR(120) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_role_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT uq_tb_role_tenant_code UNIQUE (tenant_id, role_code)
);

CREATE TABLE IF NOT EXISTS tb_user_role (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_user_role_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_user_role_user FOREIGN KEY (user_id) REFERENCES tb_user(id),
    CONSTRAINT fk_tb_user_role_role FOREIGN KEY (role_id) REFERENCES tb_role(id),
    CONSTRAINT uq_tb_user_role UNIQUE (tenant_id, user_id, role_id)
);

CREATE TABLE IF NOT EXISTS tb_auth_session (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    session_token_hash VARCHAR(128) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_auth_session_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_auth_session_user FOREIGN KEY (user_id) REFERENCES tb_user(id)
);

CREATE TABLE IF NOT EXISTS tb_conversation (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    trace_id UUID,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_conversation_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE TABLE IF NOT EXISTS tb_message (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL,
    message_text TEXT,
    trace_id UUID,
    policy_version_id UUID,
    template_version_id UUID,
    prompt_version_id UUID,
    index_version_id UUID,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_tb_message PRIMARY KEY (id),
    CONSTRAINT fk_tb_message_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_message_conversation FOREIGN KEY (conversation_id) REFERENCES tb_conversation(id)
);

CREATE INDEX IF NOT EXISTS idx_tb_message_conversation_created_at
    ON tb_message (conversation_id, created_at);

CREATE TABLE IF NOT EXISTS tb_rag_search_log (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    query_text_masked TEXT NOT NULL,
    top_k INTEGER NOT NULL DEFAULT 5,
    trace_id UUID,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_tb_rag_search_log PRIMARY KEY (id),
    CONSTRAINT fk_tb_rag_search_log_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_rag_search_log_conversation FOREIGN KEY (conversation_id) REFERENCES tb_conversation(id)
);

CREATE TABLE IF NOT EXISTS tb_rag_citation (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    message_id UUID NOT NULL,
    message_created_at TIMESTAMP NOT NULL,
    chunk_id UUID,
    rank_no INTEGER NOT NULL,
    excerpt_masked TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_rag_citation_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_rag_citation_message FOREIGN KEY (message_id) REFERENCES tb_message(id)
);

CREATE INDEX IF NOT EXISTS idx_tb_rag_citation_message ON tb_rag_citation (message_id, rank_no);

CREATE TABLE IF NOT EXISTS tb_stream_event (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    message_id UUID NOT NULL,
    message_created_at TIMESTAMP NOT NULL,
    event_type VARCHAR(30) NOT NULL,
    event_seq INTEGER NOT NULL,
    payload_json JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_stream_event_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_stream_event_message FOREIGN KEY (message_id) REFERENCES tb_message(id),
    CONSTRAINT uq_tb_stream_event_seq UNIQUE (message_id, event_seq)
);

CREATE INDEX IF NOT EXISTS idx_tb_stream_event_message_seq ON tb_stream_event (message_id, event_seq);

INSERT INTO tb_tenant (id, tenant_key, tenant_name, status, plan_tier)
SELECT '00000000-0000-0000-0000-000000000001', 'demo-tenant', 'Demo Tenant', 'active', 'standard'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_tenant WHERE tenant_key = 'demo-tenant'
);

INSERT INTO tb_tenant (id, tenant_key, tenant_name, status, plan_tier)
SELECT '00000000-0000-0000-0000-00000000000a', 'tenant-a', 'Tenant A', 'active', 'standard'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_tenant WHERE tenant_key = 'tenant-a'
);

INSERT INTO tb_tenant (id, tenant_key, tenant_name, status, plan_tier)
SELECT '00000000-0000-0000-0000-00000000000b', 'tenant-budget', 'Tenant Budget', 'active', 'standard'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_tenant WHERE tenant_key = 'tenant-budget'
);

INSERT INTO tb_role (id, tenant_id, role_code, role_name)
SELECT '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000001', 'AGENT', 'Agent'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_role WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND role_code = 'AGENT'
);

INSERT INTO tb_role (id, tenant_id, role_code, role_name)
SELECT '00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000001', 'ADMIN', 'Admin'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_role WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND role_code = 'ADMIN'
);

INSERT INTO tb_role (id, tenant_id, role_code, role_name)
SELECT '00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000001', 'OPS', 'Ops'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_role WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND role_code = 'OPS'
);

INSERT INTO tb_role (id, tenant_id, role_code, role_name)
SELECT '00000000-0000-0000-0000-000000000104', '00000000-0000-0000-0000-000000000001', 'CUSTOMER', 'Customer'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_role WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND role_code = 'CUSTOMER'
);

INSERT INTO tb_role (id, tenant_id, role_code, role_name)
SELECT '00000000-0000-0000-0000-000000000105', '00000000-0000-0000-0000-000000000001', 'SYSTEM', 'System'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_role WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND role_code = 'SYSTEM'
);

INSERT INTO tb_user (id, tenant_id, login_id, display_name, status)
SELECT '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000001', 'agent1', 'MVP Agent', 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND login_id = 'agent1'
);

INSERT INTO tb_user (id, tenant_id, login_id, display_name, status)
SELECT '00000000-0000-0000-0000-000000000202', '00000000-0000-0000-0000-000000000001', 'admin1', 'MVP Admin', 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND login_id = 'admin1'
);

INSERT INTO tb_user (id, tenant_id, login_id, display_name, status)
SELECT '00000000-0000-0000-0000-000000000203', '00000000-0000-0000-0000-000000000001', 'ops1', 'MVP Ops', 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user WHERE tenant_id = '00000000-0000-0000-0000-000000000001' AND login_id = 'ops1'
);

INSERT INTO tb_user_role (id, tenant_id, user_id, role_id)
SELECT '00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000101'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user_role
    WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
      AND user_id = '00000000-0000-0000-0000-000000000201'
      AND role_id = '00000000-0000-0000-0000-000000000101'
);

INSERT INTO tb_user_role (id, tenant_id, user_id, role_id)
SELECT '00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000202', '00000000-0000-0000-0000-000000000102'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user_role
    WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
      AND user_id = '00000000-0000-0000-0000-000000000202'
      AND role_id = '00000000-0000-0000-0000-000000000102'
);

INSERT INTO tb_user_role (id, tenant_id, user_id, role_id)
SELECT '00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000203', '00000000-0000-0000-0000-000000000103'
WHERE NOT EXISTS (
    SELECT 1 FROM tb_user_role
    WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
      AND user_id = '00000000-0000-0000-0000-000000000203'
      AND role_id = '00000000-0000-0000-0000-000000000103'
);
