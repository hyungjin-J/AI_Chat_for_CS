# AI_Chatbot OPS Runbook

## 1. 목적과 적용 범위
본 Runbook은 AI_Chatbot 운영 장애 대응 표준이다. 다음 원칙을 인시던트 전 단계에서 강제한다.

- Fail-Closed: Answer Contract 실패(스키마/인용/근거 임계치) 시 자유 텍스트 우회 금지, `safe_response`만 허용
- PII 보호: 입력/로그/캐시/응답 전 구간 마스킹
- Trace 보장: `X-Trace-Id` 100% 전파, 누락 이벤트는 배포/운영 게이트에서 차단
- RBAC/테넌트 격리: 서버가 최종 권위, UI 은닉은 보조 수단
- Budget/Rate Limit: 토큰/툴콜/세션/SSE 동시성 하드캡 강제, 초과 시 `429/403` 표준 처리

## 2. 스펙 기준선 (ReqID / ProgramID)
### ReqID
- `OPS-001`, `OPS-003`, `SYS-004`, `PERF-001`, `AI-005`, `AI-009`, `API-007`, `SEC-004`, `ADM-007`

### ProgramID
- `OPS-TRACE-QUERY`
- `OPS-METRIC-SUMMARY`
- `OPS-BLOCK-UPSERT`
- `OPS-PROVIDER-KILLSWITCH`
- `OPS-ROLLBACK-TRIGGER`
- `OPS-AUDIT-LOG-QUERY`
- `OPS-AUDIT-CHANGE-DIFF`
- `LLM-PROVIDER-HEALTH`
- `KB-REINDEX-STATUS`
- `COM-ERROR-FORMAT`
- `COM-TRACE-LOG-RULE`
- `COM-ANSWER-CONTRACT-RULE`
- `COM-SSE-EVENT-RULE`
- `COM-BUDGET-GUARD-RULE`
- `COM-RATE-LIMIT-RULE`
- `COM-RBAC-403-RULE`
- `COM-IDEMPOTENCY-RULE`

## 3. 온콜 역할
| 역할 | 책임 | 필수 권한 |
|---|---|---|
| Incident Commander (IC) | 심각도 확정, 의사결정, 종료 승인 | `OPS` |
| OPS Primary | 탐지/초동조치(API 실행), 타임라인 기록 | `OPS` |
| AI/RAG Responder | Answer Contract, citation/evidence, KB 상태 점검 | `OPS` 또는 `ADMIN` |
| Security Responder | PII/악용 대응, 차단 정책 검토 | `OPS` |
| Scribe/Comms | 공지 템플릿 발송, 업데이트 주기 준수 | `OPS` |

## 4. 심각도와 응답 시간
| Severity | 기준 | 초기 응답 | 상태 공유 주기 |
|---|---|---|---|
| `SEV-1` | PII 유출 의심, 테넌트 경계 침범, 전면 장애 | 5분 이내 | 15분 |
| `SEV-2` | 주요 기능 장애(스트리밍/검색/생성 대규모 저하) | 10분 이내 | 30분 |
| `SEV-3` | 부분 장애, 우회 가능 | 30분 이내 | 60분 |
| `SEV-4` | 경미한 지표 이상, 사용자 영향 미미 | 영업시간 내 | 필요 시 |

## 5. 인시던트 라이프사이클
1. Detect: 모니터링/알림/신고 접수
2. Triage: 심각도, 영향 테넌트, 영향 기능 확정
3. Contain: 차단/킬스위치/롤백 즉시조치
4. Eradicate: 근본 원인 제거(설정/버전/데이터 복구)
5. Recover: 서비스 정상화, 성능/SLO 재검증
6. Validate: 감사로그/추적로그/에러코드 일관성 점검
7. Close: RCA와 재발방지 액션 등록

## 6. trace_id 필수 기록 규칙
모든 인시던트는 아래 항목을 빠짐없이 기록한다.

- `incident_id`
- `root_trace_id` (최초 탐지 이벤트 trace)
- 즉시조치 API별 `action_trace_id`
- 관련 `audit_id` / `job_id`
- 영향 `tenant_key`, `session_id`, `message_id` (해당 시)
- 사용자 노출 에러코드(`AI-009-...`, `API-008-...`, `SYS-004-...` 등)

## 7. 공통 API 호출 템플릿
모든 플레이북은 아래 공통 변수/헤더를 사용한다.

```bash
export API_BASE_URL="https://<host>"
export ACCESS_TOKEN="<ops_jwt>"
export TENANT_KEY="<tenant_key>"
export TRACE_ID="<uuid>"
export IDEMPOTENCY_KEY="<uuid>"
export INCIDENT_ID="INC-YYYYMMDD-001"
```

표준 헤더:

- `Authorization: Bearer ${ACCESS_TOKEN}`
- `X-Trace-Id: ${TRACE_ID}`
- `X-Tenant-Key: ${TENANT_KEY}`
- `Idempotency-Key: ${IDEMPOTENCY_KEY}` (POST/PUT/PATCH 필수)

표준 에러 포맷(`COM-ERROR-FORMAT`):

```json
{
  "error_code": "SYS-003-XXX",
  "message": "human readable message",
  "trace_id": "uuid",
  "details": []
}
```

## 8. 커뮤니케이션 템플릿
```text
[INCIDENT] {incident_id} | {severity} | {status}
Start Time: {yyyy-mm-dd hh:mm:ss tz}
Owner(IC): {name}
Scope: {tenant/service/API}
Symptoms: {user impact + error codes}
Root Trace: {trace_id}
Immediate Actions: {block/kill-switch/rollback + action trace_id}
Current Risk: {data leak/availability/compliance}
Next Update ETA: {time}
```

## 9. 플레이북 목록
- `docs/ops/runbook/playbooks/trace_id_missing.md`
- `docs/ops/runbook/playbooks/pii_leak_suspected.md`
- `docs/ops/runbook/playbooks/answer_contract_fail_spike.md`
- `docs/ops/runbook/playbooks/llm_provider_outage.md`
- `docs/ops/runbook/playbooks/rag_zero_evidence_spike.md`
- `docs/ops/runbook/playbooks/sse_streaming_degradation.md`
- `docs/ops/runbook/playbooks/abuse_token_drain.md`
- `docs/ops/runbook/playbooks/approval_version_incident.md`

