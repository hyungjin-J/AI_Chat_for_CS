# Release Checklist (AI_Chatbot)

## Scope
- ReqID: `AI-004`, `AI-005`, `AI-009`, `RAG-003`, `PERF-001`, `SYS-004`, `OPS-001`, `OPS-100`, `OPS-102`, `API-007`, `SEC-004`
- ProgramID: `OPS-ADMIN-DASHBOARD-SUMMARY`, `OPS-ADMIN-DASHBOARD-SERIES`, `OPS-METRIC-SUMMARY`, `OPS-TRACE-QUERY`, `OPS-PROVIDER-KILLSWITCH`, `OPS-ROLLBACK-TRIGGER`, `OPS-BLOCK-UPSERT`, `OPS-TENANT-BILLING-REPORT`, `ADM-TENANT-QUOTA-UPSERT`

## 1) Pre-merge Checklist
- [ ] `python scripts/release_check.py --base-ref origin/main --head-ref HEAD` 성공
- [ ] `python scripts/validate_ui_traceability.py` 성공
- [ ] `python scripts/pii_guard_scan.py` 성공
- [ ] `python -m unittest discover -s tests -p "*_test.py"` 성공
- [ ] `cd backend && ./gradlew test` 성공
- [ ] Answer Contract 강제 검증 (`AI-009`): 스키마/인용/근거 부족 시 fail-closed 동작 확인
- [ ] 자유 텍스트 fallback 금지 (`RAG-003`) 위반 0건
- [ ] trace_id 전파 검증 (`SYS-004`): API-RAG-Tool-SSE 전 구간 누락 0건
- [ ] PII 차단 검증 (`SEC-004`): 입력/로그/캐시/응답 평문 PII 0건
- [ ] RBAC/테넌트 격리 검증: 권한 없는 요청 403, `X-Tenant-Key` 누락/불일치 차단
- [ ] Budget/Rate-limit 검증 (`API-007`): 초과 시 429(또는 정책 기반 403), 표준 헤더 반환
- [ ] 스펙 변경 PR이면 `spec_sync_report.md`가 동일 PR에서 함께 변경됨
- [ ] 스펙 변경 PR이면 Notion 업데이트 요약문 생성(자동 출력 또는 파일 저장)

## 2) Pre-deploy Checklist
- [ ] `docs/ops/rag-kpi.md` 기준 임계치(warn/critical) 확인
- [ ] PERF-001 SLO 확인: `P95 E2E <= 15s`, `P95 first-token <= 2s`
- [ ] Contract/Citation KPI 확인: `answer_contract_pass_rate`, `citation_coverage_rate`, `zero_evidence_rate`
- [ ] OPS API 점검: `GET /v1/admin/dashboard/summary`, `GET /v1/admin/dashboard/series`, `GET /v1/ops/metrics/summary`, `GET /v1/ops/traces`
- [ ] 즉시조치 API 점검: `POST /v1/ops/llm/providers/{provider}/kill-switch`, `POST /v1/ops/rollbacks`, `PUT /v1/ops/blocks/{block_id}`

## 3) Post-deploy Checklist
- [ ] 배포 후 15/30/60분 KPI 모니터링
- [ ] 오류 코드 급증 여부 점검: `AI-009-422-SCHEMA`, `AI-009-409-CITATION`, `AI-009-409-EVIDENCE`, `SYS-004-409-TRACE`, `API-008-429-BUDGET`
- [ ] 알림 Ack/해결 이력 기록 (`OPS-001`)
- [ ] 이상 징후 시 즉시 런북 실행 및 조치 결과 기록
- [ ] 릴리즈 노트, 운영 기록, 감사 로그 링크 업데이트

## 4) Rollback / Kill-switch Procedures
- Answer Contract 실패 급증: `docs/ops/runbook/playbooks/answer_contract_fail_spike.md`
- RAG zero evidence 급증: `docs/ops/runbook/playbooks/rag_zero_evidence_spike.md`
- LLM provider 장애: `docs/ops/runbook/playbooks/llm_provider_outage.md`
- SSE 성능 저하: `docs/ops/runbook/playbooks/sse_streaming_degradation.md`
- trace_id 누락: `docs/ops/runbook/playbooks/trace_id_missing.md`
- PII 유출 의심: `docs/ops/runbook/playbooks/pii_leak_suspected.md`
- 승인 버전 사고: `docs/ops/runbook/playbooks/approval_version_incident.md`
- abuse/token drain: `docs/ops/runbook/playbooks/abuse_token_drain.md`

## 5) CI Gate Commands
```bash
python scripts/release_check.py --base-ref origin/main --head-ref HEAD
python scripts/validate_ui_traceability.py
python scripts/pii_guard_scan.py
python -m unittest discover -s tests -p "*_test.py"
cd backend && ./gradlew test
```
