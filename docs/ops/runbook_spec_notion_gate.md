# Spec/Notion Gate Runbook (Phase2.1.1)

## 목적
스펙 변경 PR에서 Notion 자동 동기화가 실패한 경우에도 fail-closed 원칙을 유지하면서,
공식 수동 예외 경로(`BLOCKED -> Manual Patch -> Evidence -> Close`)를 운영 가능하게 표준화한다.

## 적용 대상 스펙 파일
- `docs/references/Summary of key features.csv`
- `docs/references/CS AI Chatbot_Requirements Statement.csv`
- `docs/references/Development environment.csv`
- `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- `docs/references/CS_AI_CHATBOT_DB.xlsx`
- `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`

## One-Page Operational Flow (MUST)
1. `BLOCKED` 감지  
   - 조건: `scripts/notion_ci_auth_preflight.py`가 `NOTION_AUTH_*`(또는 `OPENAI_API_KEY_MISSING`)로 실패
2. `Manual Patch` 작성  
   - 파일: `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
3. `Evidence` 3종 준비  
   - `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json`
   - `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
   - `spec_sync_report.md` (동일 세션 기록)
4. `Close` 게이트 통과  
   - `scripts/check_notion_manual_exception_gate.py` PASS일 때만 운영적으로 Close

## Fail-Closed 규칙
1. preflight FAIL 시 자동 동기화(Codex + MCP) 경로는 즉시 중단한다.
2. 수동 예외 경로 증적 3종 중 하나라도 누락되면 CI 실패 처리한다.
3. 예외 경로는 자동 동기화 실패를 우회하기 위한 임시 운영 절차이며, Notion 동기화 의무를 제거하지 않는다.

## 표준 오류 코드
- `NOTION_AUTH_TOKEN_MISSING`
- `NOTION_AUTH_UNAUTHORIZED`
- `NOTION_AUTH_FORBIDDEN`
- `NOTION_AUTH_PRECHECK_FAILED`
- `OPENAI_API_KEY_MISSING`

## 증적 파일 스키마 (고정)
### 1) `notion_blocked_status.json`
필수 키:
- `status`: `BLOCKED_AUTOMATION`
- `reason`: preflight error code
- `timestamp_kst`
- `manual_patch`: `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
- `targets`: Notion URL 배열

### 2) `notion_manual_patch.md`
필수 메타:
- `Last synced at`
- `Source file`
- `Version`
- `Change summary`

### 3) `spec_sync_report.md`
필수 기록:
- Phase2.1.1 섹션/항목
- BLOCKED 사유
- 위 2개 증적 파일 경로
- Close 시각/결과

## 로컬/CI 검증 명령
```bash
python scripts/notion_zero_touch_gate.py \
  --base-ref origin/main \
  --head-ref HEAD \
  --output-json tmp/ci_notion_sync_context.json
```

```bash
python scripts/notion_ci_auth_preflight.py \
  --context-json tmp/ci_notion_sync_context.json \
  --output tmp/ci_notion_auth_preflight.json
```

```bash
python scripts/check_notion_manual_exception_gate.py \
  --context tmp/ci_notion_sync_context.json \
  --preflight tmp/ci_notion_auth_preflight.json \
  --status-json docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json \
  --manual-patch docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md \
  --spec-sync spec_sync_report.md \
  --output-json docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate.json \
  --output-txt docs/review/mvp_verification_pack/artifacts/phase2_1_1_prC_notion_manual_gate.txt
```

## 책임/점검 항목
- Dev: 증적 3종 작성 및 스펙 변경 내역 반영
- Reviewer: 증적 3종 경로/내용/시각 일치 확인
- Release owner: manual gate PASS 확인 후에만 병합 승인

## 완료 체크리스트
- [ ] preflight 실패 시 자동 동기화가 중단되었다.
- [ ] `notion_blocked_status.json`이 존재하고 `status=BLOCKED_AUTOMATION`이다.
- [ ] `notion_manual_patch.md`에 메타 4종이 존재한다.
- [ ] `spec_sync_report.md`에 Phase2.1.1 BLOCKED 예외 기록이 존재한다.
- [ ] `check_notion_manual_exception_gate.py`가 PASS했다.
