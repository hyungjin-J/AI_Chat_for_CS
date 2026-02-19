# MyBatis 리팩토링 통합 진행 보고서 (ChatGPT 공유용)

- 작성 시각: 2026-02-19 20:11:05 +09:00
- 기준 커밋: `de7be6f` (working tree)
- 프로젝트 루트: `C:\Users\hjjmj\OneDrive\바탕 화면\AI_Chatbot`

## 1) 작업 목표

- JDBC 기반 DB 접근 코드를 MyBatis(Mapper + XML) 기반으로 전환
- 기존 동작(쿼리 결과/예외/트랜잭션 경계) 보존
- AGENTS.md 6.8 DoD 기준 충족
  - JDBC 직접 사용 0건
  - MyBatis `${}` 0건

## 2) 핵심 변경 요약

### 2.1 인프라/설정

- `backend/build.gradle`
  - `spring-boot-starter-jdbc` 제거
  - `org.mybatis.spring.boot:mybatis-spring-boot-starter:3.0.4` 추가
- `backend/src/main/resources/application.properties`
  - `mybatis.mapper-locations=classpath:mappers/**/*.xml`
  - `mybatis.type-aliases-package=com.aichatbot`
  - `mybatis.configuration.map-underscore-to-camel-case=true`
- `backend/src/main/java/com/aichatbot/BackendApplication.java`
  - `@MapperScan(basePackages = "com.aichatbot")` 추가

### 2.2 JDBC Repository -> MyBatis Mapper 전환

- 전환 대상(기존 JDBC 사용 7개)
  - `AuthRepository`
  - `ConversationRepository`
  - `MessageRepository`
  - `StreamEventRepository`
  - `CitationRepository`
  - `RagSearchLogRepository`
  - `TenantResolverRepository`
- 방식
  - Repository의 public 메서드 계약은 유지
  - 내부 구현만 Mapper 인터페이스 + XML 호출로 교체
  - SQL은 우선 1:1 이전(행동 보존)

### 2.3 신규 추가 파일(주요)

- Mapper 인터페이스
  - `backend/src/main/java/com/aichatbot/auth/domain/mapper/AuthMapper.java`
  - `backend/src/main/java/com/aichatbot/session/domain/mapper/ConversationMapper.java`
  - `backend/src/main/java/com/aichatbot/message/domain/mapper/MessageMapper.java`
  - `backend/src/main/java/com/aichatbot/message/domain/mapper/StreamEventMapper.java`
  - `backend/src/main/java/com/aichatbot/rag/domain/mapper/CitationMapper.java`
  - `backend/src/main/java/com/aichatbot/rag/domain/mapper/RagSearchLogMapper.java`
  - `backend/src/main/java/com/aichatbot/global/tenant/domain/mapper/TenantResolverMapper.java`
- Mapper XML
  - `backend/src/main/resources/mappers/auth/AuthMapper.xml`
  - `backend/src/main/resources/mappers/session/ConversationMapper.xml`
  - `backend/src/main/resources/mappers/message/MessageMapper.xml`
  - `backend/src/main/resources/mappers/message/StreamEventMapper.xml`
  - `backend/src/main/resources/mappers/rag/CitationMapper.xml`
  - `backend/src/main/resources/mappers/rag/RagSearchLogMapper.xml`
  - `backend/src/main/resources/mappers/global/tenant/TenantResolverMapper.xml`
- Row/Projection 보조 모델
  - `backend/src/main/java/com/aichatbot/auth/domain/AuthUserProjection.java`
  - `backend/src/main/java/com/aichatbot/session/infrastructure/ConversationRow.java`
  - `backend/src/main/java/com/aichatbot/message/infrastructure/MessageRow.java`
  - `backend/src/main/java/com/aichatbot/rag/infrastructure/CitationRow.java`

## 3) JDBC -> Mapper 매핑표

- `AuthRepository.findActiveUserByTenantAndLoginId` -> `AuthMapper.findActiveUserByTenantAndLoginId`
- `AuthRepository.findActiveUserById` -> `AuthMapper.findActiveUserById`
- `AuthRepository.findRolesByUserId` -> `AuthMapper.findRolesByUserId`
- `AuthRepository.saveAuthSession` -> `AuthMapper.saveAuthSession`
- `AuthRepository.existsValidSessionByTokenHash` -> `AuthMapper.countValidSessionByTokenHash`
- `AuthRepository.deleteSessionByTokenHash` -> `AuthMapper.deleteSessionByTokenHash`
- `ConversationRepository.create` -> `ConversationMapper.create`
- `ConversationRepository.findById` -> `ConversationMapper.findById`
- `ConversationRepository.estimateSessionTokenUsage` -> `ConversationMapper.estimateSessionTokenUsage`
- `MessageRepository.create` -> `MessageMapper.create`
- `MessageRepository.findById` -> `MessageMapper.findById`
- `MessageRepository.findByConversation` -> `MessageMapper.findByConversation`
- `StreamEventRepository.save` -> `StreamEventMapper.save`
- `StreamEventRepository.findByMessageFromSeq` -> `StreamEventMapper.findByMessageFromSeq`
- `CitationRepository.save` -> `CitationMapper.save`
- `CitationRepository.findByMessageId` -> `CitationMapper.findByMessageId`
- `RagSearchLogRepository.save` -> `RagSearchLogMapper.save`
- `TenantResolverRepository.findTenantIdByKey` -> `TenantResolverMapper.findTenantIdByKey`

## 4) 보안/테넌트/동작 보존 포인트

- `${}` 미사용, `#{}` 바인딩만 사용
- 기존 tenant 조건(기존 쿼리의 `tenant_id`/tenant 관련 필터) 유지
- 서비스 계층 트랜잭션 경계는 변경하지 않음
- 기존 에러/응답 규약, trace_id 흐름을 깨지 않도록 Repository 계약 유지

## 5) 검증 결과 (최신)

### 5.1 테스트

- 실행 명령: `backend` 디렉터리에서 `./gradlew test`
- 결과: `BUILD SUCCESSFUL`
- 로그 요약: `test UP-TO-DATE` (전체 테스트 통과 상태 유지)

### 5.2 DoD 검색 검증

- JDBC 직접 사용 검색:
  - 명령: `rg -n "JdbcTemplate|NamedParameterJdbcTemplate|DriverManager|PreparedStatement|ResultSet|import\\s+java\\.sql" -S backend/src/main backend/src/test`
  - 결과: 매치 없음 (0건)
- MyBatis `${}` 검색:
  - 명령: `rg -n "\\$\\{" -S backend/src/main/resources/mappers`
  - 결과: 매치 없음 (0건)

## 6) 문서/Notion 동기화 상태

- 스펙 문서 정합성 업데이트:
  - `docs/references/Development environment.csv`
    - `Spring Data JPA (Hibernate)` -> `MyBatis (mybatis-spring-boot-starter)`로 정합화
- 동기화 보고:
  - `spec_sync_report.md` 업데이트 완료
- Notion 반영:
  - 대상 페이지: `https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7`
  - 반영 완료 항목:
    - Last synced at
    - Source file
    - Version
    - Change summary

## 7) 현재 상태/다음 액션

- 코드/설정/스펙/Notion까지 이번 MyBatis 리팩토링 범위 반영 완료
- 커밋 전 최종 점검 권장:
  - `git diff` 리뷰
  - `./gradlew test` 1회 재확인
  - Notion 메타 값(시간/버전) 최종 확인
