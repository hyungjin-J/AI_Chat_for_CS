-- DB readiness foundation: safe, high-ROI indexes derived from mapper access patterns.
-- Keep all statements idempotent for deterministic local repro.

CREATE INDEX IF NOT EXISTS idx_tb_conversation_tenant_created_at
    ON tb_conversation (tenant_id, created_at DESC, id);

CREATE INDEX IF NOT EXISTS idx_tb_message_tenant_conversation_created_at
    ON tb_message (tenant_id, conversation_id, created_at ASC, id);

CREATE INDEX IF NOT EXISTS idx_tb_stream_event_tenant_message_seq
    ON tb_stream_event (tenant_id, message_id, event_seq);

CREATE INDEX IF NOT EXISTS idx_tb_rag_search_log_tenant_conversation_created
    ON tb_rag_search_log (tenant_id, conversation_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tb_user_role_user_role
    ON tb_user_role (user_id, role_id);

CREATE INDEX IF NOT EXISTS idx_tb_kb_chunk_embedding_tenant_model
    ON tb_kb_chunk_embedding (tenant_id, model, chunk_id);
