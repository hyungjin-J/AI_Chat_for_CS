# Figma to React Checklist

## 목적
Figma 노드 `10301:23060` 기반 설계를 React 구현으로 옮길 때, 시각/행동/정책 정합성을 릴리즈 전에 검증한다.

## 1) 레이아웃 매핑
- [ ] 3단 레이아웃 유지: Left Slim Nav(80) / Center Workspace(1000) / Right Utility(360)
- [ ] Header 64 + Content padding 24 + 입력 영역 고정 규칙 반영
- [ ] 모바일(360)에서는 Utility 패널을 Drawer로 전환

## 2) 토큰(CSS 변수) 매핑
- [ ] `--color-primary=#1e3a8a` 등 프로젝트 토큰으로 변환
- [ ] 원본 보라 포인트는 운영툴 색상 체계로 치환(네온/글로우 금지)
- [ ] Typography(Pretendard)와 spacing scale(4/8/12/16/24/32) 반영
- [ ] `tenant_key`별 스킨 오버라이드 동작 확인

## 3) Variant -> Props 매핑
- [ ] MessageComposer variant(default/blocked/cooldown) -> props 변환
- [ ] CitationPanel collapsed/expanded + selection sync
- [ ] PolicyGateBanner pass/warn/block 상태 매핑
- [ ] TemplateRecommendationList cooldown/session cap/remaining budget 표시
- [ ] DataGrid 필수 기능(필터/정렬/컬럼숨김/리사이즈/Reset) 반영

## 4) 상태 일치
- [ ] `loading/streaming/success/error/blocked` 상태가 디자인과 일치
- [ ] fail-closed 상태에서 전송 버튼 비활성
- [ ] `safe_response` 이벤트 수신 시 안전응답 UI로 전환
- [ ] 429 수신 시 Retry-After 카운트다운 + 우회 클릭 방지

## 5) SSE 계약 정합성
- [ ] 이벤트 순서: token -> citation -> done 검증
- [ ] done 이전 끊김 시 `Last-Event-ID` 기반 resume(최대 3회)
- [ ] duplicate event_id chunk 무시
- [ ] citation 누락 시 fail-closed로 전송 차단

## 6) 보안/정책 정합성
- [ ] 서버 권한(403)이 UI 숨김보다 항상 우선
- [ ] 민감 데이터는 화면/복사/다운로드/로그에서 마스킹
- [ ] Idempotency-Key 필요 API의 중복 클릭 방지
- [ ] trace_id가 요청/로그/감사 화면에서 연결됨

## 7) 접근성/반응형
- [ ] ARIA(role, live region, label) 적용
- [ ] 키보드만으로 대화/패널/모달 조작 가능
- [ ] focus trap, ESC 닫기, 포커스 복귀 정상 동작
- [ ] 360/768/1024/1366/1440+ 레이아웃 검증

## 8) 최종 사인오프
- [ ] 디자인 리뷰(디자이너)
- [ ] 기능 리뷰(프론트/백엔드)
- [ ] 정책 리뷰(보안/운영)
- [ ] QA 회귀 통과(ReqID/PII/SSE 핵심 시나리오)
