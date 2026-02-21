# PROVIDER REGRESSION EVIDENCE (SSOT)

- last_synced_at: 2026-02-21 03:25 (KST)
- source_of_truth_for_provider_evidence: this file
- related_test_id: `LLM-PROVIDER-001`

## Policy
- PR policy: conditional execution (`ENABLE_PROVIDER_REGRESSION == true`)
  - When executed in PR, `SKIPPED` is treated as failure.
  - When condition is not met, PR can skip provider regression by policy.
- Nightly policy: required execution (`provider-regression-nightly.yml`)
  - Nightly run must not end with `SKIPPED`.

## Current Latest Result In Pack
- latest_result_status: SKIPPED
- latest_result_reason: docker daemon unavailable in local environment
- latest_result_artifact: `docs/review/mvp_verification_pack/artifacts/provider_regression_gap_closure_output.txt`
- latest_result_log_untracked: `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`

## Latest PASS Evidence
- latest_pass_utc: 2026-02-18T15:36:00Z
- latest_pass_commit: 3e057a3
- latest_pass_runner: local-windows11-docker-desktop-ollama
- latest_pass_artifact: `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama_PASS_20260219_003600Z.txt`
- latest_pass_analysis_doc: `docs/review/mvp_verification_pack/artifacts/analysis_llm_provider_001.md`

## Interpretation Rules
1. `SKIPPED` in the latest local pack is acceptable for PR only when provider gate is conditional.
2. `SKIPPED` is never counted as PASS evidence.
3. Completion review must always cite `latest_pass_artifact` above when latest local run is `SKIPPED`.

## Reproduction Commands
1. `docker compose -f infra/docker-compose.yml up -d`
2. `docker compose -f infra/docker-compose.ollama.yml up -d`
3. `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`
4. `Get-Content docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`
