# 비개발자용 설명: MVP가 실제로 하는 일

## MVP가 하는 일 (사용자 관점)
상담원이 질문을 입력하면, 시스템은 먼저 관련 근거를 찾고(RAG), 그 근거로 답변을 만듭니다.  
그다음 답변 형식/근거/신뢰 조건을 다시 검사합니다(Answer Contract).  
검사를 통과한 답변만 화면에 보이고, 통과하지 못하면 안전 안내문(`safe_response`)만 보여줍니다.

## 화면/기능 흐름 (AGENT 콘솔 기준)
1. 로그인 (`/v1/auth/login`)
2. 초기 정보 조회 (`/v1/chat/bootstrap`)
3. 세션 생성 (`/v1/sessions`)
4. 질문 전송 (`/v1/sessions/{session_id}/messages`)
5. SSE 스트리밍 수신 (`/stream`, `/stream/resume`)
6. 근거 목록 조회 (`/v1/rag/answers/{answer_id}/citations`)

## 핵심 안전장치 5개
1. Fail-Closed  
검증 실패 시 자유 텍스트 답변을 노출하지 않고 안전 응답만 반환
2. Answer Contract  
답변 JSON 구조, citation 존재, evidence 임계치 충족을 강제
3. PII Masking  
이메일/전화번호/주문번호 등 개인정보를 입력/로그/응답에서 마스킹
4. trace_id  
요청 시작부터 응답 완료까지 동일 추적 ID로 전 구간 추적
5. Tenant/RBAC  
테넌트 분리와 권한 검증을 서버에서 강제(프론트 숨김만으로 허용 금지)

## safe_response가 나오는 상황 예시 5개
1. 모델 출력이 계약(JSON Schema)에 맞지 않음
2. 답변에 citation이 없음
3. evidence.score가 threshold 미만
4. 정책 위반(금지 문구/필수 문구 누락)
5. 시스템 오류로 근거 기반 답변 검증이 불가능함

## 에러코드가 보이는 방식 예시
- 인증 실패: `SEC-001-401`
- 권한 없음: `SEC-002-403`
- 예산 초과: `API-008-429-BUDGET`
- SSE 동시 연결 초과: `API-008-429-SSE`
- 안전 전환: `AI-009-200-SAFE`

관련 아티팩트:
- `docs/review/mvp_verification_pack/artifacts/rbac_401_403_checks.txt`
- `docs/review/mvp_verification_pack/artifacts/budget_429_checks.txt`
- `docs/review/mvp_verification_pack/artifacts/sse_stream_fail_closed.log`

## 10분 확인 가이드
1. `sse_stream_fail_closed.log`에서 `safe_response`와 `done` 확인
2. `pii_masking_checks.txt`에서 개인정보 마스킹 확인
3. `rbac_401_403_checks.txt`에서 401/403 확인
4. `sse_concurrency_attempts.txt`에서 SSE 429 확인
