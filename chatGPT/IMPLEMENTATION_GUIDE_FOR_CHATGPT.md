# IMPLEMENTATION GUIDE FOR CHATGPT

- updated_at_kst: 2026-03-01 17:13:24 +09:00
- base_commit_hash: 97f7502
- current_head_short: 2eced8e
- release_tag: 2026.03XX-quality-hardening-workpack
- branch: utf8-wave8-to-29

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: Wave10 canonical UTF-8 normalization for 3 canonical spec CSV files via explicit override flow.
- Added: Wave10 hash evidence files `utf8_normalization_wave10_report.md/json`.
- Changed: canonical-spec fail-fast guard remained enforced and was bypassed only with explicit confirmation text.
- Changed: full-scan UTF-8 artifacts (`utf8_full_scan_current.txt/json`) now report zero violations.
- Changed: UTF-8 baseline artifact (`utf8_full_scan_baseline_violations.json`) synchronized to zero baseline.
- Changed: `continuation_utf8_strict_gate.txt/json` regenerated and remained PASS.
- Changed: `utf8_full_scan_ratchet_gate.txt/json` regenerated and remained PASS with baseline 0.
- Added: deterministic artifact index outputs (`_INDEX.md/.json`) for latest gate evidence navigation.
- Added: fail-closed `artifact_index_gate.txt/json` that detects stale/missing index artifacts.
- Added: `scripts/build_release_gate_dashboard.py` with deterministic `release_gate_dashboard.md/.json` outputs.
- Added: `scripts/mirror_and_run_frontend.ps1` one-command helper for unicode-path-safe frontend execution.
- Changed: `docs/ops/NODE22_UNICODE_WORKSPACE_GUIDE.md` to document helper usage and smoke mode command.
- Added: PostgreSQL readiness hardening (`pgvector` image, Flyway db-tools profile, V10/V11 migrations).
- Added: `scripts/db_smoke_test.py` + `docs/ops/DB_LOCAL_DEV.md` + `docs/ops/sql/DB_QUERY_PLAN_SANITY.sql`.
- Added: Runtime docker verification on clean volumes (`down -v` flow) with PASS smoke evidence artifact.
- Changed: Health-check validation rule clarified for fail-closed trace header behavior (`X-Trace-Id` required).
- Added: Separate nightly workflow `.github/workflows/db-repro-nightly.yml` for clean-volume DB reproducibility monitoring.
- Added: `scripts/assert_application_port_boundaries.py` ratchet gate + contract + baseline artifact.
- Changed: `operations/application` and `knowledge/rag/application` now depend on domain port interfaces.
- Changed: `knowledge/rag/presentation` citation endpoint now uses `CitationQueryService` (no infra import).
- Changed: backoffice ACL gate now blocks `.domain.` imports (`FORBIDDEN_DOMAIN_IMPORT`).
- Added: `docs/ops/PGVECTOR_OPERATIONS.md` for IVFFlat operations baseline, probe tuning, and index maintenance runbook.
- Added: `scripts/vector_recall_latency_bench.py` + `scripts/tests/test_vector_recall_latency_bench.py`.
- Changed: `docs/ops/DB_LOCAL_DEV.md` with PGVECTOR benchmark execution examples and baseline delta comparison flow.
- Added: `.github/workflows/db-backup-restore-weekly.yml` and switched `db-backup-restore-nightly.yml` to dispatch-only.
- Changed: `scripts/db_backup_restore_rehearsal.py` with fixed RTO/RPO metadata, safe-seed fallback checks, and dump metadata capture.
- Changed: `scripts/mirror_and_run_frontend.py` to smoke-first mode with git-clean and Node runtime guidance.
- Added: sidecar archive policy (`ARTIFACTS_ARCHIVE_POLICY.md`) and sidecar integrity validation in artifact index/check scripts.
- Changed: spec-sync gate workflow wiring (`pr-smoke-contract`/`release-nightly-full`) to rely on strict defaults in script.
- Added: vector benchmark monitoring gate artifacts (`vector_bench_monitoring_gate.txt/json`) via `vector-bench-nightly` always-run summary step.
- Changed: all `chatGPT/*` handoff docs were synchronized to the same baseline metadata and evidence references.
- Added: `scripts/spec_impl_coverage_report.py` and `scripts/assert_spec_impl_coverage.py` for Must-first Spec -> Implementation visibility and merge-block enforcement.
- Added: 2026-03-01 same-session sync of `chatGPT/*`, `spec_sync_report.md`, and Notion metadata pages.
- Added: same-day Notion evidence artifact `docs/review/mvp_verification_pack/artifacts/notion_sync_evidence_20260301.md`.
- Changed: session metadata now tracks `current_head_short: 2eced8e` with working-tree progress context.

## 1) Scope Implemented
This continuation covers:
1. Automated spec consistency verification
2. Spec sync report fail-closed enforcement
3. Domain purity debt burn-down
4. UTF-8 baseline debt burn-down
5. Node22 unicode workspace reproducibility hardening
6. CI integration and evidence refresh
7. PGVECTOR IVFFlat operations and local recall-latency delta reproducibility
8. Separate DB reproducibility nightly scheduling (non merge-block monitoring)

Primary audit entry:
- `docs/review/agent_reports/CONTINUATION_PREFLIGHT_AUDIT.md`

## 2) Implementation Details

### 2.1 Spec Consistency Gate
Files:
- `scripts/spec_consistency_check.py`
- `scripts/tests/test_spec_consistency_check.py`

Behavior:
- Builds ReqID SSOT from requirements CSV.
- Validates ReqID references in Summary CSV.
- Parses API workbook `?꾩껜API紐⑸줉` `鍮꾧퀬` field for `ReqID:` and `ReqID+:` tokens.
- Scans UIUX/DB workbooks for ReqID-like tokens and validates against SSOT.
- Verifies curated terminology consistency: `secret_ref`, ROLE taxonomy, error payload fields, SSE tokens, trace/tenant headers.
- Detects explicit variant mismatches (`safeResponse`, `traceId`, `tenantKey`, `errorCode`).
- Scans UIUX `94_誘몃ℓ?묒쿂遺? mapping columns for placeholders (`-`, `to-do`, `placeholder`, blank, to-be-defined markers, etc.).

Outputs:
- `docs/review/mvp_verification_pack/artifacts/spec_consistency_check_report.txt`
- `docs/review/mvp_verification_pack/artifacts/spec_consistency_check_report.json`
- `docs/review/mvp_verification_pack/artifacts/spec_consistency_check_pass.txt`

### 2.2 Spec Sync Report Update Gate
Files:
- `scripts/assert_spec_sync_report_updated.py`
- `scripts/tests/test_assert_spec_sync_report_updated.py`

Behavior:
- Detects canonical spec file changes via git diff.
- Requires `spec_sync_report.md` change when canonical spec changes are present.
- Mandatory fail-closed metadata validation per changed canonical file:
  Last synced at (KST `+09:00`) / Source file / Version(or commit)=HEAD / Notion URL exact match / Change summary(3~10 lines).

Outputs:
- `docs/review/mvp_verification_pack/artifacts/spec_sync_report_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/spec_sync_report_gate.json`

### 2.3 Domain Purity Burn-down
Highlights:
- Boundary violations addressed by moving row/record types to domain model package.
- Billing cost dependency path refactored through domain port style.
- Ratchet gate evidence refreshed with reduced baseline.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/domain_layer_boundary_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/domain_layer_purity_burndown_summary.txt`
- `docs/review/mvp_verification_pack/artifacts/domain_layer_purity_baseline_violations.json`

### 2.4 UTF-8 Baseline Burn-down
Files:
- `scripts/normalize_utf8.py`

Highlights:
- Wave10 canonical normalization batch (3 files: BOM removal only) with evidence reporting.
- Fail-fast canonical-spec denylist guard remained active with explicit override + typed confirmation.
- Full UTF-8 baseline reduced from 118 to 0 while ratchet remained fail-closed.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_current.txt`
- `docs/review/mvp_verification_pack/artifacts/utf8_bom_normalization_report.md`
- `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave10_report.md`
- `docs/review/mvp_verification_pack/artifacts/utf16_normalization_report.md`
- `docs/review/mvp_verification_pack/artifacts/utf8_burndown_blocked_residuals.md`

### 2.5 Node22 Unicode Workspace Mitigation
Files:
- `scripts/check_workspace_path_ascii.py`
- `scripts/bootstrap_node_from_nvmrc.ps1`
- `docs/ops/NODE22_UNICODE_WORKSPACE_GUIDE.md`

Highlights:
- Local warning-only guard to avoid CI noise.
- Repro evidence documents unicode-path failure and ASCII workspace success path.

Output:
- `docs/review/mvp_verification_pack/artifacts/node22_unicode_workspace_repro.txt`

### 2.6 ChatGPT Handoff Update Gate Tuning
Files:
- `scripts/assert_chatgpt_handoff_updated.py`
- `scripts/tests/test_assert_chatgpt_handoff_updated.py`

Policy:
- Default mode is `core-only`.
- `core-only` blocks merge only for core implementation changes without both handoff docs updates.
- Non-core changes produce warning only to reduce developer friction.
- `strict-all` remains available for temporary hard lock if needed.

Output:
- `docs/review/mvp_verification_pack/artifacts/chatgpt_handoff_update_gate.txt`

### 2.7 Artifact Index Freshness Gate
Files:
- `scripts/build_artifact_index.py`
- `scripts/tests/test_build_artifact_index.py`

Behavior:
- Scans `docs/review/mvp_verification_pack/artifacts/` deterministically with stable ordering.
- Groups artifacts by gate/report/summary/evidence/misc families.
- Selects latest evidence by filename wave/date heuristic (not filesystem mtime).
- Emits optional archive candidates without deleting existing audit trails.
- Pins dashboard discovery in `_INDEX.md` via `## Start Here` and publishes stable `release_gate_dashboard` key in `_INDEX.json`.
- Publishes stable `spec_impl_coverage` key in `_INDEX.json` for tooling lookup.
- `--check` mode fails when `_INDEX.md` or `_INDEX.json` is stale/missing.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/_INDEX.md`
- `docs/review/mvp_verification_pack/artifacts/_INDEX.json`
- `docs/review/mvp_verification_pack/artifacts/artifact_index_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/artifact_index_gate.json`

### 2.14 Release Gate Dashboard
Files:
- `scripts/build_release_gate_dashboard.py`
- `scripts/tests/test_build_release_gate_dashboard.py`
- `scripts/tests/fixtures/release_dashboard/base/artifacts/*`
- `.github/workflows/pr-smoke-contract.yml`
- `.github/workflows/release-nightly-full.yml`
- `docs/review/mvp_verification_pack/ARTIFACTS_HYGIENE.md`

Behavior:
- Generates one-page operator view of critical gates with `PASS/FAIL/MISSING/ERROR`.
- Reads structured gate JSON first, then falls back to TXT first-lines parsing when JSON is absent.
- Includes baseline snapshot (domain, UTF-8 full-scan, API added/removed) and first-triage artifact links.
- Returns exit code `0` always (reporting-only), while encoding true statuses in JSON.
- Is regenerated in CI with `if: always()` before artifact upload.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/release_gate_dashboard.md`
- `docs/review/mvp_verification_pack/artifacts/release_gate_dashboard.json`
- `docs/review/mvp_verification_pack/artifacts/release_gate_dashboard_rollout_report_20260228.txt`

### 2.15 Spec -> Implementation Coverage Gate
Files:
- `scripts/spec_impl_coverage_report.py`
- `scripts/assert_spec_impl_coverage.py`
- `scripts/tests/test_spec_impl_coverage_report.py`
- `scripts/tests/test_assert_spec_impl_coverage.py`
- `.github/workflows/pr-smoke-contract.yml`
- `.github/workflows/release-nightly-full.yml`

Behavior:
- Reads API workbook (`?꾩껜API紐⑸줉`) and parses `ReqID:` / `ReqID+:` from `鍮꾧퀬`.
- Maps API row importance from requirements CSV (`Must/Should/Unknown`).
- Computes deterministic coverage signals per API row:
  - `backend_implemented` (Spring mapping heuristic, class+method path aware)
  - `frontend_referenced` (frontend source endpoint reference)
  - `tests_present` (test source endpoint/controller reference)
- Produces Must red/green list and missing-signal table for release-readiness triage.
- Gate is fail-closed for Must rows missing backend implementation.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_report.txt`
- `docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_report.json`
- `docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_report.md`
- `docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_gate.json`
- `docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_rollout_report_20260301.txt`

### 2.8 Node22 Unicode Path Mirror Helper
Files:
- `scripts/mirror_and_run_frontend.ps1`
- `docs/ops/NODE22_UNICODE_WORKSPACE_GUIDE.md`

Behavior:
- Uses `check_workspace_path_ascii.py` in warning-only mode.
- Mirrors repo to ASCII temp path when source workspace path is non-ASCII (or `-ForceMirror`).
- Runs `.nvmrc` bootstrap and frontend test/build sequence in mirrored path.
- Supports deterministic smoke mode with skip flags + artifact output.

Evidence:
- `docs/review/mvp_verification_pack/artifacts/node22_unicode_mirror_helper_smoke.txt`

### 2.9 DB Local Readiness Foundation
Files:
- `infra/docker-compose.yml`
- `backend/src/main/resources/db/migration/V10__db_readiness_foundation_indexes.sql`
- `backend/src/main/resources/db/postgresql-migration/V11__pgvector_enablement.sql`
- `scripts/db_smoke_test.py`
- `docs/ops/DB_LOCAL_DEV.md`
- `docs/ops/sql/DB_QUERY_PLAN_SANITY.sql`

Behavior:
- PostgreSQL service uses `pgvector/pgvector:pg16` for deterministic extension availability.
- Flyway `db-tools` profile provides explicit migration execution path in compose.
- V10 adds high-ROI safe indexes for tenant/conversation/message/search/event paths.
- V11 (PostgreSQL-only location) enables `vector` extension and provisions ivfflat index base.
- DB smoke script validates boot + schema + vector extension + temp transaction read/write path.

### 2.10 Runtime Verification Notes (2026-02-25 KST)
Executed checks:
- `docker compose -f infra/docker-compose.yml down -v`
- `docker compose -f infra/docker-compose.yml up -d postgres redis`
- `docker compose -f infra/docker-compose.yml --profile db-tools run --rm flyway`
- `python scripts/db_smoke_test.py --method docker-exec ...`
- `docker compose -f infra/docker-compose.yml --profile demo-stack up -d backend`
- `curl -H "X-Trace-Id: <uuid>" http://localhost:8080/actuator/health`

Results:
- Flyway applied and validated versions `v1..v11`.
- DB smoke status `PASS` (`select_1`, `vector_extension`, expected tables, temp write/read).
- Backend booted and connected to PostgreSQL/Redis.
- Fail-closed behavior remained intact: health endpoint returns `409` without trace header and `200` with `X-Trace-Id`.
- Collation mismatch warning was reproduced on stale volume and resolved by clean volume reset (`down -v`).

### 2.11 Separate Nightly DB Reproducibility Workflow
Files:
- `.github/workflows/db-repro-nightly.yml`
- `docs/ops/DB_LOCAL_DEV.md`

Behavior:
- Dedicated nightly workflow (GitHub Actions) runs the fixed clean-volume order:
  - `down -v -> up postgres/redis -> flyway -> db_smoke_test`.
- Backend health trace fail-closed contract is validated in the same job:
  - without `X-Trace-Id`: `409`
  - with `X-Trace-Id`: `200`
- Failure policy:
  - monitoring-only (no PR merge-block coupling),
  - explicit workflow failure (red run state),
  - `if: always()` artifact upload for root-cause triage.

Primary artifacts:
- `docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.txt`
- `docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.json`
- `docs/review/mvp_verification_pack/artifacts/db_backend_health_trace_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/db_backend_health_trace_gate.json`

### 2.12 PGVECTOR IVFFlat Operations and Local Delta Benchmark
Files:
- `docs/ops/PGVECTOR_OPERATIONS.md`
- `scripts/vector_recall_latency_bench.py`
- `scripts/tests/test_vector_recall_latency_bench.py`
- `docs/ops/DB_LOCAL_DEV.md`

Behavior:
- V11 ivfflat baseline (`lists=100`, `vector(1536)`) is documented as SSOT.
- Operations guide now defines:
  - lists sizing rule by data scale (`clamp(round(sqrt(N)), 100, 4000)`),
  - probes sweep (`1,2,4,8,16,32`),
  - `ANALYZE` cadence,
  - `REINDEX INDEX CONCURRENTLY` and rebuild conditions.
- Local benchmark CLI measures:
  - Exact TopK (index scan disabled) vs Approx TopK (`SET LOCAL ivfflat.probes = X`),
  - `recall@k`, `p50/p95 latency`,
  - baseline delta fail-closed checks (`max_recall_drop`, `max_p95_regression_ratio`).

Output contract:
- `docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_YYYYMMDD.txt`
- `docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_YYYYMMDD.json`
- optional baseline reference:
  - `docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_baseline.json`

### 2.13 Delta Sync (2026-02-27, current worktree)
Files:
- `.github/workflows/db-backup-restore-weekly.yml`
- `.github/workflows/db-backup-restore-nightly.yml`
- `.github/workflows/pr-smoke-contract.yml`
- `.github/workflows/release-nightly-full.yml`
- `.github/workflows/vector-bench-nightly.yml`
- `scripts/db_backup_restore_rehearsal.py`
- `scripts/build_artifact_index.py`
- `scripts/archive_artifacts.py`
- `scripts/mirror_and_run_frontend.py`
- `scripts/tests/test_vector_bench_workflow.py`
- `docs/ops/DB_BACKUP_RESTORE_RUNBOOK.md`
- `docs/ops/NODE22_UNICODE_WORKSPACE_GUIDE.md`
- `docs/dev/DEV_ENVIRONMENT.md`
- `docs/review/mvp_verification_pack/ARTIFACTS_HYGIENE.md`
- `docs/review/mvp_verification_pack/ARTIFACTS_ARCHIVE_POLICY.md`
- `frontend/README.md`
- `frontend/package.json`

Behavior:
- DB backup/restore rehearsal is now weekly scheduled (Monday 02:00 KST) and nightly job is manual-only to avoid duplicate schedule noise.
- Rehearsal payload now includes fixed SLO metadata (`rto_minutes=60`, `rpo_hours=24`), dump metadata (`size/sha256/created_at`), and safe-seed insert/fallback verification.
- Sensitive values in rehearsal command/output are redacted before persistence.
- Artifact archiving moved to sidecar layout (`<date>_<family>.zip` + `<date>_<family>.manifest.json`) with required fields and SHA256 integrity checks.
- Artifact gate now fail-closes on sidecar inconsistencies: missing manifest/zip, hash mismatch, invalid JSON, or `included_files` mismatch.
- Archive retention exceptions keep latest `gate/summary/report` per family while preserving copy-only (no deletion) behavior.
- Node22 unicode mirror runner now uses smoke mode as primary path (`--smoke`), emits fixed smoke artifact by default, and provides runtime mismatch guidance instead of auto bootstrap.
- `assert_spec_sync_report_updated.py` now enforces metadata + Notion evidence checks by default (workflow flags removed) and uses explicit canonical file-to-Notion mapping including UIUX workbook.
- `vector-bench-nightly.yml` now emits monitoring-only gate artifacts (`vector_bench_monitoring_gate.txt/json`) even when benchmark step fails, improving triage traceability without PR merge coupling.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/archive_policy_rollout_report_20260227.txt`
- `docs/review/mvp_verification_pack/artifacts/archive_policy_rollout_report_20260220.txt`
- `docs/review/mvp_verification_pack/archive/archive_policy_rollout_report/20260227_archive_policy_rollout_report.manifest.json`
- `docs/review/mvp_verification_pack/artifacts/node22_unicode_mirror_helper_smoke.txt`
- `docs/review/mvp_verification_pack/artifacts/spec_sync_report_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/artifact_index_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/artifact_archive_report.txt`
- `docs/review/mvp_verification_pack/artifacts/artifact_archive_report.json`
- `docs/review/mvp_verification_pack/artifacts/vector_bench_monitoring_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/vector_bench_monitoring_gate.json`
- `docs/review/mvp_verification_pack/artifacts/vector_bench_workflow_tests.txt`
- `docs/review/mvp_verification_pack/artifacts/vector_bench_spec_consistency_check.txt`
- `docs/review/mvp_verification_pack/artifacts/vector_bench_spec_sync_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/vector_bench_utf8_strict_gate.txt`
- `scripts/tests/test_archive_artifacts.py`
- `scripts/tests/test_mirror_and_run_frontend.py`

### 2.16 Session Sync (2026-03-01, Notion + ChatGPT Files)
Files:
- `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
- `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
- `chatGPT/DB_READINESS_EXECUTION_AND_PROCESS_PLAN_KO.md`
- `spec_sync_report.md`
- `docs/review/mvp_verification_pack/artifacts/notion_sync_evidence_20260301.md`

Behavior:
- Refreshed handoff metadata timestamps and commit pointers to current head (`2eced8e`) while preserving fail-closed SSOT rules.
- Appended `Session Update (2026-03-01 Progress Sync)` blocks to all mapped Notion pages for sync traceability.
- Kept canonical spec schema unchanged in this session (metadata/evidence synchronization only).

Outputs:
- `docs/review/mvp_verification_pack/artifacts/notion_sync_evidence_20260301.md`
- `spec_sync_report.md`

## 3) Validation Gates
| Gate | Status | Evidence |
|---|---|---|
| Workpack/report v2 contract | PASS | `docs/review/mvp_verification_pack/artifacts/workpack_agent_contract_v2.txt` |
| Workpack trigger consistency | PASS | `docs/review/mvp_verification_pack/artifacts/continuation_trigger_consistency_gate.txt` |
| Domain purity ratchet | PASS | `docs/review/mvp_verification_pack/artifacts/domain_layer_boundary_gate.txt` |
| Backoffice ACL ratchet | PASS | `docs/review/mvp_verification_pack/artifacts/backoffice_acl_boundary_gate.txt` |
| Frontend import boundary | PASS | `docs/review/mvp_verification_pack/artifacts/frontend_import_boundary_gate.txt` |
| UTF-8 strict diff-scope | PASS | `docs/review/mvp_verification_pack/artifacts/continuation_utf8_strict_gate.txt` |
| UTF-8 full-scan ratchet | PASS | `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.txt` |
| Artifact index freshness gate | PASS | `docs/review/mvp_verification_pack/artifacts/artifact_index_gate.txt` |
| Node22 unicode mirror helper smoke | PASS | `docs/review/mvp_verification_pack/artifacts/node22_unicode_mirror_helper_smoke.txt` |
| Scaffold smoke | PASS | `docs/review/mvp_verification_pack/artifacts/scaffold_contract_smoke.txt` |
| Spec consistency check | PASS | `docs/review/mvp_verification_pack/artifacts/spec_consistency_check_report.txt` |
| Spec implementation coverage gate | FAIL (expected, Must gaps visible) | `docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_gate.txt` |
| Spec sync report update gate | PASS | `docs/review/mvp_verification_pack/artifacts/spec_sync_report_gate.txt` |
| ChatGPT handoff update gate | PASS | `docs/review/mvp_verification_pack/artifacts/chatgpt_handoff_update_gate.txt` |
| Quality validation summary | PASS | `docs/review/mvp_verification_pack/artifacts/quality_workpack_validation_summary.txt` |

## 4) Baseline Delta
- Domain purity baseline: 6 -> 0
- UTF-8 full-scan baseline: 118 -> 0
- API compare: added=0, removed=0

## 5) Remaining Risks Top5
1. Node22 unicode-path instability can still impact developers who skip ASCII workspace mitigation.
2. Terminology checks are curated and deterministic but still cover only approved contract token sets.
3. Notion sync is now fail-closed through mandatory `spec_sync_report` checks; remaining risk is external Notion service/API availability.
4. Large artifact inventory can hide regressions without periodic curation.
5. PGVECTOR recall-latency benchmark is local-only today; CI/nightly automation is not yet wired.

## 6) Next PRs Top5
1. Extend curated terminology set only when new SSOT contract terms are formally approved.
2. Extend Node workspace guide with one-command mirror-and-run helper.
3. Tighten evidence curation for stale artifact cleanup and easier gate reading.
4. Incrementally strengthen automation around sync and handoff completeness checks.
5. Add lightweight trend stubs (dated artifact names only) for DB backup/restore and vector bench monitoring.

## 7) Safety Confirmation
- No ROLE taxonomy change.
- No error payload shape change.
- No fail-closed answer contract relaxation.
- No hardening lock relaxation.
- No tenant/RBAC authority relaxation.
- No public API/SSE contract break.
- No secrets/tokens/raw PII in committed artifacts.

## 8) Conflict Resolution Note (SSOT)
- In conflict, latest artifacts under `docs/review/mvp_verification_pack/artifacts/*` take precedence.
- `spec_sync_report.md` remains the sync log precedence target for spec/document synchronization conflicts.

