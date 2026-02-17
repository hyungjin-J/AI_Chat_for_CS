-- CS AI Chatbot PostgreSQL DDL (PostgreSQL 15+)
-- generated_at: 2026-02-17 05:04:53
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS vec;
CREATE SCHEMA IF NOT EXISTS ops;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
DO $$ BEGIN CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION WHEN undefined_file THEN RAISE NOTICE 'pgvector not installed'; END $$;
SET search_path = core, vec, ops, public;

-- TB_TENANT: 테넌트 마스터
CREATE TABLE IF NOT EXISTS core.tb_tenant (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_key varchar(100) NOT NULL,
    tenant_name varchar(200) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'active',
    plan_tier varchar(20) NOT NULL DEFAULT 'standard',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_key)
);

-- TB_TENANT_DOMAIN: 테넌트 도메인
CREATE TABLE IF NOT EXISTS core.tb_tenant_domain (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    host varchar(255) NOT NULL,
    locale varchar(10) NOT NULL DEFAULT 'ko-KR',
    is_default boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (host),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_USER: 사용자
CREATE TABLE IF NOT EXISTS core.tb_user (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    login_id varchar(120) NOT NULL,
    display_name varchar(120) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, login_id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_ROLE: 역할
CREATE TABLE IF NOT EXISTS core.tb_role (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    role_code varchar(60) NOT NULL,
    role_name varchar(120) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, role_code),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_PERMISSION: 권한
CREATE TABLE IF NOT EXISTS core.tb_permission (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    perm_code varchar(120) NOT NULL,
    perm_name varchar(150) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (perm_code)
);

-- TB_USER_ROLE: 사용자-역할 매핑
CREATE TABLE IF NOT EXISTS core.tb_user_role (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, user_id, role_id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (user_id) REFERENCES core.tb_user (id),
    FOREIGN KEY (role_id) REFERENCES core.tb_role (id)
);

-- TB_ROLE_PERMISSION: 역할-권한 매핑
CREATE TABLE IF NOT EXISTS core.tb_role_permission (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    role_id uuid NOT NULL,
    permission_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, role_id, permission_id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (role_id) REFERENCES core.tb_role (id),
    FOREIGN KEY (permission_id) REFERENCES core.tb_permission (id)
);

-- TB_AUTH_SESSION: 인증 세션
CREATE TABLE IF NOT EXISTS core.tb_auth_session (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    session_token_hash varchar(128) NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (session_token_hash),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (user_id) REFERENCES core.tb_user (id)
);

-- TB_CHANNEL: 채널
CREATE TABLE IF NOT EXISTS core.tb_channel (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    channel_code varchar(60) NOT NULL,
    channel_name varchar(120) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, channel_code),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_WIDGET_INSTANCE: 위젯 인스턴스
CREATE TABLE IF NOT EXISTS core.tb_widget_instance (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    channel_id uuid NOT NULL,
    widget_key varchar(120) NOT NULL,
    theme_json jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, widget_key),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (channel_id) REFERENCES core.tb_channel (id)
);

-- TB_CUSTOMER: 고객(PII 최소)
CREATE TABLE IF NOT EXISTS core.tb_customer (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    channel_id uuid NOT NULL,
    display_name_masked varchar(120),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (channel_id) REFERENCES core.tb_channel (id)
);

-- TB_CUSTOMER_IDENTITY: 고객 식별자 해시
CREATE TABLE IF NOT EXISTS core.tb_customer_identity (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    identity_type varchar(30) NOT NULL,
    customer_token_hash varchar(128) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, identity_type, customer_token_hash),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (customer_id) REFERENCES core.tb_customer (id)
);

-- TB_CONVERSATION: 대화 세션
CREATE TABLE IF NOT EXISTS core.tb_conversation (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    channel_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'active',
    trace_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (channel_id) REFERENCES core.tb_channel (id),
    FOREIGN KEY (customer_id) REFERENCES core.tb_customer (id)
);

-- TB_MESSAGE: 메시지(월 파티션)
CREATE TABLE IF NOT EXISTS core.tb_message (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    role varchar(20) NOT NULL,
    message_text text,
    trace_id uuid,
    policy_version_id uuid,
    template_version_id uuid,
    prompt_version_id uuid,
    index_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (conversation_id) REFERENCES core.tb_conversation (id)
) PARTITION BY RANGE (created_at);
COMMENT ON TABLE core.tb_message IS '권장 인덱스: (tenant_id, conversation_id, created_at), (tenant_id, created_at), BRIN(created_at)';

-- TB_ATTACHMENT: 첨부파일
CREATE TABLE IF NOT EXISTS core.tb_attachment (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    storage_key varchar(255) NOT NULL,
    file_name varchar(255) NOT NULL,
    mime_type varchar(120) NOT NULL,
    size_bytes bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, storage_key),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_MESSAGE_ATTACHMENT: 메시지-첨부 연결
CREATE TABLE IF NOT EXISTS core.tb_message_attachment (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    message_id uuid NOT NULL,
    message_created_at timestamptz NOT NULL,
    attachment_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, message_id, message_created_at, attachment_id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (message_id, message_created_at) REFERENCES core.tb_message (id, created_at),
    FOREIGN KEY (attachment_id) REFERENCES core.tb_attachment (id)
);

-- TB_MESSAGE_FEEDBACK: 메시지 피드백
CREATE TABLE IF NOT EXISTS core.tb_message_feedback (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    message_id uuid NOT NULL,
    message_created_at timestamptz NOT NULL,
    feedback_type varchar(30) NOT NULL,
    score smallint,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (message_id, message_created_at) REFERENCES core.tb_message (id, created_at)
);

-- TB_STREAM_EVENT: SSE 이벤트 로그
CREATE TABLE IF NOT EXISTS core.tb_stream_event (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    message_id uuid NOT NULL,
    message_created_at timestamptz NOT NULL,
    event_type varchar(30) NOT NULL,
    event_seq integer NOT NULL,
    payload_json jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, message_id, message_created_at, event_seq),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (message_id, message_created_at) REFERENCES core.tb_message (id, created_at)
);

-- TB_TOOL_DEFINITION: 툴 정의
CREATE TABLE IF NOT EXISTS core.tb_tool_definition (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    tool_name varchar(120) NOT NULL,
    tool_version varchar(40) NOT NULL DEFAULT 'v1',
    schema_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    timeout_ms integer NOT NULL DEFAULT 8000,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, tool_name, tool_version),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_TOOL_CALL_LOG: 툴 호출 로그(월 파티션)
CREATE TABLE IF NOT EXISTS core.tb_tool_call_log (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    tool_name varchar(120) NOT NULL,
    http_status integer,
    latency_ms integer,
    trace_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);
COMMENT ON TABLE core.tb_tool_call_log IS '권장 인덱스: (tenant_id, conversation_id, created_at), BRIN(created_at)';

-- TB_KB: 지식베이스
CREATE TABLE IF NOT EXISTS core.tb_kb (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    kb_key varchar(100) NOT NULL,
    kb_name varchar(200) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, kb_key),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_KB_SOURCE: 지식 원천
CREATE TABLE IF NOT EXISTS core.tb_kb_source (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    kb_id uuid NOT NULL,
    source_type varchar(30) NOT NULL,
    source_uri text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (kb_id) REFERENCES core.tb_kb (id)
);

-- TB_KB_DOCUMENT: KB 문서
CREATE TABLE IF NOT EXISTS core.tb_kb_document (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    kb_id uuid NOT NULL,
    source_id uuid,
    title varchar(255) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'ingested',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (kb_id) REFERENCES core.tb_kb (id),
    FOREIGN KEY (source_id) REFERENCES core.tb_kb_source (id)
);

-- TB_KB_DOCUMENT_VERSION: 문서 버전
CREATE TABLE IF NOT EXISTS core.tb_kb_document_version (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    document_id uuid NOT NULL,
    version_no integer NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'draft',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (document_id, version_no),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (document_id) REFERENCES core.tb_kb_document (id)
);

-- TB_KB_CHUNK: 문서 청크
CREATE TABLE IF NOT EXISTS core.tb_kb_chunk (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    kb_id uuid NOT NULL,
    document_version_id uuid NOT NULL,
    chunk_no integer NOT NULL,
    chunk_text text NOT NULL,
    opensearch_doc_id varchar(120),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (document_version_id, chunk_no),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (kb_id) REFERENCES core.tb_kb (id),
    FOREIGN KEY (document_version_id) REFERENCES core.tb_kb_document_version (id)
);

-- TB_KB_INGEST_JOB: 인제스트 작업
CREATE TABLE IF NOT EXISTS core.tb_kb_ingest_job (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    kb_id uuid NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'queued',
    total_docs integer NOT NULL DEFAULT 0,
    processed_docs integer NOT NULL DEFAULT 0,
    failed_docs integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (kb_id) REFERENCES core.tb_kb (id)
);

-- TB_KB_INDEX_VERSION: 인덱스 버전
CREATE TABLE IF NOT EXISTS core.tb_kb_index_version (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    kb_id uuid NOT NULL,
    index_version integer NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'building',
    opensearch_index_name varchar(200),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (kb_id, index_version),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (kb_id) REFERENCES core.tb_kb (id)
);

-- TB_KB_CHUNK_EMBEDDING: 청크 임베딩
CREATE TABLE IF NOT EXISTS vec.tb_kb_chunk_embedding (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    kb_chunk_id uuid NOT NULL,
    index_version_id uuid NOT NULL,
    embedding vector(1536) NOT NULL,
    embedding_dim integer NOT NULL DEFAULT 1536,
    model_name varchar(120) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (kb_chunk_id, index_version_id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (kb_chunk_id) REFERENCES core.tb_kb_chunk (id),
    FOREIGN KEY (index_version_id) REFERENCES core.tb_kb_index_version (id)
);
CREATE INDEX IF NOT EXISTS ivf_tb_kb_chunk_embedding__embedding ON vec.tb_kb_chunk_embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- TB_ANSWER_BANK: 승인 답변 저장소
CREATE TABLE IF NOT EXISTS vec.tb_answer_bank (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    question_fingerprint varchar(128) NOT NULL,
    answer_json jsonb NOT NULL,
    citation_json jsonb NOT NULL,
    policy_version_id uuid,
    index_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, question_fingerprint, policy_version_id, index_version_id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_SEMANTIC_CACHE: 시맨틱 캐시
CREATE TABLE IF NOT EXISTS vec.tb_semantic_cache (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    cache_key varchar(128) NOT NULL,
    query_embedding vector(1536),
    answer_json jsonb NOT NULL,
    session_summary text,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, cache_key),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);
CREATE INDEX IF NOT EXISTS hnsw_tb_semantic_cache__query_embedding ON vec.tb_semantic_cache USING hnsw (query_embedding vector_cosine_ops);

-- TB_RAG_SEARCH_LOG: RAG 검색 로그(월 파티션)
CREATE TABLE IF NOT EXISTS core.tb_rag_search_log (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    query_text_masked text NOT NULL,
    top_k integer NOT NULL DEFAULT 5,
    trace_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);
COMMENT ON TABLE core.tb_rag_search_log IS '권장 인덱스: (tenant_id, conversation_id, created_at), BRIN(created_at)';

-- TB_RAG_CITATION: RAG 인용
CREATE TABLE IF NOT EXISTS core.tb_rag_citation (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    message_id uuid NOT NULL,
    message_created_at timestamptz NOT NULL,
    chunk_id uuid,
    rank_no integer NOT NULL,
    excerpt_masked text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (message_id, message_created_at) REFERENCES core.tb_message (id, created_at),
    FOREIGN KEY (chunk_id) REFERENCES core.tb_kb_chunk (id)
);

-- TB_GENERATION_LOG: 생성 로그
CREATE TABLE IF NOT EXISTS core.tb_generation_log (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    message_id uuid NOT NULL,
    message_created_at timestamptz NOT NULL,
    provider_id uuid,
    model_id uuid,
    input_tokens integer,
    output_tokens integer,
    trace_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (message_id, message_created_at) REFERENCES core.tb_message (id, created_at)
);

-- TB_GUARDRAIL_EVENT: 가드레일 이벤트
CREATE TABLE IF NOT EXISTS core.tb_guardrail_event (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    conversation_id uuid,
    message_id uuid,
    message_created_at timestamptz,
    rule_code varchar(80) NOT NULL,
    action varchar(40) NOT NULL,
    trace_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_TEMPLATE: 템플릿
CREATE TABLE IF NOT EXISTS core.tb_template (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    template_key varchar(100) NOT NULL,
    category varchar(60) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, template_key),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_TEMPLATE_VERSION: 템플릿 버전
CREATE TABLE IF NOT EXISTS core.tb_template_version (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    template_id uuid NOT NULL,
    version_no integer NOT NULL,
    body_text text NOT NULL,
    approval_status varchar(20) NOT NULL DEFAULT 'draft',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (template_id, version_no),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (template_id) REFERENCES core.tb_template (id)
);

-- TB_TEMPLATE_PLACEHOLDER: 템플릿 변수
CREATE TABLE IF NOT EXISTS core.tb_template_placeholder (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    template_version_id uuid NOT NULL,
    placeholder_key varchar(80) NOT NULL,
    data_type varchar(30) NOT NULL DEFAULT 'string',
    required boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (template_version_id, placeholder_key),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (template_version_id) REFERENCES core.tb_template_version (id)
);

-- TB_POLICY: 정책
CREATE TABLE IF NOT EXISTS core.tb_policy (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    policy_key varchar(100) NOT NULL,
    category varchar(60) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, policy_key),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_POLICY_VERSION: 정책 버전
CREATE TABLE IF NOT EXISTS core.tb_policy_version (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    policy_id uuid NOT NULL,
    version_no integer NOT NULL,
    rule_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    answer_contract_json jsonb DEFAULT '{}'::jsonb,
    approval_status varchar(20) NOT NULL DEFAULT 'draft',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (policy_id, version_no),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (policy_id) REFERENCES core.tb_policy (id)
);

-- TB_PROMPT: 프롬프트
CREATE TABLE IF NOT EXISTS core.tb_prompt (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    prompt_key varchar(100) NOT NULL,
    prompt_type varchar(30) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, prompt_key),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_PROMPT_VERSION: 프롬프트 버전
CREATE TABLE IF NOT EXISTS core.tb_prompt_version (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    prompt_id uuid NOT NULL,
    version_no integer NOT NULL,
    system_prompt_text text NOT NULL,
    schema_json jsonb DEFAULT '{}'::jsonb,
    approval_status varchar(20) NOT NULL DEFAULT 'draft',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (prompt_id, version_no),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (prompt_id) REFERENCES core.tb_prompt (id)
);

-- TB_TEMPLATE_POLICY_MAP: 템플릿-정책 매핑
CREATE TABLE IF NOT EXISTS core.tb_template_policy_map (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    category varchar(60) NOT NULL,
    template_id uuid NOT NULL,
    template_version_id uuid,
    policy_id uuid NOT NULL,
    policy_version_id uuid,
    effective_from timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (template_id) REFERENCES core.tb_template (id),
    FOREIGN KEY (template_version_id) REFERENCES core.tb_template_version (id),
    FOREIGN KEY (policy_id) REFERENCES core.tb_policy (id),
    FOREIGN KEY (policy_version_id) REFERENCES core.tb_policy_version (id)
);

-- TB_LLM_PROVIDER: LLM Provider
CREATE TABLE IF NOT EXISTS core.tb_llm_provider (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    provider_code varchar(60) NOT NULL,
    provider_name varchar(120) NOT NULL,
    endpoint_url text,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, provider_code),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_LLM_MODEL: LLM 모델
CREATE TABLE IF NOT EXISTS core.tb_llm_model (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    provider_id uuid NOT NULL,
    model_code varchar(100) NOT NULL,
    context_window integer,
    max_output_tokens integer,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (provider_id, model_code),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (provider_id) REFERENCES core.tb_llm_provider (id)
);

-- TB_PROVIDER_KEY: Provider 키
CREATE TABLE IF NOT EXISTS core.tb_provider_key (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    provider_id uuid NOT NULL,
    key_name varchar(120) NOT NULL,
    secret_ref varchar(255) NOT NULL,
    rotation_cycle_days integer NOT NULL DEFAULT 90,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (provider_id, key_name),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (provider_id) REFERENCES core.tb_llm_provider (id)
);

-- TB_LLM_ROUTE: 모델 라우팅
CREATE TABLE IF NOT EXISTS core.tb_llm_route (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    route_name varchar(120) NOT NULL,
    provider_id uuid NOT NULL,
    model_id uuid NOT NULL,
    timeout_ms integer NOT NULL DEFAULT 15000,
    fallback_route_id uuid,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (tenant_id, route_name),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id),
    FOREIGN KEY (provider_id) REFERENCES core.tb_llm_provider (id),
    FOREIGN KEY (model_id) REFERENCES core.tb_llm_model (id)
);

-- TB_AUDIT_LOG: 감사 로그(월 파티션)
CREATE TABLE IF NOT EXISTS ops.tb_audit_log (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    actor_user_id uuid,
    action_type varchar(80) NOT NULL,
    target_type varchar(80),
    target_id varchar(120),
    trace_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);
COMMENT ON TABLE ops.tb_audit_log IS '권장 인덱스: (tenant_id, created_at), (tenant_id, actor_user_id, created_at), BRIN(created_at)';

-- TB_OPS_EVENT: 운영 이벤트(월 파티션)
CREATE TABLE IF NOT EXISTS ops.tb_ops_event (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    event_type varchar(80) NOT NULL,
    severity varchar(20) NOT NULL,
    component varchar(80) NOT NULL,
    message text NOT NULL,
    trace_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);
COMMENT ON TABLE ops.tb_ops_event IS '권장 인덱스: (tenant_id, created_at), (tenant_id, severity, created_at), BRIN(created_at)';

-- TB_ERROR_CATALOG: 에러 카탈로그
CREATE TABLE IF NOT EXISTS ops.tb_error_catalog (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    error_code varchar(80) NOT NULL,
    http_status integer NOT NULL,
    user_message_ko varchar(255) NOT NULL,
    retryable boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (error_code)
);

-- TB_NOTIFICATION_RULE: 알림 룰
CREATE TABLE IF NOT EXISTS ops.tb_notification_rule (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    rule_name varchar(120) NOT NULL,
    event_type varchar(80) NOT NULL,
    severity_threshold varchar(20) NOT NULL DEFAULT 'warning',
    channel_type varchar(30) NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_WEBHOOK_ENDPOINT: 웹훅 엔드포인트
CREATE TABLE IF NOT EXISTS ops.tb_webhook_endpoint (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    integration_type varchar(60) NOT NULL,
    endpoint_url text NOT NULL,
    secret_ref varchar(255) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);

-- TB_INTEGRATION_LOG: 연동 로그(월 파티션)
CREATE TABLE IF NOT EXISTS ops.tb_integration_log (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    integration_type varchar(60) NOT NULL,
    endpoint_id uuid,
    http_status integer,
    latency_ms integer,
    trace_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);
COMMENT ON TABLE ops.tb_integration_log IS '권장 인덱스: (tenant_id, integration_type, created_at), BRIN(created_at)';

-- TB_EXPORT_JOB: 내보내기 작업
CREATE TABLE IF NOT EXISTS ops.tb_export_job (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    job_type varchar(40) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'queued',
    output_uri varchar(255),
    row_count bigint,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES core.tb_tenant (id)
);


-- 파티션 인덱스 방식: Partition-per-index
-- 이유: 파티션 생성 시 child 인덱스를 즉시 생성해 누락 위험을 최소화한다.
CREATE OR REPLACE FUNCTION ops.ensure_partition_indexes(p_parent text, p_schema text, p_part text, p_suffix text)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE v_fq text := format('%I.%I', p_schema, p_part);
BEGIN
  IF p_parent = 'core.tb_message' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, conversation_id, created_at DESC)', format('ix_tb_message__tenant_conversation_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, created_at DESC)', format('ix_tb_message__tenant_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_message__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'core.tb_tool_call_log' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, conversation_id, created_at DESC)', format('ix_tb_tool_call_log__tenant_conversation_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_tool_call_log__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'core.tb_rag_search_log' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, conversation_id, created_at DESC)', format('ix_tb_rag_search_log__tenant_conversation_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_rag_search_log__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'ops.tb_audit_log' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, created_at DESC)', format('ix_tb_audit_log__tenant_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, actor_user_id, created_at DESC)', format('ix_tb_audit_log__tenant_actor_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_audit_log__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'ops.tb_ops_event' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, created_at DESC)', format('ix_tb_ops_event__tenant_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, severity, created_at DESC)', format('ix_tb_ops_event__tenant_severity_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_ops_event__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'ops.tb_integration_log' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, integration_type, created_at DESC)', format('ix_tb_integration_log__tenant_type_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_integration_log__created_at_%s', p_suffix), v_fq);
  END IF;
END $$;

CREATE OR REPLACE FUNCTION ops.create_month_partition(p_parent text, p_month date)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE s text := split_part(p_parent, '.', 1);
DECLARE r text := split_part(p_parent, '.', 2);
DECLARE ms date := date_trunc('month', p_month)::date;
DECLARE me date := (ms + interval '1 month')::date;
DECLARE y text := to_char(ms, 'YYYYMM');
DECLARE p text := format('%s_%s', r, y);
BEGIN
  EXECUTE format('CREATE TABLE IF NOT EXISTS %I.%I PARTITION OF %s FOR VALUES FROM (%L) TO (%L)', s, p, p_parent, ms, me);
  PERFORM ops.ensure_partition_indexes(p_parent, s, p, y);
  RETURN format('%I.%I', s, p);
END $$;

CREATE OR REPLACE FUNCTION ops.ensure_future_partitions(months_ahead integer DEFAULT 2)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE i integer; m date;
BEGIN
  IF months_ahead < 0 THEN RAISE EXCEPTION 'months_ahead must be >= 0'; END IF;
  FOR i IN 0..months_ahead LOOP
    m := date_trunc('month', now())::date + make_interval(months => i);
    PERFORM ops.create_month_partition('core.tb_message', m);
    PERFORM ops.create_month_partition('core.tb_tool_call_log', m);
    PERFORM ops.create_month_partition('core.tb_rag_search_log', m);
    PERFORM ops.create_month_partition('ops.tb_audit_log', m);
    PERFORM ops.create_month_partition('ops.tb_ops_event', m);
    PERFORM ops.create_month_partition('ops.tb_integration_log', m);
  END LOOP;
END $$;


CREATE OR REPLACE VIEW ops.v_partition_index_gaps AS
WITH pm AS (
  SELECT 'core.tb_message'::text p UNION ALL SELECT 'core.tb_tool_call_log'
  UNION ALL SELECT 'core.tb_rag_search_log' UNION ALL SELECT 'ops.tb_audit_log'
  UNION ALL SELECT 'ops.tb_ops_event' UNION ALL SELECT 'ops.tb_integration_log'
),
pt AS (
  SELECT pm.p parent_table, n.nspname sch, c.relname rel, regexp_replace(c.relname, '^.*_(\d{6})$', '\1') y
  FROM pg_inherits i
  JOIN pg_class c ON c.oid=i.inhrelid
  JOIN pg_namespace n ON n.oid=c.relnamespace
  JOIN pg_class p ON p.oid=i.inhparent
  JOIN pg_namespace pn ON pn.oid=p.relnamespace
  JOIN pm ON pm.p = pn.nspname || '.' || p.relname
),
exp AS (
  SELECT parent_table, sch, rel,
    CASE parent_table
      WHEN 'core.tb_message' THEN ARRAY[format('ix_tb_message__tenant_conversation_created_%s', y), format('ix_tb_message__tenant_created_%s', y), format('brin_tb_message__created_at_%s', y)]
      WHEN 'core.tb_tool_call_log' THEN ARRAY[format('ix_tb_tool_call_log__tenant_conversation_created_%s', y), format('brin_tb_tool_call_log__created_at_%s', y)]
      WHEN 'core.tb_rag_search_log' THEN ARRAY[format('ix_tb_rag_search_log__tenant_conversation_created_%s', y), format('brin_tb_rag_search_log__created_at_%s', y)]
      WHEN 'ops.tb_audit_log' THEN ARRAY[format('ix_tb_audit_log__tenant_created_%s', y), format('ix_tb_audit_log__tenant_actor_created_%s', y), format('brin_tb_audit_log__created_at_%s', y)]
      WHEN 'ops.tb_ops_event' THEN ARRAY[format('ix_tb_ops_event__tenant_created_%s', y), format('ix_tb_ops_event__tenant_severity_created_%s', y), format('brin_tb_ops_event__created_at_%s', y)]
      WHEN 'ops.tb_integration_log' THEN ARRAY[format('ix_tb_integration_log__tenant_type_created_%s', y), format('brin_tb_integration_log__created_at_%s', y)]
      ELSE ARRAY[]::text[] END expected
  FROM pt
),
act AS (
  SELECT schemaname, tablename, array_agg(indexname) idx FROM pg_indexes GROUP BY schemaname, tablename
)
SELECT e.parent_table, e.sch || '.' || e.rel AS partition_table,
       ARRAY(SELECT unnest(e.expected) EXCEPT SELECT unnest(COALESCE(a.idx, ARRAY[]::text[]))) AS missing_index_names,
       now() AS checked_at
FROM exp e LEFT JOIN act a ON a.schemaname=e.sch AND a.tablename=e.rel;

-- 운영 runbook
-- (a) SELECT ops.ensure_future_partitions(3);
-- (b) SELECT * FROM ops.v_partition_index_gaps WHERE cardinality(missing_index_names) > 0;
-- (c) SELECT ops.ensure_partition_indexes('core.tb_message', 'core', 'tb_message_202601', '202601');
-- 주의: 대형 인덱스는 CREATE INDEX CONCURRENTLY 분리 실행(Flyway/Liquibase 트랜잭션 분리 필요)

SELECT ops.ensure_future_partitions(2);