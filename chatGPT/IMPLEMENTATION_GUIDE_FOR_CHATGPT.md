# IMPLEMENTATION GUIDE FOR CHATGPT

- project: `AI_Chatbot`
- document_type: `ChatGPT 공유용 누적 구현/운영 상태 가이드`
- updated_at_kst: `2026-02-21 21:40`
- handoff_docs_location: `chatGPT/`
- status_source_priority:
  1. `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
  2. `docs/review/plans/202603XX_go_live_gap_closure_plan.md`
  3. `spec_sync_report.md`
  4. `docs/review/mvp_verification_pack/artifacts/*` (증적 파일)

## 1) 목적
이 문서는 ChatGPT(또는 타 협업 AI)에게 현재 프로젝트 상태를 빠르게 공유하기 위한 SSOT 요약본이다.
기능 설명만이 아니라 정책 고정점, 검증 증적, 남은 리스크, 산출물 경로까지 함께 제공한다.

## 2) 현재 완료 상태 요약 (2026-02-21 기준)
- 전반 상태: `Go-Live Gap Closure 반영 완료 상태 (운영 전 점검 가능 수준)`
- 핵심 도메인 상태:
  - Auth/RBAC/Ops-Admin baseline: 구현 반영 완료
  - Phase2 P0(MFA/세션/2인승인/감사체인/스케줄러락): 코드 및 문서 반영 완료
  - Go-Live 갭 클로저(Node22/spec 정규화/runbook/audit chain verify): 반영 완료
- 최근 작업 산출물:
  - 사용자용 통합 매뉴얼 세트(`menual/*통합_사용자_매뉴얼*`) 최신화 완료
  - 고객 배포용 인쇄본(`menual/에이아이챗봇_고객안내본_인쇄용_20260221.docx`, `.pdf`) 생성 완료
  - ChatGPT 공유용 가이드 2종을 `chatGPT/` 경로로 이동 및 유지 관리

## 3) 검증 게이트 상태
| 항목 | 결과 | 증적 파일 |
|---|---|---|
| Backend 테스트 | PASS | `docs/review/mvp_verification_pack/artifacts/golive_backend_test_output.txt` |
| Frontend 테스트 | PASS | `docs/review/mvp_verification_pack/artifacts/golive_frontend_test_output.txt` |
| Frontend 빌드 | PASS | `docs/review/mvp_verification_pack/artifacts/golive_frontend_build_output.txt` |
| Spec consistency | PASS (`PASS=9 FAIL=0`) | `docs/review/mvp_verification_pack/artifacts/golive_spec_consistency_after.txt` |
| UTF-8 strict decode | PASS | `docs/review/mvp_verification_pack/artifacts/golive_utf8_check.txt` |
| Notion 동기화 상태 | DONE | `docs/review/mvp_verification_pack/artifacts/golive_notion_sync_status.txt` |
| CI gate 로컬 동등 확인 | PASS 요약 | `docs/review/mvp_verification_pack/artifacts/golive_ci_gate_status.txt` |

### 3.1 이번 점검 방식(2026-02-21)
- 본 문서 업데이트 시점의 완료도 평가는 최신 증적 파일을 기준으로 교차 확인했다.
- `spec_consistency_check.py` 실시간 재실행은 로컬 실행 시간 제한으로 완료하지 못했으며, 최근 PASS 증적(`golive_spec_consistency_after.txt`)을 기준으로 상태를 기록했다.

## 4) 정책 고정점(변경 금지 요약)
- ROLE taxonomy 고정: `AGENT/CUSTOMER/ADMIN/OPS/SYSTEM`
- `Manager/System Admin`은 ROLE이 아니라 `ADMIN` 내부 `admin_level`
- 표준 에러 포맷 고정: `error_code`, `message`, `trace_id`, `details`
- stale permission 정책: `401 AUTH_STALE_PERMISSION`
- lockout 정책: `429 AUTH_LOCKED` (+ `Retry-After`)
- rate-limit 정책: `429 AUTH_RATE_LIMITED` (1분 윈도우)
- refresh reuse 정책: `409 AUTH_REFRESH_REUSE_DETECTED` + family revoke
- metric 시간 기준: UTC bucket 고정
- 스펙 변경 시 Notion 동기화 + 메타 갱신 + `spec_sync_report.md` 기록 필수

## 5) 구현 범위 스냅샷
### 5.1 인증/세션
- JWT 로그인/리프레시/로그아웃
- refresh rotation(CAS) + reuse 탐지
- lockout + rate-limit 우선순위 적용
- session 목록/개별 revoke/revoke-others
- OPS/ADMIN MFA(TOTP) 흐름

### 5.2 RBAC
- 서버 최종권위 RBAC 강제
- stale permission_version 차단(401)
- ADMIN 권한 변경 2인 승인 워크플로우

### 5.3 Ops/Admin
- 대시보드 summary/series
- 감사로그 조회/diff/export
- 감사 체인 검증 API:
  - `GET /v1/admin/audit-logs/chain-verify`
- block 즉시조치 API

### 5.4 운영 안정성
- `tb_ops_event` append-only
- `tb_api_metric_hourly` UTC idempotent upsert
- scheduler 분산락(멀티 인스턴스 안전성)
- runbook 3종:
  - `docs/ops/runbook_scheduler_lock.md`
  - `docs/ops/runbook_audit_chain.md`
  - `docs/ops/runbook_spec_notion_gate.md`

## 6) 스펙/Notion 정합성 상태
- 최근 Go-Live 세션에서 변경된 스펙:
  - `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- 핵심 정합화:
  - `PUBLIC/AUTHENTICATED` ROLE 표기 제거
  - `access_level` 분리 표기 정규화
  - Phase2 API 및 `chain-verify` 반영
- 동기화 기록:
  - `spec_sync_report.md` 섹션 10
  - Notion 상태: `DONE` (`golive_notion_sync_status.txt`)

## 7) ChatGPT 공유 시 권장 참조 순서
1. `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
2. `docs/review/plans/202603XX_go_live_gap_closure_plan.md`
3. `spec_sync_report.md`
4. `docs/review/mvp_verification_pack/artifacts/golive_spec_consistency_after.txt`
5. `docs/review/mvp_verification_pack/artifacts/golive_utf8_check.txt`
6. `menual/에이아이챗봇_고객안내본_인쇄용_20260221.docx`
7. `menual/에이아이챗봇_고객안내본_인쇄용_20260221.pdf`

## 8) 현재 워킹트리 상태(공유 시 주의)
- `git status` 기준:
  - tracked changes: `17`
  - untracked files: `26`
- 의미:
  - 구현/문서/아티팩트가 워킹트리에 누적된 상태이며, 아직 단일 릴리스 커밋으로 정리되기 전일 수 있다.
  - ChatGPT 공유 시 “현재 브랜치가 정리 중 상태”임을 함께 명시해야 해석 오류를 줄일 수 있다.

## 9) 잔여 리스크(Phase2.1)
1. Notion MCP 토큰/권한 만료 상황에 대한 CI fail-closed 운영 점검 필요
2. audit export 대량 처리 비동기화(큐) 고도화 필요
3. WebAuthn 미도입(TOTP 우선 단계)
4. scheduler lock 자동 self-healing 미구현(현재 runbook 기반 대응)

## 10) 최근 추가 산출물 (사용자 배포용)
### 10.1 통합 사용자 매뉴얼(업데이트)
- `menual/에이아이챗봇_통합_사용자_매뉴얼_20260221.docx`
- `menual/에이아이챗봇_통합_사용자_참조시트_20260221.xlsx`
- `menual/통합_사용자_매뉴얼_docx_utf8_검증_20260221.txt`
- `menual/통합_사용자_매뉴얼_xlsx_utf8_검증_20260221.txt`
- `menual/통합_사용자_매뉴얼_가독성_검증_20260221.txt`
- `menual/통합_사용자_매뉴얼_출처추적_검증_20260221.txt`

### 10.2 고객 안내본(인쇄형)
- `menual/에이아이챗봇_고객안내본_인쇄용_20260221.docx`
- `menual/에이아이챗봇_고객안내본_인쇄용_20260221.pdf`
- `menual/고객안내본_인쇄검수_체크리스트_20260221.txt`
- `menual/고객안내본_출처추적_검증_20260221.txt`
- `menual/고객안내본_utf8_검증_20260221.txt`

## 11) 빠른 공유 템플릿 (복사해서 ChatGPT에 전달 가능)
```md
프로젝트: AI_Chatbot
공유 기준 문서:
1) docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md
2) docs/review/plans/202603XX_go_live_gap_closure_plan.md
3) spec_sync_report.md

현재 상태:
- Go-Live Gap Closure 반영 완료
- backend/frontend/spec consistency/utf8 검증 PASS
- Notion sync status: DONE

핵심 정책:
- ROLE 고정(AGENT/CUSTOMER/ADMIN/OPS/SYSTEM)
- 표준 에러 포맷 유지(error_code/message/trace_id/details)
- stale=401, lockout=429, rate-limit=429, refresh reuse=409

추가 확인:
- menual/ 인쇄형 고객 안내본(docx/pdf) 최신본 확인
```

## 12) 경로 접근 불가 환경용 자기완결 브리핑 (권장)
아래 블록은 파일 경로를 모르는 ChatGPT에게 그대로 붙여넣어도 이해되도록 작성한 버전이다.

```md
프로젝트 컨텍스트(자기완결 요약):
- 이 프로젝트는 고객센터 상담 지원용 AI 챗봇이다.
- 핵심 목표는 근거 기반 응답, 보안 강화, 운영 추적성(trace_id), 서버 최종 권한통제(RBAC)다.
- 현재 상태는 Go-Live Gap Closure까지 반영된 운영 직전 수준이다.

이미 구현/반영된 핵심 기능:
1) 인증/세션
- JWT 로그인/리프레시/로그아웃
- refresh rotation + reuse 탐지
- lockout + rate-limit 정책
- 세션 목록/세션 revoke
- OPS/ADMIN 대상 MFA(TOTP)

2) 권한/보안
- ROLE 고정: AGENT/CUSTOMER/ADMIN/OPS/SYSTEM
- ADMIN 내부 권한레벨(admin_level) 모델
- stale permission 차단: 401 AUTH_STALE_PERMISSION
- refresh reuse 탐지: 409 AUTH_REFRESH_REUSE_DETECTED
- lockout/rate-limit: 429 AUTH_LOCKED / AUTH_RATE_LIMITED
- 표준 에러 포맷: error_code, message, trace_id, details

3) 운영 기능
- Ops/Admin 대시보드
- 감사로그 조회/diff/export
- 감사 체인 검증(무결성 점검)
- 스케줄러 분산락 및 운영 runbook

4) 정합성/검증
- 백엔드 테스트 PASS
- 프론트 테스트 및 빌드 PASS
- 스펙 정합성 PASS (PASS=9, FAIL=0)
- UTF-8 검증 PASS
- Notion 동기화 상태 DONE

현재 남은 리스크(Phase2.1):
1) Notion MCP 토큰/권한 만료 대비 운영 점검
2) audit export 대량 요청 비동기화
3) WebAuthn 미도입(TOTP 우선 적용 상태)
4) scheduler lock 자동 self-healing 미구현

응답 시 반드시 지킬 제약:
- ROLE taxonomy 변경 금지
- 표준 에러 포맷 변경 금지
- stale/lockout/rate-limit/reuse 상태코드 규약 변경 금지
- 스펙 변경 시 Notion 반영 + 동기화 기록 누락 금지
```

## 13) 더 잘 전달하는 방법 (실무 권장)
경로 접근이 불가능한 ChatGPT에게는 아래 3단 구성을 권장한다.

1. `상태 요약 10줄`
- 현재 완료 상태, PASS/FAIL, 남은 리스크만 먼저 전달

2. `고정 정책 블록`
- 절대 바꾸면 안 되는 규칙(ROLE, 에러포맷, 상태코드, 동기화 규칙)을 별도 블록으로 전달

3. `이번 요청 범위만 명시`
- “무엇을 바꿀지/무엇을 바꾸지 않을지”를 문장으로 제한

즉, 경로를 설명하는 방식보다 “정책 + 상태 + 목표 범위”를 텍스트로 직접 전달하는 방식이 정확도가 높다.

## 14) 영문 별도 브리핑 파일
- 경로 접근이 불가능한 AI에게 전달할 전용 영문 파일:
  - `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
- 이 파일은 경로 의존성을 최소화한 자기완결형 컨텍스트 패킷으로 유지한다.

