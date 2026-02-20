# UUID Regression Hardening Report

## 1) Summary
- 목적: `uuid = character varying` 류 회귀를 구조적으로 차단하고, UUID 처리 규칙을 코드/빌드/테스트 레벨로 고정했습니다.
- 핵심 변경:
  - MyBatis `UUIDTypeHandler` 도입으로 UUID 바인딩을 프레임워크 레벨에서 처리
  - UUID Mapper XML의 `CAST(#{...} AS UUID)` 의존 제거
  - `Controller -> Service -> Repository -> Mapper` UUID 객체 전달 경로 고정
  - UUID 회귀 정적 검사 스크립트 추가 + Gradle `test/check` 파이프라인 연결
  - 통합 테스트(잘못된 UUID/미존재 UUID/타 테넌트 접근/정상 UUID) 추가
  - 프론트 UUID 사전 검증 및 400/403/404/422 사용자 오류 안내 추가

## 2) CAST 제거 결과
- 실행 명령:
  - `rg -n "CAST\\(#\\{.*\\} AS UUID\\)" backend/src/main/resources/mappers`
- 결과:
  - UUID 관련 Mapper XML에서 `CAST(... AS UUID)` **0건**
- 비고:
  - `CAST(#{payloadJson} AS JSON)`은 UUID와 무관한 JSON 타입 변환이므로 유지

## 3) Static Lint Rule (재발 방지)
- 추가 파일:
  - `scripts/lint_uuid_params.py`
- 규칙:
  - Mapper 인터페이스(`**/mapper/*Mapper.java`)에서 `String` 파라미터 중 `*Id`/`*_id` 패턴 탐지 시 실패
  - 예외 allowlist: `loginId`, `login_id`
- allowlist 근거:
  - `login_id`는 사용자 로그인 식별자 문자열 컬럼이며 DB UUID 컬럼이 아님
- Gradle 연동:
  - `backend/build.gradle`
  - `lintUuidMapperParams` task 추가
  - `test`, `check`에 `dependsOn lintUuidMapperParams` 연결

## 4) Intentional Violation 검증
- 임시 위반 파일 생성:
  - `backend/src/main/java/com/aichatbot/tmp/mapper/UuidLintViolationMapper.java`
  - 내용: `@Param("tenantId") String tenantId`
- 실행 결과:
  - `python scripts/lint_uuid_params.py` -> **FAIL(의도한 실패)**
- 정리:
  - 임시 파일 삭제 후 재실행
  - `python scripts/lint_uuid_params.py` -> **PASS**

## 5) Backend UUID 흐름 강제
- 경계 파싱 유틸:
  - `backend/src/main/java/com/aichatbot/global/util/UuidParser.java`
- 컨트롤러 적용:
  - `SessionController`, `MessageStreamV1Controller`, `CitationController`
- 서비스 레이어 처리:
  - `SessionService`, `MessageGenerationService`, `SseStreamService`
  - 잘못된 UUID: `422 API-003-422`
  - 미존재 UUID: `404 API-004-404`
  - 타 테넌트 접근: `403 SEC-002-403`

## 6) 통합 테스트 추가
- 추가 파일:
  - `backend/src/test/java/com/aichatbot/session/presentation/UuidAccessContractTest.java`
- 케이스:
  - invalid UUID format -> `422`
  - non-existent UUID -> `404`
  - cross-tenant session/message access -> `403`
  - valid UUID happy path -> `200`

## 7) Frontend 보강
- UUID 유틸:
  - `frontend/src/utils/uuid.ts`
- UI/요청 전 검증:
  - `frontend/src/App.tsx`
  - URL `session_id` 및 스트림 `message_id` 사전 검증
  - 400/422/403/404 상태별 사용자 메시지 분기

## 8) 실행 검증 결과
- Backend:
  - `backend\\gradlew.bat test --no-daemon` -> **PASS**
  - `backend\\gradlew.bat check --no-daemon` -> **PASS** (`lintUuidMapperParams` 포함)
- Provider regression:
  - `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1` -> **PASS**
- Frontend:
  - `frontend\\npm run build` -> **PASS**

## 9) 리스크/트레이드오프
- 장점:
  - SQL CAST 의존 제거로 쿼리 가독성 및 유지보수성 향상
  - 사람 기억이 아닌 정적 검사/빌드 게이트로 UUID 규칙 강제
  - 테넌트 혼선 시 403, 미존재 시 404로 장애 원인 분리 용이
- 트레이드오프:
  - `UUIDTypeHandler` 도입으로 MyBatis 설정 의존성이 명확해짐(대신 일관성 확보)
  - 회귀 방지 스크립트 유지보수가 필요(allowlist 관리 필요)

## 10) 확장 체크리스트 (새 Mapper 추가 시)
1. Mapper 파라미터가 DB UUID 컬럼이면 `String`이 아닌 `UUID`를 사용한다.
2. XML에서 `CAST(#{...} AS UUID)`를 추가하지 않는다.
3. 컨트롤러 경계에서 `UuidParser.parseRequired(...)`로 검증한다.
4. 서비스는 `UUID`만 받도록 시그니처를 유지한다.
5. `python scripts/lint_uuid_params.py` 및 `gradlew test/check`를 통과시킨다.
