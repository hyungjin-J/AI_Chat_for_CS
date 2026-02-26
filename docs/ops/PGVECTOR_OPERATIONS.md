# PGVECTOR_OPERATIONS

## 1) Purpose and scope
- Standardize pgvector IVFFlat operations for the current PostgreSQL migration baseline.
- Provide deterministic tuning steps for `lists` and `ivfflat.probes`.
- Provide load/reload runbook for `ANALYZE`, `REINDEX`, and index rebuild.

Out of scope:
- HNSW rollout in production. HNSW is blocked until a separate experiment document and at least 3 benchmark artifacts are approved.

## 2) Current baseline (SSOT: V11)
Source of truth:
- `backend/src/main/resources/db/postgresql-migration/V11__pgvector_enablement.sql`

Current fixed structure:
- `CREATE EXTENSION IF NOT EXISTS vector;`
- Column: `tb_kb_chunk_embedding.embedding_vector_1536 vector(1536)`
- Index: `idx_tb_kb_chunk_embedding_vec_cosine_ivfflat`
- Index options: `WITH (lists = 100)`
- Post-migration stats refresh: `ANALYZE tb_kb_chunk_embedding;`

Important note:
- Current application runtime does not enforce a global `ivfflat.probes` value.
- Probe tuning is performed through SQL/session control and benchmark evidence.

## 3) IVFFlat lists guidance (data-size based)
Starting formula:
- `lists_start = clamp(round(sqrt(N)), 100, 4000)`
- `N = row count where embedding_vector_1536 is NOT NULL for target tenant/workload`

Recommended ranges:
- `< 50k`: `100 ~ 200`
- `50k ~ 200k`: `200 ~ 500`
- `200k ~ 1M`: `500 ~ 1200`
- `> 1M`: `1200 ~ 4000`

Operational rules:
- Changing `lists` requires index rebuild.
- Do not change `lists` as a first response to incidents; tune `probes` first.

## 4) probes tuning procedure
Default probe sweep:
- `1, 2, 4, 8, 16, 32`

Principle:
- Higher probes generally improve recall but increase latency.
- Keep `lists` fixed while sweeping probes.

Benchmark command (local compose):
```powershell
python scripts/vector_recall_latency_bench.py `
  --method docker-exec `
  --compose-file infra/docker-compose.yml `
  --compose-service postgres `
  --database aichatbot `
  --db-user aichatbot `
  --tenant-id 00000000-0000-0000-0000-000000000001 `
  --top-k 10 `
  --query-count 30 `
  --probe-values 1,2,4,8,16,32 `
  --output-txt docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_20260226.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_20260226.json
```

Baseline delta comparison:
```powershell
python scripts/vector_recall_latency_bench.py `
  --method docker-exec `
  --compose-file infra/docker-compose.yml `
  --compose-service postgres `
  --database aichatbot `
  --db-user aichatbot `
  --tenant-id 00000000-0000-0000-0000-000000000001 `
  --top-k 10 `
  --query-count 30 `
  --probe-values 1,2,4,8,16,32 `
  --baseline-json docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_baseline.json `
  --max-recall-drop 0.03 `
  --max-p95-regression-ratio 1.30 `
  --output-txt docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_20260226.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_20260226.json
```

To set/update baseline:
- Copy a known-good benchmark JSON to:
  - `docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_baseline.json`
- Use only same workload shape (`tenant_id`, `top_k`, `query_count`, probe sweep).

## 5) ANALYZE / REINDEX / rebuild policy
Run `ANALYZE`:
- Immediately after migration or bulk load/reload.
- At least daily when embedding writes are frequent.
- Immediately when `n_dead_tup` surges or query plan shifts unexpectedly.

Command:
```sql
ANALYZE tb_kb_chunk_embedding;
```

Run `REINDEX INDEX CONCURRENTLY` when:
- Latency regresses after repeated update/delete cycles.
- Index bloat symptoms appear in diagnostics.

Command:
```sql
REINDEX INDEX CONCURRENTLY idx_tb_kb_chunk_embedding_vec_cosine_ivfflat;
```

Use DROP/CREATE rebuild when:
- Data reload ratio is large (for example, 20%+ changed rows).
- You are changing `lists`.

Rebuild template:
```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_tb_kb_chunk_embedding_vec_cosine_ivfflat;
CREATE INDEX CONCURRENTLY idx_tb_kb_chunk_embedding_vec_cosine_ivfflat
    ON tb_kb_chunk_embedding USING ivfflat (embedding_vector_1536 vector_cosine_ops)
    WITH (lists = 500);
ANALYZE tb_kb_chunk_embedding;
```

## 6) Bulk load / reload runbook
1. Prepare:
- Freeze heavy retrieval jobs if possible.
- Capture pre-change benchmark artifact.

2. Load path:
- Insert/update embeddings in batches.
- Keep tenant isolation (`tenant_id`) enforced.

3. Post-load immediate actions:
- `ANALYZE tb_kb_chunk_embedding;`
- Run benchmark sweep and compare to baseline delta.

4. If regression remains:
- Tune probes first.
- If still unstable, run `REINDEX INDEX CONCURRENTLY`.
- If changing `lists` is needed, perform rebuild window with explicit evidence.

5. Evidence persistence:
- Save txt/json benchmark outputs under `docs/review/mvp_verification_pack/artifacts/`.

## 7) Failure indicators and immediate response
Indicators:
- Recall drop beyond baseline tolerance.
- p95 latency ratio beyond tolerance.
- Query plan drift after data churn.
- Dead tuple growth in diagnostics.

Immediate response order:
1. Confirm data/state with diagnostics and `ANALYZE`.
2. Re-sweep probes.
3. Reindex.
4. Rebuild IVFFlat with reviewed lists value.
5. Re-run benchmark and archive evidence.

## 8) SQL snippets for operator checks
Eligible vector row count for target tenant:
```sql
SELECT COUNT(*)
FROM tb_kb_chunk_embedding e
JOIN tb_kb_chunk c ON c.id = e.chunk_id AND c.tenant_id = e.tenant_id
JOIN tb_kb_document_version dv ON dv.id = c.document_version_id AND dv.tenant_id = c.tenant_id
WHERE e.tenant_id = '00000000-0000-0000-0000-000000000001'
  AND e.embedding_vector_1536 IS NOT NULL
  AND dv.status = 'approved';
```

Session-level probes override for manual investigation:
```sql
BEGIN;
SET LOCAL ivfflat.probes = 16;
-- retrieval query here
ROLLBACK;
```
