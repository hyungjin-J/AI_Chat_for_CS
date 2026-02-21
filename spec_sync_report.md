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

## 8) 이번 세션(2026-02-21) 스펙 변경 및 Notion 동기화 기록
- 기준 커밋: `d0ec39c` (working tree)
- 기준 시각(Asia/Seoul): `2026-02-21 16:54:05 +09:00`
- `/mnt/data` 접근 상태: 미가용
- 로컬 SSOT 사용 경로:
  - `docs/references/**`
  - `docs/uiux/**`
- 변경된 스펙 파일:
  - `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
  - `docs/references/CS_AI_CHATBOT_DB.xlsx`
  - `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`

### 8.1 `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- Notion URL: https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- 변경 내용:
  - `전체API목록`에서 Auth 3종(`/v1/auth/login`, `/v1/auth/refresh`, `/v1/auth/logout`) 계약을 하드닝 고정점 기준으로 갱신
  - `AUTH_STALE_PERMISSION(401)`, `AUTH_LOCKED(429)`, `AUTH_RATE_LIMITED(429)`, `AUTH_REFRESH_REUSE_DETECTED(409)` 명시
  - refresh cookie `Path=/v1/auth`, CSRF Origin allowlist, body fallback 조건부 허용 정책 반영
  - Ops/Admin API 6종(대시보드/감사로그/RBAC matrix/block)의 UTC bucket, metric allowlist, permission_version 연계 정책 반영
- Last synced at: `2026-02-21 16:54:05 +09:00`
- Commit: `d0ec39c` (working tree)
- Notion sync completed: `YES`

### 8.2 `docs/references/CS_AI_CHATBOT_DB.xlsx`
- Notion URL: https://www.notion.so/2ed405a3a720812180d9d508b77f31a4
- 변경 내용:
  - `TB_USER`, `TB_AUTH_SESSION`, `TB_AUDIT_LOG`, `TB_OPS_EVENT`, `TB_API_METRIC_HOURLY` 스키마를 구현 기준(V3 migration)으로 정합화
  - 신규 시트 `TB_RBAC_MATRIX`, `TB_OPS_BLOCK` 추가
  - 감사 로그 before/after JSON 민감정보 차단 규칙(원문 저장 금지) 명시
  - `tb_api_metric_hourly` 유니크 키 `(tenant_id, hour_bucket_utc, metric_key)` 및 idempotent upsert 기준 반영
- Last synced at: `2026-02-21 16:54:05 +09:00`
- Commit: `d0ec39c` (working tree)
- Notion sync completed: `YES`

### 8.3 `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`
- Notion URL: https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444
- 변경 내용:
  - 에러코드 시트에 `AUTH_STALE_PERMISSION`, `AUTH_LOCKED`, `AUTH_RATE_LIMITED`, `AUTH_REFRESH_REUSE_DETECTED` 추가
  - 권한별 UI 시트에 `ADMIN` 내부 `admin_level(MANAGER/SYSTEM_ADMIN)` 정책 반영
  - OPS/ADMIN 콘솔 메뉴와 RBAC matrix 변경 화면 매핑 보강
- Last synced at: `2026-02-21 16:54:05 +09:00`
- Commit: `d0ec39c` (working tree)
- Notion sync completed: `YES`

### 8.4 추적성(ReqID 기준) 변경 요약
- `SEC-001`: 로그인/리프레시/로그아웃 하드닝, lockout/rate-limit/reuse 대응
- `SEC-002`: 서버 RBAC 최종권위, stale permission 401 처리, admin_level 내부 권한레벨 분리
- `OPS-001`/`OPS-003`: 감사로그/운영 이벤트/즉시조치(block) 운영 경로 정합화
- `API-007`: 표준 에러 포맷 + Retry-After 정책 고정

### 8.5 TBD / Phase2 이관
- Notion 페이지 내 원본 파일 첨부 자동화는 MCP 기능 한계로 메타/요약 블록 갱신 중심으로 운영
- API workbook의 카테고리 시트/프로그램ID 목록 시트는 `_guide` 규칙에 따라 자동 동기화 영역으로 수동 편집하지 않음

## 9) 이번 세션(2026-02-21, Phase2 P0) 코드/운영 보강 기록
- 기준 브랜치 상태: working tree
- 기준 문서:
  - `docs/review/plans/202603XX_production_readiness_phase2_plan.md`
  - `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
- 수행 범위 요약:
  - MFA(TOTP) + 세션 관리 API/화면
  - RBAC 2인 승인 워크플로우 + 감사 해시체인 + 감사 export
  - 스케줄러 분산락 + retention/partition baseline + CI 게이트 워크플로우
- 스펙 파일(CSV/XLSX) 추가 변경 여부:
  - **없음 (No additional spec file edit in this session)**
- Notion 동기화 필요 여부:
  - 스펙 파일 무변경이므로 본 세션에 신규 Notion 본문/메타 갱신 대상 없음
- 증적 산출물:
  - `docs/review/mvp_verification_pack/artifacts/phase2_backend_gradle_test_output_202603XX.txt`
  - `docs/review/mvp_verification_pack/artifacts/phase2_frontend_test_output_202603XX.txt`
  - `docs/review/mvp_verification_pack/artifacts/phase2_frontend_build_output_202603XX.txt`
  - `docs/review/mvp_verification_pack/artifacts/phase2_utf8_check_202603XX.txt`

## 10) 이번 세션(2026-02-21, Go-Live Gap Closure) 스펙 변경 및 동기화 기록
- 기준 문서: `docs/review/plans/202603XX_go_live_gap_closure_plan.md`
- 기준 시각(Asia/Seoul): `2026-02-21 21:00 +09:00`
- 변경된 스펙 파일:
  - `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`

### 10.1 `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- Notion URL: https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- 변경 내용:
  - `PUBLIC`, `AUTHENTICATED` 레거시 ROLE 표기를 제거하고 `비고(access_level=...)`로 정규화
  - Phase2 API 누락 엔드포인트 11건 추가 반영
    - `/v1/auth/mfa/totp/enroll`
    - `/v1/auth/mfa/totp/activate`
    - `/v1/auth/mfa/verify`
    - `/v1/auth/mfa/recovery-codes/regenerate`
    - `/v1/auth/sessions`
    - `/v1/auth/sessions/{session_id}`
    - `/v1/auth/sessions/revoke-others`
    - `/v1/admin/rbac/approval-requests`
    - `/v1/admin/rbac/approval-requests/{request_id}/approve`
    - `/v1/admin/rbac/approval-requests/{request_id}/reject`
    - `/v1/admin/audit-logs/export`
  - Go-Live 운영 점검 API 추가 반영:
    - `/v1/admin/audit-logs/chain-verify`
  - `/v1/admin/rbac/matrix/{resource_key}`를 2인 승인 요청 생성 의미(202/PENDING)로 정규화
- 검증 결과:
  - `python scripts/spec_consistency_check.py` => `PASS=9 FAIL=0`
  - 증적: `docs/review/mvp_verification_pack/artifacts/golive_spec_consistency_after.txt`

### 10.2 Notion 동기화 상태
- 자동 동기화(MCP): **DONE**
  - 반영 페이지: https://www.notion.so/2ed405a3a720816594e4dc34972174ec
  - 반영 시각: `2026-02-21 21:08:04 +09:00`
  - 반영 메타: Last synced at / Source file / Version(or commit) / Change summary
  - 반영 본문: Spec Sync Metadata 섹션(Go-Live Gap Closure 변경점) 갱신
- 참고 아티팩트:
  - `docs/review/mvp_verification_pack/artifacts/golive_notion_sync_status.txt`
  - `docs/review/mvp_verification_pack/artifacts/golive_notion_manual_sync_patch.md` (fallback 문서, 기록 보존)

## 11) 이번 세션(2026-02-21, Phase2.1 PR1~PR3) 스펙 변경 및 동기화 기록
- 기준 문서: `docs/review/plans/202603XX_phase2_1_ops_maturity_plan.md`
- 기준 커밋: `79383ab` (working tree)
- 기준 시각(Asia/Seoul): `2026-02-21 22:58 +09:00`
- 변경된 스펙 파일:
  - `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
  - `docs/references/CS_AI_CHATBOT_DB.xlsx`
  - `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`

### 11.1 `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- Notion URL: https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- 변경 내용:
  - Async audit export API 3종 추가
    - `POST /v1/admin/audit-logs/export-jobs`
    - `GET /v1/admin/audit-logs/export-jobs/{job_id}`
    - `GET /v1/admin/audit-logs/export-jobs/{job_id}/download`
  - Legacy sync export(`GET /v1/admin/audit-logs/export`)를 fallback-only 정책으로 명시
  - ROLE taxonomy 고정 + `access_level` 표현 규칙 유지

### 11.2 `docs/references/CS_AI_CHATBOT_DB.xlsx`
- Notion URL: https://www.notion.so/2ed405a3a720812180d9d508b77f31a4
- 변경 내용:
  - 신규 테이블 시트 추가:
    - `TB_AUDIT_EXPORT_JOB`
    - `TB_AUDIT_EXPORT_CHUNK`
    - `TB_SCHEDULER_LOCK`
  - 목차(`목차` 시트) 총 테이블 수/누락 시트 인덱스 최신화
  - V7/V8(Async export spool + scheduler self-healing) 스키마 반영

### 11.3 `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`
- Notion URL: https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444
- 변경 내용:
  - `17_OPS002_감사로그즉시조치` 시트 API 목록에 async export-jobs 경로 반영
  - 사용 테이블에 `TB_AUDIT_EXPORT_JOB`, `TB_AUDIT_EXPORT_CHUNK`, `TB_SCHEDULER_LOCK` 반영

### 11.4 검증 결과
- `python scripts/spec_consistency_check.py` => `PASS=9 FAIL=0`
- 증적: `docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_spec_consistency_202603XX.txt`

### 11.5 Notion 동기화 상태
- 자동 동기화(MCP): **BLOCKED**
  - 사유: `Auth required` (Notion MCP 인증 미연결)
- 수동 반영 패치 문서 생성:
  - `docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_notion_manual_sync_patch_202603XX.md`
- 상태 기록:
  - `docs/review/mvp_verification_pack/artifacts/phase2_1_pr2_notion_sync_status_202603XX.txt`

## 12) 이번 세션(2026-02-21, Phase2.1.1 Release Hygiene) Notion BLOCKED 예외 경로 고정
- 기준 문서: `docs/review/plans/202603XX_phase2_1_1_release_hygiene_plan.md`
- 기준 커밋: `98e0868` (working tree)
- 기준 시각(Asia/Seoul): `2026-02-21 23:45:19 +09:00`
- 스펙 파일(CSV/XLSX) 추가 변경 여부:
  - **없음 (No additional spec file edit in this session)**
- 자동 동기화 상태:
  - BLOCKED 유지(`NOTION_AUTH_*` fail-closed)

### 12.1 Phase2.1.1 고정 증적 파일(필수 3종)
1. 상태 파일:
   - `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json`
   - 필수 값: `status=BLOCKED_AUTOMATION`, `reason`, `timestamp_kst`
2. 수동 패치 문서:
   - `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
   - 필수 메타: Last synced at / Source file / Version / Change summary
3. 동기화 보고 기록:
   - `spec_sync_report.md` (현재 섹션 12)

### 12.2 운영 Close 규칙
- `scripts/check_notion_manual_exception_gate.py` PASS일 때만 BLOCKED 상태를 운영적으로 Close 처리한다.
- PASS 전까지는 자동 동기화 우회 완료로 간주하지 않으며, PR 병합 기준에서 예외 경로 미충족으로 실패 처리한다.
