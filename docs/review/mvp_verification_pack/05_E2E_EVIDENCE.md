# E2E 증빙 (Sanitized)

토큰/PII는 `***`로 마스킹 처리했다.

## 1) 기본 플로우
- 파일: `artifacts/e2e_curl_transcripts.txt`
- 확인: 로그인 -> 세션 생성 -> 메시지 생성 성공

## 2) 정상 SSE + citation (PASS)
- 경로: `GET /v1/sessions/{session_id}/messages/{message_id}/stream`
- 파일: `artifacts/sse_stream_normal.log`
- 확인 이벤트 순서:
  - `heartbeat -> tool -> citation -> token -> token -> done`
- 확인 포인트:
  - `done.response_type = answer`
  - citation 이벤트 존재
  - 계약 검증 통과 후 token 전송

## 3) Citation API (PASS)
- 경로: `GET /v1/rag/answers/{answer_id}/citations`
- 파일: `artifacts/citations_api_response.json`
- 확인:
  - citations 1건 이상
  - `excerpt_masked` 포함
  - raw email/phone/order id 미노출

## 4) fail-closed (PASS)
- 파일: `artifacts/sse_stream_fail_closed.log`
- 확인:
  - `safe_response` 발생
  - 이후 `done` 발생
  - answer token 누출 없음

## 5) 테넌트 격리 (PASS)
- 파일: `artifacts/tenant_isolation_403_checks.txt`
- 확인:
  - 유효 토큰 + 잘못된 `X-Tenant-Key`로 접근 시
  - `HTTP 403`, `error_code=SYS-002-403`, `details=["tenant_mismatch"]`

## 6) trace_id 종단 일치 (PASS)
- 파일: `artifacts/trace_id_checks.txt`
- 확인:
  - HTTP trace_id = SSE trace_id = DB 저장 trace_id

## 7) PII 마스킹 (PASS)
- 파일: `artifacts/pii_masking_checks.txt`
- 확인:
  - 요청 PII(이메일/전화/주문번호) 마스킹 저장
  - citation excerpt 마스킹 유지

## 8) SSE resume (PASS)
- 경로: `GET /v1/sessions/{session_id}/messages/{message_id}/stream/resume?last_event_id={n}`
- 파일: `artifacts/sse_resume_proof.log`
- 확인:
  - `last_event_id=2` 이후 이벤트(`id=3`부터) 재생

## 9) Postgres + Flyway + bootRun (PASS)
- 파일: `artifacts/backend_bootrun_postgres_output.txt`
- 확인 문자열:
  - `Database: ... (PostgreSQL 16.12)`
  - `Successfully validated 1 migration`
  - `Tomcat started on port 8080`
