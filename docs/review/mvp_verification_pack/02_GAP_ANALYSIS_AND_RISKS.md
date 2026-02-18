# MVP 갭 분석 및 리스크 (기준: MVP_IMPLEMENTATION_REVIEW_PACK.md + 스펙 파일)

## 기준선
- 구현 기준 문서: `docs/MVP_IMPLEMENTATION_REVIEW_PACK.md`
- 참조 스펙:
  - `docs/references/CS AI Chatbot_Requirements Statement.csv`
  - `docs/references/google_ready_api_spec_v0.3_20260216.xlsx` (`전체API목록`)
  - `docs/references/CS_AI_CHATBOT_DB.xlsx`
  - `docs/uiux/CS_RAG_UI_UX_설계서.xlsx` (`01_에러메시지코드`)

## 반드시 수정 (차단 이슈)

### 1) 정상 답변+근거 인용 스트리밍 증거 부재 리스크 (해소 완료)
- 증상:
  - 정상 시나리오 증거가 없으면 fail-closed만 증명되고 정상 경로 신뢰성이 낮아짐
- 중요성:
  - AGENTS.md의 근거 기반 응답 원칙 검증 불충분
- 재현/검증:
  - `artifacts/sse_stream_normal.log` 확인 (`tool -> citation -> token -> done`)
- 상태:
  - 현재 통과로 해소

### 2) Evidence score/threshold 의미 약화 리스크
- 증상:
  - 점수 계산이 형식적이면 실제 근거 품질을 반영하지 못할 수 있음
- 중요성:
  - 근거 없는 답변 노출 방지 정책의 실효성 약화
- 재현/검증:
  - 경계값 입력으로 evidence 통과/실패 분기 확인
- 권장 조치:
  - 점수 산식에 근거 일치도/정책 검증 지표를 반영

### 3) trace_id 정규화로 상관관계 단절 리스크 (해소 완료)
- 증상:
  - 입력 trace_id와 저장/스트림 trace_id가 다르면 추적 실패
- 중요성:
  - AGENTS.md의 end-to-end 추적 원칙 위배
- 재현/검증:
  - `artifacts/trace_id_checks.txt`에서 HTTP/SSE/DB 동일 값 확인
- 상태:
  - UUID 정책 강제 + 불일치 방지로 통과

### 4) PostgreSQL + Flyway 부팅 경로 실패 리스크 (해소 완료)
- 증상:
  - DB 지원 버전/드라이버 이슈 시 앱 부팅 실패
- 중요성:
  - MVP 데모/운영 경로 차단
- 재현/검증:
  - `artifacts/backend_bootrun_postgres_output.txt`
- 상태:
  - PG 16.12 + 마이그레이션 적용 통과

### 5) Tenant filter 누락으로 교차 접근 리스크 (해소 완료)
- 증상:
  - 다른 테넌트 리소스 접근이 차단되지 않으면 데이터 노출 가능
- 중요성:
  - AGENTS.md 테넌트 격리 원칙 위반
- 재현/검증:
  - `artifacts/tenant_isolation_403_checks.txt`
- 상태:
  - 403 + 일관 코드로 통과

## 권장 수정

### 6) Fail-Closed 전환 케이스 확장
- 현재:
  - 주요 케이스는 증명됨
- 추가 권장:
  - schema/citation/evidence/policy 실패 유형별 회귀 테스트 분리

### 7) Idempotency 분산 환경 보강
- 현재:
  - MVP 단일 환경 중심
- 추가 권장:
  - Redis/DB 기반 키 저장과 TTL 정책 강화

### 8) SSE 이어받기 다중 환경 검증 확대
- 현재:
  - 1개 환경 재현 통과
- 추가 권장:
  - 네트워크 지연/재접속 조건별 재현 스위트 추가

## 추가 개선 권장

### 9) 프론트 빌드 표준화 강화
- Node/npm 버전 핀 고도화, CI 캐시 전략 명시

### 10) 관측 지표 자동 리포트
- `first_token_ms`, `fail_closed_rate`, `citation_coverage` 자동 집계

## 10분 체크
1. `sse_stream_fail_closed.log` 확인
2. `sse_stream_normal.log` 확인
3. `tenant_isolation_403_checks.txt` 확인
4. `trace_id_checks.txt` 확인
5. `pii_masking_checks.txt` 확인
