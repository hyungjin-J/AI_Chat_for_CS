# MVP Assumptions

This document captures safety-preserving assumptions made to implement the agent-console-first MVP quickly.

## Scope assumptions

1. API workbook rows are used as the source of truth for path, role intent, and common guard rules.
2. MVP uses AGENT-first flow; customer widget flows are intentionally not implemented.
3. `answer_id` is treated as `message_id` for citation lookup.

## Auth assumptions

1. Seeded demo users are used for MVP login:
   - `agent1 / agent1-pass`
   - `admin1 / admin1-pass`
   - `ops1 / ops1-pass`
2. Refresh tokens are stored as hash in `TB_AUTH_SESSION`.
3. Header role auth fallback remains enabled by default for legacy tests (`APP_SECURITY_ALLOW_HEADER_AUTH=true`).

## Data/storage assumptions

1. Flyway creates only minimum MVP tables required by request.
2. H2 is the default runtime DB for local test execution; Postgres can be used by overriding datasource env vars.
3. `trace_id` DB columns are UUID in spec; non-UUID incoming trace headers are normalized deterministically to UUID for storage.

## RAG/LLM assumptions

1. Retrieval uses deterministic keyword fallback (`keyword_fallback`) against seeded in-memory chunks.
2. If retrieval returns no usable evidence, fail-closed is triggered and only `safe_response` is emitted.
3. LLM output must be Answer Contract JSON only; raw unvalidated model text is never streamed.
4. If Ollama is unavailable, system falls back to safe contract JSON (not free-text fallback).

## Contract and safety assumptions

1. Answer Contract v1 validation uses JSON Schema + business rules:
   - citation required for `response_type=answer`
   - evidence score must be above configured threshold
2. Any contract failure leads to fail-closed (`safe_response` then `done`).
3. PII masking is applied before model prompt construction and before persistence/stream payload emission.

## Budget/rate assumptions

1. Budget guard is enforced for input tokens, output tokens, tool calls, top_k, and per-session token budget.
2. SSE concurrency is enforced per user key.
3. Over-limit responses use documented 429 error codes and rate-limit headers.

## Known MVP limits (PHASE2)

1. Idempotency storage is in-memory; persistence-backed dedupe table is not yet added.
2. Retrieval is not yet pgvector-based.
3. Header auth fallback should be disabled in production and replaced by JWT-only enforcement.
4. No production-grade distributed SSE concurrency store (single-node in-memory guard only).
