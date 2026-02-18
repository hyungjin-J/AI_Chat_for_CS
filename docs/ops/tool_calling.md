# Tool Calling 운영 가이드

## 목적
- Spring AI `@Tool` 기반 도구 호출을 채팅 흐름에 연결해, 정책성 정보를 안정적으로 보강합니다.
- 민감정보는 LLM 프롬프트가 아니라 `ToolContext`로만 전달합니다.

## 현재 적용된 도구
- 도구명: `policy_lookup`
- 구현 위치: `backend/src/main/java/com/aichatbot/tool/application/PolicyLookupTool.java`
- 호출 오케스트레이션: `backend/src/main/java/com/aichatbot/tool/application/SpringAiToolCallingService.java`

## 언제 도구를 호출하나
- 질문에 아래 키워드가 포함되면 도구를 우선 시도합니다.
- 환불/refund, 정책/policy, 배송/지연(delay)

## 보안 원칙
- `tenant_key`, `trace_id`, `user_role`는 `ToolContext`로만 전달
- 위 값은 프롬프트 본문에 넣지 않음
- SSE `tool` 이벤트에는 마스킹된 요약만 기록
- 최종 답변은 기존 Answer Contract 검증을 그대로 따름
  - 검증 실패 시 `safe_response` + `done` (Fail-Closed)

## 스트리밍 이벤트 반영
- 도구 실행 시 `event: tool` 이벤트가 추가됩니다.
- 예시 필드: `tool_name`, `status`, `policy_code`, `summary_masked`, `trace_id`

## 주의
- 도구 실행 성공과 최종 답변 성공은 별개입니다.
- 도구가 실행되어도 citations/스키마/근거 임계치를 통과하지 못하면 안전 응답으로 종료됩니다.
