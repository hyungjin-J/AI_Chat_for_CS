# AGENTS.md — AI_Chatbot 프로젝트 전역 규칙 (Global Rules)

> **적용 범위**: 이 파일은 `AI_Chatbot` 저장소(프로젝트 루트)에 위치하며, 이 저장소에서 작업하는 **모든 AI 코딩 에이전트(Codex, Cursor, Claude 등)** 에게 동일하게 적용됩니다.  
> **프로젝트 루트(사용자 기준)**: `C:\Users\hjjmj\OneDrive\바탕 화면\AI_Chatbot`
> **DB 접근 표준**: 본 프로젝트의 DB 접근은 **MyBatis 기반으로 통일**한다(아래 6.8 참조).


---

## 1) 프로젝트 북극성(필수 인지)

### 1.1 한 줄 요약
고객센터 상담원이 **근거 기반(RAG)** 으로 빠르고 안전하게 답변을 작성/검수/전송할 수 있도록 돕는 **CS 서포팅 AI 챗봇**을 구현한다.

### 1.2 성공 조건(절대 기준)
- **근거 없는 답변을 사용자에게 노출하지 않는다**(Answer Contract + citations + evidence threshold, fail-closed).
- **PII(개인정보)** 는 입력/메모리/캐시/로그/응답 모든 경로에서 **마스킹 또는 제외**된다.
- 운영에서 **trace_id 하나로** “요청 → 검색 → 도구 → 모델 → 응답(스트리밍)”을 끝까지 추적 가능해야 한다.
- **RBAC/테넌트 격리**는 언제나 서버가 최종 권위(source of truth)다.
- 프로덕션 SLO를 지키지 못할 때는 **자유 텍스트로 땜질하지 말고 안전 응답(safe_response)으로 실패**한다.

---

## 2) ‘소스 오브 트루스’(스펙 파일) — 반드시 준수

> 아래 파일들은 구현의 기준선입니다. **코드/테스트/문서가 스펙과 충돌하면 “코드가 틀린 것”** 으로 간주합니다.

### 2.1 스펙 변경 규칙(문서 무결성)
- 스펙 파일의 컬럼/시트 구조는 **임의로 바꾸지 않는다**(자동화/문서화 파이프라인이 깨질 수 있음).
- 스펙을 바꿨다면, 같은 PR/커밋에서 **구현/테스트도 함께** 업데이트한다.
- 요구사항ID(예: `API-003`, `AI-009`, `TMP-001`)는 **추적성(tracing)** 을 위해 유지한다.
- ReqID(요구사항ID) 마스터(단일 진실원천)는 `CS AI Chatbot_Requirements Statement.csv`로 고정한다.
  - 다른 스펙/문서는 **Requirements에 존재하는 ReqID만 참조**해야 한다.
  - 새로운 ReqID가 필요하면 “먼저 Requirements에 등록 → 나머지 문서 반영” 순서를 지킨다.
- API 워크북(`google_ready_api_spec...xlsx`)은 **_guide의 규칙을 따른다**:  
  - API 행 편집은 **`전체API목록` 시트에서만** 수행한다.  
  - 카테고리별 시트/프로그램ID 목록 시트는 수동 편집 금지(자동 동기화 영역).  
  - 수식/드롭다운/자동 생성 셀을 덮어쓰지 않는다.

### 2.2 레퍼런스 문서 변경 시 Notion 동기화 의무 (필수)

#### 목적
레퍼런스 스펙 파일(CSV/XLSX)과 Notion 문서가 분기되면, 요구사항/추적성/구현이 즉시 깨진다.  
따라서 아래 파일 중 하나라도 수정하면, 해당 내용을 담고 있는 Notion 페이지도 **같은 작업 흐름(같은 PR/커밋/작업 세션)에서 즉시 업데이트**해야 한다.  
(자동화 가능하면 자동화, 자동화가 어렵다면 “변경 요약 + 표/DB 업데이트 + 최신 파일 첨부”까지 수행)

#### 동기화 대상 매핑(파일 ↔ Notion)
- `Summary of key features.csv`
  - https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149
- `CS AI Chatbot_Requirements Statement.csv`
  - https://www.notion.so/2ed405a3a720816594e4dc34972174ec
- `Development environment.csv`
  - https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7
- `google_ready_api_spec_v0.3_20260216.xlsx`
  - https://www.notion.so/2ed405a3a720816594e4dc34972174ec
  - ※ Requirements 페이지와 동일 링크일 수 있음. 페이지 내부에 “API Spec” 섹션/토글을 분리해 관리한다.
- `CS_AI_CHATBOT_DB.xlsx`
  - https://www.notion.so/2ed405a3a720812180d9d508b77f31a4
- `CS_RAG_UI_UX_설계서.xlsx`
  - https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444
  - ※ 이미지 업로드/등록 시도 금지
  - ※ 각 시트별로 제목 토글로 나누어 작성
  - ※ 필요 시 Notion DB 적용 가능(단 토글 구조 유지)

#### Notion 페이지 메타데이터(권장 → 운영상 사실상 필수)
Notion 각 페이지 상단에 아래 정보를 유지하여 “최신/동기화 여부”를 사람이 즉시 판단할 수 있어야 한다.
- `Last synced at` (날짜/시간)
- `Source file` (파일명)
- `Version` 또는 `Git commit/tag`
- `Change summary` (핵심 변경 3~10줄)

#### 체크리스트(작업 종료 조건)
- (필수) 수정된 파일 내용이 Notion 페이지에 반영되었다.
- (필수) Notion 페이지 상단 메타(`Last synced at / Source file / Version(or commit)`)가 갱신되었다.
- (권장) 변경 요약과 TBD(근거 부족 항목)가 명확히 기록되었다.

---

### 2.2-A Notion 동기화 미이행 시 실패 처리 규칙 (강제 집행 레이어)

⚠️ 이 규칙은 권고가 아니다. 집행 규칙이다.

#### 1. 실패 정의

다음 중 하나라도 충족하지 않으면 작업은 “실패(Failed)”로 간주한다.

- 스펙 파일(.csv / .xlsx)이 변경되었으나 해당 Notion 페이지가 업데이트되지 않은 경우
- Notion 페이지 상단 메타 정보가 갱신되지 않은 경우
  - Last synced at
  - Source file
  - Version 또는 commit
  - Change summary
- spec_sync_report.md에 Notion 반영 내역이 기록되지 않은 경우

위 조건 중 하나라도 누락되면:

→ 작업 미완료  
→ PR 병합 금지  
→ 배포 금지  
→ 재작업 대상  

---

#### 2. Definition of Done(DoD) 재정의

스펙 파일이 변경된 작업은 다음을 모두 만족해야 “완료”로 인정한다:

- [ ] 로컬 스펙 파일 수정 완료
- [ ] 해당 Notion 페이지 동기화 완료
- [ ] Notion 메타 정보 갱신 완료
- [ ] spec_sync_report.md 작성 완료

이 네 가지가 모두 충족되지 않으면 작업 완료로 인정하지 않는다.

---

#### 3. 자동 검증 권장(강력 권고)

가능한 경우 다음을 자동화한다:

- Git diff에서 .csv/.xlsx 변경 감지
- spec_sync_report.md 존재 여부 확인
- 커밋 메시지 또는 PR 템플릿에 Notion 동기화 체크 항목 포함

자동 검증 실패 시:
→ CI 실패 처리
→ 병합 차단

---

#### 4. 예외 규정 없음

“이번만 예외”, “단순 오타 수정” 등은 예외 사유가 되지 않는다.  
스펙 파일이 변경된 모든 경우 Notion 동기화는 필수이다.

### 2.2-B Notion 동기화 자동화 (Codex + MCP) — CI 표준 (권장 → 운영상 사실상 필수)

#### 목적
스펙/운영 문서 변경 → Notion 반영을 사람 기억에 의존하면 누락/분기가 발생한다.  
따라서 동기화는 **Codex + MCP로 자동 실행**하는 것을 표준으로 한다(가능한 경우 수동 금지 수준).

#### 핵심 원칙 (Fail-Closed 유지)
- 2.2-A의 실패 정의/DoD/예외 없음 규칙은 자동화에도 그대로 적용된다.
- 동기화 대상 변경이 감지되면 CI에서 `codex exec`로 Notion 동기화를 실행한다.
- Notion MCP 초기화 실패 또는 동기화 실패 시: **CI 실패 처리 → 병합/배포 금지**.
- Notion은 “단일 진실원천”이 아니다. 진실원천은 레포의 스펙/문서 파일이며, Notion은 가시화 레이어다.

#### Codex MCP 구성 (필수)
Codex MCP 설정은 `~/.codex/config.toml` 또는 프로젝트 `.codex/config.toml`로 구성할 수 있다.  
CI에서는 `~/.codex/config.toml`을 런타임에 생성하여 사용한다.

**(필수) 네트워크 설정**
Codex 기본 sandbox에서는 네트워크가 꺼져 있으므로, workspace-write에서 네트워크를 명시적으로 허용해야 한다.
```toml
approval_policy = "never"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
```

**(필수) Notion MCP fail-closed**
- CI에서는 `required = true`를 사용하여 Notion MCP 초기화 실패 시 즉시 작업을 실패 처리한다.
- Notion은 Hosted MCP(OAuth)를 제공하며, CI는 일반적으로 `npx -y @notionhq/notion-mcp-server` + `NOTION_TOKEN` 조합을 사용한다.

```toml
[mcp_servers.notion]
command = "npx"
args = ["-y", "@notionhq/notion-mcp-server@2.1.0"]
env_vars = ["NOTION_TOKEN"]
required = true
```

#### CI 실행 표준
- Codex CLI는 버전 고정을 위해 `@openai/codex@0.101.0`을 사용한다.
- 동기화 대상이 변경된 PR에서 CI는 `codex exec`를 실행한다.
- 동기화 대상 변경이 없으면 CI는 안전하게 스킵한다.
- 동기화 대상 변경이 있는데 동기화가 실패하면 CI를 실패시켜 병합을 차단한다.

#### 비밀정보/토큰 정책 (강제)
- `NOTION_TOKEN`, `OPENAI_API_KEY` 등 시크릿은 저장소에 절대 커밋하지 않는다.
- 시크릿은 CI Secrets 또는 로컬 `.env`(gitignored)로만 주입한다.

#### 자동화 마커 (멱등성)
- Notion 페이지 자동 동기화 블록은 `[[AUTO_SYNC:...]]` 마커로 식별한다.
- `spec_sync_report.md`에도 커밋/동기화 키 기반 마커를 남겨 재실행 시 중복 반영을 방지한다.

### 2.3 스펙 정합성 자동 검증(권장)
스펙 간 정합성은 사람 점검만으로는 회귀(regression)되기 쉽다. 가능하면 아래 검증을 자동화한다(예: `spec_consistency_check.py`).

**최소 체크(권장)**
- Summary/DevEnv/API Spec/UIUX가 참조하는 모든 ReqID가 Requirements에 존재
- API Spec의 `비고(ReqID:)` 목록 오타/누락 없음
- 표준 용어(예: `secret_ref`, ROLE, SSE 이벤트 타입)가 문서/스펙에 일관되게 사용
- UIUX “미매핑 처분”에 placeholder(예: `-`, 공백 key)가 남지 않음

---

## 3) 모듈/스택 개요 (Development environment 기준)

### 3.1 Backend (Spring Boot / Java)
- Java **17.0.16**, Spring Boot **3.x**
- Spring Web(MVC) 또는 WebFlux(스트리밍 요구 고려)
- Spring Security(JWT + RBAC)
- **MyBatis (mybatis-spring-boot-starter) — DB 접근 표준**
- PostgreSQL 16+ (+ pgvector 선택), Redis(운영 필수/개발 선택)
- Micrometer / OpenTelemetry(관측), Resilience4j(재시도/서킷)
- Spring AI(도구 호출/오케스트레이션), (선택) OpenSearch/Elasticsearch(하이브리드 검색)

### 3.2 Frontend (React / TypeScript)
- Node.js **22 LTS**, React **18**, TypeScript **5**, Vite **5**
- SSE Client(EventSource/Fetch stream), Axios(or fetch wrapper)
- 상태 관리(Zustand/Redux Toolkit), UI 프레임워크(MUI/Ant Design 등)

### 3.3 Data/AI 구성요소
- 문서 파싱: Apache Tika, (선택) Tesseract OCR
- 임베딩 모델(예: bge-m3 등), (선택) Reranker
- LLM: Ollama(로컬) + 외부 API Provider(선택) **이중 지원**
- Answer Contract: JSON Schema validation/repair + citations 강제
- RAG 평가/회귀 테스트(운영 필수 권장)

### 3.4 로컬 개발 빠른 시작(에이전트용)

> **원칙**: 저장소에 이미 존재하는 스크립트/Makefile/README가 있으면 그것을 1순위로 따른다.  
> 아래는 “자동 탐지 기반” 기본 규칙이며, 레포의 실제 도구(Gradle/Maven, pnpm/npm/yarn)에 맞춰 선택한다.

- **Infra (권장: Docker Compose)**
  - `docker compose up -d` (Postgres/Redis/OpenSearch 등)
  - `docker compose logs -f` 로 부팅/헬스체크 확인
- **Backend**
  - Gradle Wrapper가 있으면: `./gradlew test`, `./gradlew bootRun`
  - Maven Wrapper가 있으면: `./mvnw test`, `./mvnw spring-boot:run`
- **Frontend**
  - `pnpm-lock.yaml` 있으면: `pnpm install`, `pnpm dev`, `pnpm test`
  - `package-lock.json` 있으면: `npm ci`, `npm run dev`, `npm test`
  - `yarn.lock` 있으면: `yarn install --frozen-lockfile`, `yarn dev`, `yarn test`
- **기본 헬스체크**
  - API: `/health` 또는 Actuator endpoint(레포 설정에 따름)
  - DB/Redis 연결 및 마이그레이션 적용 여부 확인
  - SSE 스트리밍 연결(프론트에서 first-token 시간 확인)

**환경변수/시크릿 원칙**
- 시크릿/토큰/키는 **레포에 평문으로 커밋 금지**.
- 로컬은 `.env`(gitignore) 또는 Docker secret, 운영은 Vault/KMS 참조를 기본으로 한다.
- 테넌트/채널/권한 테스트를 위해 최소한 아래 값들이 외부 주입 가능해야 한다(이름은 레포 기준):
  - DB URL/USER/PASSWORD, Redis URL
  - JWT signing key(또는 key alias)
  - LLM provider 설정(Ollama base URL, External provider key alias)
  - 관측(OTel exporter endpoint) / 로그 파이프라인 설정

---

## 4) 절대 규칙(Non-negotiables) — 위반 시 “버그”

### 4.1 Answer Contract / Fail-Closed
- 사용자에게 노출되는 답변은 **항상 검증 가능한 구조화 결과**여야 한다.
- 다음 상황은 **자유 텍스트로 대체 금지**이며, 반드시 **차단(fail-closed)** 또는 **safe_response**:
  - 스키마 검증 실패
  - 인용(citation) 누락
  - 근거(evidence) 임계치 미달
  - 정책(금지/필수 문구) 위반
- 허용되는 안전 응답은 제한적이어야 한다(예: “확인 필요/모름/추가 질문”).

### 4.2 PII(개인정보) — 입력/로그/캐시 전 구간 차단
- 전화/이메일/주소/주문번호 등 PII는:
  - **LLM 입력 전 마스킹/제거**
  - **로그 저장 전 마스킹**
  - **세션 요약/semantic cache에 저장 금지(PII excluded)**
- 비밀키/토큰/내부 식별자는 **ToolContext 등 비공개 컨텍스트**로만 전달(모델 입력에 포함 금지).

### 4.3 trace_id 전파 100% (관측/감사)
- 모든 요청은 `X-Trace-Id`(또는 서버 생성 trace_id)로 시작하여,
  `session_id`, `message_id` 등과 함께 **전 구간 전파**한다.
- trace_id 누락 이벤트는 **저장 차단 + 경보** 대상이다(배포 게이트).

### 4.4 테넌트 격리 / RBAC
- `X-Tenant-Key` 기준으로 정책/스킨/지식베이스/캐시를 완전히 분리한다.
- 권한(role)은 **서버에서 최종 검증**한다(UI는 보조).
- ROLE 표준: `AGENT`, `CUSTOMER`, `ADMIN`, `OPS`, `SYSTEM`
  - `Manager`, `System Admin` 같은 표현은 “ROLE”이 아니라 `ADMIN` 내부의 **권한 레벨(permissions)** 로 문서/기능에서 표기한다.
- 권한 없는 호출은 403. 권한 변경 시 활성 세션 권한 재평가.

### 4.5 예산(Budget) & Abuse Defense
- 입력/출력 토큰, tool call 횟수, TopK, 세션 누적 예산, SSE 동시 연결 상한을 **사용자/테넌트 단위로 강제**한다.
- 초과 시 429(또는 정책에 따라 403) + 일관된 rate-limit 헤더 제공.
- 우회 시도는 감사 로그에 남기고 즉시 차단 가능해야 한다.

### 4.6 승인/버전 기반 운영(템플릿/정책/모델)
- “승인된(approved) 버전만” 운영 경로에서 사용한다.
- 장애/품질 저하 시 **즉시 롤백**할 수 있어야 한다(활성 버전 관리).

---

## 5) 공통 코딩 컨벤션 (전 스택 공통)

### 5.1 기본 포맷
- 들여쓰기: **Space 4칸**, 탭 금지
- 한 줄 길이: 가급적 **100자 내외**, 120자 하드 제한(언어별 포매터가 있다면 그 설정을 따른다)
- 조건문/반복문: 한 줄이라도 **중괄호/블록을 생략하지 않는다**
- 주석: “무엇(What)”보다 **“왜(Why)”** 를 설명한다(특히 정책/예외/보안/성능의 이유).

### 5.2 네이밍(요약)
- “의미 없는 이름(a, b, data1)” 금지.  
- 도메인 언어를 사용한다(예: `tenantKey`, `traceId`, `answerContract`, `evidenceSet`).

### 5.3 에러 처리 / 응답 규약(필수)
- 에러는 반드시 표준 형태로 통일한다(예시는 아래).
- 에러코드는 “문서화된 코드만” 사용한다(API-007 규칙).

**권장 표준 에러 응답(JSON)**
```json
{
  "error_code": "SYS-003-XXX",
  "message": "human readable message",
  "trace_id": "uuid",
  "details": []
}
```

---

## 6) Backend 컨벤션 (Java / Spring Boot)

### 6.1 패키지/레이어 구조(권장)
루트 패키지(예): `com.aichatbot`

도메인 기준 패키지 분리 + 글로벌 공통 영역 분리

예시:
```
com.aichatbot
├─ global
│  ├─ config
│  ├─ security
│  ├─ error
│  ├─ observability
│  └─ util
├─ auth
├─ session
├─ message
├─ rag
├─ knowledgebase
├─ template
├─ admin
└─ ops
```

**레이어 원칙:**
- `Controller`: 요청 검증/매핑/권한 체크/trace 컨텍스트 설정까지만(Thin)
- `Service`: 비즈니스 로직(단, 너무 비대해지면 도메인 서비스로 분해)
- `Repository/DAO`: 영속화/조회
- `DTO/VO`: 외부 계약(API)과 내부 모델을 명확히 분리

### 6.2 네이밍 규칙
- 변수/메서드: `camelCase`
- 클래스/레코드: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- 패키지: `lower-case`

### 6.3 API 구현 규칙(워크북 준수)
Endpoint/Method/Role/Request/Response는 `google_ready_api_spec...xlsx`의 `전체API목록` 을 1순위 기준으로 구현한다.

**공통 헤더(대표):**
- `X-Trace-Id`: `<uuid>`
- `X-Tenant-Key`: `<tenant_key>`
- `Idempotency-Key`: `<uuid>` (POST/재시도 가능 요청)
- 인증 필요 시 `Authorization`: `Bearer <access_token>`

JSON 필드 네이밍: `snake_case` 를 기본으로 한다(예: `session_id`, `message_id`, `top_k`).

Java DTO/record는 `camelCase`로 작성하되, Jackson naming strategy(예: SnakeCase)로 직렬화/역직렬화를 통일한다.

### 6.4 Idempotency(필수)
- `Idempotency-Key` + (가능하다면) `client_nonce` 기반으로 중복 요청을 안전하게 처리한다.
- 재시도에 대해 “중복 처리”가 발생하지 않게 저장/락/캐시 전략을 갖춘다.

### 6.5 데이터베이스(PostgreSQL) 규칙(권장)
- 마이그레이션: Flyway/Liquibase 중 하나로 버전 관리
- 테이블/컬럼: 기본은 `snake_case`(Postgres 관례)
  - 예: `tb_session`, `tb_message`, `created_at`, `updated_at`
- 공통 컬럼(권장): `created_at`, `updated_at`, `created_by`, `updated_by`, `tenant_key`
- PII 컬럼은 암호화/마스킹 정책을 명확히 하고, 로그로 평문이 새지 않게 한다.
**추가 원칙(필수):**
- DB 접근은 **MyBatis Mapper 계층을 통해서만** 수행한다(6.8 참조).
- `tenant_key`는 모든 조회/변경 쿼리에서 누락되면 보안 결함으로 간주한다(테넌트 격리 4.4와 동일 레벨).

### 6.6 관측(Observability) 구현 규칙
로그는 가급적 JSON 구조화 로그로 남기고, 최소 포함 필드:
- `trace_id`, `tenant_key`, `session_id`, `message_id`, `user_role`, `event_type`, `latency_ms`

OpenTelemetry/Micrometer로:
- API latency, SSE first-token latency, tool call latency
- fail-closed block count, answer_contract pass rate
- rate limited / quota exceeded count

### 6.7 안정성(Resilience)
외부 LLM/검색/스토리지 호출:
- timeout, retry(지수 백오프), circuit breaker 적용
- 단, 실패 시 자유 텍스트로 우회 금지(안전 응답/에러코드로 종료)

### 6.8 Data Access 표준 — MyBatis 강제 (필수)
> 목적: JDBC 직접 사용을 제거하고, 일관된 데이터 접근/트랜잭션/보안 규칙을 강제한다.

#### 6.8.1 금지 사항(Non-negotiables)
- **JDBC 직접 사용 금지**: `DriverManager`, `Connection`, `PreparedStatement`, `ResultSet`, `JdbcTemplate`, `NamedParameterJdbcTemplate` 등 사용 금지.
- **문자열 치환 기반 동적 SQL 금지**: MyBatis에서 `${}` 사용 금지. 기본은 `#{}`로만 바인딩한다.
- 예외가 필요하면 “왜 필요한지(Why) + 입력 검증 + 화이트리스트”를 코드/리뷰에 남기고, 보안 위험을 제거한다.

#### 6.8.2 표준 구조/위치 규칙
- Mapper 인터페이스: `src/main/java/**/domain/**/mapper/*Mapper.java` (도메인 기준 패키지 내부 권장)
- Mapper XML: `src/main/resources/mappers/**/**/*Mapper.xml`
- XML namespace는 Mapper 인터페이스 FQCN(완전한 클래스명)으로 통일한다.

#### 6.8.3 네이밍/SQL 작성 규칙
- SQL id는 메서드명과 1:1 매핑한다.
- `resultMap`을 적극 사용하여 컬럼↔필드 매핑을 명시한다(복잡 조인/중첩 결과는 특히 필수).
- 페이징/정렬은 파라미터 바인딩으로만 처리하며, 정렬 컬럼이 동적이면 반드시 화이트리스트로 제한한다.

#### 6.8.4 트랜잭션 경계
- 트랜잭션 경계는 **Service 계층(@Transactional)** 을 원칙으로 한다.
- Mapper/DAO는 트랜잭션을 “생성”하지 않으며, 기존 트랜잭션 컨텍스트에 참여한다.

#### 6.8.5 테넌트/RBAC/감사 연동(필수)
- 모든 쿼리는 `tenant_key` 조건을 포함한다(조회/수정/삭제 동일).
- 감사/추적이 필요한 변경 쿼리는 `trace_id`와 연계 가능한 형태(서비스 레이어에서 이벤트/로그)를 유지한다.

#### 6.8.6 Definition of Done (DB 접근 리팩토링)
- [ ] 저장소 전체에서 JDBC 직접 사용이 **0건**이어야 한다(검색으로 증명).
- [ ] 모든 DB 접근이 MyBatis Mapper를 통해서만 수행된다.
- [ ] `${}` 사용이 **0건**이어야 한다(검색으로 증명).
- [ ] 주요 쿼리에서 `tenant_key` 필터 누락이 없다(샘플 점검 + 코드 리뷰 기준).

---

## 7) Frontend 컨벤션 (React / TypeScript)

### 7.1 기본 규칙
- TypeScript strict 지향(가능한 any 금지)
- 컴포넌트: `PascalCase.tsx`
- 훅: `useSomething.ts`
- 상태/비즈니스 로직은 UI 컴포넌트에서 분리(커스텀 훅/서비스 레이어)

**권장 구조:**
```
src/
├─ api/              # axios/fetch wrapper, interceptors
├─ features/         # 도메인 단위(채팅, 템플릿, KB, 어드민 등)
├─ components/       # 재사용 컴포넌트
├─ hooks/
├─ pages/
├─ store/
├─ styles/
└─ utils/
```

### 7.2 SSE 스트리밍 UX(필수)
스트리밍 이벤트는 서버 계약을 따른다:
- `token`, `tool`, `citation`, `done`, `error`, `heartbeat`, `safe_response`

네트워크 단절 시 자동 재연결 + Last-Event-ID/resume 처리(UI-005).
first-token을 빠르게 보여주되(목표 1~2s), 최종 응답은 Answer Contract를 만족해야 한다.

### 7.3 보안/PII
- 근거 패널/미리보기 HTML 렌더링 시 XSS 방지(예: DOMPurify).
- 클라이언트 로그/에러 리포팅(Sentry 등)에도 PII가 남지 않게 필터링한다.

### 7.4 UI/스타일(권장)
- CSS 네이밍: BEM + kebab-case
- 다크모드: CSS 변수 기반으로 토큰화(가능하면 `data-theme="dark"`)
- 기본 해상도: 1920×1080 (최소 1366×768), 모바일(≤768px)은 제한적 지원을 전제로 한다.
- 레이아웃 기본값(권장): Header(64px) + Sidebar(280px, 축소 시 64px) + Content(가변, padding 24px)
- 폰트(권장): Pretendard 우선(Title 24px/Bold, Body 14px/Regular)

**컬러 토큰(초기 권장값 — 필요 시 테넌트/스킨별 오버라이드)**

| Token | Hex | 용도 |
| :--- | :--- | :--- |
| Primary | #1e3a8a | 주요 버튼/헤더/선택 |
| Success | #059669 | 완료/승인/성공 |
| Warning | #d97706 | 경고/주의 |
| Error | #dc2626 | 실패/삭제/Danger |
| Info | #0284c7 | 안내/정보 |
| Background | #f6f8fc | 기본 배경(순수 흰색 지양) |
| Text | #0f172a | 본문 텍스트 |

**그리드(테이블) 기본 기능(어드민 화면 기준)**
- 필터링/정렬(라이브러리 기본 기능 활용)
- 컬럼 숨김/표시 토글
- 컬럼 리사이즈
- 컬럼 초기화(Reset) 액션

---

## 8) AI/RAG 구현 규칙 (핵심)

### 8.1 RAG 파이프라인(요약)
1. 입력 전처리/필터(PII/금칙어/길이 제한)
2. 의도 분류/라우팅(FAQ/RAG/Tool/Handoff)
3. 검색(벡터 + BM25 하이브리드 + 필터링)
4. (선택) rerank
5. 답변 생성(근거 포함)
6. Answer Contract 검증(스키마/인용/근거점수)
7. 통과 시만 사용자 노출, 실패 시 fail-closed 또는 safe_response

### 8.2 금지/필수 문구 정책(RAG-002)
- 카테고리별 정책 번들(필수/금지 문구)을 버전 관리하고 즉시 반영 가능해야 한다.
- 금지 표현이 발견되면 경고/재생성/차단 규칙을 적용한다.

### 8.3 템플릿 추천/치환(TMP-001~005)
- 템플릿 추천 도구는 기본 채팅 흐름에서 자동 실행 금지.
- 오직 UI 버튼 액션으로만 실행(쿨다운/세션 상한/예산 적용).
- placeholder 자동 채움 시:
  - 근거/질문/모델 출력에서 변수 추출
  - 미존재 변수는 빈칸/가이드로 남김
  - PII는 마스킹된 값만 치환
- 운영 사용 템플릿은 승인된 버전만.

### 8.4 캐시/가속(CCH-001, CCH-002)
- 승인 답변 은행(Answer Bank): 동일/유사 질문 반복 시 즉시 응답 경로 제공
- semantic cache + session summary memory:
  - PII 제외
  - TTL + invalidation 정책 필수

### 8.5 오프라인/배치/평가 스크립트(Python 등) 컨벤션(사용 시)
- 스타일: PEP 8 준수, 함수/변수 `snake_case`, 클래스 `PascalCase`, 상수 `UPPER_SNAKE_CASE`
- 타입: 가능한 한 타입 힌트 작성(특히 데이터 구조/모델 I/O)
- 재현성: 모델/임베딩/청킹 파라미터와 버전을 로그/리포트로 남기고, 랜덤 시드는 고정 가능하도록 한다.
- 데이터 취급: 원문/로그/캐시에 PII가 섞이지 않도록 마스킹/샘플링 규칙을 적용한다.
- 산출물: 평가 결과(precision/recall, citation coverage, policy violation rate 등)는 CSV/XLSX로 저장하되 스키마를 고정한다.

---

## 9) API / SSE 계약(Contract) — 구현/테스트에 포함

### 9.1 공통 헤더
- `X-Trace-Id`, `X-Tenant-Key`는 기본 필수(예외는 PUBLIC API만 최소화).
- `Idempotency-Key`는 재시도 가능한 POST에 적용.
- SSE는 `Last-Event-ID` 또는 `last_event_id`로 이어받기 지원.

### 9.2 SSE 이벤트 타입(최소)
- `token`: 토큰/청크 단위 출력
- `tool`: 도구 호출 상태/결과 요약(민감정보 제거)
- `citation`: 인용 근거 메타(문서ID/조항/버전/링크 등)
- `heartbeat`: 연결 유지
- `done`: 완료
- `error`: 표준 에러코드 포함
- `safe_response`: fail-closed 시 안전 응답

### 9.3 상태 코드 가이드(권장)
- `200 OK`: 정상 조회/스트림
- `201 Created` / `202 Accepted`: 비동기/큐잉 성격의 요청
- `401`/`403`: 인증/권한
- `409`/`422`: Answer Contract 실패 등 검증 에러
- `429`: rate-limit/quota/budget 초과

---

## 10) 테스트/품질 게이트(필수)

### 10.1 Backend
- Unit Test: JUnit5
- Integration Test: Testcontainers(Postgres/Redis/OpenSearch/Ollama 등)
- 최소 테스트:
  - Answer Contract 검증(통과/실패/fail-closed)
  - PII 마스킹(입력/로그/캐시)
  - rate-limit/budget (API-007)
  - trace_id 전파 누락 방지(SYS-004)
  - RBAC 매트릭스(SEC-002)

### 10.2 Frontend
- Vitest + React Testing Library
- 최소 테스트:
  - 스트리밍 렌더링 + 재연결(UI-004/UI-005)
  - 오류 상태 UX(UI-006)
  - 권한 가드(SEC-002)

### 10.3 RAG 회귀 테스트(권장 → 운영에서는 사실상 필수)
- 대표 시나리오/문서셋으로:
  - 인용 누락률
  - 정책 위반률(금지/필수 문구)
  - fail-closed 전환률
  - latency SLO(P95)

---

## 11) 문서/스프레드시트/PDF 등 산출물 작업 규칙 (Codex Skills 적용)
이 프로젝트는 “스펙 파일(표)”과 “운영 문서”의 비중이 큽니다. 에이전트는 코드뿐 아니라 문서 품질도 동일하게 책임집니다.

### 11.1 CSV/XLSX 편집 원칙
- 컬럼/시트 구조, 헤더명, 데이터 타입을 임의 변경 금지.
- 변경 시:
  - 관련 코드/테스트/문서 업데이트 동반
  - 스펙 내 요구사항ID/프로그램ID의 참조 무결성 유지
- API 워크북은 `_guide` 시트의 운영 규칙을 따른다.
- CSV 저장 규칙(권장): UTF-8, 구분자 `,`, 헤더 유지. (엑셀 호환이 필요하면 BOM 사용 여부는 팀 규칙에 따름)
- CSV의 컬럼명/순서/의미(스키마)는 “API/요구사항 추적성”의 일부이므로 임의 변경 금지.
- XLSX 편집 시: 수식/드롭다운/서식/시트명을 보존하고, 자동 생성 셀을 덮어쓰지 않는다.
- 수식이 있는 시트는 계산 오류(#REF!, #DIV/0! 등)가 없도록 확인하고, 엑셀 호환성이 낮은 동적 배열 함수(FILTER/XLOOKUP 등) 사용을 피한다.

### 11.2 DOCX/PDF 생성·수정(있을 경우)
문서는 “보이는 결과물”이 중요하므로, 렌더링 결과(레이아웃/표/폰트 깨짐)를 반드시 확인한다.
인용/링크/참조는 사람이 읽을 수 있는 형태로 유지한다(도구 내부 토큰 금지).

**DOCX 편집(권장):**
- 구조/스타일을 코드로 제어할 수 있는 도구(예: `python-docx`)를 사용해 재현 가능하게 수정한다.
- 큰 변경(섹션/표/스타일) 후에는 PDF로 렌더링하여 페이지 단위로 레이아웃을 검수한다(표 깨짐/줄바꿈/폰트 누락 방지).

**PDF 생성/수정(권장):**
- 코드로 생성 시(예: `reportlab`) 페이지 렌더링 이미지를 확인해 잘림/겹침/가독성 문제를 제거한다.

**산출물 품질 기준:**
- 깨진 표/겹치는 텍스트/잘린 요소/임시 문구(placeholder) 남김은 금지.

---

## 12) 에이전트 작업 방식(권장 워크플로우)

### 12.1 작업 시작 시
1. 변경하려는 기능의 요구사항ID(예: AI-009, API-003)를 먼저 확인한다.
2. API 변경이면 워크북 `전체API목록`에서 계약(요청/응답/권한)을 확인한다.
3. 설계/구현/테스트/문서 업데이트 범위를 짧게 계획한다.

### 12.2 작업 종료(Definition of Done)
- 스펙과 구현이 일치한다(요구사항ID 기준).
- 테스트가 통과한다(백엔드/프론트/회귀).
- PII/보안/trace_id/예산/정책 위반이 없다.
- 운영 관측(로그/메트릭/트레이스)이 누락 없이 남는다.
- 변경 사항이 문서화되어 다음 사람이 이해 가능하다.
- (스펙 수정 시 필수) Notion 동기화가 완료되지 않으면 작업 완료로 인정하지 않는다. (2.2-A 참조)

---

## 13) 자주 발생하는 실패 패턴(금지)
- 근거/인용이 없는데 “그럴듯한 답”을 생성해 노출
- 계약 실패를 숨기기 위한 자유 텍스트 fallback
- trace_id 누락된 로그/이벤트를 “일단 저장”
- 테넌트 키 없이 캐시/세션/검색을 공유
- 템플릿 추천 Tool을 모델이 임의 호출 가능하게 방치
- rate-limit/budget 규칙을 UI에서만 처리(서버 강제 없음)

---

## 14) 인코딩(Encoding) 전역 규칙 (필수)

### 14.1 UTF-8 강제 규칙
본 프로젝트에서 작성·수정·생성되는 모든 한글 텍스트는 반드시 **UTF-8 인코딩**을 사용한다.

**적용 대상(예시):**
- 소스/설정: `.java`, `.kt`, `.ts`, `.tsx`, `.js`, `.py`, `.md`, `.json`, `.yml`, `.yaml`, `.properties`, `.sql`
- 데이터/산출물: `.csv`, `.txt`, 생성되는 `.xlsx`, `.docx` 내부 텍스트, 로그 및 배치 산출물
- CSV 저장 시 기본 인코딩은 UTF-8로 한다. (엑셀 호환이 필요하면 UTF-8 BOM 사용 여부를 명확히 결정하고 일관되게 적용)
- 서버/컨테이너 기본 파일 인코딩은 UTF-8로 설정한다.
  - Java: `-Dfile.encoding=UTF-8`
  - Linux/Container: `LANG=C.UTF-8` 또는 `LANG=en_US.UTF-8`

### 14.2 금지 사항
- EUC-KR, CP949 등 레거시 인코딩 사용 금지
- 한글 깨짐()이 발생하는 상태로 커밋 금지
- Excel 기본 ANSI 저장 후 재업로드 금지

### 14.3 검증 규칙(권장)
- PR 전, 한글이 포함된 파일은 인코딩이 UTF-8인지 확인한다.
- CI 단계에서 가능하다면 UTF-8 검사 스크립트를 실행한다.
- 한글이 깨진 로그/응답이 발견되면 즉시 수정 후 재배포한다.

---

## 15) Agent Skills 운영 규칙 (Codex Skills 적용 지침)
목적: “스킬을 설치만 하고 방치”하는 상황을 막고, 이 프로젝트의 **P0 위험 구간(사고/운영 장애)** 을 스킬 기반 워크플로우로 고정한다.

### 15.1 원칙
- 스킬은 **프로젝트 표준 워크플로우(절차 지식)** 를 제공하는 도구이며, `AGENTS.md`의 전역 규칙(보안/계약/PII/테넌트)을 대체하지 않는다.
- 스킬 설치/업데이트는 “외부 코드를 받아 실행”할 수 있으므로, 다음을 지킨다:
  - 신뢰 가능한 저장소만 사용
  - 가능하면 커밋/태그로 버전 고정(핀ning)
  - 신규 도입 시: (1) `SKILL.md` 검토 → (2) 샌드박스 적용 → (3) 프로젝트 규칙과 충돌 여부 확인

### 15.2 P0 설치 세트(요구사항 Must 안전장치)
아래 스킬들은 멱등/레이트리밋/Redis/관측/가드레일/웹훅/pgvector 등 **운영 사고가 가장 자주 나는 구간**을 직접 커버한다.
- `idempotency`
- `rate-limiting-abuse-protection`
- `redis-patterns`
- `observability-setup`
- `software-backend`
- `guardrails-safety-filter-builder`
- `webhook-receiver-hardener`
- `postgres-semantic-search`

### 15.3 P1 설치 세트(품질/운영/관리자 안정화)
- `openai-api` (외부 LLM Provider 채택/교체/폴백 정책 구현 시)
- `rag-architect` (RAG 설계/평가/지표)
- `dashboard-patterns` (관리자/대시보드 UI 패턴)
- `release-notes` (릴리즈 노트 표준화)
- `release-check` (릴리즈 준비도 점검 게이트)
- `skill-creator` (프로젝트 전용 커스텀 스킬 제작)

### 15.4 스킬 사용 우선순위(작업 라우팅)
- 멱등/중복 방지/재시도 안전성 → `idempotency`
- 레이트리밋/쿼터/abuse 방어 헤더/429 계약 → `rate-limiting-abuse-protection`
- Redis 기반 세션/TTL/분산 카운터/락 → `redis-patterns`
- trace_id/OTel/구조화 로그/메트릭 → `observability-setup`
- 백엔드 계약(검증 at the edge, RFC 9457 style errors, timeouts, rate limiting) → `software-backend`
- 프롬프트 인젝션/PII 필터/출력 마스킹/거부 정책 → `guardrails-safety-filter-builder`
- 웹훅 서명 검증/중복 수신/재시도/안전 처리 → `webhook-receiver-hardener`
- Postgres+pgvector 인덱싱/쿼리/성능(필요 시 BM25와 결합) → `postgres-semantic-search`
- 관리자 UI 구성/표/필터/권한 UX → `dashboard-patterns`
- 릴리즈 산출물/체크리스트 자동화 → `release-notes`, `release-check`

### 15.5 “범용 스킬로는 위험한” 영역은 커스텀 스킬로 고정(권장)
요구사항이 **프로젝트 특화 계약(버튼 트리거, 스트리밍 순서, fail-closed 등)** 을 강제하는 영역은 범용 스킬로 억지 해결하지 말고,
프로젝트 전용 커스텀 스킬로 “절대 규칙”을 박아둔다.

**권장 커스텀 스킬 후보:**
- `template-recommend-tool-gating`
  - 버튼 클릭/스코프 토큰 없이는 템플릿 추천 Tool 호출 금지
  - ToolContext는 LLM 입력에 포함하지 않음(서버 내부 컨텍스트로만 유지)
- `citation-fail-closed-streaming`
  - citation 매핑 실패/파싱 실패 시 스트림 전송 차단 + 안전 전환(error/safe_response)
  - done 이전 종료 및 resume token 규약 포함
- `tenant-routing-and-isolation`
  - `session_id` ↔ `tenant_key` 강결합, 인덱스/캐시 prefix 규칙 강제
  - 테넌트 경계 침범 차단(쿼리 필터/정책)
- `approval-versioning-only`
  - 운영 read path는 “approved version”만 참조
  - 롤백은 “이전 approved”로만 가능
  - 변경 이벤트는 감사로그(trace_id)와 연결

  ## 16) Repository Hygiene & Artifacts Policy (강제)

### 16.1 아티팩트 분류(필수)
본 저장소의 “구현 코드 외 산출물”은 반드시 아래 4분류 중 하나로 귀속한다.

- Source of Truth: 사람이 편집하는 공식 스펙/문서
  - 예: docs/references/*.csv|*.xlsx, docs/uiux/*.xlsx, AGENTS.md, spec_sync_report.md
- Generated: 스크립트로 재생성 가능한 산출물(수정 금지)
  - 예: docs/references/generated/**
- Reports: 검증/게이트/추적성 결과(기록 가치가 있는 리포트)
  - 예: docs/**/reports/**
- Temp/Cache/Backup: 임시/캐시/덤프/백업(원칙적으로 git 추적 금지)

### 16.2 디렉터리 계약(Directory Contract)
- 새로운 최상위 폴더 생성 금지.
- 예외가 필요하면:
  1) docs/ops/AUXILIARY_FILE_INDEX.md 업데이트
  2) AGENTS.md에 규칙 추가
  3) CI gate 업데이트
  를 같은 PR에서 완료한다.

### 16.3 Generated/Reports 편집 규칙(강제)
- generated/ 또는 reports/ 하위 파일은 기본적으로 “수정 금지(Do not edit by hand)”를 원칙으로 한다.
- 생성 스크립트/명령/생성일(또는 run_id)을 파일 헤더 또는 인접 README에 남긴다.
- 생성 위치는 원본과 섞지 말고, 반드시 generated/ 또는 reports/로 격리한다.

### 16.4 tmp/ 정책(강제)
- tmp/는 로컬 작업용 임시 폴더이며, git에는 tmp/.gitkeep만 허용한다.
- tmp/** 하위의 JSON/CSV/MD 덤프 파일 커밋 금지.
- tmp/**가 PR diff에 포함되면 CI에서 실패 처리하는 것을 권장한다.

### 16.5 캐시/파이썬 바이트코드 커밋 금지(강제)
- **/__pycache__/**, *.pyc, .pytest_cache/, .mypy_cache/ 등 캐시는 절대 커밋 금지.
- PR diff에 포함되면 “버그”로 간주하고 제거한다.

### 16.6 _backup/ 정책(선택 -> 팀에서 1개로 고정)
아래 중 하나를 저장소 표준으로 채택한다(혼용 금지).
- (권장) _backup/은 레포에 커밋하지 않고, tag/release/CI artifact/외부 스토리지로 대체
- (대안) _backup/은 zip 압축 + 최근 N개만 유지 + 보관정책 README 필수

## 17) Repository Hygiene & Artifacts Policy

### 17.1 tmp/ 커밋 금지
- `tmp/`는 로컬 임시 작업 전용 폴더다.
- Git에는 `tmp/.gitkeep`만 허용한다.
- `tmp/**` 하위 파일(JSON/CSV/MD/덤프 등) 커밋은 금지한다.

### 17.2 캐시 파일 커밋 금지
- `**/__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`는 커밋 금지다.
- PR diff에 포함되면 위생 위반으로 간주하고 제거한다.

### 17.3 generated/reports 편집 규칙
- `generated/`, `reports/` 폴더의 파일은 기본적으로 수동 편집 금지다.
- 변경은 원본 스크립트 수정 후 재생성으로만 반영한다.
- 스크립트, 명령, 생성시각(또는 run id)을 함께 기록한다.

### 17.4 새 최상위 폴더 생성 금지 + 예외 절차
- 새로운 최상위 디렉터리 생성은 금지한다.
- 예외가 필요하면 같은 PR에서 아래 3가지를 모두 수행한다.
1. `docs/ops/AUXILIARY_FILE_INDEX.md` 갱신
2. 본 `AGENTS.md` 규칙 반영
3. CI/검증 스크립트 영향 범위 점검 결과 첨부
