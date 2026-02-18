# LLM-PROVIDER-001 분석 및 조치 결과

- 분석 대상 로그: `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`
- 최초 문제 상태: `status=SKIPPED`
- 재검증 시각: 2026-02-19 00:36 (KST)

## 1) SKIPPED의 정확한 조건(초기)
초기 로그에서 normal 시나리오는 아래 흐름으로 종료되었다.
- `heartbeat -> tool(rag_retrieve) -> safe_response -> error(AI-009-422-SCHEMA) -> done(response_type=safe)`
- `event:citation`이 없어서 회귀 스크립트 기준 PASS 조건(`normal_has_citation=true`)을 만족하지 못했다.

즉, **정상 질문에서 Answer Contract 검증 실패로 fail-closed가 발생**했고,
그 결과 `LLM-PROVIDER-001`은 SKIPPED였다.

## 2) 적용한 수정
- Ollama 출력 안정화
  - `format=json`, `temperature/top_p` 고정 옵션 적용
  - 응답 JSON 추출 및 1회 repair 경로 추가 (`LlmService.repairAnswerContractJson`)
- Prompt 안정화
  - 깨진 문자열 제거, 계약 필드/인용 규칙을 명시한 UTF-8 정상 프롬프트로 교체
- Tool citation 연결 강화
  - `PolicyLookupTool`에 citation 메타 포함(`policy_code`, `policy_version`, `section`, `source_ref`, `citation_chunk_id`, `excerpt_masked`)
  - `MessageGenerationService`에서 Tool 결과를 citation 후보에 포함
  - 모델이 Tool citation을 누락해도 `TOOL_CITATION` 보강 저장/스트리밍
- SSE 보안 유지
  - `event:tool` payload는 마스킹 요약만 포함, `tenant_key/user_role` 미노출 유지

## 3) 현재 결과
최신 로그 기준:
- `status=PASS`
- normal: `event:citation` 존재 (RAG + `TOOL_CITATION`)
- fail case: `safe_response` 후 `done`, token 누출 없음

결론: `LLM-PROVIDER-001`은 PASS로 전환 가능한 증빙이 확보되었다.
