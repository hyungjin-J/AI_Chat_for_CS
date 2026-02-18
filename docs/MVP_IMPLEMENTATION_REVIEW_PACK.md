# MVP Implementation Review Pack

## 1) 현재 MVP 상태
- 상태: **Demo Ready**
- 범위: agent-console-first MVP
- 원칙: Answer Contract + citation + evidence 미충족 시 fail-closed(`safe_response`)

## 2) 구현 범위
- 인증/세션/메시지 API
- SSE 스트리밍 + resume
- RAG 검색 + citation 저장/조회
- Answer Contract v1 검증
- PII 마스킹(입력/로그/excerpt)
- trace_id 전파
- tenant 격리 + RBAC
- budget/SSE 동시성 제한

## 3) SSE/API 표준 경로
- `GET /v1/sessions/{session_id}/messages/{message_id}/stream`
- `GET /v1/sessions/{session_id}/messages/{message_id}/stream/resume?last_event_id={n}`
- `GET /v1/rag/answers/{answer_id}/citations` (MVP: `answer_id == message_id`)

## 4) 최신 검증 결과 요약
- `AUTO-FE-001` PASS
- `SSE-NORMAL-001` PASS
- `NEG-TENANT-001` PASS
- `PII-RESP-001` PASS
- `OBS-TRACE-001` PASS
- PostgreSQL bootRun + Flyway PASS
- `SSE-RESUME-001` PASS

상세 결과/근거:
- `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`
- `docs/review/mvp_verification_pack/05_E2E_EVIDENCE.md`
- `docs/review/mvp_verification_pack/06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md`

## 5) 핵심 아티팩트
- `docs/review/mvp_verification_pack/artifacts/backend_bootrun_postgres_output.txt`
- `docs/review/mvp_verification_pack/artifacts/frontend_build_output.txt`
- `docs/review/mvp_verification_pack/artifacts/sse_stream_normal.log`
- `docs/review/mvp_verification_pack/artifacts/citations_api_response.json`
- `docs/review/mvp_verification_pack/artifacts/tenant_isolation_403_checks.txt`
- `docs/review/mvp_verification_pack/artifacts/trace_id_checks.txt`
- `docs/review/mvp_verification_pack/artifacts/pii_masking_checks.txt`
- `docs/review/mvp_verification_pack/artifacts/sse_resume_proof.log`

## 6) 남은 리스크 (Phase 2)
- 다중 인스턴스 환경 idempotency 저장소 고도화
- pgvector 기반 검색 고도화(현재 keyword fallback 포함)
- 관측 지표 자동 리포팅 강화
