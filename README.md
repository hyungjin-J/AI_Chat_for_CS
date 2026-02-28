# AI_Chatbot (CS Support AI Chatbot)

고객센터 상담원을 위한 RAG 기반 AI 챗봇 프로젝트입니다.  
핵심 목표는 빠른 응답이 아니라, **근거 기반 답변 + 보안 + 운영 추적성**을 동시에 만족하는 운영형 시스템입니다.

## TL;DR
- 현재 기준: **2026-02-22 Production Continuation Gap Closing (PR-1~PR-4) 반영 완료**
- 실행 기준 계획서: `docs/review/plans/20260222_production_continuation_gap_closing_plan.md`
- 아키텍처 기준: `platform/sharedkernel/contexts/channels(backoffice)`
- 정책 잠금:
  - ROLE 고정: `AGENT`, `CUSTOMER`, `ADMIN`, `OPS`, `SYSTEM`
  - 표준 에러 포맷 고정: `error_code`, `message`, `trace_id`, `details`
  - Hardening lock 완화 금지
  - Notion fail-closed 정책 유지

## Architecture Snapshot (DDD)
```text
com.aichatbot
├─ platform
├─ sharedkernel
├─ contexts
│  ├─ identity
│  ├─ conversation
│  ├─ knowledge
│  ├─ billing
│  └─ operations
└─ channels
   └─ backoffice
```

## What Was Implemented (PR-1 ~ PR-4)

### PR-1: 문서 SSOT + 에이전트 시스템 고정
- `AGENTS.md`를 contexts/platform/sharedkernel/channels 기준으로 최신화
- Workpack 3문서(01/02/03) + 전문 에이전트 보고서(DDD/SEC/QA) 계약을 CI fail-closed로 고정
- 템플릿 및 계약 검사 스크립트/테스트 추가

핵심 파일:
- `AGENTS.md`
- `scripts/assert_workpack_agent_report_contract.py`
- `scripts/contracts/workpack_agent_report_contract.json`
- `scripts/tests/test_assert_workpack_agent_report_contract.py`
- `docs/review/templates/agent_reports/*.md`

### PR-2: MyBatis mapper namespace drift 게이트
- `backend/src/main/resources/mappers/**/*.xml` 전수 namespace 검증 게이트 추가
- 중복 namespace/경로-namespace 컨텍스트 불일치/legacy namespace 재유입 차단
- `TenantResolverMapper.xml` 경로를 `mappers/platform`로 정합화

핵심 파일:
- `scripts/verify_mapper_namespaces.py`
- `scripts/contracts/mapper_namespace_contract.json`
- `scripts/tests/test_verify_mapper_namespaces.py`
- `backend/src/main/resources/mappers/platform/TenantResolverMapper.xml`

### PR-3: Legacy package 재도입 차단
- `com.aichatbot.(auth|billing|message|rag|...)` legacy 루트 패키지 재등장 시 CI FAIL

핵심 파일:
- `scripts/block_legacy_packages.py`
- `scripts/contracts/legacy_package_blocker_contract.json`
- `scripts/tests/test_block_legacy_packages.py`

### PR-4: Billing persistence 운영형 전환 (P0)
- billing 저장소를 in-memory 중심에서 mapper-backed persistence로 확장
- Flyway V9 마이그레이션 추가
- `memory|mybatis` 모드 스위치 유지(기본 `mybatis`)
- Testcontainers 통합 테스트 추가

핵심 파일:
- `backend/src/main/resources/db/migration/V9__billing_mapper_persistence.sql`
- `backend/src/main/java/com/aichatbot/contexts/billing/domain/mapper/*Mapper.java`
- `backend/src/main/resources/mappers/billing/*.xml`
- `backend/src/test/java/com/aichatbot/contexts/billing/infrastructure/BillingMapperPersistenceIntegrationTest.java`

## Validation Gates (Latest)
| Gate | Status | Evidence |
|---|---|---|
| Workpack + Agent report contract | PASS | `docs/review/mvp_verification_pack/artifacts/agent_system_pr1_lint_output.txt` |
| UTF-8 strict decode (PR-1) | PASS | `docs/review/mvp_verification_pack/artifacts/agent_system_pr1_utf8_check.txt` |
| Mapper namespace drift gate | PASS | `docs/review/mvp_verification_pack/artifacts/mapper_namespace_gate.txt` |
| Legacy package blocker | PASS | `docs/review/mvp_verification_pack/artifacts/legacy_package_blocker.txt` |
| Billing persistence integration test | PASS | `docs/review/mvp_verification_pack/artifacts/billing_persistence_itest.txt` |
| Backend regression test | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_2_3_billing_mapper_tests.txt` |
| Frontend tests | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_2_3_frontend_test.txt` |
| Frontend build | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_2_3_frontend_build.txt` |
| Spec consistency | PASS (`FAIL=0`) | `docs/review/mvp_verification_pack/artifacts/phase2_2_3_spec_consistency.txt` |
| UTF-8 strict decode (changed files) | PASS | `docs/review/mvp_verification_pack/artifacts/phase2_2_3_utf8_check.txt` |
| Public API compare | PASS (`added=0, removed=0`) | `docs/review/mvp_verification_pack/artifacts/phase2_2_3_public_api_compare.txt` |

## Quick Start

### 1) Infra
```bash
docker compose -f infra/docker-compose.yml up -d
```

### 2) Backend
```bash
cd backend
gradlew.bat bootRun
```

### 3) Frontend
```bash
cd frontend
npm ci --prefer-offline --no-audit --fund=false
npm run dev
```

## Verification Commands

### One-command (권장)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1
```

### Core gates
```powershell
python scripts/assert_workpack_agent_report_contract.py
python scripts/verify_mapper_namespaces.py
python scripts/block_legacy_packages.py
cd backend; ./gradlew.bat test --no-daemon
cd ../frontend; npm ci --prefer-offline --no-audit --fund=false; npm run test:run; npm run build
python ../scripts/spec_consistency_check.py
```

## Notion Sync Policy
- 스펙 파일 변경(`.csv/.xlsx`) 시 Notion 동기화 + 메타 갱신 + `spec_sync_report.md` 기록은 필수입니다.
- 필수 매핑 및 fail-closed 규칙은 `AGENTS.md` 2.2/2.2-A/2.2-B를 따릅니다.

## Key Documents
- Global rules: `AGENTS.md`
- Production continuation plan: `docs/review/plans/20260222_production_continuation_gap_closing_plan.md`
- ChatGPT handoff docs:
  - `chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md`
  - `chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md`
- Spec sync log: `spec_sync_report.md`

## Security Notes
- 민감정보/토큰/시크릿/PII 평문 커밋 금지
- `X-Trace-Id`, `X-Tenant-Key` 전파 강제
- Answer Contract 실패 시 자유 텍스트 우회 금지(safe response 또는 차단)

## Ops Trend Summary (Weekly Monitoring)
- Build script: `python scripts/build_ops_trend_report.py --artifacts-dir docs/review/mvp_verification_pack/artifacts --limit 8`
- Output artifacts:
  - `docs/review/mvp_verification_pack/artifacts/ops_trend_report.txt`
  - `docs/review/mvp_verification_pack/artifacts/ops_trend_report.json`
- Scope covered:
  - DB backup/restore rehearsal artifacts
  - DB reproducibility/nightly artifacts
  - Vector bench monitoring artifacts (if present)
- Missing artifact families are reported as `MISSING` (no crash, monitoring-only).
- The report is indexed in:
  - `docs/review/mvp_verification_pack/artifacts/_INDEX.md`
  - `docs/review/mvp_verification_pack/artifacts/_INDEX.json`
