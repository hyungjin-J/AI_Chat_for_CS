# DB Readiness 실행 반영 + 운영/완성 프로세스 제안 (KO)

- updated_at_kst: 2026-03-01 17:13:24 +09:00
- base_commit_hash: 97f7502
- current_head_short: 2eced8e
- release_tag: 2026.03XX-quality-hardening-workpack
- branch: utf8-wave8-to-29

## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)
- Added: DB 백업/복구 리허설 전용 주간 워크플로 `.github/workflows/db-backup-restore-weekly.yml`을 추가했다.
- Changed: 기존 `db-backup-restore-nightly`는 중복 스케줄 충돌 방지를 위해 `workflow_dispatch` 전용으로 전환했다.
- Changed: `scripts/db_backup_restore_rehearsal.py`에 운영 SLO 고정값(`rto_minutes=60`, `rpo_hours=24`)을 결과에 상시 기록하도록 반영했다.
- Added: 리허설 결과에 dump 메타(`dump_size_bytes`, `dump_sha256`, `dump_created_at_utc`)를 포함하도록 확장했다.
- Added: information_schema 기반 safe-seed 삽입 전략과 fallback 검증 경로(`SAFE_SEED_*`)를 구현했다.
- Changed: 리허설 스크립트 로그/명령 출력에서 비밀값이 노출되지 않도록 민감정보 마스킹 처리를 강화했다.
- Changed: 복구 후 safe-seed 검증 단계가 추가되어 restore 무결성 확인이 더 엄격해졌다.
- Changed: `docs/ops/DB_BACKUP_RESTORE_RUNBOOK.md`에 주간 자동화, 실패 코드 분류, 재시도 정책, dump 업로드 금지 규칙을 명시했다.
- Added: `docs/ops/sql/DB_OPERATIONS_QUERIES.sql` 기반 운영 점검 쿼리팩 실행 절차를 runbook에 추가했다.
- Changed: 아티팩트 인덱스/아카이브 게이트가 sidecar manifest 무결성까지 fail-closed로 검증하도록 강화됐다.
- Changed: `spec_sync_report` 게이트는 워크플로 옵션 플래그 없이 스크립트 기본값으로 엄격 검증되도록 정리됐다.
- Fixed: 본 문서의 인코딩 깨짐과 핸드오프 필수 메타/검증 게이트 누락 문제를 UTF-8 기준으로 복구했다.
- Added: 벡터 벤치 모니터링 워크플로 계약 테스트/스펙 게이트 증적(`vector_bench_*`)을 운영 증적으로 추가했다.
- Changed: `chatGPT/*` 3개 문서를 동일 시점 메타와 기준선으로 동기화했다.
- Added: 2026-03-01 Notion 메타 동기화 증적 파일 `notion_sync_evidence_20260301.md`를 추가했다.
- Changed: `spec_sync_report.md`에 2026-03-01 세션 블록을 추가해 Notion-로컬 동기화 추적성을 갱신했다.
- Changed: 현재 헤드(`2eced8e`) 기준 진행 이력을 본 문서 메타/요약에 반영했다.

## 1) 현재 구현된 DB 준비 상태
실행 순서(로컬/CI 공통 골격):
1. `docker compose -f infra/docker-compose.yml down -v`
2. `docker compose -f infra/docker-compose.yml up -d postgres redis`
3. `docker compose -f infra/docker-compose.yml --profile db-tools run --rm flyway`
4. `python scripts/db_smoke_test.py ...`
5. 백업/복구 리허설(`scripts/db_backup_restore_rehearsal.py`) 또는 주간 워크플로 실행
6. backend 헬스 체크에서 `X-Trace-Id` fail-closed 동작 확인

검증된 핵심 상태:
- Flyway 체인은 `v1..v11` 기준으로 적용/검증 흐름이 유지된다.
- PostgreSQL 서비스는 pgvector 사용 기반(`vector` extension) 준비 상태다.
- 복구 리허설은 단순 dump/restore를 넘어 safe-seed 또는 fallback 검증을 포함한다.
- 리허설 출력은 운영 감사에 필요한 SLO/해시/크기/생성시각 메타를 포함한다.
- 보안상 dump payload 파일은 CI 업로드 대상에서 제외된다(txt/json 보고서만 업로드).

## 2) 운영 프로세스(권장 우선순위)
### P0. 재현 가능한 부트스트랩 강제
- `up -> flyway -> smoke` 순서를 표준 절차로 고정한다.
- smoke 실패 시 다음 단계(백엔드 기동, 리허설, 배포)를 차단한다.

### P0. 주간 백업/복구 리허설 운영
- 주간 스케줄: KST 월요일 02:00 (UTC cron `0 17 * * 0`)
- 리허설 결과 txt/json 아티팩트를 필수 보관한다.
- 실패 코드(`COMPOSE_*`, `FLYWAY_*`, `SAFE_SEED_*`, `PG_DUMP_*`, `PG_RESTORE_*`, `DB_SMOKE_*`, `CORE_QUERY_*`)로 원인 분류한다.

### P0. 테넌트 격리 쿼리 감사
- 운영/리허설 핵심 조회·수정 SQL에서 `tenant_key` 누락 여부를 정기 점검한다.
- 누락 발견 시 보안 결함으로 간주하고 즉시 수정한다.

### P1. 쿼리 플랜 및 인덱스 품질 유지
- `docs/ops/sql/DB_QUERY_PLAN_SANITY.sql`과 운영 쿼리팩을 주기적으로 실행한다.
- 주요 쿼리의 인덱스 사용 여부와 성능 편차를 baseline과 비교한다.

### P1. pgvector 운영 관리
- 데이터량 증가 시 ivfflat 파라미터(`lists`, `probes`)를 재평가한다.
- `ANALYZE`/`REINDEX` 기준을 운영 문서(`docs/ops/PGVECTOR_OPERATIONS.md`)와 동일하게 적용한다.

## 3) 실패 처리 및 보안 규칙
재시도 정책:
- 1차 실패 시 즉시 1회 재시도.
- 동일 코드가 반복되면 자동 재시도 중단 후 코드 그룹별 분석으로 전환.

보안/증적 규칙:
- dump payload(`*.dump`)는 저장소 커밋 및 CI 아티팩트 업로드 금지.
- 리허설 txt/json에는 마스킹된 정보만 기록한다.
- 민감정보는 해시/크기/생성시각 같은 메타 정보로만 추적한다.

## 4) 즉시 실행 가능한 체크리스트
1. 주간 워크플로 실행 이력에서 `db-backup-restore-weekly` PASS 여부 확인
2. 리허설 결과의 `rto_minutes`, `rpo_hours`, `dump_sha256` 필드 존재 여부 확인
3. `safe_seed_*` 체크가 `PASS` 또는 정책상 허용된 `SKIPPED`인지 확인
4. restore 이후 `db_smoke_test` PASS 여부 확인
5. `artifact_index_gate`와 `artifact_archive_report`가 함께 PASS인지 확인

## 5) Validation Gates
| Gate | Status | Evidence |
|---|---|---|
| DB local readiness smoke | PASS | `docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.txt` |
| Spec sync report update gate | PASS | `docs/review/mvp_verification_pack/artifacts/spec_sync_report_gate.txt` |
| Artifact index freshness gate | PASS | `docs/review/mvp_verification_pack/artifacts/artifact_index_gate.txt` |
| Artifact archive integrity report | PASS | `docs/review/mvp_verification_pack/artifacts/artifact_archive_report.txt` |
| Quality validation summary | PASS | `docs/review/mvp_verification_pack/artifacts/quality_workpack_validation_summary.txt` |
| Vector bench workflow test evidence | PASS | `docs/review/mvp_verification_pack/artifacts/vector_bench_workflow_tests.txt` |

## 6) 남은 리스크 Top3
1. 백업/복구 리허설의 최신 증적 파일명은 날짜 기반이므로, 장기 추세 분석에는 별도 집계 자동화가 필요하다.
2. Docker 러너 상태 불안정 시 주간 워크플로가 간헐 실패할 수 있어 인프라 노이즈 분리가 필요하다.
3. 운영 쿼리팩은 읽기 전용이지만, 프로덕션 적용 시 실행 권한/접속 정책을 환경별로 더 엄격히 분리해야 한다.

## 7) SSOT 충돌 해결 원칙
충돌 시 우선순위:
1. `AGENTS.md`
2. `docs/review/mvp_verification_pack/artifacts/*`
3. `spec_sync_report.md`
4. `chatGPT/*` 문서

## 8) 2026-03-01 동기화 반영 메모
- 반영 범위:
  - `chatGPT/*` 3개 문서 메타/요약 갱신
  - `spec_sync_report.md` 세션 업데이트
  - Notion 매핑 페이지 5종 세션 블록 업데이트
- 동기화 증적:
  - `docs/review/mvp_verification_pack/artifacts/notion_sync_evidence_20260301.md`
