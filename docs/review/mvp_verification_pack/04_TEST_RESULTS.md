# MVP 테스트 결과 (최신 실행 반영)

실행일: `2026-02-18`

| Test ID | 상태 | 근거 파일 |
|---|---|---|
| AUTO-BE-001 | PASS | `artifacts/backend_gradle_test_output.txt` |
| AUTO-PY-001 | PASS | `artifacts/python_sse_test_output.txt` |
| AUTO-FE-001 | PASS | `artifacts/frontend_build_output.txt` |
| BOOT-PG-001 | PASS | `artifacts/backend_bootrun_postgres_output.txt` |
| SSE-NORMAL-001 | PASS | `artifacts/sse_stream_normal.log` |
| SSE-FAIL-001 | PASS | `artifacts/sse_stream_fail_closed.log` |
| SSE-RESUME-001 | PASS | `artifacts/sse_resume_proof.log` |
| NEG-TENANT-001 | PASS | `artifacts/tenant_isolation_403_checks.txt` |
| OBS-TRACE-001 | PASS | `artifacts/trace_id_checks.txt` |
| PII-REQ-001 | PASS | `artifacts/pii_masking_checks.txt` |
| PII-RESP-001 | PASS | `artifacts/citations_api_response.json`, `artifacts/pii_masking_checks.txt` |
| E2E-SESSION-001 | PASS | `artifacts/e2e_curl_transcripts.txt` |

## FAIL -> PASS 전환 확인
1. `AUTO-FE-001` PASS
2. `SSE-NORMAL-001` PASS
3. `NEG-TENANT-001` PASS
4. `PII-RESP-001` PASS
5. `OBS-TRACE-001` PASS
6. PostgreSQL bootRun PASS
7. `SSE-RESUME-001` PASS

## 비고
- trace_id 정책: UUID 형식만 허용, 비UUID는 `SYS-004-409-TRACE`로 거절
- 테넌트 불일치 정책: `403 + SYS-002-403 + details=["tenant_mismatch"]`
- SSE 표준 경로:
  - `GET /v1/sessions/{session_id}/messages/{message_id}/stream`
  - `GET /v1/sessions/{session_id}/messages/{message_id}/stream/resume?last_event_id={n}`
