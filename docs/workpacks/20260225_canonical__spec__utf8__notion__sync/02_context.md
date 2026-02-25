# Workpack Context - 20260225_canonical__spec__utf8__notion__sync

## Technical Context

- UTF-8 ratchet residual was reduced to canonical spec scope (`3`) after prior non-canonical waves.
- Canonical spec files are protected by fail-fast guard and require explicit override text.
- AGENTS 2.2-A requires same-session Notion sync and `spec_sync_report.md` metadata update.
- Merge-block closure also requires workpack/agent/handoff evidence updates.

## Evidence Inputs

- UTF-8 strict/full-scan artifacts under `docs/review/mvp_verification_pack/artifacts/`.
- Canonical conversion evidence:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave10_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave10_report.json`
- Existing manual-hook reference:
  - `docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json`

## Risk Notes

- Canonical CSV mutation must remain encoding-only; decoded hash must be unchanged.
- Notion sync omission is a hard failure per AGENTS 2.2-A.
- Stale `_INDEX.md/_INDEX.json` causes artifact index freshness gate failure.
