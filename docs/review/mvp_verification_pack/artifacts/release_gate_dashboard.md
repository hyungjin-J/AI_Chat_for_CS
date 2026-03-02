# Release Gate Dashboard

- git_head_short: `2eced8e`
- git_branch: `utf8-wave8-to-29`
- artifacts_dir: `C:/Users/hjjmj/OneDrive/바탕 화면/AI_Chatbot/docs/review/mvp_verification_pack/artifacts`
- index_json: `C:/Users/hjjmj/OneDrive/바탕 화면/AI_Chatbot/docs/review/mvp_verification_pack/artifacts/_INDEX.json`
- overall_status: `FAIL`

## Gate Status Table
| Gate name | Status | Evidence path(s) | Key metric |
| --- | --- | --- | --- |
| Domain layer boundary gate | PASS | [domain_layer_boundary_gate.json](domain_layer_boundary_gate.json)<br>[domain_layer_boundary_gate.txt](domain_layer_boundary_gate.txt) | baseline_violation_count=0, new_violation_count=0, current_violation_count=0 |
| Application port boundary gate | PASS | [application_port_boundary_gate.json](application_port_boundary_gate.json)<br>[application_port_boundary_gate.txt](application_port_boundary_gate.txt) | baseline_violation_count=0, new_violation_count=0, current_violation_count=0 |
| UTF-8 strict decode gate | PASS | [continuation_utf8_strict_gate.json](continuation_utf8_strict_gate.json)<br>[continuation_utf8_strict_gate.txt](continuation_utf8_strict_gate.txt) | violation_count=0, scanned_file_count=141 |
| UTF-8 full-scan ratchet gate | PASS | [utf8_full_scan_ratchet_gate.json](utf8_full_scan_ratchet_gate.json)<br>[utf8_full_scan_ratchet_gate.txt](utf8_full_scan_ratchet_gate.txt) | baseline_violation_count=0, new_violation_count=0, violation_count=0, scanned_file_count=1169 |
| Spec consistency check | PASS | [spec_consistency_check_report.json](spec_consistency_check_report.json)<br>[spec_consistency_check_pass.txt](spec_consistency_check_pass.txt)<br>[spec_consistency_check_report.txt](spec_consistency_check_report.txt) | violation_count=0 |
| Spec sync report gate | PASS | [spec_sync_report_gate.json](spec_sync_report_gate.json)<br>[spec_sync_report_gate.txt](spec_sync_report_gate.txt) | spec_changed_count=5, evidence_section_count=23 |
| Spec implementation coverage gate | PASS | [spec_impl_coverage_gate.json](spec_impl_coverage_gate.json)<br>[spec_impl_coverage_gate.txt](spec_impl_coverage_gate.txt) | must_api_rows=86, must_backend_missing_count=0, must_tests_missing_count=0 |
| Artifact index gate | PASS | [artifact_index_gate.json](artifact_index_gate.json)<br>[artifact_index_gate.txt](artifact_index_gate.txt) | indexed_file_count=499, violation_count=0 |
| Artifact archive report | PASS | [artifact_archive_report.json](artifact_archive_report.json)<br>[artifact_archive_report.txt](artifact_archive_report.txt) | archived_file_count=1, violation_count=0 |
| Node22 unicode mirror helper smoke | PASS | [node22_unicode_mirror_helper_smoke.txt](node22_unicode_mirror_helper_smoke.txt) | path_mode=mirrored, node_check_status=WARNING, mirror_performed=True |
| DB local readiness smoke | SKIPPED | [db_local_readiness_smoke.json](db_local_readiness_smoke.json)<br>[db_local_readiness_smoke.txt](db_local_readiness_smoke.txt) | reason_code=DOCKER_ENGINE_DOWN, method=docker-exec, violation_count=1 |
| DB backend health trace gate | SKIPPED | [db_backend_health_trace_gate.json](db_backend_health_trace_gate.json)<br>[db_backend_health_trace_gate.txt](db_backend_health_trace_gate.txt) | reason_code=DOCKER_ENGINE_DOWN, violation_count=1 |
| Production deploy smoke | SKIPPED | [prod_deploy_smoke_20260303.json](prod_deploy_smoke_20260303.json)<br>[prod_deploy_smoke_20260303.txt](prod_deploy_smoke_20260303.txt) | reason_code=DOCKER_ENGINE_DOWN |
| Operational E2E smoke | FAIL | [e2e_smoke_report_20260303.json](e2e_smoke_report_20260303.json)<br>[e2e_smoke_trace_samples_20260303.txt](e2e_smoke_trace_samples_20260303.txt) | reason_code=TARGET_UNREACHABLE, status=FAIL |
| RAG regression gate | FAIL | [rag_regression_gate_20260303.json](rag_regression_gate_20260303.json)<br>[rag_regression_gate_20260303.txt](rag_regression_gate_20260303.txt) | reason_code=TARGET_UNREACHABLE, violation_count=1 |
| SSE perf gate | FAIL | [perf_sse_gate_20260303_actual.json](perf_sse_gate_20260303_actual.json)<br>[perf_sse_gate_20260303.txt](perf_sse_gate_20260303.txt) | reason_code=TARGET_UNREACHABLE, violation_count=1 |
| Audit chain verifier | FAIL | [golive_audit_chain_verify_20260303.json](golive_audit_chain_verify_20260303.json)<br>[golive_audit_chain_verify_20260303.txt](golive_audit_chain_verify_20260303.txt) | violation_count=1, checked_rows=0, failure_count=0 |

## Baseline Snapshot
- Domain purity baseline (expected 0): `0` (source: `domain_layer_boundary_gate.json`)
- UTF-8 full-scan baseline (expected 0): `0` (source: `utf8_full_scan_ratchet_gate.json`)
- Public API compare added/removed: `added=0, removed=0` (source: `phase2_2_3_public_api_compare.txt`)

## If FAIL, where to look first
- failing_gates: Operational E2E smoke, RAG regression gate, SSE perf gate, Audit chain verifier
- priority_artifacts:
  - [artifact_index_gate.json](artifact_index_gate.json)
  - [artifact_index_gate.txt](artifact_index_gate.txt)
  - [spec_sync_report_gate.json](spec_sync_report_gate.json)
  - [spec_sync_report_gate.txt](spec_sync_report_gate.txt)
  - [spec_consistency_check_report.json](spec_consistency_check_report.json)
  - [spec_consistency_check_pass.txt](spec_consistency_check_pass.txt)
  - [release_gate_dashboard.json](release_gate_dashboard.json)
