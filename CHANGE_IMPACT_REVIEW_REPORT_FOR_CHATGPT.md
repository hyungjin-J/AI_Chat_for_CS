# 변경 영향 점검 보고서 (ChatGPT 공유용)

- 작성일: 2026-02-20
- 대상 프로젝트: `AI_Chatbot`
- 점검 목적:
  - 최근 다수 파일 변경이 프로젝트 전체 진행에 부정적 영향을 주는지 점검
  - 회귀 이슈(`uuid = character varying`) 해소 여부 확인

## 1) 결론 요약

- 현재 기준 **치명적(Critical)/높음(High) 영향 이슈는 발견되지 않음**.
- 초기 회귀 실패 원인이었던 UUID 타입 충돌은 관련 Mapper/Repository 보강으로 해소됨.
- 핵심 검증 결과:
  - Backend 테스트: PASS
  - Provider 회귀(`run_provider_regression.ps1`): PASS
  - Frontend 빌드: PASS

## 2) 변경 범위 요약

총 25개 파일 변경.

- 모델 기본값/운영 문서/회귀 스크립트
  - `backend/src/main/java/com/aichatbot/global/config/AppProperties.java`
  - `backend/src/main/resources/application.properties`
  - `docs/ops/OLLAMA_SETUP.md`
  - `scripts/run_provider_regression.ps1`

- UUID 타입 정합성 보강 (MyBatis Mapper/Repository)
  - Auth: Mapper 인터페이스/Repository/XML
  - Session(Conversation): Mapper 인터페이스/Repository/XML
  - Message: Mapper 인터페이스/Repository/XML
  - Stream Event: Mapper 인터페이스/Repository/XML
  - RAG(KB Search / Search Log / Citation): Mapper 인터페이스/Repository/XML

## 3) 핵심 이슈 및 조치

### 3.1 원인

- PostgreSQL UUID 컬럼에 String 파라미터가 바인딩되어 아래 오류 발생:
  - `operator does not exist: uuid = character varying`
  - `column "id" is of type uuid but expression is of type character varying`

### 3.2 조치

- Mapper 인터페이스 파라미터를 `String`에서 `UUID`로 전환.
- Repository 레이어에서 `toString()` 전달을 제거하고 UUID 객체 전달.
- XML SQL에서 UUID 컬럼 비교/INSERT에 `CAST(#{...} AS UUID)` 적용.
- Provider 회귀 스크립트에 `session_id`, `message_id` 미생성 시 즉시 실패 처리 추가.

## 4) 검증 내역

### 4.1 Backend

- 명령:
  - `cd backend; .\gradlew.bat test --no-daemon`
- 결과: PASS

### 4.2 Provider 회귀

- 명령:
  - `powershell -ExecutionPolicy Bypass -File scripts/run_provider_regression.ps1`
- 결과: PASS
- 증빙:
  - `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log`
  - 최신 상태: `status=PASS`, `normal_has_citation=true`, `fail_has_safe_response=true`

### 4.3 Frontend

- 명령:
  - `cd frontend; npm run build`
- 결과: PASS

### 4.4 정적 점검 (Mapper ID 파라미터)

- 점검:
  - Mapper 인터페이스에서 `@Param("...id") String` 패턴 탐색
- 결과:
  - UUID 컬럼 대상 ID 파라미터의 String 사용 사례는 제거됨
  - 예외 1건(`loginId`)은 계정 식별자 문자열 컬럼으로 정상

## 5) 부정적 영향 관점 리스크 평가

### 5.1 현재 잔여 리스크 (낮음)

1. PostgreSQL 의존도 증가
- 현재 SQL이 `CAST(... AS UUID)`를 사용하므로 DB 벤더 독립성은 낮아짐.
- 단, 본 프로젝트 표준 DB가 PostgreSQL이므로 운영 리스크는 낮음.

2. Mapper UUID 정합성의 지속 관리 필요
- 이번 수정 범위 밖 신규 Mapper가 String UUID를 다시 도입하면 유사 회귀 가능.
- 예방을 위한 정적 점검/리뷰 규칙 강화 권장.

## 6) 권장 후속 액션

1. CI에 UUID 타입 정합성 린트 추가
- 예: Mapper 인터페이스의 `*Id` 파라미터 String 사용 탐지 규칙.

2. E2E 회귀 경로 고정
- `login -> session create -> message -> stream` 경로를 CI 상시 검증.

3. 운영 문서 최신화 유지
- `docs/ops/OLLAMA_SETUP.md`의 최근 검증 메모는 현재 PASS 기준으로 갱신 완료.

## 7) ChatGPT 공유용 한 줄 요약

- "UUID/String 바인딩 불일치로 발생하던 PostgreSQL 타입 충돌을 Mapper/Repository/XML 전반에서 정합화하여 해결했고, backend test + provider regression + frontend build 재검증까지 PASS 확인됨."
