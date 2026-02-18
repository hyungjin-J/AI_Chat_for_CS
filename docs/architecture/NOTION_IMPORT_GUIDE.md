# Notion 반영 가이드 - 시스템 아키텍처

대상 페이지:
- `https://www.notion.so/2ee405a3a72080868020e37dc33abad4`

## 1) 아키텍처 다이어그램 업로드

1. 대상 Notion 페이지를 엽니다.
2. 아래 파일을 업로드합니다.
   - `docs/architecture/diagrams/cs_rag_system_architecture_v1.png`
3. 이미지를 페이지 최상단에 배치합니다.

## 2) 아키텍처 문서 붙여넣기

1. 로컬 파일을 엽니다.
   - `docs/architecture/NOTION_System_Architecture.md`
2. 전체 내용을 복사합니다.
3. Notion에서 이미지 아래에 붙여넣습니다.
4. 제목 계층과 목록 포맷이 유지되는지 확인합니다.

## 3) 선택: 소스 아티팩트 첨부

- 편집 가능한 원본 보관을 위해 `docs/architecture/diagrams/cs_rag_system_architecture_v1.svg` 파일을 첨부합니다.

## 4) 빠른 검증 체크리스트

- [ ] 페이지 상단에 다이어그램이 선명하게 표시된다.
- [ ] 계층 섹션(클라이언트/엣지/백엔드/AI/데이터/관측/외부시스템)이 모두 존재한다.
- [ ] 주요 흐름(정상 경로 + fail-closed 경로)이 포함되어 있다.
- [ ] 보안 섹션에 PII, RBAC, 테넌트 격리, trace_id, 예산 가드가 포함되어 있다.
- [ ] 관측 지표(KPI)가 정리되어 있다.
- [ ] MVP와 Phase-2 경계가 명확하다.
- [ ] 아이콘 출처/라이선스가 포함되어 있다.

## 5) 재생성 명령어 (재현 가능)

저장소 루트에서 실행:

```powershell
npm install --prefix tools/architecture
npm run generate:icons --prefix tools/architecture
python scripts/generate_architecture_diagram.py
```

생성 결과:
- `docs/architecture/assets/icons/*.svg`
- `docs/architecture/assets/icons/*.png`
- `docs/architecture/diagrams/cs_rag_system_architecture_v1.png`
- `docs/architecture/diagrams/cs_rag_system_architecture_v1.svg`

## 6) Notion API 자동화 상태

- 현재 환경에서는 `NOTION_API_TOKEN`이 감지되지 않았습니다.
- 요청 조건에 따라 Notion API 동기화는 수행하지 않았습니다.
- 현재 기준 정식 반영 경로는 수동 업로드/붙여넣기입니다.
