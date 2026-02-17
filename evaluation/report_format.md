# RAG KPI Evaluation Report Format

## 1) 목적
`evaluation/run_rag_kpi_eval.py`가 생성하는 결과 포맷과 게이트 기준을 표준화한다.

## 2) 출력 파일
- 기본 경로: `evaluation/report.json`
- 인코딩: UTF-8

## 3) JSON Top-level Schema
```json
{
  "generated_at": "2026-02-17T00:00:00+00:00",
  "mode": "live | dry_run",
  "summary": {
    "total_cases": 0,
    "passed_cases": 0,
    "failed_cases": 0
  },
  "results": [
    {
      "case_id": "RAG-KPI-0001",
      "tenant_id": "tenant-alpha",
      "scenario": "normal_rag_window",
      "from_ts": "2026-02-10T00:00:00+00:00",
      "to_ts": "2026-02-10T23:59:59+00:00",
      "passed": true,
      "failed_kpis": [],
      "kpis": [
        {
          "kpi_id": "KPI-AC-001",
          "value": 99.8,
          "unit": "pct",
          "target": ">= 99.5",
          "passed": true,
          "severity": "ok",
          "detail": "Answer Contract pass rate"
        }
      ]
    }
  ]
}
```

## 4) KPI Gate Rules
- 케이스 단위 `passed=true` 조건:
  - 모든 KPI `passed=true`
- 전체 리포트 `PASS` 조건:
  - `failed_cases == 0`

## 5) Hard Fail Conditions (즉시 실패)
아래 조건은 단일 케이스에서 1건이라도 만족하면 해당 케이스 즉시 `FAIL`.

- `KPI-FF-001` (free-text fallback leakage) `>= 1`
- `KPI-PII-001` (PII suspected count) `>= 1`
- `KPI-TR-001` (trace coverage) `< 99.9`
- `KPI-LAT-001` (p95 E2E) `> 15000ms`
- `KPI-LAT-002` (p95 first-token) `> 2000ms`

## 6) 운영 연계
- 경보 라우팅/대응은 `docs/ops/rag-kpi.md` 5장 매핑을 따른다.
- trace drilldown은 `OPS-TRACE-QUERY`를 사용한다.

