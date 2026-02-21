# Spec/Notion Gate Runbook (Phase2.1)

## 목적
스펙 파일(CSV/XLSX) 변경이 발생한 PR에서 Notion 동기화 누락을 fail-closed로 차단하고, 인증/권한 오류를 즉시 복구하기 위한 운영 절차를 제공한다.

## 적용 대상 파일
- `docs/references/Summary of key features.csv`
- `docs/references/CS AI Chatbot_Requirements Statement.csv`
- `docs/references/Development environment.csv`
- `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- `docs/references/CS_AI_CHATBOT_DB.xlsx`
- `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`

## 파이프라인 동작 요약
1. `scripts/notion_zero_touch_gate.py`로 스펙 변경 여부를 감지한다.
2. 변경이 있으면 `scripts/notion_ci_auth_preflight.py`를 먼저 실행한다.
3. preflight가 `PASS`일 때만 Codex + MCP 동기화를 실행한다.
4. 동기화 후 `spec_sync_report.md` 마커와 변경 범위를 검증한다.
5. 하나라도 실패하면 CI를 즉시 실패 처리한다.

## 표준 오류 코드 (Fail-Closed)
- `NOTION_AUTH_TOKEN_MISSING`: `NOTION_TOKEN` 미설정
- `OPENAI_API_KEY_MISSING`: `OPENAI_API_KEY` 미설정
- `NOTION_AUTH_UNAUTHORIZED`: Notion API 401
- `NOTION_AUTH_FORBIDDEN`: Notion API 403
- `NOTION_AUTH_PRECHECK_FAILED`: 네트워크/기타 예외

## 장애 대응 절차
### 1) NOTION_AUTH_TOKEN_MISSING
1. GitHub Secrets에 `NOTION_TOKEN` 존재 여부를 확인한다.
2. Notion Integration 토큰을 재발급해 Secret을 갱신한다.
3. Workflow를 rerun하고 preflight 아티팩트를 확인한다.

### 2) OPENAI_API_KEY_MISSING
1. GitHub Secrets에 `OPENAI_API_KEY`를 재주입한다.
2. rerun 후 preflight 단계 통과 여부를 확인한다.

### 3) NOTION_AUTH_UNAUTHORIZED (401)
1. 토큰 만료 또는 잘못된 토큰 여부를 점검한다.
2. 토큰 재발급 후 재실행한다.
3. 여전히 실패하면 Integration이 연결된 workspace를 확인한다.

### 4) NOTION_AUTH_FORBIDDEN (403)
1. 대상 Notion 페이지/DB에 Integration 권한이 부여되었는지 확인한다.
2. 읽기/쓰기 권한을 재부여한다.
3. rerun 후 `tmp/ci_notion_auth_preflight.json`의 HTTP status를 확인한다.

### 5) NOTION_AUTH_PRECHECK_FAILED
1. GitHub Actions 네트워크 상태를 확인한다.
2. Notion API 장애 여부를 확인한다.
3. 복구 전까지 PR은 병합 금지 상태를 유지한다.

## 로컬 점검 커맨드
```bash
python scripts/notion_zero_touch_gate.py \
  --base-ref origin/main \
  --head-ref HEAD \
  --output-json docs/review/mvp_verification_pack/artifacts/phase2_1_pr1_notion_gate_context_202603XX.json
```

```bash
OPENAI_API_KEY=*** NOTION_TOKEN=*** \
python scripts/notion_ci_auth_preflight.py \
  --context-json docs/review/mvp_verification_pack/artifacts/phase2_1_pr1_notion_gate_context_202603XX.json \
  --output docs/review/mvp_verification_pack/artifacts/phase2_1_pr1_notion_auth_preflight_result_202603XX.json
```

## 증적 파일
- `docs/review/mvp_verification_pack/artifacts/phase2_1_pr1_notion_auth_preflight_202603XX.txt`
- `docs/review/mvp_verification_pack/artifacts/phase2_1_pr1_notion_gate_context_202603XX.json`
- `docs/review/mvp_verification_pack/artifacts/phase2_1_pr1_notion_auth_preflight_result_202603XX.json`
- `docs/review/mvp_verification_pack/artifacts/phase2_1_pr1_ci_step_summary_202603XX.txt`

## 완료 체크리스트
- [ ] preflight 실패가 명확한 오류 코드/메시지로 출력된다.
- [ ] runbook 링크가 실패 메시지에 포함된다.
- [ ] 성공 시 Notion 동기화가 실행되고 `spec_sync_report.md` 마커가 생성된다.
- [ ] Notion 메타(Last synced at / Source file / Version / Change summary)가 갱신된다.
