# CS 지원 AI 챗봇(RAG) - 시스템 아키텍처

- 버전: `v1.0`
- 최종 업데이트: `2026-02-18`
- 대상 Notion 페이지: `https://www.notion.so/2ee405a3a72080868020e37dc33abad4`

## 아키텍처 다이어그램 (가장 먼저 업로드)

1. 이미지 파일 업로드: `docs/architecture/diagrams/cs_rag_system_architecture_v1.png`
2. Notion 페이지 최상단에 배치
3. (선택) 원본 보관용으로 `docs/architecture/diagrams/cs_rag_system_architecture_v1.svg` 첨부

---

## 1) 시스템 개요

본 시스템은 상담원 콘솔 중심의 CS 지원 AI 챗봇이며, RAG와 엄격한 답변 통제 정책을 적용합니다. 기본 처리 경로는 질문 접수 -> 검색(RAG) -> LLM 생성 -> Answer Contract 검증 -> SSE 스트리밍입니다. 검증 실패(스키마/인용/근거 점수 미달) 시 자유 텍스트로 우회하지 않고 fail-closed로 전환하여 `safe_response`만 노출합니다.

---

## 2) 계층별 아키텍처

### 클라이언트 계층

- 스택: React 18, TypeScript 5, Vite 5
- 역할:
  - 상담원 로그인 및 세션 부트스트랩
  - 질문 전송 및 SSE 스트림 렌더링
  - 근거(citation/evidence) 패널 표시
  - safe_response/오류코드 배너 표시
  - 중복 SSE 청크 제거 및 resume 처리

### 엣지/웹 서버 계층

- 스택: Nginx + TLS/SSL 종료
- 역할:
  - 외부 유입 트래픽 처리
  - 백엔드(Spring Boot) 리버스 프록시
  - 헤더 전달(`X-Trace-Id`, 테넌트 라우팅 헤더)

### 백엔드 계층

- 스택: Java 17, Spring Boot 3.x, Spring Security
- 역할:
  - JWT 인증 및 RBAC 강제(서버가 최종 권위)
  - `X-Tenant-Key` 기반 테넌트 격리/라우팅
  - Trace 전파(`X-Trace-Id` -> request/search/tool/model/stream)
  - LLM 입력/저장 전 PII 마스킹
  - RAG 오케스트레이션 + Answer Contract 검증
  - SSE 이벤트 생성 및 resume 재생
  - 예산/레이트리밋 가드 + 멱등성 체크

### AI/RAG 구성요소 계층

- 구성요소:
  - 문서 파싱 서비스(Apache Tika, 선택 OCR)
  - 임베딩 모델 서비스
  - 선택적 리랭커 서비스
  - LLM 제공자: 로컬 Ollama + 외부 Provider API(선택)
- 역할:
  - 검색 컨텍스트 조립
  - 구조화 답변(JSON 계약 형태) 생성
  - 정책 가드레일 검사

### 데이터/검색 계층

- 스택: PostgreSQL 16+(pgvector 선택), Redis, OpenSearch/Elasticsearch(선택)
- 역할:
  - 세션/메시지/인용/스트림 이벤트 저장
  - RAG 검색 로그 및 근거 메타데이터 저장
  - 캐시/세션/카운터 상태 저장
  - Phase-2 하이브리드 검색(BM25 + 벡터) 확장 기반

### 관측 계층

- 스택: OpenTelemetry + Micrometer + ELK 호환 파이프라인
- 역할:
  - 전 계층 로그/메트릭/트레이스 수집
  - ingress부터 stream done까지 추적성 확보
  - 가드레일/지연 장애 알림 신호 제공

### 외부 시스템 계층

- 구성요소:
  - 외부 LLM Provider API
  - 헬프데스크/티켓 시스템(선택)
  - 웹훅 수신/전송 엔드포인트

---

## 3) 주요 요청 흐름

### 흐름 A: 채팅 질문 -> RAG -> 계약 검증 -> SSE

1. 상담원이 질문 전송 (`POST /v1/sessions/{session_id}/messages`)
2. 백엔드가 인증/RBAC/테넌트/trace/멱등성/예산 검증
3. 검색 및 모델 프롬프트 전에 PII 마스킹 수행
4. Retrieval 실행(`top_k`) 및 마스킹된 검색 로그 저장
5. LLM이 구조화 JSON 후보 생성
6. Answer Contract 검증:
   - 스키마 유효성
   - citation 존재 여부
   - evidence 임계치 충족 여부
7. 통과 시 SSE 이벤트 순서로 전송:
   - `tool` -> `citation` -> `token` -> `done`
8. 클라이언트가 답변 및 근거 패널 렌더링

### 흐름 B: Fail-Closed 시나리오

주요 트리거:
- 스키마 검증 실패
- citation 누락
- evidence 점수 임계치 미달
- 정책 위반

처리 방식:
1. 정상 답변 게시 차단
2. `safe_response` 이벤트 전송
3. `done` 이벤트 전송
4. 자유 텍스트 fallback 미노출

---

## 4) 보안 및 컴플라이언스 통제

### PII 전 구간 마스킹

- LLM 입력 전 마스킹
- 로그/저장 전 마스킹
- citation excerpt/UI payload 마스킹
- 비밀값(secret/token) 평문 저장 금지

### RBAC + 테넌트 격리

- 역할 검증은 서버에서 강제
- `X-Tenant-Key` 필수 및 서버 매핑
- 비인가 요청은 표준 `error_code`와 함께 `403`

### trace_id 전파 및 감사 추적성

- 모든 요청 경로에 `trace_id` 존재
- retrieval/tool/model/stream 이벤트까지 전파
- trace 누락은 정책에 따라 차단 가능

### 예산 및 오남용 방어

- 입/출력 토큰 한도
- tool call/`top_k` 한도
- 세션 누적 예산 상한
- SSE 동시 연결 상한
- 초과 시 일관된 헤더/코드로 `429/403` 반환

---

## 5) 관측 계획

### 필수 지표

- API 지연(`p50/p95/p99`)
- SSE first-token 지연 / 완료 지연
- Answer Contract 통과/실패 건수
- fail-closed 전환율
- citation coverage / evidence 품질 지표
- budget/rate-limit 트리거 건수
- 테넌트 단위 에러율/포화도

### 권장 대시보드

- 요청 파이프라인 지연 대시보드
- 가드레일 결과 대시보드(스키마/인용/근거/정책)
- SSE 상태 대시보드(오픈 스트림, resume 비율, 오류)
- LLM Provider 안정성 대시보드(timeout/fallback/retry)

---

## 6) MVP 경계와 Phase-2

### MVP (구현 범위)

- 상담원 중심 채팅 플로우
- JWT 인증 + RBAC
- 테넌트 라우팅 격리
- trace 전파
- Answer Contract fail-closed 경로
- SSE 스트림 + resume 엔드포인트
- citation/stream-event 저장
- 기본 키워드 fallback 검색
- 예산 + SSE 동시성 가드

### Phase-2 (계획 범위)

- 영속 멱등 저장소(DB/Redis)
- pgvector/하이브리드 검색 + 리랭커 운영 경로 적용
- 분산 SSE 동시성 제어 고도화
- 외부 LLM 라우팅/정책 팩 강화
- 관리자/운영 콘솔 및 워크플로우 확장

---

## 7) 아이콘 및 라이선스 출처

- 브랜드 아이콘 출처: `simple-icons`
- 라이선스: 0BSD (permissive)
- 래스터화/가공: `sharp`
- 가드레일 개념 아이콘(`fail-closed`, `PII`, `trace`, `RBAC`, `budget`)은 로컬 중립 아이콘으로 생성

아이콘 경로:
- `docs/architecture/assets/icons/`

생성 스크립트:
- `tools/architecture/generate_icons.mjs`
- `scripts/generate_architecture_diagram.py`
