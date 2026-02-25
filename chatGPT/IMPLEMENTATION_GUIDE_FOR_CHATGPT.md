# IMPLEMENTATION GUIDE FOR CHATGPT

- updated_at_kst: 2026-02-25 23:39:05 +09:00
- base_commit_hash: 97f7502
- current_head_short: a83c840
- release_tag: 2026.03XX-quality-hardening-workpack
- branch: main

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
- Added: `scripts/mirror_and_run_frontend.ps1` one-command helper for unicode-path-safe frontend execution.
- Changed: `docs/ops/NODE22_UNICODE_WORKSPACE_GUIDE.md` to document helper usage and smoke mode command.
- Added: PostgreSQL readiness hardening (`pgvector` image, Flyway db-tools profile, V10/V11 migrations).
- Added: `scripts/db_smoke_test.py` + `docs/ops/DB_LOCAL_DEV.md` + `docs/ops/sql/DB_QUERY_PLAN_SANITY.sql`.
- Added: Runtime docker verification on clean volumes (`down -v` flow) with PASS smoke evidence artifact.
- Changed: Health-check validation rule clarified for fail-closed trace header behavior (`X-Trace-Id` required).

## 1) Scope Implemented
This continuation covers:
1. Automated spec consistency verification
2. Spec sync report fail-closed enforcement
3. Domain purity debt burn-down
4. UTF-8 baseline debt burn-down
5. Node22 unicode workspace reproducibility hardening
6. CI integration and evidence refresh

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
- Parses API workbook `전체API목록` `비고` field for `ReqID:` and `ReqID+:` tokens.
- Scans UIUX/DB workbooks for ReqID-like tokens and validates against SSOT.
- Verifies curated terminology consistency: `secret_ref`, ROLE taxonomy, error payload fields, SSE tokens, trace/tenant headers.
- Detects explicit variant mismatches (`safeResponse`, `traceId`, `tenantKey`, `errorCode`).
- Scans UIUX `94_미매핑처분` mapping columns for placeholders (`-`, `TODO`, `placeholder`, blank, to-be-defined markers, etc.).

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
- Optionally validates metadata tokens: Last synced at / Source file / Version or commit / Change summary.

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
- `--check` mode fails when `_INDEX.md` or `_INDEX.json` is stale/missing.

Outputs:
- `docs/review/mvp_verification_pack/artifacts/_INDEX.md`
- `docs/review/mvp_verification_pack/artifacts/_INDEX.json`
- `docs/review/mvp_verification_pack/artifacts/artifact_index_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/artifact_index_gate.json`

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
3. Notion synchronization traceability still depends on explicit report discipline.
4. Large artifact inventory can hide regressions without periodic curation.
5. Gate output volume can reduce triage speed without summary rollups.

## 6) Next PRs Top5
1. Extend curated terminology set only when new SSOT contract terms are formally approved.
2. Extend Node workspace guide with one-command mirror-and-run helper.
3. Tighten evidence curation for stale artifact cleanup and easier gate reading.
4. Incrementally strengthen automation around sync and handoff completeness checks.
5. Add summarized release-ready gate dashboard output for operators.

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
