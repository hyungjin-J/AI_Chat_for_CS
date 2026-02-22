# Agent Prompt Set - Orchestrator Preflight Control

## Control-Plane Agent Prompt
```text
[AGENTS.md 준수][MODE: PLAN MODE = OFF]
목표: scripts/agent/manual_hook.py와 docs/agent_manual 4챕터를 생성/유지한다.
요구:
- manual_hook CLI: --task, --changed-files (필수), --changed-files-file (보조)
- 출력 JSON: status/manual_chapters/chapter_summaries/blockers/next_actions
- 매뉴얼 누락/위반 시 exit 1 fail-closed
- docs/agent_manual/{01,02,03,04}_*.md 유지
검증:
- python scripts/agent/manual_hook.py --task "..." --changed-files-file "<artifact path>"
- python -m unittest scripts.tests.test_manual_hook
산출:
- 변경 파일 목록 + hook 증적 경로 + 회귀 테스트 결과
```

## Documentation Architect Agent Prompt
```text
[AGENTS.md 준수][MODE: PLAN MODE = OFF]
목표: workpack 3문서 + AGENTS 12.3 사전 보고서 문서를 유지한다.
경로:
- docs/workpacks/20260222_orchestrator_preflight_control/{01_plan,02_context,03_checklist}.md
- docs/review/plans/20260222_orchestrator_preflight_control_design_and_hardening_plan.md
- docs/review/plans/20260222_orchestrator_preflight_control_implementation_checklist.md
필수:
- "승인 전에는 코드 변경 금지" 문구 포함
- PR 분해/역할 배정/DoD 게이트 명시
검증:
- UTF-8 strict + 탭/제어문자 금지
- 문서 lint 게이트 통과
```

## QA/Gate Agent Prompt
```text
[AGENTS.md 준수][MODE: PLAN MODE = OFF]
목표: 선통제 체계의 게이트와 증적 경로를 고정한다.
작업:
- preflight 실행 순서 문서화
- 증적 파일 경로를 docs/review/mvp_verification_pack/artifacts/orchestrator_control_* 로 고정
- 필수 게이트 실행:
  - backend test
  - frontend npm ci/test/build
  - spec consistency
  - utf8 strict
  - lint_chatgpt_handoff_docs
  - lint_validation_gate_tables
  - notion manual gate
산출:
- PASS/FAIL 요약 + 누락 증적 + remediation
```

## Release/Handoff Agent Prompt
```text
[AGENTS.md 준수][MODE: PLAN MODE = OFF]
목표: 오케스트레이터 선통제 절차를 handoff 가능 상태로 반영한다.
작업:
- 필요 시 chatGPT handoff 문서 2종 갱신
- Validation Gate 표에 orchestrator_control 증적 경로 반영
- Open Risks/Next PRs에 통제 절차 리스크 반영
검증:
- lint_chatgpt_handoff_docs PASS
- evidence path 존재성 PASS
```

