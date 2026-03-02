# Artifact Hygiene

## Purpose
`docs/review/mvp_verification_pack/artifacts` keeps the latest, human-readable evidence for fast triage.
Old wave/smoke artifacts are preserved (never deleted) by archiving into zip bundles under
`docs/review/mvp_verification_pack/archive`.
Detailed policy: `docs/review/mvp_verification_pack/ARTIFACTS_ARCHIVE_POLICY.md`.

## Principles
- Fail-closed: stale/missing `_INDEX` or archive manifest fails `artifact_index_gate`.
- No deletion policy: archived evidence is copy-only and tracked in git history.
- Deterministic indexing: `_INDEX.md/.json` and legacy `_ARCHIVE_MANIFEST.json` are generated in stable order.
- Dual support: legacy bundles remain valid while sidecar archive manifests are the default for new archives.
- Pinned evidence is never archived.

## Reading Order
1. `release_gate_dashboard.md`
2. `spec_impl_coverage_report.md`
3. `_INDEX.md`
4. Individual gate/report artifacts referenced by the dashboard and index

## Notion Sync Evidence Runbook
When canonical spec files (`docs/references/*.csv`, `.xlsx`, `docs/uiux/*.xlsx`) are updated,
create or refresh a same-day evidence file:
- Path pattern: `docs/review/mvp_verification_pack/artifacts/notion_sync_evidence_<YYYYMMDD>.md` (KST date)
- Required fields per evidence block:
  - `last_synced_at_kst`
  - `source_file(s)`
  - `version/commit`
  - `notion_page` (must match `AGENTS.md` mapping)
  - `change_summary` (3~10 lines)

Validation command (default warning-only for notion evidence):
```powershell
python scripts/assert_spec_sync_report_updated.py `
  --base-ref origin/main `
  --head-ref HEAD `
  --mode warning-only
```

Temporary hard lock mode (strict-all, fail-closed for missing/invalid notion evidence):
```powershell
python scripts/assert_spec_sync_report_updated.py `
  --base-ref origin/main `
  --head-ref HEAD `
  --mode strict-all
```

## Archive Candidate Rules
- Primary source: `_INDEX.json.archive_candidates`.
- Additional exclusions:
  - already archived files from `_ARCHIVE_MANIFEST.json`
  - already archived files from sidecar manifests (`archive/<family>/*.manifest.json`)
  - retention exception (per family): keep latest `gate`, latest `summary`, latest `report`
  - pinned files from `scripts/contracts/fixed_artifact_paths.json`
  - pinned files referenced in backticks (`artifacts/...`) from:
    - `docs/review/mvp_verification_pack/00_EXEC_SUMMARY.md`
    - `docs/review/mvp_verification_pack/03_TEST_PLAN.md`
    - `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`
    - `docs/review/mvp_verification_pack/06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md`
    - `docs/review/verification_pack/README.md`
    - `docs/MVP_IMPLEMENTATION_REVIEW_PACK.md`

## Archive Layout
- Root: `docs/review/mvp_verification_pack/archive/`
- Sidecar standard:
  - `docs/review/mvp_verification_pack/archive/<family>/<YYYYMMDD>_<family>.zip`
  - `docs/review/mvp_verification_pack/archive/<family>/<YYYYMMDD>_<family>.manifest.json`
- Legacy compatibility:
  - `docs/review/mvp_verification_pack/archive/bundles/YYYYMMDD/<family>__YYYYMMDDTHHMMSSZ.zip`
  - `docs/review/mvp_verification_pack/archive/_ARCHIVE_MANIFEST.json`

Legacy manifest schema:
- `schema_version`
- `archive_root`
- `bundle_count`
- `archived_file_count`
- `bundles[]`: `bundle_path`, `family`, `created_at_utc`, `file_count`, `members[]`
- `archived_files[]`: `original_path`, `family`, `bundle_path`

Sidecar manifest required fields:
- `zip_sha256`
- `created_at_kst`
- `source_commit`
- `family_name`
- `included_files[]` (`path`, `sha256`)
- `excluded_files[]`

## Standard Commands
1. Build index and gate artifacts:
```powershell
python scripts/build_artifact_index.py `
  --artifact-root docs/review/mvp_verification_pack/artifacts `
  --index-md docs/review/mvp_verification_pack/artifacts/_INDEX.md `
  --index-json docs/review/mvp_verification_pack/artifacts/_INDEX.json `
  --gate-output-txt docs/review/mvp_verification_pack/artifacts/artifact_index_gate.txt `
  --gate-output-json docs/review/mvp_verification_pack/artifacts/artifact_index_gate.json
```

2. Archive eligible artifacts:
```powershell
python scripts/archive_artifacts.py `
  --artifact-root docs/review/mvp_verification_pack/artifacts `
  --index-json docs/review/mvp_verification_pack/artifacts/_INDEX.json `
  --archive-root docs/review/mvp_verification_pack/archive `
  --manifest-json docs/review/mvp_verification_pack/archive/_ARCHIVE_MANIFEST.json `
  --output-txt docs/review/mvp_verification_pack/artifacts/artifact_archive_report.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/artifact_archive_report.json
```

3. Check mode (fail-closed):
```powershell
python scripts/build_artifact_index.py `
  --check `
  --artifact-root docs/review/mvp_verification_pack/artifacts `
  --index-md docs/review/mvp_verification_pack/artifacts/_INDEX.md `
  --index-json docs/review/mvp_verification_pack/artifacts/_INDEX.json `
  --gate-output-txt docs/review/mvp_verification_pack/artifacts/artifact_index_gate.txt `
  --gate-output-json docs/review/mvp_verification_pack/artifacts/artifact_index_gate.json
```

4. Spec -> implementation coverage:
```powershell
python scripts/spec_impl_coverage_report.py `
  --report-txt docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_report.txt `
  --report-json docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_report.json `
  --report-md docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_report.md

python scripts/assert_spec_impl_coverage.py `
  --report-json docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_report.json `
  --output-txt docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_gate.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/spec_impl_coverage_gate.json
```

## Restore Flow (Archive -> Artifacts)
1. Locate target bundle in `_ARCHIVE_MANIFEST.json`.
2. Extract only required members back into `docs/review/mvp_verification_pack/artifacts`.
3. Rebuild `_INDEX.md/.json` and rerun `--check`.
4. Re-run `scripts/assert_verification_pack_consistency.ps1` if referenced evidence is restored.

## CI Meaning
`artifact_index_gate` now validates both:
- `_INDEX.md/.json` freshness
- `_ARCHIVE_MANIFEST.json` freshness and bundle existence (legacy)
- sidecar strict integrity (zip/manifest/hash/included_files list)

Violation codes:
- `INDEX_MISSING`
- `INDEX_STALE`
- `ARCHIVE_MANIFEST_MISSING`
- `ARCHIVE_MANIFEST_STALE`
- `ARCHIVE_BUNDLE_MISSING`
- `ARCHIVE_SIDECAR_MANIFEST_MISSING`
- `ARCHIVE_ZIP_MISSING`
- `ARCHIVE_ZIP_SHA256_MISMATCH`
- `ARCHIVE_INCLUDED_LIST_MISMATCH`
- `ARCHIVE_MANIFEST_INVALID_JSON`
- `ARCHIVE_MANIFEST_REQUIRED_FIELD_MISSING`

## Troubleshooting
- `ARCHIVE_MANIFEST_MISSING`: run `build_artifact_index.py` once in write mode.
- `ARCHIVE_MANIFEST_STALE`: regenerate index/manifest after archive operations.
- `ARCHIVE_BUNDLE_MISSING`: recover bundle file or rebuild manifest from actual bundles.
- Unexpected pinned skips: verify fixed-path contract and backtick references in review docs.
