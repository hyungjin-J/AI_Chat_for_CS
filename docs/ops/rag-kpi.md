# RAG Production KPI Targets & Measurement

## 1. Scope
- 목적: RAG 품질/신뢰성 KPI를 운영 게이트 수준으로 정의하고, 기존 로그/테이블에서 계산 가능하게 표준화한다.
- 적용 ReqID: `AI-004`, `AI-005`, `AI-009`, `RAG-003`, `PERF-001`, `SYS-004`, `OPS-001`, `OPS-100`
- 적용 ProgramID:
  - `OPS-ADMIN-DASHBOARD-SUMMARY` (`GET /v1/admin/dashboard/summary`)
  - `OPS-ADMIN-DASHBOARD-SERIES` (`GET /v1/admin/dashboard/series`)
  - `OPS-METRIC-SUMMARY` (`GET /v1/ops/metrics/summary`)
  - `OPS-TRACE-QUERY` (`GET /v1/ops/traces`)

## 2. Measurement Principles
- Answer Contract 강제: 스키마/인용/근거 실패는 `fail-closed`로 처리하며 KPI에서 별도 실패로 집계한다.
- 자유 텍스트 fallback 허용 금지: 검증 실패 후 사용자 노출 텍스트 우회는 위반으로 집계한다.
- Trace 강제: KPI 산출 대상 이벤트는 `trace_id` 연결 가능해야 한다.
- PII 배제: `query_text_masked`, `excerpt_masked` 등 마스킹 컬럼 기준으로만 측정한다.
- 집계 단위:
  - 기본 시간축: `1m/5m/1h/1d`
  - 기본 차원: `tenant_id`, `provider_id`, `model_id`, `endpoint`, `rule_code`, `tool_name`

### 2.1 Error Code Basis (UI/UX 01_에러메시지코드)
KPI 위반 판정 및 알림 메시지는 `01_에러메시지코드` 시트의 아래 코드를 기준으로 분류한다.
- `AI-009-422-SCHEMA`
- `AI-009-409-CITATION`
- `AI-009-409-EVIDENCE`
- `AI-009-200-SAFE`
- `SSE-002-504`
- `SSE-003-409-RESUME`
- `SYS-004-409-TRACE`
- `API-008-429-BUDGET`
- `SEC-003-409-PII`

## 3. KPI Catalog
| KPI ID | KPI 명 | Formula | Data Source | Breakdown | Warn | Critical | ReqID |
|---|---|---|---|---|---|---|---|
| `KPI-AC-001` | Answer Contract Pass Rate | `1 - contract_fail_count / response_attempt_count` | `TB_GUARDRAIL_EVENT`, `TB_STREAM_EVENT` | tenant, model, time | `< 99.5%` | `< 99.0%` | AI-009, RAG-003 |
| `KPI-CT-001` | Citation Coverage Rate | `cited_response_count / rag_response_count` | `TB_RAG_CITATION`, `TB_GENERATION_LOG`, `TB_RAG_SEARCH_LOG` | tenant, provider/model, time | `< 99.0%` | `< 98.0%` | AI-005, RAG-003 |
| `KPI-EV-001` | Zero Evidence Rate | `zero_evidence_count / rag_response_count` | `TB_RAG_CITATION`, `TB_GUARDRAIL_EVENT`, `TB_GENERATION_LOG`, `TB_RAG_SEARCH_LOG` | tenant, time | `> 1.0%` | `> 2.0%` | AI-004, AI-005 |
| `KPI-FC-001` | Fail-Closed Conversion Rate | `safe_response_count / response_attempt_count` | `TB_STREAM_EVENT` | tenant, endpoint, time | `> 2.0%` | `> 5.0%` | AI-009, RAG-003 |
| `KPI-FF-001` | Free-text Fallback Leakage | `fallback_leak_count` | `TB_STREAM_EVENT`, `TB_RAG_CITATION`, `TB_GUARDRAIL_EVENT` | tenant, time | `>= 1` | `>= 1` | AI-009, RAG-003 |
| `KPI-TR-001` | Trace Coverage | `events_with_trace / trace_required_events` | `TB_GUARDRAIL_EVENT`, `TB_RAG_SEARCH_LOG`, `TB_GENERATION_LOG`, `TB_TOOL_CALL_LOG` | tenant, table, time | `< 99.99%` | `< 99.9%` | SYS-004 |
| `KPI-PII-001` | PII Leak Suspected Count | `pii_pattern_match_count` | `TB_RAG_SEARCH_LOG`, `TB_RAG_CITATION` | tenant, source_table, time | `>= 1` | `>= 1` | AI-009, SYS-004 |
| `KPI-LAT-001` | E2E Latency P95 | `p95_latency_ms` | `TB_API_METRIC_HOURLY` | tenant, endpoint, method, status | `> 12000ms` | `> 15000ms` | PERF-001, OPS-100 |
| `KPI-LAT-002` | First Token P95 | `P95(first_token_created_at - message_created_at)` | `TB_STREAM_EVENT` | tenant, time | `> 1800ms` | `> 2000ms` | PERF-001 |
| `KPI-SSE-001` | Stream Completion Rate | `done_count / stream_started_count` | `TB_STREAM_EVENT` | tenant, endpoint, time | `< 99.0%` | `< 98.0%` | PERF-001, OPS-001 |
| `KPI-TOOL-001` | Tool Call Success Rate | `2xx_tool_calls / total_tool_calls` | `TB_TOOL_CALL_LOG` | tenant, tool_name, time | `< 99.0%` | `< 97.0%` | OPS-001, OPS-100 |
| `KPI-FB-001` | Positive Feedback Rate | `positive_feedback_count / total_feedback_count` | `TB_MESSAGE_FEEDBACK` | tenant, feedback_type, time | `< 70%` | `< 60%` | OPS-001 |

## 4. SQL / Pseudo Query Examples
기본 파라미터:
- `:from_ts`, `:to_ts`, `:tenant_id` (옵션)

### KPI-AC-001 Answer Contract Pass Rate
```sql
WITH attempts AS (
    SELECT tenant_id, message_id, message_created_at
    FROM core.tb_stream_event
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND event_type IN ('done', 'safe_response', 'error')
      AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid)
    GROUP BY tenant_id, message_id, message_created_at
),
contract_fail AS (
    SELECT tenant_id, message_id, message_created_at
    FROM core.tb_guardrail_event
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid)
      AND rule_code IN ('AI-009-422-SCHEMA', 'AI-009-409-CITATION', 'AI-009-409-EVIDENCE')
      AND lower(action) IN ('block', 'deny', 'fail_closed')
    GROUP BY tenant_id, message_id, message_created_at
)
SELECT
    COUNT(*) AS response_attempt_count,
    (SELECT COUNT(*) FROM contract_fail) AS contract_fail_count,
    ROUND(100.0 * (1 - (SELECT COUNT(*) FROM contract_fail)::numeric / NULLIF(COUNT(*), 0)), 4) AS answer_contract_pass_rate_pct
FROM attempts;
```

### KPI-CT-001 Citation Coverage Rate
```sql
WITH rag_generated AS (
    SELECT g.tenant_id, g.message_id, g.message_created_at
    FROM core.tb_generation_log g
    WHERE g.created_at BETWEEN :from_ts AND :to_ts
      AND (:tenant_id IS NULL OR g.tenant_id = :tenant_id::uuid)
      AND EXISTS (
          SELECT 1
          FROM core.tb_rag_search_log rs
          WHERE rs.tenant_id = g.tenant_id
            AND rs.trace_id = g.trace_id
      )
),
cited AS (
    SELECT DISTINCT tenant_id, message_id, message_created_at
    FROM core.tb_rag_citation
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid)
)
SELECT
    COUNT(*) AS rag_response_count,
    COUNT(*) FILTER (
        WHERE (tenant_id, message_id, message_created_at) IN (SELECT tenant_id, message_id, message_created_at FROM cited)
    ) AS cited_response_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE (tenant_id, message_id, message_created_at) IN (SELECT tenant_id, message_id, message_created_at FROM cited)
        )::numeric / NULLIF(COUNT(*), 0), 4
    ) AS citation_coverage_rate_pct
FROM rag_generated;
```

### KPI-EV-001 Zero Evidence Rate
```sql
WITH rag_generated AS (
    SELECT g.tenant_id, g.message_id, g.message_created_at
    FROM core.tb_generation_log g
    WHERE g.created_at BETWEEN :from_ts AND :to_ts
      AND (:tenant_id IS NULL OR g.tenant_id = :tenant_id::uuid)
      AND EXISTS (
          SELECT 1
          FROM core.tb_rag_search_log rs
          WHERE rs.tenant_id = g.tenant_id
            AND rs.trace_id = g.trace_id
      )
),
zero_citation AS (
    SELECT rg.*
    FROM rag_generated rg
    WHERE NOT EXISTS (
        SELECT 1
        FROM core.tb_rag_citation c
        WHERE c.tenant_id = rg.tenant_id
          AND c.message_id = rg.message_id
          AND c.message_created_at = rg.message_created_at
    )
),
evidence_fail AS (
    SELECT DISTINCT tenant_id, message_id, message_created_at
    FROM core.tb_guardrail_event
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND rule_code = 'AI-009-409-EVIDENCE'
)
SELECT
    COUNT(*) AS rag_response_count,
    COUNT(*) FILTER (
        WHERE (tenant_id, message_id, message_created_at) IN (
            SELECT tenant_id, message_id, message_created_at FROM zero_citation
            UNION
            SELECT tenant_id, message_id, message_created_at FROM evidence_fail
        )
    ) AS zero_evidence_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE (tenant_id, message_id, message_created_at) IN (
                SELECT tenant_id, message_id, message_created_at FROM zero_citation
                UNION
                SELECT tenant_id, message_id, message_created_at FROM evidence_fail
            )
        )::numeric / NULLIF(COUNT(*), 0), 4
    ) AS zero_evidence_rate_pct
FROM rag_generated;
```

### KPI-FC-001 Fail-Closed Conversion Rate
```sql
SELECT
    COUNT(DISTINCT (tenant_id, message_id, message_created_at)) FILTER (WHERE event_type IN ('done', 'safe_response', 'error')) AS response_attempt_count,
    COUNT(DISTINCT (tenant_id, message_id, message_created_at)) FILTER (WHERE event_type = 'safe_response') AS safe_response_count,
    ROUND(
        100.0 * COUNT(DISTINCT (tenant_id, message_id, message_created_at)) FILTER (WHERE event_type = 'safe_response')::numeric
        / NULLIF(COUNT(DISTINCT (tenant_id, message_id, message_created_at)) FILTER (WHERE event_type IN ('done', 'safe_response', 'error')), 0),
        4
    ) AS fail_closed_conversion_rate_pct
FROM core.tb_stream_event
WHERE created_at BETWEEN :from_ts AND :to_ts
  AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid);
```

### KPI-FF-001 Free-text Fallback Leakage
```sql
WITH done_msg AS (
    SELECT DISTINCT tenant_id, message_id, message_created_at
    FROM core.tb_stream_event
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND event_type = 'done'
),
safe_msg AS (
    SELECT DISTINCT tenant_id, message_id, message_created_at
    FROM core.tb_stream_event
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND event_type = 'safe_response'
),
cited AS (
    SELECT DISTINCT tenant_id, message_id, message_created_at
    FROM core.tb_rag_citation
    WHERE created_at BETWEEN :from_ts AND :to_ts
),
blocked AS (
    SELECT DISTINCT tenant_id, message_id, message_created_at
    FROM core.tb_guardrail_event
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND rule_code LIKE 'AI-009-%'
)
SELECT COUNT(*) AS fallback_leak_count
FROM done_msg d
WHERE (d.tenant_id, d.message_id, d.message_created_at) NOT IN (SELECT tenant_id, message_id, message_created_at FROM cited)
  AND (d.tenant_id, d.message_id, d.message_created_at) NOT IN (SELECT tenant_id, message_id, message_created_at FROM safe_msg)
  AND (d.tenant_id, d.message_id, d.message_created_at) NOT IN (SELECT tenant_id, message_id, message_created_at FROM blocked);
```

### KPI-TR-001 Trace Coverage
```sql
WITH events AS (
    SELECT tenant_id, trace_id, created_at, 'tb_guardrail_event' AS source FROM core.tb_guardrail_event
    UNION ALL
    SELECT tenant_id, trace_id, created_at, 'tb_rag_search_log' AS source FROM core.tb_rag_search_log
    UNION ALL
    SELECT tenant_id, trace_id, created_at, 'tb_generation_log' AS source FROM core.tb_generation_log
    UNION ALL
    SELECT tenant_id, trace_id, created_at, 'tb_tool_call_log' AS source FROM core.tb_tool_call_log
)
SELECT
    source,
    COUNT(*) AS trace_required_events,
    COUNT(*) FILTER (WHERE trace_id IS NOT NULL) AS events_with_trace,
    ROUND(100.0 * COUNT(*) FILTER (WHERE trace_id IS NOT NULL)::numeric / NULLIF(COUNT(*), 0), 4) AS trace_coverage_pct
FROM events
WHERE created_at BETWEEN :from_ts AND :to_ts
  AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid)
GROUP BY source;
```

### KPI-PII-001 PII Leak Suspected Count
```sql
WITH masked_text AS (
    SELECT tenant_id, created_at, query_text_masked AS text_value, 'tb_rag_search_log' AS source
    FROM core.tb_rag_search_log
    UNION ALL
    SELECT tenant_id, created_at, excerpt_masked AS text_value, 'tb_rag_citation' AS source
    FROM core.tb_rag_citation
)
SELECT
    source,
    COUNT(*) FILTER (
        WHERE text_value ~* '[A-Z0-9._%+-]+@[A-Z0-9.-]+'
           OR text_value ~* '(\\+?\\d[\\d\\-\\s]{7,}\\d)'
    ) AS pii_pattern_match_count
FROM masked_text
WHERE created_at BETWEEN :from_ts AND :to_ts
  AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid)
GROUP BY source;
```

### KPI-LAT-001 E2E Latency P95
```sql
SELECT
    tenant_id,
    endpoint,
    method,
    MAX(p95_latency_ms) AS p95_e2e_latency_ms
FROM core.tb_api_metric_hourly
WHERE metric_hour BETWEEN :from_ts AND :to_ts
  AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid)
  AND endpoint LIKE '%/stream%'
GROUP BY tenant_id, endpoint, method;
```

### KPI-LAT-002 First Token P95
```sql
WITH first_token AS (
    SELECT
        tenant_id,
        message_id,
        message_created_at,
        MIN(created_at) AS first_token_at
    FROM core.tb_stream_event
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND event_type = 'token'
      AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid)
    GROUP BY tenant_id, message_id, message_created_at
)
SELECT
    tenant_id,
    percentile_cont(0.95) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (first_token_at - message_created_at)) * 1000
    ) AS p95_first_token_ms
FROM first_token
GROUP BY tenant_id;
```

### KPI-SSE-001 Stream Completion Rate
```sql
WITH started AS (
    SELECT DISTINCT tenant_id, message_id, message_created_at
    FROM core.tb_stream_event
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND event_type = 'token'
),
done_msg AS (
    SELECT DISTINCT tenant_id, message_id, message_created_at
    FROM core.tb_stream_event
    WHERE created_at BETWEEN :from_ts AND :to_ts
      AND event_type = 'done'
)
SELECT
    COUNT(*) AS stream_started_count,
    COUNT(*) FILTER (
        WHERE (tenant_id, message_id, message_created_at) IN (SELECT tenant_id, message_id, message_created_at FROM done_msg)
    ) AS done_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE (tenant_id, message_id, message_created_at) IN (SELECT tenant_id, message_id, message_created_at FROM done_msg)
        )::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS stream_completion_rate_pct
FROM started;
```

### KPI-TOOL-001 Tool Call Success Rate
```sql
SELECT
    tenant_id,
    tool_name,
    COUNT(*) AS total_tool_calls,
    COUNT(*) FILTER (WHERE http_status BETWEEN 200 AND 299) AS ok_tool_calls,
    ROUND(100.0 * COUNT(*) FILTER (WHERE http_status BETWEEN 200 AND 299)::numeric / NULLIF(COUNT(*), 0), 4) AS tool_success_rate_pct
FROM core.tb_tool_call_log
WHERE created_at BETWEEN :from_ts AND :to_ts
  AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid)
GROUP BY tenant_id, tool_name;
```

### KPI-FB-001 Positive Feedback Rate
```sql
SELECT
    tenant_id,
    feedback_type,
    COUNT(*) AS total_feedback_count,
    COUNT(*) FILTER (
        WHERE (score IS NOT NULL AND score >= 4)
           OR lower(feedback_type) IN ('thumbs_up', 'positive')
    ) AS positive_feedback_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE (score IS NOT NULL AND score >= 4)
               OR lower(feedback_type) IN ('thumbs_up', 'positive')
        )::numeric / NULLIF(COUNT(*), 0),
        4
    ) AS positive_feedback_rate_pct
FROM core.tb_message_feedback
WHERE created_at BETWEEN :from_ts AND :to_ts
  AND (:tenant_id IS NULL OR tenant_id = :tenant_id::uuid)
GROUP BY tenant_id, feedback_type;
```

## 5. Alert Routing & Runbook Mapping
| Trigger KPI | Severity Rule | Route | Primary Runbook |
|---|---|---|---|
| `KPI-AC-001`, `KPI-FC-001`, `KPI-FF-001` | Warn/Critical 임계치 하회 또는 `fallback_leak_count >= 1` | AI On-call + OPS | `docs/ops/runbook/playbooks/answer_contract_fail_spike.md` |
| `KPI-CT-001`, `KPI-EV-001` | 인용 커버리지 하락, zero-evidence 상승 | RAG On-call + OPS | `docs/ops/runbook/playbooks/rag_zero_evidence_spike.md` |
| `KPI-LAT-001`, `KPI-LAT-002`, `KPI-SSE-001` | PERF 임계치 위반 | SRE + OPS | `docs/ops/runbook/playbooks/sse_streaming_degradation.md` |
| `KPI-TR-001` | trace coverage 임계치 하락 | SRE + Platform | `docs/ops/runbook/playbooks/trace_id_missing.md` |
| `KPI-PII-001` | 1건 이상 즉시 경보 | Security + OPS | `docs/ops/runbook/playbooks/pii_leak_suspected.md` |
| `KPI-TOOL-001` | Tool 성공률 임계치 하락 | Platform + OPS | `docs/ops/runbook/playbooks/llm_provider_outage.md` |

## 6. Dashboard/API Binding
- `OPS-ADMIN-DASHBOARD-SUMMARY`
  - 최신 KPI 상태(`normal/warn/critical`), 위반 카운트, 현재 trace drilldown 링크 표시
- `OPS-ADMIN-DASHBOARD-SERIES`
  - KPI별 시계열(`1m/5m/1h/1d`)과 tenant/provider/model 필터 제공
- `OPS-METRIC-SUMMARY`
  - 상위 SLO KPI (`KPI-LAT-001`, `KPI-LAT-002`, `KPI-TR-001`) 요약 제공
- `OPS-TRACE-QUERY`
  - 경보 KPI와 연결된 `trace_id` 조회 및 root-cause drilldown 제공

## 7. Gate Rules (Production)
- 배포/운영 게이트 실패 조건:
  - `KPI-FF-001 >= 1`
  - `KPI-PII-001 >= 1`
  - `KPI-TR-001 < 99.9%`
  - `KPI-LAT-001 > 15000ms` 또는 `KPI-LAT-002 > 2000ms`
- 위 조건 충족 시 자동 경보 + 대응 플레이북 실행, 자유 텍스트 우회 대응 금지
