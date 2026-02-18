# AI_Chatbot (CS 서포팅 AI 챗봇)

고객센터 상담원의 답변 작성을 지원하는 RAG 기반 AI 챗봇 프로젝트입니다.
핵심 원칙은 다음과 같습니다.
- Fail-Closed(검증 실패 시 안전응답)
- PII 마스킹(입력/로그/응답/인용문)
- trace_id 종단 추적(HTTP/SSE/DB)
- Tenant 격리 + RBAC 서버 강제
- 예산/레이트리밋 가드

## 1) 현재 상태
- MVP 상태: **Demo Ready 유지 + Phase2.1 운영 게이트 반영**
- 상태 진실원천(SSOT): `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`
- 검증팩 현재 포인터: `docs/review/mvp_verification_pack/CURRENT.md`

## 2) 로컬 실행
### 인프라
```bash
docker compose -f infra/docker-compose.yml up -d
```

### 백엔드
```bash
cd backend
gradlew.bat bootRun
```

### 프론트엔드
```bash
cd frontend
npm ci
npm run dev
```

## 3) 검증/증빙 생성
### 전체 검증 진입점
```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify_all.ps1
```

### 개별 실행 예시
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_mvp_e2e_evidence.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_mvp_negative_tests.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1
powershell -ExecutionPolicy Bypass -File scripts/generate_metrics_report.ps1
```

아티팩트 출력 경로:
- `docs/review/mvp_verification_pack/artifacts/`

## 4) 주요 문서
- 구현 리뷰: `docs/MVP_IMPLEMENTATION_REVIEW_PACK.md`
- 검증 요약: `docs/review/mvp_verification_pack/00_EXEC_SUMMARY.md`
- 테스트 결과(SSOT): `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`
- 아티팩트 요약: `docs/review/mvp_verification_pack/06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md`
- Phase2 진행 요약: `PHASE2_PROGRESS_SUMMARY_FOR_CHATGPT.md`
- 운영 데모 런북: `docs/DEMO_RUNBOOK.md`
- 브랜치 보호 설정 가이드: `docs/ops/BRANCH_PROTECTION_SETUP.md`

## 5) Notion 링크
### 레퍼런스 스펙 동기화 페이지
- Summary of key features.csv
  - https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149
- CS AI Chatbot_Requirements Statement.csv
  - https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- Development environment.csv
  - https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7
- google_ready_api_spec_v0.3_20260216.xlsx
  - https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- CS_AI_CHATBOT_DB.xlsx
  - https://www.notion.so/2ed405a3a720812180d9d508b77f31a4
- CS_RAG_UI_UX_설계서.xlsx
  - https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444

### 설계/운영 문서 페이지
- 시스템 아키텍처
  - https://www.notion.so/2ee405a3a72080868020e37dc33abad4
- 프로젝트 용어 정리(글로서리)
  - https://www.notion.so/30a405a3a720804b8d41e65628abe376

## 6) 보안/운영 주의사항
- 시크릿/토큰/PII를 저장소에 평문으로 커밋하지 않습니다.
- 모든 요청은 `X-Trace-Id`, `X-Tenant-Key` 정책을 준수해야 합니다.
- Answer Contract 검증 실패 시 자유 텍스트 우회 없이 `safe_response`로 종료합니다.
