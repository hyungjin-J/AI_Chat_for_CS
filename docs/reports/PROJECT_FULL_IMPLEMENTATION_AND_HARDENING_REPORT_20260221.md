# PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_20260221

- generated_at_utc: 2026-02-21T08:35:00Z
- generated_at_kst: 2026-02-21 17:35:00 +09:00
- repository: AI_Chatbot
- report_scope: Project-start to current working tree (Auth + RBAC + OPS/Admin + Hardening + Spec/Notion Sync)
- baseline_tracking: `dirty_baseline.patch`

## A. Executive Summary

### 프로젝트 목적
- 고객센터 상담 환경에서 RAG 근거 기반 응답, 정책 게이트, 운영 추적성(trace_id), RBAC/테넌트 격리를 갖춘 상용 운영형 CS AI Chatbot 구축.

### MVP -> 운영형 구조 진화 요약
- 초기 MVP 중심 구조에서 다음 운영형 축이 추가/강화되었다.
1. 인증/세션: JWT access/refresh 분리, refresh rotation + reuse 탐지, logout revoke, lockout/rate-limit.
2. 권한: 서버 최종권위 RBAC(ROLE 고정 + ADMIN 내부 admin_level), stale permission 차단.
3. 운영: OPS/Admin 콘솔, 감사로그 조회/차분(diff), 즉시조치(block), ops event + hourly metric 파이프라인.
4. 보안 하드닝: CSRF Origin allowlist, cookie 정책 고정, audit sanitizer, 표준 에러/trace_id 통일.
5. 거버넌스: Hardening Gate 선행 문서화, 스펙-Notion 동기화, spec_sync_report 추적성.

### 현재 상용화 준비 수준 평가
- 기능 완성도: Auth/RBAC/Ops-Admin 핵심 흐름 구현 완료.
- 품질 게이트: 타깃 백엔드/프론트 테스트 및 빌드 증적 확보.
- 운영 문서화: Hardening Gate + spec_sync_report + 본 종합보고서로 SSOT 보강.
- 잔여 리스크: 전체 백엔드 풀 스위트의 비핵심 회귀 가능성, Notion 첨부 자동화 제약은 Phase2 보강 권장.

## B. 아키텍처 진화 타임라인

| Date | Milestone | 핵심 변화 |
|---|---|---|
| 2026-02-17 | Bootstrap/V1 | 기본 백엔드/프론트/인프라와 MVP 핵심 스키마(V1) 구축 |
| 2026-02-17 | Ops/CI Governance | 운영 거버넌스/검증 파이프라인 정비, Notion sync CI 기반 도입 |
| 2026-02-18 | MVP Verification Pack | 검증팩 및 증적 체계 강화, 문서 추적성 보강 |
| 2026-02-19 | Provider/Citation + MyBatis 전환 | provider 증적 정리, JDBC -> MyBatis 표준화 |
| 2026-02-20 | RAG Hybrid + UUID hardening | 하이브리드 검색, UUID 타입 정합성/회귀 차단 강화 |
| 2026-02-21 | Hardening Gate + Auth/RBAC/Ops-Admin | 정책 10개 고정, Auth/RBAC/Ops/Admin 운영 하드닝 확장 |

### 구조 진화 요약(텍스트 다이어그램)
```text
MVP Core(V1)
  -> RAG Hybrid(V2)
  -> UUID/MyBatis Hardening
  -> Auth/RBAC/Ops-Admin(V3)
  -> Hardening Gate + Spec/Notion Traceability
```

## C. 보안 고도화 내역

### 인증 구조 개선 전/후
- Before: 단순 세션 중심 인증.
- After: access/refresh 분리 + refresh family 관리 + CAS 재사용 탐지 + logout family revoke.
- Why: 세션 탈취/재사용 공격 시 단일 토큰 폐기만으로는 방어가 불충분하기 때문.

### refresh reuse 탐지
- 정책: `UPDATE ... WHERE consumed_at IS NULL AND revoked_at IS NULL`의 row=1만 성공.
- row=0 처리: `409 AUTH_REFRESH_REUSE_DETECTED` + `session_family` 전량 revoke + 감사로그.
- Why: race/replay 공격을 원자적으로 판별하고 즉시 세션 패밀리 격리하기 위해.

### CSRF 방어 정책
- 대상: `/v1/auth/refresh`, `/v1/auth/logout`.
- 방식: Origin allowlist 검사 + prod에서 Origin 미존재 기본 거부(예외 client_type allowlist만 허용).
- Why: 쿠키 기반 refresh/logout 호출의 cross-site 오남용 차단.

### SameSite/Lax 기본 정책
- 기본: same-site 배포 가정, `SameSite=Lax`.
- 분리 도메인: `SameSite=None; Secure` + Origin allowlist 강화로 전환.
- Why: 호환성과 보안을 동시에 유지하기 위한 배포 토폴로지별 정책 분리.

### audit sanitizer 정책
- before/after JSON 저장 전 민감 필드 마스킹(`password`, `token`, `refresh_jti`, `secret`, `api_key` 등).
- JWT/Bearer 유사 텍스트도 마스킹.
- Why: 감사 목적 데이터에 민감정보 원문이 축적되는 2차 유출 리스크 방지.

### PII/토큰 로그 차단
- Trace/Audit/Error 흐름에서 토큰 원문 저장 금지, PII 마스킹 정책 유지.
- Why: 운영 로그/증적 파일 자체가 공격 표면이 되지 않도록 하기 위해.

### stale permission 차단
- `permission_version` 불일치 시 `401 AUTH_STALE_PERMISSION` 고정.
- 프론트: refresh 1회만 시도, 실패/동일오류 반복 시 즉시 로그인 전환.
- Why: 권한 하향 시 기존 토큰의 잔여 권한 사용을 차단.

### Redis + DB 혼합 lockout/rate-limit
- Redis: 빠른 판정(tenant+ip 1분 윈도우).
- DB: lockout 상태/감사 이력의 권위 저장소.
- Why: 속도와 추적성(감사/운영)을 동시에 확보.

### 즉시 차단(block)
- `ACCOUNT`/`IP` block을 Ops API로 즉시 반영.
- Why: 보안 이벤트 발생 시 운영자 개입 시간을 최소화.

## D. RBAC 및 권한 모델 설명

### ROLE 고정
- `AGENT`, `CUSTOMER`, `ADMIN`, `OPS`, `SYSTEM`만 ROLE로 사용.

### ADMIN 내부 admin_level
- `MANAGER`, `SYSTEM_ADMIN`은 ROLE이 아닌 ADMIN 내부 권한레벨로 처리.
- Why: 역할 폭증을 막고 관리 정책을 matrix로 세분화하기 위해.

### matrix 기반 세부 권한
- `tb_rbac_matrix`에서 `resource_key + role_code + admin_level` 조합으로 허용 여부 관리.
- 권한 변경 시 tenant 사용자 permission_version 증가.

### stale permission 처리 흐름
```text
권한 변경
 -> permission_version 증가
 -> 기존 access token과 버전 불일치
 -> 서버가 401 AUTH_STALE_PERMISSION 반환
 -> 프론트 refresh 1회
 -> 실패 또는 동일 stale 재발 시 로그인 전환
```

### deny audit linkage
- RBAC deny 발생 시 `RBAC_DENIED`를 ops_event + audit_log에 함께 기록.
- Why: 권한 오탐/오남용 분석을 trace_id 단위로 가능하게 하기 위해.

## E. 운영(Ops) 아키텍처

### tb_ops_event append-only
- 서비스 레이어에서 운영 이벤트를 append-only로 적재.
- metric_key allowlist(v1):
  - `auth_login_success`
  - `auth_login_failed`
  - `auth_rate_limited`
  - `auth_account_locked`
  - `auth_account_unlocked`
  - `auth_refresh_success`
  - `auth_refresh_reuse_detected`
  - `rbac_denied`
  - `ops_block_applied`

### tb_api_metric_hourly 집계 전략
- `@Scheduled(cron="0 * * * * *", zone="UTC")` 실행.
- UTC 기준 hour bucket 집계.
- upsert는 `(tenant_id, hour_bucket_utc, metric_key)` 유니크 키 기반 idempotent 처리.
- Why: 중복 실행/재실행에도 지표 일관성을 보장하기 위해.

### 대시보드 데이터 흐름
```mermaid
flowchart LR
A[tb_ops_event] --> B[OpsMetricAggregationJob UTC]
B --> C[tb_api_metric_hourly]
C --> D[/v1/admin/dashboard/summary]
C --> E[/v1/admin/dashboard/series]
```

### 감사로그 diff 설계
- `/v1/admin/audit-logs` 목록 조회 + `/v1/admin/audit-logs/{audit_id}/diff`로 before/after JSON 비교.
- 민감값은 저장 전 sanitizer 통과본만 조회 가능.

## F. 데이터베이스 변경 요약

### 신규 테이블
- V2: `tb_kb_document`, `tb_kb_document_version`, `tb_kb_chunk`, `tb_kb_chunk_embedding`
- V3: `tb_audit_log`, `tb_ops_event`, `tb_api_metric_hourly`, `tb_rbac_matrix`, `tb_ops_block`

### 확장 테이블
- V3 확장: `tb_user`(permission_version, admin_level, lockout fields)
- V3 확장: `tb_auth_session`(session_family_id, refresh_jti_hash, parent_refresh_jti_hash, consumed/revoked fields, client/ip/trace)

### 마이그레이션 버전별 요약
- V1(`V1__mvp_core.sql`): 멀티테넌트/사용자/역할/세션/대화/메시지/RAG 로그/스트림 기본 스키마.
- V2(`V2__rag_hybrid_retrieval.sql`): KB 문서/버전/청크/임베딩 및 하이브리드 검색 데이터 구조.
- V3(`V3__auth_rbac_ops_admin_hardening.sql`): Auth 하드닝, RBAC matrix, Ops 이벤트/집계, 감사로그, block 제어.

### tenant 격리 전략
- 모든 핵심 테이블이 `tenant_id` 기반.
- 요청 단계에서 `X-Tenant-Key` 강제 및 tenant resolve 실패 시 즉시 차단.

## G. API 변경 요약

### Auth 엔드포인트
- `POST /v1/auth/login`
  - 우선순위: `rate-limit -> lockout`
  - rate-limit: `429 AUTH_RATE_LIMITED`
  - lockout: `429 AUTH_LOCKED` + `Retry-After`
- `POST /v1/auth/refresh`
  - cookie 우선, body fallback 정책 제어
  - CAS 실패(reuse) 시 `409 AUTH_REFRESH_REUSE_DETECTED`
- `POST /v1/auth/logout`
  - `/v1/auth` path 쿠키 revoke/delete + CSRF Origin 검사

### Admin/Ops 신규 API
- `GET /v1/admin/dashboard/summary` (OPS)
- `GET /v1/admin/dashboard/series` (OPS)
- `GET /v1/admin/audit-logs` (OPS)
- `GET /v1/admin/audit-logs/{audit_id}/diff` (OPS)
- `PUT /v1/admin/rbac/matrix/{resource_key}` (ADMIN)
- `PUT /v1/ops/blocks/{block_id}` (OPS)

### 상태코드/에러 포맷 정책
- 상태코드: `401/403/409/422/429` 유지.
- 표준 에러: `error_code`, `message`, `trace_id`, `details` 유지.
- 신규 고정 에러코드:
  - `AUTH_STALE_PERMISSION` (401)
  - `AUTH_LOCKED` (429)
  - `AUTH_RATE_LIMITED` (429)
  - `AUTH_REFRESH_REUSE_DETECTED` (409)

## H. 테스트 및 검증 결과

### Backend 테스트 요약
- 증적 파일: `docs/review/mvp_verification_pack/artifacts/backend_auth_rbac_ops_test_output_20260221.txt`
- 결과: 타깃 계약 테스트/린트 경로 PASS.
- 포함 시나리오:
  - stale permission -> `401 AUTH_STALE_PERMISSION`
  - refresh reuse -> `409 AUTH_REFRESH_REUSE_DETECTED`
  - lockout -> `429 AUTH_LOCKED` + `Retry-After`
  - rate-limit 우선순위 -> `429 AUTH_RATE_LIMITED`
  - metric allowlist + UTC 집계 idempotency

### Frontend 테스트/빌드 요약
- 테스트 증적: `docs/review/mvp_verification_pack/artifacts/frontend_auth_console_test_output_20260221.txt`
- 빌드 증적: `docs/review/mvp_verification_pack/artifacts/frontend_build_output_20260221.txt`
- 결과:
  - Vitest 6 files / 14 tests PASS
  - `tsc -b` PASS
- 포함 시나리오:
  - 로그인/권한가드
  - 401 refresh 1회 재시도
  - stale permission 반복 시 로그인 전환(루프 방지)

### UTF-8 검증 결과
- 기존 증적: `docs/review/mvp_verification_pack/artifacts/glossary_utf8_check.txt` PASS.
- 본 보고서 생성 후 UTF-8 strict read 검증 PASS.
- 검증 로그: `docs/review/mvp_verification_pack/artifacts/project_full_report_utf8_check_20260221.txt`

## I. 스펙/Notion 동기화 현황

### 변경된 스펙 파일(2026-02-21 세션)
- `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- `docs/references/CS_AI_CHATBOT_DB.xlsx`
- `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`

### 업데이트된 Notion 페이지
- Requirements/API: https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- DB: https://www.notion.so/2ed405a3a720812180d9d508b77f31a4
- UI/UX: https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444

### Last synced / Version 요약
- Last synced at: `2026-02-21 16:54:05 +09:00`
- Version(commit): `d0ec39c`(working tree 기준)
- 변경 요약/TBD: `spec_sync_report.md` 섹션 8에 기록.

### spec_sync_report 연동
- 참조 파일: `spec_sync_report.md`
- 본 보고서와 충돌 없음(하드닝 정책/스펙 변경 내역/Notion 링크 일치).

## J. 현재 리스크 및 Phase2 제안

### 남은 기술 부채/리스크
1. 전체 백엔드 풀 스위트의 비핵심 회귀 가능성 점검이 추가로 필요.
2. Notion 파일 첨부 자동화는 MCP 한계로 메타/요약 중심 운영 중.
3. 일부 운영 문서의 과거 인코딩 혼선 흔적(콘솔 출력 기준)은 지속 모니터링 필요.

### 성능/운영 확장 포인트
1. Ops 지표 조회 쿼리의 대용량 tenant 최적화(파티셔닝/rollup 정책).
2. 감사로그 diff의 구조화 비교기(semantic diff + 필드별 하이라이트).
3. RBAC matrix 변경 이력의 approval workflow(2인 승인).

### Phase2 제안
1. MFA/WebAuthn 도입으로 관리자 계정 보안 강화.
2. ABAC(Attribute-based) 보강으로 세분화된 정책 집행.
3. Observability 확장(분산 트레이스 샘플링 정책 + SLO 기반 알람 자동화).

## Appendix 1. Hardening Gate/정책 고정점 반영 상태
- 참조: `docs/review/plans/20260221_auth_rbac_ops_admin_design_and_hardening_plan.md`
- 10개 고정 정책(401 stale, 429 lockout, CAS reuse 409, UTC bucket, Redis key, dirty baseline, 프론트 루프 방지, reuse code 고정, hourly unique key, rate-limit->lockout 우선순위) 기준으로 구현/테스트/문서 반영됨.

## Appendix 2. Dirty Baseline 대비 변경 파일 목록

- baseline 파일 수: 26
- 현재 변경 파일 수: 96
- baseline 대비 신규/추가 변경 경로 수: 70

주요 신규/추가 변경 경로(요약):
- Backend(Auth/RBAC/Ops/Audit):
  - `backend/src/main/java/com/aichatbot/auth/**`
  - `backend/src/main/java/com/aichatbot/admin/**`
  - `backend/src/main/java/com/aichatbot/ops/**`
  - `backend/src/main/java/com/aichatbot/global/audit/**`
  - `backend/src/main/resources/db/migration/V3__auth_rbac_ops_admin_hardening.sql`
  - `backend/src/main/resources/mappers/admin/**`
  - `backend/src/main/resources/mappers/ops/**`
  - `backend/src/main/resources/mappers/global/audit/**`
- Backend tests:
  - `backend/src/test/java/com/aichatbot/auth/**`
  - `backend/src/test/java/com/aichatbot/ops/**`
- Frontend(Auth/Console):
  - `frontend/src/auth/**`
  - `frontend/src/api/**`
  - `frontend/src/routes/**`
  - `frontend/src/layout/**`
  - `frontend/src/pages/**`
- Spec/Docs/Artifacts:
  - `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
  - `docs/references/CS_AI_CHATBOT_DB.xlsx`
  - `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`
  - `spec_sync_report.md`
  - `docs/review/plans/20260221_auth_rbac_ops_admin_design_and_hardening_plan.md`
  - `docs/review/plans/20260221_auth_rbac_ops_admin_implementation_checklist.md`
  - `docs/review/mvp_verification_pack/artifacts/*_20260221.txt`

(원시 비교 산출: `docs/review/mvp_verification_pack/artifacts/dirty_baseline_diff_20260221.txt`)

## Appendix 3. 참고 SSOT 문서
- Hardening Gate Plan: `docs/review/plans/20260221_auth_rbac_ops_admin_design_and_hardening_plan.md`
- Implementation Checklist: `docs/review/plans/20260221_auth_rbac_ops_admin_implementation_checklist.md`
- Spec Sync Report: `spec_sync_report.md`
- Prior Completion Baseline: `docs/review/final/PROJECT_COMPLETION_REPORT.md`
