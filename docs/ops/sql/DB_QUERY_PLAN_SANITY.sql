-- Optional query-plan sanity script (manual run, not CI default).
-- Run after migrations: psql -U aichatbot -d aichatbot -f docs/ops/sql/DB_QUERY_PLAN_SANITY.sql

-- 1) Similarity retrieval path (tenant + approved KB chunks + vector distance).
-- If there is no non-null embedding_vector_1536 row yet, this still validates join/filter/plan shape.
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
WITH probe AS (
    SELECT embedding_vector_1536 AS qv
    FROM tb_kb_chunk_embedding
    WHERE embedding_vector_1536 IS NOT NULL
    LIMIT 1
)
SELECT
    c.id AS chunk_id,
    dv.document_id,
    c.chunk_no
FROM probe
JOIN tb_kb_chunk_embedding e
  ON e.embedding_vector_1536 IS NOT NULL
JOIN tb_kb_chunk c
  ON c.id = e.chunk_id
 AND c.tenant_id = e.tenant_id
JOIN tb_kb_document_version dv
  ON dv.id = c.document_version_id
 AND dv.tenant_id = c.tenant_id
WHERE e.tenant_id = '00000000-0000-0000-0000-000000000001'
  AND dv.status = 'approved'
ORDER BY e.embedding_vector_1536 <=> probe.qv
LIMIT 5;

-- 2) Recent conversation/message list path.
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT
    m.id,
    m.conversation_id,
    m.created_at
FROM tb_message m
WHERE m.tenant_id = '00000000-0000-0000-0000-000000000001'
  AND m.conversation_id = '00000000-0000-0000-0000-000000000001'
ORDER BY m.created_at ASC
LIMIT 50;
