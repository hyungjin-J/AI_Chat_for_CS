CREATE TABLE IF NOT EXISTS tb_tenant_quota (
    tenant_key VARCHAR(100) NOT NULL,
    max_qps INTEGER NOT NULL,
    max_daily_tokens BIGINT NOT NULL,
    max_monthly_cost NUMERIC(18, 6) NOT NULL,
    effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP NULL,
    breach_action VARCHAR(20) NOT NULL,
    updated_by VARCHAR(120) NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT pk_tb_tenant_quota PRIMARY KEY (tenant_key, effective_from)
);

CREATE INDEX IF NOT EXISTS idx_tb_tenant_quota_tenant_effective
    ON tb_tenant_quota (tenant_key, effective_from DESC);

CREATE TABLE IF NOT EXISTS tb_tenant_plan (
    plan_code VARCHAR(60) PRIMARY KEY,
    plan_name VARCHAR(120) NOT NULL,
    description VARCHAR(500) NULL
);

CREATE TABLE IF NOT EXISTS tb_tenant_subscription (
    tenant_key VARCHAR(100) PRIMARY KEY,
    plan_code VARCHAR(60) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS idx_tb_tenant_subscription_started
    ON tb_tenant_subscription (tenant_key, started_at DESC);

CREATE TABLE IF NOT EXISTS tb_tenant_usage_daily (
    tenant_key VARCHAR(100) NOT NULL,
    usage_date DATE NOT NULL,
    request_count BIGINT NOT NULL,
    input_tokens BIGINT NOT NULL,
    output_tokens BIGINT NOT NULL,
    tool_calls BIGINT NOT NULL,
    estimated_cost NUMERIC(18, 6) NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT pk_tb_tenant_usage_daily PRIMARY KEY (tenant_key, usage_date)
);

CREATE INDEX IF NOT EXISTS idx_tb_tenant_usage_daily_tenant_date
    ON tb_tenant_usage_daily (tenant_key, usage_date);

CREATE TABLE IF NOT EXISTS tb_tenant_usage_monthly (
    tenant_key VARCHAR(100) NOT NULL,
    usage_month_date DATE NOT NULL,
    request_count BIGINT NOT NULL,
    input_tokens BIGINT NOT NULL,
    output_tokens BIGINT NOT NULL,
    tool_calls BIGINT NOT NULL,
    estimated_cost NUMERIC(18, 6) NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT pk_tb_tenant_usage_monthly PRIMARY KEY (tenant_key, usage_month_date)
);

CREATE INDEX IF NOT EXISTS idx_tb_tenant_usage_monthly_tenant_month
    ON tb_tenant_usage_monthly (tenant_key, usage_month_date);

CREATE TABLE IF NOT EXISTS tb_generation_log (
    id VARCHAR(64) PRIMARY KEY,
    tenant_key VARCHAR(100) NOT NULL,
    message_id VARCHAR(64) NOT NULL,
    provider_id VARCHAR(80) NOT NULL,
    model_id VARCHAR(120) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    tool_calls INTEGER NOT NULL,
    prompt_masked TEXT NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tb_generation_log_tenant_created
    ON tb_generation_log (tenant_key, created_at);

CREATE INDEX IF NOT EXISTS idx_tb_generation_log_date
    ON tb_generation_log (created_at);

CREATE TABLE IF NOT EXISTS tb_cost_rate_card (
    rate_card_id VARCHAR(64) PRIMARY KEY,
    provider_id VARCHAR(80) NOT NULL,
    model_id VARCHAR(120) NOT NULL,
    input_token_cost_per_1k NUMERIC(18, 6) NOT NULL,
    output_token_cost_per_1k NUMERIC(18, 6) NOT NULL,
    tool_call_cost NUMERIC(18, 6) NOT NULL,
    effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS idx_tb_cost_rate_card_lookup
    ON tb_cost_rate_card (provider_id, model_id, effective_from DESC);

CREATE TABLE IF NOT EXISTS tb_billing_audit_log (
    id VARCHAR(64) PRIMARY KEY,
    tenant_key VARCHAR(100) NOT NULL,
    actor_user_id VARCHAR(120) NOT NULL,
    actor_role VARCHAR(120) NOT NULL,
    action_type VARCHAR(80) NOT NULL,
    target_type VARCHAR(80) NOT NULL,
    target_id VARCHAR(120) NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    before_json TEXT NOT NULL,
    after_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tb_billing_audit_log_tenant_created
    ON tb_billing_audit_log (tenant_key, created_at DESC);
