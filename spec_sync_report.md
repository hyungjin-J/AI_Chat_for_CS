# Spec Sync Report

## 1) 보고 목적
- 스펙/운영 문서 변경과 Notion 반영 이력을 한 곳에서 추적하기 위한 동기화 보고서입니다.
- 본 문서는 UTF-8 기준으로 관리합니다.

## 2) 최근 스펙 동기화 기준 이력
- 기준 일시: 2026-02-17
- 기준 커밋: `3edba1d`
- 반영 대상(레퍼런스 스펙):
  - `docs/references/CS AI Chatbot_Requirements Statement.csv`
  - `docs/references/Summary of key features.csv`
  - `docs/references/Development environment.csv`
  - `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
  - `docs/references/CS_AI_CHATBOT_DB.xlsx`
  - `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`
- 관련 Notion 반영 완료(각 페이지 메타: Last synced at / Source file / Version / Change summary)

## 3) 이번 세션(2026-02-18) 반영 범위
- 레퍼런스 스펙(CSV/XLSX) 구조/본문 변경: **없음**
- 운영 검증 문서/증빙 반영: **있음**
  - `docs/review/mvp_verification_pack/*`
  - `PHASE2_PROGRESS_SUMMARY_FOR_CHATGPT.md`
  - `07_MVP_GLOSSARY_CEO_KR.xlsx`

## 4) 이번 세션 Notion 동기화 계획/결과
- 글로서리 페이지(경영진 공유용):
  - 대상: `https://www.notion.so/30a405a3a720804b8d41e65628abe376`
  - 반영 내용:
    - Phase2.1 기준 용어(SSOT, Branch Protection, Consistency Gate, Artifact Scan, SSE 실한도 검증, Node 22.12.0 고정)
    - 경영진 1페이지 요약(최신 지표/리스크/TOP5 처리 결과)
  - 반영 결과: **완료 (2026-02-18 20:25 KST)**
- 레퍼런스 스펙 페이지 5종:
  - 이번 세션은 스펙 파일 자체 변경이 없어 본문 수정 대상 아님(메타 갱신 불필요)

## 5) 체크리스트
- [x] 스펙 파일 구조 무결성 유지
- [x] 운영 문서 SSOT 정합성 유지(04 기준)
- [x] 글로서리 xlsx 최신화
- [x] Notion 글로서리 페이지 동기화
- [x] UTF-8 깨짐 재점검

## 6) 이번 세션(2026-02-19) 스펙 변경 및 동기화 기록
- 변경 파일:
  - `docs/references/Development environment.csv`
- 추가 점검 결과:
  - Notion 동기화 매핑 대상 파일(`Summary of key features.csv`, `CS AI Chatbot_Requirements Statement.csv`,
    `google_ready_api_spec_v0.3_20260216.xlsx`, `CS_AI_CHATBOT_DB.xlsx`, `CS_RAG_UI_UX_설계서.xlsx`)은
    이번 세션 Git 변경분에서 추가 변경 없음
- 변경 요약:
  - Backend & Analytics 섹션의 DB 접근 라이브러리 표기를 `Spring Data JPA (Hibernate)`에서
    `MyBatis (mybatis-spring-boot-starter)`로 변경
  - 설명을 Mapper/XML 기반 DB 접근 표준으로 정합화
- 연관 코드 반영:
  - backend JDBC repository -> MyBatis Mapper/XML 전환
- Notion 동기화 대상:
  - `https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7`
- Notion 반영 상태:
  - 반영 완료 (2026-02-19 20:06:22 +09:00)
  - 반영 항목: Last synced at / Source file / Version(or commit) / Change summary 갱신

## 7) 이번 세션(2026-02-20) 스펙 변경 및 Notion 동기화 기록
- 기준 커밋: `6eb8baa`
- 기준 시각(Asia/Seoul): `2026-02-20 21:36`
- 변경된 스펙 파일(git diff summary):
  - `docs/references/Summary of key features.csv` (5 lines changed)
  - `docs/references/CS AI Chatbot_Requirements Statement.csv` (4 lines changed)
  - `docs/references/Development environment.csv` (4 lines changed)
  - `docs/references/google_ready_api_spec_v0.3_20260216.xlsx` (binary changed, `전체API목록` only)

### 7.1 `docs/references/Summary of key features.csv`
- Notion URL: https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149
- 변경 내용:
  - 하이브리드 검색 행 ReqID를 `KB-003` -> `AI-004`로 정정
  - `KB-003` 전용 의미(버전 상태/승인/롤백/폐기) 분리 행 보강
- Last synced at: `2026-02-20 21:36 +09:00`
- Commit: `6eb8baa`
- Notion sync completed: `YES`

### 7.2 `docs/references/CS AI Chatbot_Requirements Statement.csv`
- Notion URL: https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- 변경 내용:
  - `AI-004` 상세 가이드에 Contextual Retrieval + Summary-first + Hybrid(vector+BM25+optional rerank) 명시
  - `KB-002` 상세 가이드에 semantic boundary chunking / summary indexing / embedding input 규칙 명시
- Last synced at: `2026-02-20 21:36 +09:00`
- Commit: `6eb8baa`
- Notion sync completed: `YES`

### 7.3 `docs/references/Development environment.csv`
- Notion URL: https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7
- 변경 내용:
  - OpenSearch/BM25/하이브리드 문맥의 잘못된 `KB-003` 참조를 `AI-004`(및 `KB-002`) 중심으로 정정
- Last synced at: `2026-02-20 21:36 +09:00`
- Commit: `6eb8baa`
- Notion sync completed: `YES`

### 7.4 `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- Notion URL: https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- 변경 내용:
  - `전체API목록` 시트의 `/v1/rag/retrieve`, `/v1/rag/answer` 비고 ReqID를 `AI-004` 기준으로 정합화
  - 카테고리 시트/수식/구조 미수정
- Last synced at: `2026-02-20 21:36 +09:00`
- Commit: `6eb8baa`
- Notion sync completed: `YES`

### 7.5 비고
- MCP 경로에서 파일 첨부 API는 제공되지 않아 페이지 메타/요약 블록 중심으로 동기화함.
- 본 세션 변경 파일 기준 Notion 동기화 완료 상태를 위 4개 항목에 명시함.
