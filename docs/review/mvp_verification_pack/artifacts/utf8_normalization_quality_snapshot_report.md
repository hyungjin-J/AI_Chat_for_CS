# UTF-8 Normalization Report

- generated_at_utc: 2026-02-27T08:52:34.978909+00:00
- dry_run: NO
- candidate_count: 6
- changed_count: 6
- skipped_count: 0
- verification_method: decoded-text SHA-256 + byte SHA-256

| file | old_encoding | action | old_bytes_sha256 | new_bytes_sha256 | old_decoded_sha256 | new_decoded_sha256 | line_endings(old->new) | status |
|---|---|---|---|---|---|---|---|---|
| `docs/review/mvp_verification_pack/ARTIFACTS_HYGIENE.md` | `utf-8-sig` | `BOM_REMOVED` | `00a425550e5abc7a1dc1efc7ead3ae29566390a3d95e1afa197d2365ae03490d` | `aea91b698f372e526959c867b5578bdad0488f59b9e0445e9254a05b0ca820bd` | `aea91b698f372e526959c867b5578bdad0488f59b9e0445e9254a05b0ca820bd` | `aea91b698f372e526959c867b5578bdad0488f59b9e0445e9254a05b0ca820bd` | `MIXED(CRLF=1,LF=117,CR=0)->MIXED(CRLF=1,LF=117,CR=0)` | `CHANGED` |
| `docs/review/mvp_verification_pack/artifacts/archive_policy_rollout_report_20260220.txt` | `utf-8-sig` | `BOM_REMOVED` | `8bf5f9ab8f2ec18a4ed55cd13dfe8a54d76e1c6cc8ba8eab78079093539192d8` | `84d9cb360061aabb0a3bdb80ed575c7031142bfb14cbcd003eb809e55e640a63` | `84d9cb360061aabb0a3bdb80ed575c7031142bfb14cbcd003eb809e55e640a63` | `84d9cb360061aabb0a3bdb80ed575c7031142bfb14cbcd003eb809e55e640a63` | `CRLF->CRLF` | `CHANGED` |
| `docs/review/mvp_verification_pack/artifacts/archive_policy_rollout_report_20260227.txt` | `utf-8-sig` | `BOM_REMOVED` | `f6d6f409561855258c756543f7ce5a9d7758d3db55abaabc97f495aa133462b0` | `a278d04f224a8b5868085bcf9b9005c26da181c0f0e53c7d9eda3bece01a3409` | `a278d04f224a8b5868085bcf9b9005c26da181c0f0e53c7d9eda3bece01a3409` | `a278d04f224a8b5868085bcf9b9005c26da181c0f0e53c7d9eda3bece01a3409` | `CRLF->CRLF` | `CHANGED` |
| `scripts/build_artifact_index.py` | `utf-8-sig` | `BOM_REMOVED` | `3c1e76f98f8983ae1bfb86b54a478cb9301411fa4725006aed16e4f590969c1c` | `96831ae1525975bf6815da55d2a4e7cb2a8427d2cf3306eb084732c956ee6ff0` | `96831ae1525975bf6815da55d2a4e7cb2a8427d2cf3306eb084732c956ee6ff0` | `96831ae1525975bf6815da55d2a4e7cb2a8427d2cf3306eb084732c956ee6ff0` | `MIXED(CRLF=1,LF=1158,CR=0)->MIXED(CRLF=1,LF=1158,CR=0)` | `CHANGED` |
| `tmp/spec_consistency_check_plan_probe_stdout.txt` | `utf-16` | `UTF16_TO_UTF8` | `65e7d46eb27338db98884c39850d77049e0b3b8451fd315453431ebfec1ed898` | `16fabe7c44f8610b6df03e74e1e7a4fee0b3eed8c0ebb9a98703fd1f835b4920` | `16fabe7c44f8610b6df03e74e1e7a4fee0b3eed8c0ebb9a98703fd1f835b4920` | `16fabe7c44f8610b6df03e74e1e7a4fee0b3eed8c0ebb9a98703fd1f835b4920` | `CRLF->CRLF` | `CHANGED` |
| `tmp/uiux_errorcode_resolution_changed_files.txt` | `utf-8-sig` | `BOM_REMOVED` | `aac81c7861376a18c5bf9d7a24f401b6a2e212eef00cf82dad9d5f54002f193c` | `881f23375bab779e78d88364f3ef6857c5ed8b0a18408bf80813a93668f3451d` | `881f23375bab779e78d88364f3ef6857c5ed8b0a18408bf80813a93668f3451d` | `881f23375bab779e78d88364f3ef6857c5ed8b0a18408bf80813a93668f3451d` | `MIXED(CRLF=1,LF=147,CR=0)->MIXED(CRLF=1,LF=147,CR=0)` | `CHANGED` |
