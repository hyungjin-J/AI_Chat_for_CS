# GoLive Notion Manual Sync Patch (2026-02-21)

## 대상 페이지
- Requirements/API Spec: https://www.notion.so/2ed405a3a720816594e4dc34972174ec

## Source file
- `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`

## 메타 갱신 값(복사 반영용)
- Last synced at: `2026-02-21T21:00:00+09:00`
- Source file: `docs/references/google_ready_api_spec_v0.3_20260216.xlsx`
- Version(commit): `working-tree (go-live gap closure)`
- Change summary:
  1. `PUBLIC/AUTHENTICATED`를 ROLE 컬럼에서 제거하고 `비고(access_level=...)`로 분리
  2. Phase2 API 누락 엔드포인트 11건 반영(MFA/session/rbac-approval/audit export)
  3. `GET /v1/admin/audit-logs/chain-verify` 신규 반영
  4. RBAC matrix API를 즉시 적용 -> 승인요청 생성(202 PENDING) 의미로 정규화

## 본문 반영 포인트
1. "Auth API" 섹션에 MFA/session API 추가
2. "Admin/Ops API" 섹션에 approval 요청 조회/승인/반려 및 chain-verify 추가
3. 접근수준 표기 규칙:
   - ROLE 컬럼: `AGENT/CUSTOMER/ADMIN/OPS/SYSTEM`만 사용
   - 접근수준: `비고`에 `access_level=PUBLIC|AUTHENTICATED`

## 상태
- Notion MCP 자동 반영: **BLOCKED (Auth required)**
- 수동 반영 필요
