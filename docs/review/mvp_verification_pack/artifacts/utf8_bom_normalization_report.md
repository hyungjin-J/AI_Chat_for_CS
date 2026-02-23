# UTF-8 BOM Normalization Report

- generated_at_utc: 2026-02-23T15:53:49Z
- wave1_baseline_delta: 118 -> 98 (reduced 20)
- wave2_baseline_delta: 98 -> 78 (reduced 20)
- cumulative_baseline_delta: 118 -> 78 (reduced 40)
- method: UTF-8 BOM removal only (decoded text hash unchanged)
- baseline_file: `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_baseline_violations.json`
- wave2_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave2_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave2_report.json`

## Wave2 Reduced Items (20)

| Code | Path |
|---|---|
| `UTF8_BOM_FORBIDDEN` | `tmp/ci_notion_sync_context.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/ci_notion_sync_context_test.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/create_customer_print_pack.py` |
| `UTF8_BOM_FORBIDDEN` | `tmp/create_session_idem_redis.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/login.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/login_body.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/login_body_idem_redis.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/message_body.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/message_body_fail_closed.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/message_body_pii.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_login.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_fail.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_1.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_2.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_3.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_4.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_5.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_session.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/session_body.json` |

## Additional Non-baseline Cleanup

- `docs/review/mvp_verification_pack/artifacts/chatgpt_handoff_remediation_summary.txt`
  - resolved newly introduced BOM violation in current working tree (not counted in baseline reduction)

## Verification

Run:

```powershell
python scripts/assert_utf8_strict.py `
  --full-scan `
  --baseline-file docs/review/mvp_verification_pack/artifacts/utf8_full_scan_baseline_violations.json `
  --output-txt docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.json
```

Expected:
- `status=PASS`
- `baseline_violation_count=78`
- `new_violation_count=0`
