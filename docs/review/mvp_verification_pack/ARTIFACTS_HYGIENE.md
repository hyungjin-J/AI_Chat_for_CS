# Artifact Hygiene

## Purpose
`docs/review/mvp_verification_pack/artifacts` keeps the latest, human-readable evidence for fast triage.
Old wave/smoke artifacts are preserved (never deleted) by moving them into zip bundles under
`docs/review/mvp_verification_pack/archive`.

## Principles
- Fail-closed: stale/missing `_INDEX` or archive manifest fails `artifact_index_gate`.
- No deletion policy: archived evidence is moved into zip bundles and tracked in git history.
- Deterministic indexing: `_INDEX.md/.json` and `_ARCHIVE_MANIFEST.json` are generated in stable order.
- Pinned evidence is never archived.

## Archive Candidate Rules
- Primary source: `_INDEX.json.archive_candidates`.
- Additional exclusions:
  - already archived files from `_ARCHIVE_MANIFEST.json`
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
- Bundles: `docs/review/mvp_verification_pack/archive/bundles/YYYYMMDD/<family>__YYYYMMDDTHHMMSSZ.zip`
- Manifest: `docs/review/mvp_verification_pack/archive/_ARCHIVE_MANIFEST.json`

Manifest schema:
- `schema_version`
- `archive_root`
- `bundle_count`
- `archived_file_count`
- `bundles[]`: `bundle_path`, `family`, `created_at_utc`, `file_count`, `members[]`
- `archived_files[]`: `original_path`, `family`, `bundle_path`

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

## Restore Flow (Archive -> Artifacts)
1. Locate target bundle in `_ARCHIVE_MANIFEST.json`.
2. Extract only required members back into `docs/review/mvp_verification_pack/artifacts`.
3. Rebuild `_INDEX.md/.json` and rerun `--check`.
4. Re-run `scripts/assert_verification_pack_consistency.ps1` if referenced evidence is restored.

## CI Meaning
`artifact_index_gate` now validates both:
- `_INDEX.md/.json` freshness
- `_ARCHIVE_MANIFEST.json` freshness and bundle existence

Violation codes:
- `INDEX_MISSING`
- `INDEX_STALE`
- `ARCHIVE_MANIFEST_MISSING`
- `ARCHIVE_MANIFEST_STALE`
- `ARCHIVE_BUNDLE_MISSING`

## Troubleshooting
- `ARCHIVE_MANIFEST_MISSING`: run `build_artifact_index.py` once in write mode.
- `ARCHIVE_MANIFEST_STALE`: regenerate index/manifest after archive operations.
- `ARCHIVE_BUNDLE_MISSING`: recover bundle file or rebuild manifest from actual bundles.
- Unexpected pinned skips: verify fixed-path contract and backtick references in review docs.
