CREATE TABLE IF NOT EXISTS tb_kb_document (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    title VARCHAR(300) NOT NULL,
    source_type VARCHAR(40),
    category VARCHAR(100),
    effective_date DATE,
    owner VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_kb_document_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id)
);

CREATE TABLE IF NOT EXISTS tb_kb_document_version (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    document_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    approved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_kb_document_version_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_kb_document_version_document FOREIGN KEY (document_id) REFERENCES tb_kb_document(id),
    CONSTRAINT uq_tb_kb_document_version UNIQUE (tenant_id, document_id, version_no)
);

CREATE TABLE IF NOT EXISTS tb_kb_chunk (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    document_version_id UUID NOT NULL,
    chunk_no INTEGER NOT NULL,
    chunk_hash VARCHAR(128) NOT NULL,
    chunk_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    context_header TEXT,
    summary_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_kb_chunk_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_kb_chunk_document_version FOREIGN KEY (document_version_id) REFERENCES tb_kb_document_version(id),
    CONSTRAINT uq_tb_kb_chunk UNIQUE (tenant_id, document_version_id, chunk_no)
);

CREATE TABLE IF NOT EXISTS tb_kb_chunk_embedding (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    chunk_id UUID NOT NULL,
    embedding_vector VARCHAR(8192),
    embedding_dim INTEGER NOT NULL DEFAULT 1536,
    model VARCHAR(120) NOT NULL,
    embedding_input_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tb_kb_chunk_embedding_tenant FOREIGN KEY (tenant_id) REFERENCES tb_tenant(id),
    CONSTRAINT fk_tb_kb_chunk_embedding_chunk FOREIGN KEY (chunk_id) REFERENCES tb_kb_chunk(id),
    CONSTRAINT uq_tb_kb_chunk_embedding UNIQUE (tenant_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_tb_kb_document_version_status
    ON tb_kb_document_version (tenant_id, status, document_id, version_no);

CREATE INDEX IF NOT EXISTS idx_tb_kb_chunk_document_version
    ON tb_kb_chunk (tenant_id, document_version_id, chunk_no);

ALTER TABLE tb_rag_search_log
    ALTER COLUMN conversation_id DROP NOT NULL;

ALTER TABLE tb_rag_citation
    DROP CONSTRAINT IF EXISTS fk_tb_rag_citation_message;

INSERT INTO tb_kb_document (id, tenant_id, title, source_type, category, effective_date, owner)
SELECT '41000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
       'refund_and_delivery_policy', 'policy', 'CS', CURRENT_DATE, 'ops-team'
WHERE NOT EXISTS (SELECT 1 FROM tb_kb_document WHERE id = '41000000-0000-0000-0000-000000000001');

INSERT INTO tb_kb_document_version (id, tenant_id, document_id, version_no, status, approved_at)
SELECT '42000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
       '41000000-0000-0000-0000-000000000001', 1, 'approved', CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM tb_kb_document_version WHERE id = '42000000-0000-0000-0000-000000000001');

INSERT INTO tb_kb_chunk (id, tenant_id, document_version_id, chunk_no, chunk_hash, chunk_text, token_count, context_header, summary_text)
SELECT '43000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
       '42000000-0000-0000-0000-000000000001', 1, 'hash-001',
       'refund is processed to the original method in 3-5 business days after approval.', 25,
       '[DOC] refund_and_delivery_policy | ver=1 | chunk=1/2 | source=policy | category=CS | owner=ops-team',
       'refund approval leads to processing within 3-5 business days.'
WHERE NOT EXISTS (SELECT 1 FROM tb_kb_chunk WHERE id = '43000000-0000-0000-0000-000000000001');

INSERT INTO tb_kb_chunk (id, tenant_id, document_version_id, chunk_no, chunk_hash, chunk_text, token_count, context_header, summary_text)
SELECT '43000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001',
       '42000000-0000-0000-0000-000000000001', 2, 'hash-002',
       'for delayed delivery, compensation is either refund or coupon depending on delay duration.', 29,
       '[DOC] refund_and_delivery_policy | ver=1 | chunk=2/2 | source=policy | category=CS | owner=ops-team',
       'delivery delay compensation is chosen by delay duration and order state.'
WHERE NOT EXISTS (SELECT 1 FROM tb_kb_chunk WHERE id = '43000000-0000-0000-0000-000000000002');

INSERT INTO tb_kb_chunk_embedding (id, tenant_id, chunk_id, embedding_vector, embedding_dim, model, embedding_input_text)
SELECT '44000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
       '43000000-0000-0000-0000-000000000001', '[0.11,0.07,0.15]', 1536, 'demo-embedding-v1',
       '[DOC] refund_and_delivery_policy | ver=1 | chunk=1/2\nrefund approval leads to processing within 3-5 business days.'
WHERE NOT EXISTS (SELECT 1 FROM tb_kb_chunk_embedding WHERE id = '44000000-0000-0000-0000-000000000001');

INSERT INTO tb_kb_chunk_embedding (id, tenant_id, chunk_id, embedding_vector, embedding_dim, model, embedding_input_text)
SELECT '44000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001',
       '43000000-0000-0000-0000-000000000002', '[0.13,0.09,0.12]', 1536, 'demo-embedding-v1',
       '[DOC] refund_and_delivery_policy | ver=1 | chunk=2/2\ndelivery delay compensation is chosen by delay duration and order state.'
WHERE NOT EXISTS (SELECT 1 FROM tb_kb_chunk_embedding WHERE id = '44000000-0000-0000-0000-000000000002');
