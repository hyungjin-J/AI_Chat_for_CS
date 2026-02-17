# AI_Chatbot (고객센터 서포팅 AI 챗봇)

이 저장소는 `AGENTS.md` 규칙을 기준으로 구성된 기본 스캐폴딩입니다.  
핵심 원칙: **Fail-Closed, PII 마스킹, 테넌트 격리, trace_id 전파, 예산/레이트리밋 강제**

## 1) 사전 요구사항
- Windows CMD
- Git
- Java 17
- Node.js + npm
- Python 3.11+
- Docker Desktop (선택, 로컬 인프라 실행용)

## 2) 루트 이동 (CMD)
```cmd
cd /d "C:\Users\hjjmj\OneDrive\바탕 화면\AI_Chatbot"
```

## 3) 자동화 스크립트 실행 순서 (CMD)
초기 부트스트랩 스크립트는 루트 오염을 피하기 위해 `tools\bootstrap_archive\`에 분리 보관합니다.
```cmd
tools\bootstrap_archive\00_bootstrap.cmd
tools\bootstrap_archive\10_generate_backend.cmd
tools\bootstrap_archive\11_backend_skeleton.cmd
tools\bootstrap_archive\20_generate_frontend.cmd
tools\bootstrap_archive\21_frontend_skeleton.cmd
tools\bootstrap_archive\30_generate_infra.cmd
tools\bootstrap_archive\40_install_skills.cmd
tools\bootstrap_archive\50_generate_gitignore.cmd
tools\bootstrap_archive\60_generate_readme.cmd
tools\bootstrap_archive\90_verify.cmd
tools\bootstrap_archive\99_git_init_commit_push.cmd
```

## 4) 개별 실행 가이드
- 백엔드 실행:
```cmd
cd /d "C:\Users\hjjmj\OneDrive\바탕 화면\AI_Chatbot\backend"
gradlew.bat bootRun
```

- 프론트 실행:
```cmd
cd /d "C:\Users\hjjmj\OneDrive\바탕 화면\AI_Chatbot\frontend"
npm install
npm run dev
```

- 인프라 실행 (Docker 필요):
```cmd
cd /d "C:\Users\hjjmj\OneDrive\바탕 화면\AI_Chatbot"
docker compose -f "infra\docker-compose.yml" up -d
```

## 5) 보안 주의사항
- `infra/docker-compose.yml`의 비밀번호는 **로컬 예시값**입니다.
- 운영 환경에서는 반드시 환경변수 + Vault/KMS/Secret Manager를 사용하세요.
- `.env`, 인증서/키 파일(`*.pem`, `*.key`, `*.p12`, `*.jks`)은 커밋 금지입니다.

## 6) 스킬 설치 정책
- 기본 정책: `.agents/skills`는 커밋하지 않습니다.
- 설치 명령/성공 여부는 `docs/ops/CODEX_WORKLOG.md`에서 추적합니다.

## 7) 운영/품질 기준 요약
- trace_id: 요청/응답 헤더(`X-Trace-Id`) 전파
- tenant_key: `X-Tenant-Key` 필수, 누락 시 400
- 표준 에러 포맷: `{ "error_code", "message", "trace_id" }`
- SSE 이벤트 타입: `token`, `tool`, `citation`, `done`, `error`, `safe_response`
- PII는 로그/캐시/UI 노출 금지(마스킹)
