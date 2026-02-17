# Spec Sync Report

## 1) 변경 요약
- 작업 시각: 2026-02-17
- 기준 커밋: `3edba1d`
- 백업 폴더: `_backup/spec_sync_20260217_170610`
- 대상 파일(로컬) 반영 완료:
  - `docs/references/CS AI Chatbot_Requirements Statement.csv`
  - `docs/references/Summary of key features.csv`
  - `docs/references/Development environment.csv`
  - `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
  - `docs/references/CS_AI_CHATBOT_DB.xlsx`
  - `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`

## 2) ReqID 추가/수정 목록
Requirements 마스터(`CS AI Chatbot_Requirements Statement.csv`)에 아래 24개 ReqID를 신규 등록함.

- `ADM-004`, `ADM-005`, `ADM-006`, `ADM-007`
- `ETL-001`
- `LLM-001`, `LLM-002`, `LLM-003`
- `MCP-001`, `MCP-002`
- `PERF-001`
- `RAG-001`, `RAG-002`, `RAG-003`
- `SEC-004`
- `TMP-001`, `TMP-002`, `TMP-003`, `TMP-004`, `TMP-005`
- `TOOL-001`, `TOOL-002`, `TOOL-003`
- `API-403`

근거 반영:
- 대부분 `Summary of key features.csv`의 ReqID별 설명/수용기준을 기반으로 생성
- `API-403`은 `google_ready_api_spec_v0.3_20260216.xlsx`의 `COM-RBAC-403-RULE` 근거로 생성

추가 보정:
- Requirements 본문의 `key_ref/api_key_ref` 용어를 `secret_ref`로 정규화
- SSE 용어 `token/chunk` 표현 제거 및 표준 이벤트 타입 기준으로 보정
- API 경로 표기를 API Spec 계약 기준으로 보정 (`{id}` -> `{session_id}` 등)

## 3) 용어 표준화 결과
### secret_ref
- `google_ready_api_spec_v0.3_20260216.xlsx`의 `전체API목록` Request/비고에서 `key_ref/api_key_ref` 제거
- Provider Key API Body 예시를 DB 스키마(`TB_PROVIDER_KEY`) 기준으로 정합화:
  - `key_name`
  - `secret_ref`
  - `rotation_cycle_days`

### ROLE
- API Spec Role 값 정규화 결과: `ADMIN`, `AGENT`, `CUSTOMER`, `OPS`, `SYSTEM`만 사용
- `PUBLIC` 제거

### SSE
- 표준 이벤트 타입 기준: `token/tool/citation/done/error/heartbeat/safe_response`
- `token/chunk` 잔존 표현 제거

## 4) 파일별 주요 반영
### A. `CS AI Chatbot_Requirements Statement.csv`
- ReqID 24건 추가
- `API-005`를 attachment 계약(`/v1/attachments/presign`, `/v1/attachments/{attachment_id}/complete`) 기준으로 수정
- `API-004` SSE 경로를 `/v1/sessions/{session_id}/messages/{message_id}/stream` 기준으로 보정

### B. `Summary of key features.csv`
- `API-403` 행 추가
- `중요도&난이도&유형` 컬럼 전행 정규화:
  - `PHASEX | Must/Should | 난이도:상/중/하 | 유형:도메인`
- Summary의 모든 ReqID가 Requirements 마스터에 존재하도록 정합화

### C. `Development environment.csv`
- `version` 공란 14건 상태값 채움 (`선택` 또는 `프로젝트에서 확정`)
- description의 ReqID range 표기(`AAA-001~003`)를 explicit ID 목록으로 확장
- Vault/KMS, Observability, pgvector 항목에 Phase/필수여부 태그 보강

### D. `google_ready_api_spec_v0.3_20260216.xlsx`
- 편집 범위: **`전체API목록` 시트만**
- provider-keys 관련 API Request/비고를 `secret_ref` 표준으로 정리
- 공통 규약(Method=`-`, Endpoint=`-`) 10행은 유지

### E. `CS_AI_CHATBOT_DB.xlsx`
- `TB_EXPORT_JOB`에 BackendOnly 비고 명시
- 목차/관련 시트에 `tenant_key`(API 라우팅 키) vs `tenant_id`(DB UUID FK) 용어 설명 추가
- `secret_ref` 표준 주석 보강

### F. `CS_RAG_UI_UX_설계서.xlsx`
- `90_불일치목록`: `INC-001`을 Resolved 상태로 갱신
- `91_추적성매트릭스`: `API-403` 행 추가 (ReqID→Screen→API→DB→Telemetry→TC)
- `94_미매핑처분`: placeholder key(`-`) 제거
- `93_검증결과`: B-4 집계/BackendOnly/N-A 카운트 갱신

## 5) 자동 검증 결과
실행 스크립트: `scripts/spec_consistency_check.py`

결과(`docs/uiux/spec_consistency_check_report.json`):
- PASS: 8
- FAIL: 0

검증 항목:
- Summary/Dev/API Spec/UIUX 참조 ReqID가 Requirements 마스터에 존재
- API Spec 비고 ReqID 오타/누락 없음
- `secret_ref`/ROLE/SSE 표준 용어 일관성
- UIUX `94_미매핑처분` placeholder key 없음

## 6) Notion 반영 내역
동기화 완료 시각: `2026-02-17 17:44:58 +09:00`

수행 결과:
- 요청된 5개 Notion 페이지 동기화 완료
- 각 페이지에 `Spec Sync Metadata` 섹션 반영:
  - `Last synced at`
  - `Source file`
  - `Version (git commit)`
  - `Change summary`

페이지별 반영:
- `https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149`
  - Source: `docs/references/Summary of key features.csv`
- `https://www.notion.so/2ed405a3a720816594e4dc34972174ec`
  - Source: `docs/references/CS AI Chatbot_Requirements Statement.csv`
  - Source: `docs/references/google_ready_api_spec_v0.3_20260216.xlsx` (동일 페이지 내 API Spec 섹션 기준)
- `https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7`
  - Source: `docs/references/Development environment.csv`
- `https://www.notion.so/2ed405a3a720812180d9d508b77f31a4`
  - Source: `docs/references/CS_AI_CHATBOT_DB.xlsx`
- `https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444`
  - Source: `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`
  - 제약 준수: 이미지 업로드/등록 시도 없음, 시트별 토글 구조 반영

## 7) 남은 TBD 및 근거
- Requirements 신규 행의 `사전 조건` 23건은 `TBD(근거: Summary ReqID=...)`로 유지
  - 이유: Summary/Dev/API/UIUX에 상세 사전조건이 직접 명시되지 않음
  - 근거 위치: `Summary of key features.csv` ReqID별 행
- Notion 동기화 관련 미완료 항목 없음

## 8) AGENTS.md 패치 제안 (읽기 전용 준수)
현재 AGENTS.md 직접 수정은 하지 않음.

제안(필요 시):
- ROLE 표준에 `PUBLIC` 비허용(사전 인증 없는 엔드포인트도 `CUSTOMER`로 표기) 문구를 명시적으로 추가
- API 문서 용어 규칙에 `secret_ref` 단일 표준 + alias 허용 범위(서버 내부 호환) 문구를 한 줄로 강화
