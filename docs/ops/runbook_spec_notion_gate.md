# Spec/Notion Gate Runbook (Phase2.1.2)

## 목적
스펙 변경 PR에서 Notion 자동 동기화가 실패했을 때도 fail-closed 원칙을 유지하고,
수동 예외 close에서 발생하는 증적 누락 실수를 줄이기 위한 운영 표준이다.

## 적용 대상 스펙 파일
- `docs/references/Summary of key features.csv`
- `docs/references/CS AI Chatbot_Requirements Statement.csv`
- `docs/references/Development environment.csv`
- `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- `docs/references/CS_AI_CHATBOT_DB.xlsx`
- `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`

## 고정 증적 경로 (절대 변경 금지)
- `docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json`
- `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`
- `spec_sync_report.md`

## One-Page Operational Flow (MUST)
1. `BLOCKED` 감지
   - 조건: `scripts/notion_ci_auth_preflight.py`가 `NOTION_AUTH_*` 또는 `OPENAI_API_KEY_MISSING`으로 FAIL
2. 증적 템플릿 생성 (수동 작성 시작 전에 반드시 실행)
   - `python scripts/gen_notion_manual_evidence_template.py`
   - 기존 고정 파일이 있으면 기본 동작은 overwrite 금지이며, 필요한 경우에만 `--force` 사용
3. 수동 패치 수행
   - `docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md`의 placeholder를 실제 값으로 교체
   - Notion 페이지 메타 4종(Last synced at / Source file / Version / Change summary) 갱신
4. 동기화 로그 기록
   - `spec_sync_report.md`에 BLOCKED 사유, 증적 2개 경로, close 시각/결과 기록
5. Close 게이트 검증
   - `scripts/check_notion_manual_exception_gate.py` PASS일 때만 운영적으로 close

## Fail-Closed 규칙
1. preflight FAIL 시 자동 동기화(Codex + MCP) 경로는 즉시 중단한다.
2. 증적 3종 중 하나라도 누락되면 CI를 FAIL 처리한다.
3. 수동 예외 close는 자동 동기화 의무를 대체하지 않는다.

## 표준 오류 코드
- `NOTION_AUTH_TOKEN_MISSING`
- `NOTION_AUTH_UNAUTHORIZED`
- `NOTION_AUTH_FORBIDDEN`
- `NOTION_AUTH_PRECHECK_FAILED`
- `OPENAI_API_KEY_MISSING`

## 증적 파일 스키마 (고정)
### 1) `notion_blocked_status.json`
필수 키:
- `status` (`BLOCKED_AUTOMATION`)
- `reason`
- `detected_at_kst`
- `preflight_ref`

권장 키:
- `manual_patch`
- `targets`

### 2) `notion_manual_patch.md`
필수 메타:
- `Last synced at`
- `Source file`
- `Version`
- `Change summary`

필수 운영 메타:
- `Owner`
- `Recorded at`

### 3) `spec_sync_report.md`
필수 기록:
- Phase2.1 수동 예외 섹션/항목
- BLOCKED 사유
- 고정 증적 2개 파일 경로
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
  --output-json docs/review/mvp_verification_pack/artifacts/phase2_1_2_notion_manual_gate.json \
  --output-txt docs/review/mvp_verification_pack/artifacts/phase2_1_2_notion_manual_gate.txt
```

## 책임/점검 항목
- Dev: 템플릿 생성, 수동 패치, spec_sync_report 기록 완료
- Reviewer: 증적 3종 경로/필드/시각 일치 확인
- Release owner: manual gate PASS 확인 후에만 close 승인

## 완료 체크리스트
- [ ] preflight FAIL 시 자동 동기화가 중단되었다.
- [ ] 템플릿 생성기로 고정 증적 파일 2종을 생성했다.
- [ ] `notion_blocked_status.json`에 `status/reason/detected_at_kst/preflight_ref`가 채워졌다.
- [ ] `notion_manual_patch.md`에 메타 4종 + Owner/Recorded at이 채워졌다.
- [ ] `spec_sync_report.md`에 BLOCKED 사유/증적 경로/close 결과가 기록되었다.
- [ ] `check_notion_manual_exception_gate.py`가 PASS했다.
