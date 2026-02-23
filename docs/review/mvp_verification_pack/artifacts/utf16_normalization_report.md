# UTF-16 Normalization Report

- generated_at_utc: 2026-02-23T15:53:49Z
- prior_normalized_count: 42
- current_session_new_utf16_conversions: 0
- decoded_hash_mismatch_count: 0
- note: Wave2 focused on low-risk UTF-8 BOM reduction; no additional UTF-16 files were converted.

## Current NON_UTF8_TEXT Residuals (2)

- `docs/review/mvp_verification_pack/artifacts/backend_bootrun_postgres_output.txt`
- `docs/review/mvp_verification_pack/artifacts/sse_concurrency_contract_test_output.txt`

## Verification

Run:

```powershell
python scripts/assert_utf8_strict.py `
  --full-scan `
  --output-txt docs/review/mvp_verification_pack/artifacts/utf8_full_scan_current.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/utf8_full_scan_current.json
```

Expected:
- `violation_count=78`
- `NON_UTF8_TEXT` count remains `2`
