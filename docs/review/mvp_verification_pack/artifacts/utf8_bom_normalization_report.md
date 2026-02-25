# UTF-8 BOM Normalization Report

- generated_at_utc: 2026-02-25T14:35:30Z
- wave1_baseline_delta: 118 -> 98 (reduced 20)
- wave2_baseline_delta: 98 -> 78 (reduced 20)
- wave3_baseline_delta: 78 -> 66 (reduced 12)
- wave4_baseline_delta: 66 -> 56 (reduced 10)
- wave5_baseline_delta: 56 -> 46 (reduced 10)
- wave6_baseline_delta: 46 -> 40 (reduced 6)
- wave7_baseline_delta: 40 -> 33 (reduced 7)
- wave8_baseline_delta: 33 -> 25 (reduced 8)
- wave9_baseline_delta: 25 -> 3 (reduced 22)
- wave10_baseline_delta: 3 -> 0 (reduced 3)
- cumulative_baseline_delta: 118 -> 0 (reduced 118)
- method: UTF-8 BOM removal + safe CP949-to-UTF8 normalization (decoded text hash unchanged)
- wave9_selection_rationale: converted all non-canonical residuals from baseline (BOM-only files + 2 cp949 artifact logs).
- wave10_selection_rationale: normalized the remaining canonical-spec CSV BOM residuals under explicit override + Notion/spec_sync compliance workflow.
- baseline_file: `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_baseline_violations.json`
- wave2_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave2_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave2_report.json`
- wave3_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave3_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave3_report.json`
- wave4_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave4_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave4_report.json`
- wave5_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave5_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave5_report.json`
- wave6_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave6_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave6_report.json`
- wave7_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave7_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave7_report.json`
- wave8_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave8_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave8_report.json`
- wave9_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave9_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave9_report.json`
- wave10_detailed_hash_report:
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave10_report.md`
  - `docs/review/mvp_verification_pack/artifacts/utf8_normalization_wave10_report.json`

## Wave9 Reduced Items (22)

| Code | Path |
|---|---|
| `NON_UTF8_TEXT` | `docs/review/mvp_verification_pack/artifacts/backend_bootrun_postgres_output.txt` |
| `NON_UTF8_TEXT` | `docs/review/mvp_verification_pack/artifacts/sse_concurrency_contract_test_output.txt` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_6.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_7.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_8.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_9.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_10.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_11.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_12.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_13.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_14.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_15.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_16.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_17.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_18.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_19.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/metrics_message_normal_20.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/provider_session.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/sse_real_login.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/sse_real_msg.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/sse_real_session.json` |
| `UTF8_BOM_FORBIDDEN` | `tmp/update_menual_docs.py` |

## Wave10 Reduced Items (3)

| Code | Path |
|---|---|
| `UTF8_BOM_FORBIDDEN` | `docs/references/CS AI Chatbot_Requirements Statement.csv` |
| `UTF8_BOM_FORBIDDEN` | `docs/references/Development environment.csv` |
| `UTF8_BOM_FORBIDDEN` | `docs/references/Summary of key features.csv` |

## Verification

Run:

```powershell
python scripts/assert_utf8_strict.py `
  --full-scan `
  --baseline-file docs/review/mvp_verification_pack/artifacts/utf8_full_scan_baseline_violations.json `
  --git-base-ref HEAD~1 `
  --output-txt docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.json
```

Expected:
- `status=PASS`
- `baseline_violation_count=0`
- `new_violation_count=0`
