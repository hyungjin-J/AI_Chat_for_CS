# 202603XX Go-Live Gap Closure Plan (Draft)

문서 대상: `docs/review/plans/202603XX_go_live_gap_closure_plan.md`  
모드: `PLAN MODE` (코드 변경 금지, 계획/문서만 확정)  
기준 SSOT:
1. `docs/review/plans/202603XX_production_readiness_phase2_plan.md`
2. `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
3. `docs/review/plans/20260221_auth_rbac_ops_admin_design_and_hardening_plan.md`
4. `spec_sync_report.md`
5. `docs/references/**`, `docs/uiux/**`
6. `scripts/spec_consistency_check.py`, `scripts/notion_zero_touch_gate.py`

## 1) Why
202603XX Phase2(P0) 구현은 완료되었지만, 상용화 게이트 기준으로는 문서/스펙/CI/운영정합성 잔여 결함이 남아 있다.  
이번 Gap Closure의 목적은 기능 추가가 아니라 “배포 직전 실패 요인”을 제거해 다음 조건을 동시에 만족하는 것이다.
1. 스펙-코드-리포트-Notion이 단일 진실원천으로 정렬됨
2. CI/로컬 실행 환경이 Node 22 표준으로 재현 가능
3. 운영팀이 scheduler lock 장애와 audit chain 이상을 즉시 대응 가능
4. 증적 파일 기반으로 Go-Live 승인 판단 가능

## 2) Scope / Out of Scope
### Scope
1. Node 22 고정(로컬/CI) 및 엔진 경고 제거 정책 확정
2. `spec_consistency_check`의 `role_standard` FAIL=1 해소
3. Phase2 신규 API/DB 반영 누락 여부를 스펙 XLSX와 대조해 정합성 복구
4. Notion 동기화/메타/spec_sync_report 게이트 충족
5. Scheduler lock 장애 runbook 구체화
6. Audit chain verifier + 알림 운영 최소선 확정
7. 202603XX 최종 보고서 갱신

### Out of Scope
1. ROLE taxonomy 변경 금지(`AGENT/CUSTOMER/ADMIN/OPS/SYSTEM` 외 추가 금지)
2. Hardening Gate 정책 변경 금지(쿠키/CSRF/lockout/rotation/UTC bucket 포함)
3. 비즈니스 기능 신규 개발(MFA/WebAuthn/권한모델 재설계 등)
4. API 응답 포맷 변경 금지(`error_code`, `message`, `trace_id`, `details` 유지)

## 3) Gap List (Severity + 근거)
| Gap ID | Severity | 결함 요약 | 근거(파일/커맨드) | 종료 조건 |
|---|---|---|---|---|
| G-A | BLOCKER | Node 엔진 표준 불일치 (로컬 Node v24, 정책은 22) | `node -v`=`v24.11.1`, `npm -v`=`11.6.2`; `frontend/package.json` engines=`>=22 <23`; 워크플로는 `node-version: "22"`만 사용 | CI/로컬 모두 `22.12.0` 기준으로 고정되고 증적 남김 |
| G-B | BLOCKER | `spec_consistency_check` FAIL=1 (`role_standard`) | `python scripts/spec_consistency_check.py` => `PASS=7 FAIL=1`; samples=`AUTHENTICATED`,`PUBLIC`,`PUBLIC(Refresh token ??)` | FAIL=0 달성, role 표준 위반 0건 |
| G-C | BLOCKER | Phase2 API/DB 반영과 스펙/리포트 기록 불일치 | `PROJECT_FULL_IMPLEMENTATION...202603XX.md`에 “스펙 수정 없음” 기록, 그러나 실제 코드에는 Phase2 API 존재; XLSX 검사 결과 신규 API 11건 미기재, DB 신규 테이블 다수 미기재 | API/DB/UIUX 스펙과 리포트, Notion, spec_sync_report가 동일 상태로 정렬 |
| G-D | MUST | scheduler lock 장애 runbook 미상세 | 보고서 잔여 리스크 명시(`scheduler lock fallback runbook 상세화 필요`); runbook playbook에 scheduler lock 전용 대응 부재 | 장애 시나리오별 즉시조치/검증/복구/알림 기준 문서화 |
| G-E | MUST | audit chain 검증/알림 운영 고도화 부족 | 보고서 잔여 리스크 명시(`감사 체인 검증 배치/알림 운영 정책 고도화 필요`); 체인 생성은 있으나 운영 검증 루틴/알림 기준 미약 | verifier 절차 + 알림 임계치 + 실패시 차단/완화 정책 명문화 및 실행 증적 확보 |

## 4) Decision Locks (추가 고정점)
| Lock ID | 고정 결정 |
|---|---|
| L-01 | `PUBLIC`, `AUTHENTICATED`는 ROLE이 아니라 접근수준(access level)로 고정한다. |
| L-02 | API 스펙 `전체API목록`의 `권한`(col 10)은 ROLE 5종 또는 공란만 허용한다. |
| L-03 | 접근수준은 `비고`(col 11)에 `access_level=PUBLIC` 또는 `access_level=AUTHENTICATED`로 기록한다. |
| L-04 | `/v1/auth/refresh`는 `access_level=PUBLIC` + `auth_mechanism=refresh_cookie`를 `비고`에 명시한다. |
| L-05 | `scripts/spec_consistency_check.py`에 접근수준 토큰 표준 검사(`access_level_standard`)를 추가해 재발 방지한다. |
| L-06 | Node는 `.nvmrc`와 Volta를 단일 기준으로 `22.12.0` 고정, CI도 patch 버전 고정(`22.12.0`)한다. |
| L-07 | 스펙 파일이 변경되면 Notion 동기화 + 메타 갱신 + `spec_sync_report.md` 기록 없이는 PR 실패 처리한다. |
| L-08 | PR-A와 PR-B는 DoD를 독립 통과 가능하게 설계한다(아래 8절). |

## 5) `role_standard` FAIL=1 원인 위치 찾는 방법 (재현 절차 고정)
### 5.1 스크립트 위치 확인
```powershell
rg -n "check_role_standard|ALLOWED_ROLES|ws.cell\\(row_idx, 10\\)" scripts/spec_consistency_check.py
```

### 5.2 실제 위반 행 찾기(자동)
```powershell
@'
from openpyxl import load_workbook
wb = load_workbook("docs/references/google_ready_api_spec_v0.3_20260216.xlsx", data_only=True)
ws = wb.worksheets[1]  # 전체API목록
allowed = {"AGENT","CUSTOMER","ADMIN","OPS","SYSTEM"}
for r in range(2, ws.max_row + 1):
    role = ws.cell(r, 10).value
    if role is None:
        continue
    role = str(role).strip()
    if role and role not in allowed:
        print(r, ws.cell(r,5).value, ws.cell(r,6).value, role)
'@ | python -
```
예상 검출:
1. row 2 `POST /v1/auth/login` `PUBLIC`
2. row 3 `POST /v1/auth/refresh` `PUBLIC(Refresh token ??)`
3. row 4 `POST /v1/auth/logout` `AUTHENTICATED`

### 5.3 엑셀 수동 확인
1. `docs/references/google_ready_api_spec_v0.3_20260216.xlsx` 열기  
2. `전체API목록` 시트 선택  
3. `권한`(열 10) 필터 적용  
4. 허용값(`AGENT/CUSTOMER/ADMIN/OPS/SYSTEM`) 외 값만 표시  
5. 위반 행을 `비고` 기반 접근수준 표기로 이전 후 `권한` 정규화

## 6) PUBLIC/AUTHENTICATED 판별 기준 및 정규화 결정
### 판별 기준
1. JWT/서버 권한검사(`@PreAuthorize`, RBAC 매트릭스)의 주체로 직접 사용되면 ROLE
2. “인증 필요 여부” 또는 “토큰 없이 접근 가능 여부”를 표현하면 접근수준(access level)
3. ROLE taxonomy 고정 규칙에 없는 값이면 접근수준으로 분류

### 최종 결정
1. `PUBLIC`, `AUTHENTICATED`는 접근수준으로 확정
2. `권한` 칼럼에는 넣지 않음
3. `비고` 칼럼에 `access_level=` 토큰으로 표준화
4. 재발 방지용 검사 규칙을 `spec_consistency_check.py`에 추가

## 7) PR 분해 (최소 2개, 독립 DoD)
## PR-A: Spec/Notion Gate Green + Node 22 표준화 + CI 고정
### 목표
1. BLOCKER(G-A/G-B/G-C) 전부 해소
2. 스펙/Notion/보고서 정합성 회복
3. Go-Live 환경 재현성 확보

### 변경 대상 파일(경로 단위)
1. `.nvmrc`
2. `frontend/package.json` (필요 시 engines/volta 정합)
3. `.github/workflows/mvp-demo-verify.yml`
4. `.github/workflows/pr-smoke-contract.yml`
5. `.github/workflows/release-nightly-full.yml`
6. `.github/workflows/provider-regression-nightly.yml`
7. `.github/workflows/notion-zero-touch-sync.yml`
8. `scripts/check_all.ps1` (Node 버전 출력/실패 메시지 정합)
9. `scripts/spec_consistency_check.py` (access_level 표준 검사 추가)
10. `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
11. `docs/references/CS_AI_CHATBOT_DB.xlsx`
12. `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`
13. `spec_sync_report.md`
14. `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`

### 실행 커맨드
```powershell
node -v
npm -v
python scripts/spec_consistency_check.py
cd backend && ./gradlew.bat test --no-daemon
cd frontend && npm ci && npm run test:run && npm run build
python scripts/notion_zero_touch_gate.py --base-ref <base> --head-ref <head> --output-json docs/review/mvp_verification_pack/artifacts/phase2_golive_notion_gate_202603XX.json
```

### 테스트/검증 포인트
1. `spec_consistency_check` FAIL=0
2. Node 정책 위반 시 CI 실패 확인
3. API spec에 Phase2 API 11건 반영 확인
4. DB spec에 V4~V6 핵심 테이블 반영 확인
5. Notion 메타 4종 갱신 및 `spec_sync_report.md` 기록 일치

### 증적 파일명 규칙
1. `docs/review/mvp_verification_pack/artifacts/phase2_golive_node_versions_202603XX.txt`
2. `docs/review/mvp_verification_pack/artifacts/phase2_golive_spec_consistency_202603XX.txt`
3. `docs/review/mvp_verification_pack/artifacts/phase2_golive_backend_test_202603XX.txt`
4. `docs/review/mvp_verification_pack/artifacts/phase2_golive_frontend_test_202603XX.txt`
5. `docs/review/mvp_verification_pack/artifacts/phase2_golive_frontend_build_202603XX.txt`
6. `docs/review/mvp_verification_pack/artifacts/phase2_golive_notion_gate_202603XX.json`
7. `docs/review/mvp_verification_pack/artifacts/phase2_golive_utf8_check_202603XX.txt`

### 롤백 전략
1. Node/CI 고정 변경은 workflow + `.nvmrc` 단위로 커밋 롤백
2. 스펙 변경 롤백 시 Notion/`spec_sync_report.md`에 rollback entry 필수
3. `spec_consistency_check.py` 규칙 완화는 금지, 실패 시 데이터 정정 우선

### PR-A DoD
- [ ] `python scripts/spec_consistency_check.py` 결과 `FAIL=0`
- [ ] CI Node 버전 `22.12.0` 고정 증적 존재
- [ ] Phase2 API/DB/UIUX 스펙 반영 완료
- [ ] Notion 동기화 + 메타 갱신 + `spec_sync_report.md` 기록 완료
- [ ] UTF-8 검증 로그 PASS

---

## PR-B: Runbook(Ops) + Audit Chain Verifier/알림 + 보고서 갱신
### 목표
1. MUST(G-D/G-E) 해소
2. 운영 대응 문서와 검증 자동화 연결
3. 최종 보고서에 잔여 리스크 “해소” 상태 반영

### 변경 대상 파일(경로 단위)
1. `docs/ops/runbook/README.md`
2. `docs/ops/runbook/playbooks/scheduler_lock_incident.md` (신규)
3. `docs/ops/runbook/playbooks/audit_chain_integrity_incident.md` (신규)
4. `scripts/verify_audit_chain_integrity.py` (신규, read-only verifier)
5. `.github/workflows/release-nightly-full.yml` (verifier step/alert artifact)
6. `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`
7. `docs/review/mvp_verification_pack/artifacts/phase2_golive_utf8_check_202603XX.txt` (갱신)
8. `docs/review/mvp_verification_pack/artifacts/phase2_golive_runbook_dryrun_202603XX.txt`
9. `docs/review/mvp_verification_pack/artifacts/phase2_golive_audit_chain_verify_202603XX.txt`

### 실행 커맨드
```powershell
python scripts/verify_audit_chain_integrity.py --tenant-key <tenant> --from-utc <from> --to-utc <to>
cd backend && ./gradlew.bat test --no-daemon
python scripts/spec_consistency_check.py
cd frontend && npm ci && npm run test:run && npm run build
node -v
npm -v
```

### 테스트/검증 포인트
1. scheduler lock 장애 시나리오별 runbook 실행성(탐지/완화/복구/사후조치)
2. audit chain verifier PASS/FAIL 기준 및 알림 조건 문서화
3. verifier 실패 시 export 제한 또는 경보 우선순위 정의
4. 보고서 잔여 리스크 섹션 업데이트 반영

### 증적 파일명 규칙
1. `docs/review/mvp_verification_pack/artifacts/phase2_golive_runbook_dryrun_202603XX.txt`
2. `docs/review/mvp_verification_pack/artifacts/phase2_golive_audit_chain_verify_202603XX.txt`
3. `docs/review/mvp_verification_pack/artifacts/phase2_golive_utf8_check_202603XX.txt`
4. `docs/review/mvp_verification_pack/artifacts/phase2_golive_ci_gate_status_202603XX.txt`

### 롤백 전략
1. verifier 스텝 오류 시 workflow step을 feature flag로 비활성화하고 runbook 수동 절차 유지
2. 신규 playbook 문서는 revert 가능하나 기존 runbook 링크 무결성 유지
3. 보고서 업데이트는 rollback 이력으로 보존

### PR-B DoD
- [ ] scheduler lock 전용 playbook 존재 및 README 링크 반영
- [ ] audit chain verifier 실행/증적 파일 생성
- [ ] 알림 임계치/대응 등급 문서화
- [ ] 202603XX 보고서 잔여 리스크 섹션 갱신 완료
- [ ] UTF-8 검증 PASS

## 8) PR-A / PR-B 독립 통과 전략
1. PR-A는 스펙/CI/Node/Notion 게이트만으로 독립 합격 가능해야 한다.
2. PR-B는 기능 스펙 변경 없이 운영문서+검증 루틴 중심으로 독립 합격 가능해야 한다.
3. PR-B는 PR-A merge 이후 rebase를 전제로 하되, DoD는 “runbook/verifier/report” 항목만으로 판정한다.
4. PR-A 실패가 PR-B 합격 조건에 직접 결합되지 않도록 증적 파일을 분리한다.
5. PR 공통으로 표준 에러 포맷/ROLE taxonomy/Hardening Gate 잠금은 검증 항목으로만 확인한다.

## 9) Validation Commands (최종 고정)
```powershell
python scripts/spec_consistency_check.py
cd backend && ./gradlew.bat test --no-daemon
cd frontend && npm ci && npm run test:run && npm run build
node -v
npm -v
```
추가:
1. UTF-8 strict decode 로그 생성: `docs/review/mvp_verification_pack/artifacts/phase2_golive_utf8_check_202603XX.txt`
2. 스펙 변경 시 Notion gate 실행:
```powershell
python scripts/notion_zero_touch_gate.py --base-ref <base> --head-ref <head> --output-json docs/review/mvp_verification_pack/artifacts/phase2_golive_notion_gate_202603XX.json
```

## 10) Public API / Interface / Type 영향
1. 런타임 API 동작 변경은 없다(문서/스펙/운영/CI 정합성 보강 중심).
2. API 스펙 인터페이스 표현 규칙만 고정:
   - `권한` = ROLE 전용
   - `비고` = 접근수준(`access_level`) 및 인증메커니즘 표현
3. 표준 에러 포맷과 상태코드 정책은 유지한다.

## 11) 최종 DoD (Go-Live Gate)
- [ ] `spec_consistency_check` FAIL=0
- [ ] CI/로컬 Node 22.12.0 고정 증적 확보
- [ ] Phase2 API/DB/UIUX 스펙 반영 및 Notion 동기화 완료
- [ ] `spec_sync_report.md`에 파일/링크/메타/요약/TBD 기록
- [ ] scheduler lock runbook + audit chain verifier/알림 체계 반영
- [ ] UTF-8 strict decode 증적 PASS
- [ ] `PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`와 모순 없음

## 12) Assumptions / Defaults
1. ROLE taxonomy는 고정(`AGENT/CUSTOMER/ADMIN/OPS/SYSTEM`)
2. `PUBLIC/AUTHENTICATED`는 접근수준으로만 사용
3. same-site/cross-site 쿠키·CSRF 정책은 기존 Hardening Gate 고정값 유지
4. 스펙 변경이 있으면 Notion 메타 4종 갱신은 예외 없이 필수
5. `/mnt/data` 미가용 시 로컬 SSOT(`docs/references/**`, `docs/uiux/**`)를 기준으로 추적성 유지
