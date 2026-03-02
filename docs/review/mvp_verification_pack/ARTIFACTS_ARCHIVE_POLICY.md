# Artifacts Archive Policy

## Purpose
Reduce signal-to-noise in `docs/review/mvp_verification_pack/artifacts` while preserving auditability.

## Scope
- Artifact source: `docs/review/mvp_verification_pack/artifacts`
- Archive root: `docs/review/mvp_verification_pack/archive`
- Gate: `scripts/build_artifact_index.py --check`

## Candidate Selection
1. Primary source: `_INDEX.json.archive_candidates`.
2. Exclusions:
- Pinned paths (`scripts/contracts/fixed_artifact_paths.json` and pinned references in review docs)
- Already archived paths (legacy `_ARCHIVE_MANIFEST.json` + sidecar manifests)
- Retention exception: per family, keep latest `gate`, latest `summary`, latest `report` (one each)

## Archive Layout
- New standard:
  - `docs/review/mvp_verification_pack/archive/<family_name>/<YYYYMMDD>_<family_name>.zip`
  - `docs/review/mvp_verification_pack/archive/<family_name>/<YYYYMMDD>_<family_name>.manifest.json`
- Legacy compatibility:
  - `docs/review/mvp_verification_pack/archive/bundles/...`
  - `docs/review/mvp_verification_pack/archive/_ARCHIVE_MANIFEST.json`

## Sidecar Manifest Contract
Required fields:
- `zip_sha256`
- `created_at_kst` (`YYYY-MM-DD HH:MM:SS +09:00`)
- `source_commit` (HEAD 40-char hash)
- `family_name`
- `included_files` (`[{path, sha256}]`)
- `excluded_files`

## Safety
- Copy-only policy: archived files are zipped but never deleted from `artifacts` by this script version.
- Secret/PII handling follows repository AGENTS guardrails.

## Fail-Closed Verification
When any sidecar archive exists, `artifact_index_gate --check` validates:
1. zip exists
2. sibling manifest exists
3. `manifest.zip_sha256 == actual zip sha256`
4. `set(manifest.included_files.path) == set(zip members)`

Any mismatch causes `status=FAIL` and non-zero exit code.

## Rollback
1. Remove target sidecar zip/manifest pair(s).
2. Rebuild index and gate artifacts:
```powershell
python scripts/build_artifact_index.py `
  --artifact-root docs/review/mvp_verification_pack/artifacts `
  --index-md docs/review/mvp_verification_pack/artifacts/_INDEX.md `
  --index-json docs/review/mvp_verification_pack/artifacts/_INDEX.json `
  --gate-output-txt docs/review/mvp_verification_pack/artifacts/artifact_index_gate.txt `
  --gate-output-json docs/review/mvp_verification_pack/artifacts/artifact_index_gate.json
```
3. Re-run check mode to confirm PASS.
