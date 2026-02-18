# AI_Chatbot (CS 서포팅 AI 챗봇)

고객센터 상담원을 위한 근거 기반(RAG) 답변 보조 시스템입니다.  
핵심 원칙은 `Fail-Closed`, `PII 마스킹`, `trace_id 종단 추적`, `Tenant 격리 + RBAC`, `Budget Guard`입니다.

## 1) 현재 상태
- MVP 상태: **Demo Ready**
- 표준 SSE 경로:
  - `GET /v1/sessions/{session_id}/messages/{message_id}/stream`
  - `GET /v1/sessions/{session_id}/messages/{message_id}/stream/resume?last_event_id={n}`
- 검증 문서:
  - `docs/review/mvp_verification_pack/00_EXEC_SUMMARY.md`
  - `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`
  - `docs/review/mvp_verification_pack/05_E2E_EVIDENCE.md`

## 2) 로컬 실행

### 인프라 실행
```bash
docker compose -f infra/docker-compose.yml up -d
```

### 백엔드 실행
```bash
cd backend
gradlew.bat bootRun
```

### 프론트 실행
```bash
cd frontend
npm ci
npm run dev
```

## 3) 테스트/증빙 재생성

### 백엔드 테스트
```bash
cd backend
gradlew.bat test --no-daemon
```

### 프론트 빌드
```bash
cd frontend
npm ci
npm run build
```

### E2E 증빙 생성
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_mvp_e2e_evidence.ps1
```

아티팩트 출력 위치:
- `docs/review/mvp_verification_pack/artifacts/`

## 4) 주요 문서
- 구현 리뷰: `docs/MVP_IMPLEMENTATION_REVIEW_PACK.md`
- 가정/판단: `docs/MVP_ASSUMPTIONS.md`
- 아키텍처: `docs/architecture/NOTION_System_Architecture.md`
- 검증 팩: `docs/review/mvp_verification_pack/`

## 5) 노션 설계서 링크 (Source Sync)
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
- 시스템 아키텍처 페이지  
  - https://www.notion.so/2ee405a3a72080868020e37dc33abad4

## 6) 보안/운영 주의사항
- 시크릿/토큰/PII를 저장소에 커밋하지 않습니다.
- 모든 요청은 `X-Trace-Id`, `X-Tenant-Key` 정책을 준수해야 합니다.
- Answer Contract 검증 실패 시 자유 텍스트 우회 없이 `safe_response`를 반환합니다.
