# 202603XX Production Readiness Phase2 Plan

- status: `PLAN_LOCK_DRAFT`
- generated_at: `2026-02-21`
- baseline references:
  1. `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_20260221.md`
  2. `docs/review/plans/20260221_auth_rbac_ops_admin_design_and_hardening_plan.md`
  3. `AGENTS.md`
  4. `spec_sync_report.md`
- immutable policy: `20260221 Hardening Gate + 공용 정책 고정점 10개`

## Why
1. OPS/ADMIN 계정은 단일 비밀번호만으로 운영 권한을 가져서는 안 되며, 실운영 직전 단계에서 MFA 강제가 필요하다.
2. Refresh family 보안이 있어도 사용자 스스로 세션을 조회/회수(revoke)할 수 없으면 탈취 대응 시간이 길어진다.
3. RBAC matrix 즉시 적용 모델은 오조작/권한 남용 리스크가 크므로 2인 승인 워크플로우가 필요하다.
4. 감사로그는 마스킹 정책만으로 충분하지 않고, 해시 체인 기반 위변조 탐지 증거가 필요하다.
5. 단일 인스턴스 기준 스케줄러는 멀티 인스턴스에서 중복 실행 리스크가 있다.
6. PR 속도와 release 안정성을 동시에 만족하려면 smoke/contract와 nightly full 게이트를 분리해야 한다.

## Scope
1. MFA(TOTP 우선) + Recovery Code + OPS/ADMIN 강제.
2. 세션 목록 조회/개별 revoke/다른 세션 일괄 revoke.
3. RBAC 변경 2인 승인(`PENDING -> APPROVED(2인) -> APPLY`).
4. 감사로그 tamper-evident hash chain + JSON/CSV export + 범위 제한.
5. UTC 스케줄러 분산락 + retention/partitioning baseline.
6. PR smoke/contract + release/nightly full 회귀 게이트 체계.
7. 신규 누적 보고서 `PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md` 작성.

## Out of Scope
1. ROLE taxonomy 변경(`AGENT/CUSTOMER/ADMIN/OPS/SYSTEM` 외 ROLE 추가 금지).
2. Hardening Gate 완화(쿠키/CSRF/lockout/rotation 정책 해제 금지).
3. WebAuthn 본 구현(Phase2에서는 확장 포인트만 유지).
4. 대규모 물리 테이블 cutover.

## Decisions (Fixed)
| ID | Decision |
|---|---|
| D-01 | 20260221 공용 정책 고정점 10개는 변경 없이 유지한다. |
| D-02 | MFA 1차 구현은 TOTP(RFC6238, 30초, 6자리)로 고정한다. |
| D-03 | OPS/ADMIN 로그인은 MFA 강제, 미설정 사용자는 `mfa_setup_required` 상태만 허용한다. |
| D-04 | Recovery code는 10개 one-time 발급, 평문 저장 금지(해시 저장). |
| D-05 | 세션 revoke는 단일 세션 및 session_family revoke 연동을 함께 지원한다. |
| D-06 | `/v1/admin/rbac/matrix/{resource_key}`는 즉시 적용이 아닌 요청 생성(PENDING) 의미로 고정한다. |
| D-07 | 승인자는 요청자와 달라야 하며, 승인 2건은 서로 다른 사용자여야 한다. |
| D-08 | 감사체인은 tenant 단위 hash chain으로 저장하고 입력은 sanitizer 통과본만 허용한다. |
| D-09 | 감사 export는 OPS 전용, tenant/date/row 제한을 강제한다. |
| D-10 | 스케줄러 멀티인스턴스 제어는 DB lease lock(`tb_scheduler_lock`) 방식으로 고정한다. |
| D-11 | retention baseline은 정책 테이블 + 정리 job + partition prep hook 포함으로 고정한다. |
| D-12 | 회귀 게이트는 PR(small smoke/contract)와 nightly/release(full) 2계층으로 분리한다. |

## Data Model
### Migrations
- `V4__mfa_session_management.sql`
- `V5__rbac_approval_audit_integrity.sql`
- `V6__scheduler_lock_retention_partition_baseline.sql`

### V4
| Table | Key columns | Purpose |
|---|---|---|
| `tb_user_mfa` | `user_id, secret_ciphertext, enabled, enforced, verified_at` | MFA 상태 |
| `tb_user_mfa_recovery_code` | `user_id, code_hash, used_at, expires_at` | 복구코드 one-time |
| `tb_auth_mfa_challenge` | `id, challenge_type, attempt_count, locked_until, expires_at, consumed_at` | MFA 챌린지 |
| `tb_auth_session`(ext) | `device_name, revoked_by_session_id` | 세션 가시성/조치 연계 |

### V5
| Table | Key columns | Purpose |
|---|---|---|
| `tb_rbac_change_request` | `resource_key, role_code, admin_level, allowed, status` | RBAC 변경 요청 |
| `tb_rbac_change_approval` | `request_id, approver_user_id, decision` | 승인 이력 |
| `tb_audit_chain_state` | `tenant_id, last_seq, last_hash` | 감사 해시 체인 헤드 |
| `tb_audit_log`(ext) | `chain_seq, hash_prev, hash_curr, hash_algo` | tamper-evident |
| `tb_audit_export_log` | `format, from_utc, to_utc, row_count, trace_id` | export 증적 |

### V6
| Table | Key columns | Purpose |
|---|---|---|
| `tb_scheduler_lock` | `lock_key, owner_id, lease_until_utc, fencing_token` | 분산락 |
| `tb_data_retention_policy` | `table_name, retention_days, enabled` | 보존 정책 |
| `tb_data_retention_run` | `table_name, started_at, ended_at, deleted_rows, status` | 정리 실행 로그 |
| `tb_partition_plan` | `table_name, bucket_month_utc, status` | 월 파티션 준비 baseline |

## API Contract
표준 에러 포맷 유지: `error_code`, `message`, `trace_id`, `details`

### PR1 (MFA + Session)
- `POST /v1/auth/mfa/totp/enroll`
- `POST /v1/auth/mfa/totp/activate`
- `POST /v1/auth/mfa/verify`
- `POST /v1/auth/mfa/recovery-codes/regenerate`
- `GET /v1/auth/sessions`
- `DELETE /v1/auth/sessions/{session_id}`
- `POST /v1/auth/sessions/revoke-others`

### PR2 (RBAC Approval + Audit)
- `PUT /v1/admin/rbac/matrix/{resource_key}` (요청 생성)
- `GET /v1/admin/rbac/approval-requests`
- `POST /v1/admin/rbac/approval-requests/{request_id}/approve`
- `POST /v1/admin/rbac/approval-requests/{request_id}/reject`
- `GET /v1/admin/audit-logs/export`

### PR3 (Internal Ops)
- 스케줄러 lock 기반 실행(외부 API 없음)
- retention/partition prep 내부 job 추가

## UX Flow
1. 로그인 후 OPS/ADMIN은 `mfa_required` 또는 `mfa_setup_required`로 분기한다.
2. MFA 설정/검증 성공 후만 최종 토큰 발급 및 콘솔 진입을 허용한다.
3. 보안 페이지에서 내 세션 목록 조회, 의심 세션 revoke, 나머지 세션 일괄 종료를 지원한다.
4. RBAC 변경은 요청 생성 후 2인 승인 완료 시점에만 적용된다.
5. 감사 export는 OPS만 사용 가능하며 범위 초과 요청은 즉시 거부한다.

## Failure Modes
| Scenario | Detection | Handling |
|---|---|---|
| MFA brute force | challenge attempt count | `429 AUTH_MFA_LOCKED` + `Retry-After` |
| Recovery 재사용 | `used_at` 존재 | `409 AUTH_MFA_RECOVERY_USED` |
| RBAC 자기 승인/중복 | unique + service rule | `409 RBAC_APPROVAL_INVALID` |
| Audit chain 끊김 | chain verifier | 경보 + export 제한 |
| Scheduler 중복 실행 | lease lock miss | skip + metric/audit 기록 |
| Retention 오삭제 | dry-run + limit | 즉시 중단 + run log |

## Regression Paths
1. `AuthService.login` 응답 타입 변경으로 프론트 로그인 흐름이 깨질 수 있다.
2. stale permission 401(`AUTH_STALE_PERMISSION`) 규약이 변질될 수 있다.
3. refresh CAS 로직과 세션 revoke 기능이 충돌할 수 있다.
4. RBAC direct apply 경로가 남아 2인 승인 우회가 발생할 수 있다.
5. audit chain 입력에 raw payload가 섞여 민감정보 노출 위험이 생길 수 있다.
6. scheduler lock 도입 시 집계 누락/지연이 발생할 수 있다.

## Validation Commands
- Backend: `cd backend && ./gradlew.bat test --no-daemon`
- Frontend: `cd frontend && npm ci && npm run test:run && npm run build`
- UTF-8 check artifact: `docs/review/mvp_verification_pack/artifacts/phase2_utf8_check_202603XX.txt`
- spec gate: `python scripts/spec_consistency_check.py`
- notion gate(스펙 변경 시): `python scripts/notion_zero_touch_gate.py`

## DoD
1. PR1~PR3 범위 구현 + 테스트 통과.
2. 20260221 Hardening Gate 및 10개 고정 정책과 충돌 없음.
3. 스펙 변경 시 Notion 메타/동기화 + `spec_sync_report.md` 반영 완료.
4. UTF-8 검증 산출물 PASS.
5. 신규 누적 보고서 `PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md` 작성 완료.

## Rollback Plan
1. PR 단위 독립 롤백(PR1/PR2/PR3).
2. PR2 롤백 시 direct apply 우회가 열리지 않도록 write-protect 플래그 유지.
3. PR3 롤백 시 집계 job 일시 중지 후 lock 제거.
4. 보안 정책(Hardening Gate)은 롤백 대상에서 제외.

## Security Notes
1. MFA secret/recovery code 평문 저장 금지.
2. 감사 체인 입력은 sanitizer 결과만 허용.
3. export 응답에서도 민감필드 마스킹 재적용.
4. 신규 endpoint는 `X-Trace-Id`, `X-Tenant-Key` 강제.
5. `401/403/409/422/429` 상태코드 규약 유지.
6. 세션/승인/export 조작은 전부 audit 이벤트로 남긴다.
