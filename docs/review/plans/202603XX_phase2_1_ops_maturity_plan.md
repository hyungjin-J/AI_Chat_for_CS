# 202603XX Phase2.1 Ops Maturity Plan

- status: `IMPLEMENTATION_BASELINE_LOCKED`
- reference:
  - `docs/review/plans/20260221_auth_rbac_ops_admin_design_and_hardening_plan.md`
  - `docs/review/plans/202603XX_production_readiness_phase2_plan.md`
  - `docs/review/plans/202603XX_go_live_gap_closure_plan.md`
  - `docs/reports/PROJECT_FULL_IMPLEMENTATION_AND_HARDENING_REPORT_202603XX.md`

## Summary
- 운영 직전 리스크 4개(Notion CI auth 만료, audit export 대량 처리, scheduler lock self-healing, WebAuthn 설계 공백)를 해소한다.
- 구현 범위는 PR1~PR3 코드 반영 + PR4(WebAuthn) 설계 문서화다.
- 고정 정책:
  1. Audit export 저장소는 DB spool(`tb_audit_export_job`, `tb_audit_export_chunk`)만 사용.
  2. WebAuthn은 Phase2.1에서는 설계-only, Phase2.2에서 런타임 구현.

## Scope
1. Notion CI auth preflight + fail-closed 메시지 + runbook.
2. Async audit export job + polling/download + TTL cleanup.
3. Scheduler stuck lock 감지/회복 + observability.
4. WebAuthn Phase2.2 설계 SSOT 확정.

## Out of Scope
1. ROLE taxonomy 변경 금지.
2. Hardening Gate 완화 금지.
3. WebAuthn 런타임 구현 금지.
4. 표준 에러 포맷/상태코드 규약 변경 금지.

## Decision Locks
- `P21-L01` Export storage: DB spool only.
- `P21-L02` Export state machine: `PENDING -> RUNNING -> DONE/FAILED/EXPIRED`.
- `P21-L03` tenant/date/row/max_bytes/max_duration 동시 강제.
- `P21-L04` export payload sanitizer 재적용.
- `P21-L05` export TTL 기본 24h + cleanup job 필수.
- `P21-L06` export 요청/완료/실패/다운로드 이벤트를 `ops_event + audit_log`에 모두 기록.
- `P21-L07` `ExportStorage` 인터페이스 유지(Phase2.2 object storage 전환 대비).
- `P21-L08` WebAuthn은 설계-only 고정.

## PR1
- Notion CI token ops + runbook
- preflight fail-closed(`NOTION_AUTH_*`) 적용

## PR2
- Async audit export(DB spool) + API + 테스트 + 스펙/Notion 동기화

## PR3
- Scheduler self-healing + observability + runbook + 테스트

## PR4
- WebAuthn Phase2.2 설계 문서 고정

## Validation Commands
```bash
python scripts/spec_consistency_check.py
cd backend && ./gradlew.bat test --no-daemon
cd frontend && npm ci && npm run test:run && npm run build
node -v
npm -v
```

## DoD
1. PR1~PR3 구현/검증 완료.
2. `spec_consistency_check` FAIL=0 유지.
3. 스펙 변경 시 Notion + 메타 + `spec_sync_report.md` 기록 완료.
4. UTF-8 strict decode PASS 증적 생성.
5. `chatGPT` 문서 2종 업데이트 완료(AGENTS 16.8).
