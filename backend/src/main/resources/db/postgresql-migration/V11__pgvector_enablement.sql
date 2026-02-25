-- PostgreSQL-only migration.
-- Enables pgvector and provisions a dedicated vector column/index without changing existing text column semantics.

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE tb_kb_chunk_embedding
    ADD COLUMN IF NOT EXISTS embedding_vector_1536 vector(1536);

CREATE INDEX IF NOT EXISTS idx_tb_kb_chunk_embedding_vec_cosine_ivfflat
    ON tb_kb_chunk_embedding USING ivfflat (embedding_vector_1536 vector_cosine_ops)
    WITH (lists = 100);

ANALYZE tb_kb_chunk_embedding;
