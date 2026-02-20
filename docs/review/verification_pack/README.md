# Verification Pack (Project Completion)

## 1. 목적
- 본 문서는 프로젝트 완성 검증을 재현하기 위한 실행 가이드다.
- 실행 결과의 단일 진실원천(SSOT)은 `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`이다.

## 2. 실행 순서 (Windows PowerShell)
1. 인프라 기동
   - `docker compose -f infra/docker-compose.yml up -d`
2. 백엔드 테스트
   - `cd backend && .\gradlew.bat test --no-daemon`
3. 프론트 테스트/빌드
   - `cd frontend && npm ci && npm run test:run && npm run build`
4. 검증팩 정합성 검사
   - `powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1`
5. provider 회귀(조건부)
   - `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`

호환 명령:
- `scripts/verify_all.ps1`, `scripts/verify_all.sh`는 내부적으로 `check_all`을 호출한다.

## 3. 검증 결과 기준
- backend test: PASS
- frontend test/build: PASS
- verification_pack_consistency: PASS
- UUID CAST 검색 결과: `NO_MATCH`
- MyBatis `${}` 검색 결과: `NO_MATCH`
- provider regression: 환경 준비 시 PASS, 미준비 시 SKIPPED(원인/재실행 가이드 포함)

## 4. 주요 증빙 파일
- `docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt`
- `docs/review/mvp_verification_pack/artifacts/frontend_test_output.txt`
- `docs/review/mvp_verification_pack/artifacts/frontend_build_output.txt`
- `docs/review/mvp_verification_pack/artifacts/gap_closure_consistency_output.txt`
- `docs/review/mvp_verification_pack/artifacts/uuid_cast_scan_output.txt`
- `docs/review/mvp_verification_pack/artifacts/mybatis_dollar_scan_output.txt`
- `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`

## 5. 주의사항
- provider 회귀는 Docker Desktop + Ollama 컨테이너 상태에 의존한다.
- Node 표준 버전은 22.x이며, 로컬 Node 24 환경에서는 엔진 경고가 출력될 수 있다.
- 시크릿/PII는 로그/문서/테스트 데이터에 포함하지 않는다.
