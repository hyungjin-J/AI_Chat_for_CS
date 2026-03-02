# RAG Regression Harness

## Dataset Schema (fixed)
- `eval/datasets/rag_regression_cases.csv`
- Columns:
  - `case_id`
  - `tenant_key`
  - `user_role`
  - `query`
  - `expected_policy_bundle`
  - `requires_citation` (`0` or `1`)
  - `notes`

## Run
```bash
python eval/seed_kb_minimal.py --base-url http://localhost:8080 --tenant-key demo-tenant --min-docs 3
python eval/run_rag_regression.py --base-url http://localhost:8080 --dataset eval/datasets/rag_regression_cases.csv --out eval/out/latest
python eval/assert_rag_quality_gate.py --report eval/out/latest/report.json --thresholds eval/thresholds.yaml
```

## Failure reason codes
- `DATA_UNAVAILABLE`
- `INDEXING_INCOMPLETE`
- `PROVIDER_UNAVAILABLE`
- `THRESHOLD_UNDERSHOOT`
- `METRIC_COMPUTATION_BUG`

## Outputs
- `eval/out/latest/report.json`
- `eval/out/latest/summary.csv`
- `docs/review/mvp_verification_pack/artifacts/rag_regression_gate_YYYYMMDD.txt`
- `docs/review/mvp_verification_pack/artifacts/rag_regression_gate_YYYYMMDD.json`
