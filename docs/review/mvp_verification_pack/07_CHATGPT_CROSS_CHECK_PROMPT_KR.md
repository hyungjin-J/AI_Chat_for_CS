# ChatGPT 교차검증 제출용 프롬프트 (MVP 검증 묶음)

## 1) 통합 검증 프롬프트
아래 내용을 ChatGPT에 그대로 붙여 넣으세요.

```text
당신은 소프트웨어 검증 심사관입니다.
아래 MVP 검증 묶음 파일들을 교차 검증해 주세요.

[검증 목표]
- 실행 증거(아티팩트) 기반 통과/실패 타당성 확인
- 문서 간 모순 확인
- 핵심 안전 규칙(Fail-Closed, PII 마스킹, trace_id, tenant 격리, RBAC) 점검

[검증 원칙]
1) 실행 증거가 없으면 통과로 인정하지 말 것
2) 문서 주장과 아티팩트가 충돌하면 실패 또는 판정유보로 판정
3) 추정 금지, 파일 근거 기반으로만 판단
4) 보안 필수 항목 미흡 시 "Demo 조건부"로 표시

[대상 파일]
- docs/review/mvp_verification_pack/00_EXEC_SUMMARY.md
- docs/review/mvp_verification_pack/03_TEST_PLAN.md
- docs/review/mvp_verification_pack/04_TEST_RESULTS.md
- docs/review/mvp_verification_pack/05_E2E_EVIDENCE.md
- docs/review/mvp_verification_pack/06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md
- docs/review/mvp_verification_pack/artifacts/backend_bootrun_postgres_output.txt
- docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt
- docs/review/mvp_verification_pack/artifacts/frontend_build_output.txt
- docs/review/mvp_verification_pack/artifacts/sse_stream_normal.log
- docs/review/mvp_verification_pack/artifacts/sse_stream_fail_closed.log
- docs/review/mvp_verification_pack/artifacts/sse_resume_proof.log
- docs/review/mvp_verification_pack/artifacts/citations_api_response.json
- docs/review/mvp_verification_pack/artifacts/tenant_isolation_403_checks.txt
- docs/review/mvp_verification_pack/artifacts/trace_id_checks.txt
- docs/review/mvp_verification_pack/artifacts/pii_masking_checks.txt
- docs/review/mvp_verification_pack/artifacts/e2e_curl_transcripts.txt
- docs/review/mvp_verification_pack/artifacts/python_sse_test_output.txt

[판정 항목]
A. SSE-NORMAL-001
B. NEG-TENANT-001
C. OBS-TRACE-001
D. AUTO-FE-001
E. PostgreSQL bootRun + Flyway
F. PII-RESP-001
G. SSE-RESUME-001

[출력 형식]
1) 총평 (5~10줄)
2) 항목별 판정표 (A~G)
   - 상태: 통과 / 실패 / 판정유보
   - 근거 파일
   - 근거 요약
3) 문서 간 불일치 목록
4) 보안/컴플라이언스 리스크 TOP 5
5) 결론: 데모 준비 완료 여부(예/아니오/조건부) + 추가 증거 3개
```

## 2) 제출 전 체크리스트
- [ ] 파일 인코딩 UTF-8 확인
- [ ] 토큰/PII 마스킹 확인
- [ ] 00/04/05/06 문서 상태 일치 확인
- [ ] 아티팩트 경로 오타 확인
