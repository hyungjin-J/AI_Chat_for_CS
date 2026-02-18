# DEMO_RUNBOOK

## 목적
비개발자도 10분 안에 MVP 데모를 재현할 수 있도록 실행 절차를 표준화한다.

## 1) 사전 준비
- Docker Desktop 실행
- Java 17, Node 22.12.0, Python 3.11 설치
- 저장소 루트에서 `.env.example`를 참고해 환경변수 확인

### Node 22 강제 정책
- `scripts/verify_all.ps1`는 Node 22가 아니면 기본적으로 실패한다.
- 임시 로컬 우회가 필요한 경우에만 `APP_VERIFY_ALLOW_NON_22_NODE=true`를 사용한다.
- 권장 전환:
  - `nvm use 22.12.0`
  - 또는 Volta 사용 시 `volta install node@22.12.0 npm@10.9.0`

## 2) 10분 데모 시나리오
1. 인프라 기동
   - `docker compose -f infra/docker-compose.yml up -d`
2. 전체 검증/증빙 생성
   - `powershell -ExecutionPolicy Bypass -File scripts/verify_all.ps1`
3. 아티팩트 확인
   - `docs/review/mvp_verification_pack/artifacts/sse_stream_normal.log`
   - `docs/review/mvp_verification_pack/artifacts/sse_stream_fail_closed.log`
   - `docs/review/mvp_verification_pack/artifacts/trace_id_checks.txt`
   - `docs/review/mvp_verification_pack/artifacts/tenant_isolation_403_checks.txt`
4. 경영진 보고용 문서 확인
   - `docs/review/mvp_verification_pack/00_EXEC_SUMMARY.md`
   - `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`

## 3) 데모 모드 전환
### A. Mock provider 데모(기본)
- 목적: 항상 동일한 재현성 확보
- 설정:
  - `APP_LLM_PROVIDER=mock`

### B. Ollama 실데모(선택)
- 목적: 실제 모델 경로 점검
- 설정:
  - `APP_LLM_PROVIDER=ollama`
  - `APP_OLLAMA_BASE_URL=http://localhost:11434`
- 실행:
  - `docker compose -f infra/docker-compose.ollama.yml up -d`
  - `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`

## 4) 자주 발생하는 오류와 해결
### 1) 8080 포트 충돌
- 증상: backend_not_ready
- 조치: 기존 8080 점유 프로세스 종료 후 재실행

### 2) PostgreSQL 연결 실패
- 증상: Flyway 마이그레이션 실패
- 조치:
  - `docker compose -f infra/docker-compose.yml ps`
  - postgres가 `healthy`인지 확인

### 3) 프론트 빌드 실패
- 증상: `npm run build` 실패
- 조치:
  - Node 22 사용 확인
  - `frontend/package-lock.json` 기준으로 `npm ci` 재실행

### 4) Provider 회귀 SKIPPED
- 증상: `provider_regression_ollama.log`에 SKIPPED
- 조치:
  - `docker compose -f infra/docker-compose.ollama.yml up -d`
  - `APP_OLLAMA_BASE_URL=http://localhost:11434` 설정
  - `curl http://localhost:11434/api/tags` 응답 확인

## 5) 안전성 체크(반드시 확인)
- Fail-Closed 시 `safe_response`만 노출되고 token 누출이 없는지
- 응답/로그/증빙 파일에 PII 원문이 없는지
- 동일 trace_id가 HTTP/SSE/DB에서 일치하는지
- tenant mismatch가 `403 + SYS-002-403 + details=["tenant_mismatch"]`로 차단되는지

## 6) 운영 안전 설정 메모
- Branch Protection 필수:
  - required check 이름: `mvp-demo-verify / verify`
  - 설정 가이드: `docs/ops/BRANCH_PROTECTION_SETUP.md`
- Idempotency Redis 장애 전략:
  - dev/demo: `APP_IDEMPOTENCY_REDIS_FAIL_STRATEGY=fallback_memory`
  - production: `APP_IDEMPOTENCY_REDIS_FAIL_STRATEGY=fail_closed` 권장
- 해석 주의:
  - `fallback_memory`가 발동되면 분산 환경에서 중복 방지 강도가 약해질 수 있음
  - `idempotency_redis_fallback_total` 메트릭으로 발생 여부 모니터링

## 7) 메트릭/노출 보안
- `/actuator/prometheus`는 운영에서 외부 공개 금지
- 최소 요구:
  - 내부 네트워크/VPN에서만 접근
  - Ingress/WAF에서 IP 제한 또는 인증 추가
  - 운영 프로파일에서 endpoint exposure 최소화
