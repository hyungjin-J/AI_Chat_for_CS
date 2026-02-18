# MVP 테스트 계획 (Test Plan)

## 범위
- 기준 문서: `docs/MVP_IMPLEMENTATION_REVIEW_PACK.md`
- 검증 축:
  - 인증/권한/테넌트
  - 세션/메시지/SSE
  - Fail-Closed/Answer Contract
  - PII 마스킹
  - trace_id 전파
  - 예산/동시성 제한

## 공통 전제
- OS: Windows
- 백엔드: `backend/gradlew.bat`
- 프론트엔드: npm (`package-lock.json`)
- 산출 경로: `docs/review/mvp_verification_pack/artifacts/`

## A. 자동 테스트

| Test ID | 목적 | 사전조건 | 실행 명령 | 기대 결과 | 증빙 파일 |
|---|---|---|---|---|---|
| AUTO-BE-001 | 백엔드 테스트 실행 | JDK 17 | `cd backend && .\gradlew.bat test` | 테스트 성공 | `artifacts/backend_gradle_test_output.txt` |
| AUTO-PY-001 | Python SSE 단위 테스트 | Python 3.11 | `python tests/sse_stream_basic_test.py` | 테스트 성공 | `artifacts/python_sse_test_output.txt` |
| AUTO-FE-001 | 프론트 빌드 재현 | Node/npm 설치 | `cd frontend && npm ci && npm run build` | 빌드 성공 | `artifacts/frontend_build_output.txt` |

## B. E2E API 테스트

공통 헤더:
- `X-Tenant-Key`
- `X-Trace-Id` (UUID)
- `Authorization: Bearer <token>`
- `Idempotency-Key`

| Test ID | 목적 | 단계 | 기대 결과 | 증빙 파일 |
|---|---|---|---|---|
| E2E-AUTH-401 | 인증 미제공 차단 | 인증 없이 bootstrap 호출 | `SEC-001-401` | `artifacts/rbac_401_403_checks.txt` |
| E2E-AUTH-403 | 권한 없는 호출 차단 | 권한 불일치 호출 | `SEC-002-403` 또는 정책 코드 | `artifacts/rbac_401_403_checks.txt` |
| E2E-SESSION-001 | 세션 생성 | `POST /v1/sessions` | `201` + `session_id` | `artifacts/e2e_curl_transcripts.txt` |
| E2E-MSG-001 | 메시지 생성 | `POST /messages` | `202` + `message_id` | `artifacts/e2e_curl_transcripts.txt` |

## C. SSE 프로토콜 테스트

| Test ID | 목적 | 단계 | 기대 결과 | 증빙 파일 |
|---|---|---|---|---|
| SSE-NORMAL-001 | 정상 answer+citation 스트림 | `GET /stream` | `tool -> citation -> token -> done` | `artifacts/sse_stream_normal.log` |
| SSE-FAIL-001 | fail-closed 토큰 누출 방지 | 실패 입력으로 stream 호출 | `safe_response -> done`, answer token 누출 없음 | `artifacts/sse_stream_fail_closed.log` |
| SSE-RESUME-001 | resume 재생성 | `GET /v1/sessions/{session_id}/messages/{message_id}/stream/resume?last_event_id=n` | `n+1` 이후 이벤트 재생 | `artifacts/sse_resume_proof.log` |
| SSE-CONC-429 | 동시 접속 제한 | 다중 SSE 동시 호출 | `API-008-429-SSE` | `artifacts/sse_concurrency_attempts.txt` |

## D. 네거티브 테스트

| Test ID | 목적 | 단계 | 기대 결과 | 증빙 파일 |
|---|---|---|---|---|
| NEG-422-IDEM | Idempotency-Key 검증 | 키 없이 POST | `API-003-422` | `artifacts/e2e_curl_transcripts.txt` |
| NEG-TENANT-001 | 교차 테넌트 차단 | tenant-a 리소스를 tenant-b로 조회 | `403` + 일관 `error_code` | `artifacts/tenant_isolation_403_checks.txt` |
| NEG-BUDGET-001 | 예산 초과 차단 | 반복 호출로 budget 초과 | `API-008-429-BUDGET` | `artifacts/budget_429_checks.txt` |

## E. PII 마스킹 테스트

| Test ID | 목적 | 단계 | 기대 결과 | 증빙 파일 |
|---|---|---|---|---|
| PII-REQ-001 | 입력 마스킹 | PII 포함 질문 전송 | 저장/로그에서 마스킹 | `artifacts/pii_masking_checks.txt` |
| PII-RESP-001 | 응답 excerpt 마스킹 | citation API 조회 | `excerpt_masked`에 원문 PII 없음 | `artifacts/citations_api_response.json`, `artifacts/pii_masking_checks.txt` |

## F. 관측(trace_id) 테스트

| Test ID | 목적 | 단계 | 기대 결과 | 증빙 파일 |
|---|---|---|---|---|
| OBS-TRACE-001 | trace_id 종단간 일치 | 동일 요청에서 HTTP/SSE/DB 비교 | 동일 trace_id 확인 | `artifacts/trace_id_checks.txt` |

## 10분 검증 순서
1. `backend_gradle_test_output.txt`
2. `frontend_build_output.txt`
3. `sse_stream_normal.log`
4. `sse_stream_fail_closed.log`
5. `tenant_isolation_403_checks.txt`
6. `trace_id_checks.txt`
7. `pii_masking_checks.txt`
