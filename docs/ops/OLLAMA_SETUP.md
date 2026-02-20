# Ollama Docker 실행 표준 가이드

- 대상: AI_Chatbot 프로젝트 개발/검증 환경
- 기본 원칙: **Ollama는 로컬 설치가 아닌 Docker Compose 실행을 표준으로 사용**
- 기본 모델: `qwen2.5:3b-instruct`

## 1) 빠른 시작 (Windows PowerShell)

1. Ollama 컨테이너 실행
```powershell
docker compose -f infra/docker-compose.ollama.yml up -d
```

2. 상태 확인
```powershell
docker compose -f infra/docker-compose.ollama.yml ps
```

3. 로그 확인(필요 시)
```powershell
docker compose -f infra/docker-compose.ollama.yml logs -f ollama
```

4. 모델 다운로드
```powershell
docker compose -f infra/docker-compose.ollama.yml exec ollama ollama pull qwen2.5:3b-instruct
```

5. 모델 목록/헬스 확인
```powershell
curl.exe -s http://localhost:11434/api/tags
```

## 2) 네트워크 접근 규칙

- 호스트(내 PC)에서 접근: `http://localhost:11434`
- Compose 내부의 다른 컨테이너(예: backend)에서 접근: `http://ollama:11434`

권장 환경변수:
```text
APP_OLLAMA_BASE_URL=http://localhost:11434
APP_OLLAMA_MODEL=qwen2.5:3b-instruct
```

## 3) provider regression 실행 순서

1. Ollama 기동/모델 준비
2. 아래 스크립트 실행
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1
```

3. 결과 확인
- 증빙 로그: `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`

## 4) 트러블슈팅

### 4.1 `11434` 포트 충돌
- 증상: Ollama 컨테이너가 뜨지 않거나 API 연결 실패
- 확인: `docker compose -f infra/docker-compose.ollama.yml ps`
- 조치: 기존 프로세스 종료 후 재기동

### 4.2 healthcheck 실패
- 증상: 컨테이너 상태가 `unhealthy`
- 확인: `docker inspect aichatbot-ollama --format "{{json .State.Health}}"`
- 조치: 로그 확인 후 재시작
```powershell
docker compose -f infra/docker-compose.ollama.yml restart ollama
```

### 4.3 모델 다운로드 지연
- 증상: 첫 `pull`이 오래 걸림
- 원인: 모델 크기(3B 약 2GB 내외) + 네트워크 속도
- 조치: 충분한 시간 확보, 완료 후 `api/tags`로 확인

### 4.4 디스크 용량 부족
- 증상: pull 실패/중단
- 조치: Docker 디스크 여유 확보 후 재시도

## 5) SSOT 반영 규칙

- `LLM-PROVIDER-001`을 `PASS`로 변경하려면 아래 조건이 모두 필요합니다.
1. `scripts/run_provider_regression.ps1` 실제 실행
2. `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log` 생성
3. 로그 내 최종 상태가 `status=PASS`

- 위 증빙 없이 문서 상태만 변경하면 안 됩니다.

## 6) 선택 사항 (비표준)

- 로컬 네이티브 Ollama 설치 방식은 선택 사항이며, 본 프로젝트 표준 경로는 Docker Compose입니다.

## 7) 최근 검증 메모 (2026-02-20)

- 모델 정리:
  - 삭제: `qwen2.5:7b-instruct`, `qwen2.5:1.5b`
  - 유지: `qwen2.5:3b-instruct` (약 1.9GB)
- 단독 모델 응답 확인:
  - `POST /api/generate` (`prompt: Reply with exactly: OK`) 응답 `OK` 확인
- 회귀 스크립트 실행:
  - `scripts/run_provider_regression.ps1` 실행 결과 `PASS`
  - 상세 로그: `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`
- 이슈 해결 메모:
  - 초기 실패 원인: 여러 Mapper에서 UUID 컬럼에 문자열 파라미터가 바인딩되어 DB 타입 충돌
  - 조치: Mapper/Repository UUID 타입 정합성 보강 + SQL `CAST(... AS UUID)` 적용 후 재검증 완료
