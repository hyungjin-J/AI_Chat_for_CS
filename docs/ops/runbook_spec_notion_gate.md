# Spec/Notion Gate 운영 Runbook

## 목적
스펙 파일 변경 시 Notion 동기화 누락으로 배포가 차단되는 것을 예방한다.

## 동기화 대상
- `docs/references/Summary of key features.csv`
- `docs/references/CS AI Chatbot_Requirements Statement.csv`
- `docs/references/Development environment.csv`
- `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- `docs/references/CS_AI_CHATBOT_DB.xlsx`
- `docs/uiux/CS_RAG_UI_UX_설계서.xlsx`

## 1) 필수 순서
1. 로컬 스펙 파일 수정
2. Notion 본문/메타 동기화
3. `spec_sync_report.md` 기록
4. 게이트 스크립트 확인

## 2) Notion 메타 4종
- `Last synced at`
- `Source file`
- `Version`(commit/tag)
- `Change summary`

## 3) 점검 커맨드
```bash
python scripts/notion_zero_touch_gate.py --base-ref <base> --head-ref <head> --output-json docs/review/mvp_verification_pack/artifacts/golive_notion_gate.json
```

```bash
python scripts/spec_consistency_check.py
```

## 4) 실패 처리
다음 중 하나라도 누락되면 실패:
- Notion 본문 미반영
- 메타 미갱신
- `spec_sync_report.md` 미기록

실패 시 조치:
1. PR을 `Failed` 상태로 전환
2. 누락 항목 보완 후 게이트 재실행

## 5) 증적 파일 권장
- `golive_spec_consistency_before.txt`
- `golive_spec_consistency_after.txt`
- `golive_notion_gate.json`
- `golive_utf8_check.txt`
