# UTF-8 Normalization Report

- generated_at_utc: 2026-02-24T14:26:13.007046+00:00
- dry_run: NO
- candidate_count: 7
- changed_count: 7
- skipped_count: 0
- verification_method: decoded-text SHA-256 + byte SHA-256

| file | old_encoding | action | old_bytes_sha256 | new_bytes_sha256 | old_decoded_sha256 | new_decoded_sha256 | line_endings(old->new) | status |
|---|---|---|---|---|---|---|---|---|
| `docs/review/mvp_verification_pack/artifacts/provider_regression_exit_code.txt` | `utf-8-sig` | `BOM_REMOVED` | `224717ec20be9761bcf2546fc7cb181694f29867b31adbabad22ebaf3470d340` | `7a0ae22f4bbd97c1212bda208fc96c52e5471474effd776ac1f11174954ded01` | `7a0ae22f4bbd97c1212bda208fc96c52e5471474effd776ac1f11174954ded01` | `7a0ae22f4bbd97c1212bda208fc96c52e5471474effd776ac1f11174954ded01` | `CRLF->CRLF` | `CHANGED` |
| `docs/review/mvp_verification_pack/artifacts/rbac_401_403_checks.txt` | `utf-8-sig` | `BOM_REMOVED` | `09c4c037fb886f4abb2971299925c875505ef7622812ea992815ea71991c0571` | `b32a03018688be0f6cbc1466488bc0bdbfc52e6a9d92d7ae6148b97732e6b174` | `b32a03018688be0f6cbc1466488bc0bdbfc52e6a9d92d7ae6148b97732e6b174` | `b32a03018688be0f6cbc1466488bc0bdbfc52e6a9d92d7ae6148b97732e6b174` | `MIXED(CRLF=1,LF=9,CR=0)->MIXED(CRLF=1,LF=9,CR=0)` | `CHANGED` |
| `docs/review/mvp_verification_pack/artifacts/sse_concurrency_attempts.txt` | `utf-8-sig` | `BOM_REMOVED` | `477d48a66c98d2a37bd7a44bb8b0c8b2d04cd718bfdf6b27c48d85f74ff4342e` | `2b758435043bbf036cd94a863dd4816e077f508118f82b4d171e96c01d3c5933` | `2b758435043bbf036cd94a863dd4816e077f508118f82b4d171e96c01d3c5933` | `2b758435043bbf036cd94a863dd4816e077f508118f82b4d171e96c01d3c5933` | `MIXED(CRLF=1,LF=3,CR=0)->MIXED(CRLF=1,LF=3,CR=0)` | `CHANGED` |
| `docs/review/mvp_verification_pack/artifacts/sse_concurrency_real_limit_proof.txt` | `utf-8-sig` | `BOM_REMOVED` | `c75ad4108c7ac59c06dc9e813a8d24e2656e9e17736d72a035c8f5a5bf655240` | `430ad40f791d8682edb3829323eaf390011066f916af1b5d6f4e0b1e6c598ac0` | `430ad40f791d8682edb3829323eaf390011066f916af1b5d6f4e0b1e6c598ac0` | `430ad40f791d8682edb3829323eaf390011066f916af1b5d6f4e0b1e6c598ac0` | `MIXED(CRLF=1,LF=9,CR=0)->MIXED(CRLF=1,LF=9,CR=0)` | `CHANGED` |
| `docs/review/mvp_verification_pack/artifacts/tenant_isolation_403_checks.txt` | `utf-8-sig` | `BOM_REMOVED` | `87ee877265585bfd73e28ce10b63e0c77bceaa343f69022d5d7697b5ce355822` | `be67d31d4fe89741ddf5b96c49a07684159470c2cc38734a0c0b88edea941b09` | `be67d31d4fe89741ddf5b96c49a07684159470c2cc38734a0c0b88edea941b09` | `be67d31d4fe89741ddf5b96c49a07684159470c2cc38734a0c0b88edea941b09` | `CRLF->CRLF` | `CHANGED` |
| `docs/review/mvp_verification_pack/artifacts/trace_id_checks.txt` | `utf-8-sig` | `BOM_REMOVED` | `00f017a0282101b7cde825d989d8322d9fde0f22656299774f32894975524e22` | `9d89ec8003e7d0f163a237e5d97d7f3fb00140e3566cb57cc0241f5a5ac36691` | `9d89ec8003e7d0f163a237e5d97d7f3fb00140e3566cb57cc0241f5a5ac36691` | `9d89ec8003e7d0f163a237e5d97d7f3fb00140e3566cb57cc0241f5a5ac36691` | `MIXED(CRLF=4,LF=6,CR=0)->MIXED(CRLF=4,LF=6,CR=0)` | `CHANGED` |
| `docs/review/mvp_verification_pack/artifacts/uuid_cast_scan_output.txt` | `utf-8-sig` | `BOM_REMOVED` | `45016a486b62be6030d0d45b31aeb16c23f22719b00159b425899e1bd753579b` | `d2afc6cecc60188aae3b4e3a5351dcaa915a973a990bd4a90471cfdb95a2d7b4` | `d2afc6cecc60188aae3b4e3a5351dcaa915a973a990bd4a90471cfdb95a2d7b4` | `d2afc6cecc60188aae3b4e3a5351dcaa915a973a990bd4a90471cfdb95a2d7b4` | `CRLF->CRLF` | `CHANGED` |
