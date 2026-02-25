# DB Readiness 실행 반영 + 운영/완성 프로세스 제안 (KO)

- updated_at_kst: 2026-02-25 01:15:00 +09:00
- scope: Docker 기반 DB 재현성 검증 + 프로젝트 완성 관점 DB 프로세스 정리

## 1) 이번 세션 실제 실행 반영

실행 순서:
1. `docker compose -f infra/docker-compose.yml down -v`
2. `docker compose -f infra/docker-compose.yml up -d postgres redis`
3. `docker compose -f infra/docker-compose.yml --profile db-tools run --rm flyway`
4. `python scripts/db_smoke_test.py --method docker-exec --compose-file infra/docker-compose.yml --compose-service postgres --output-txt docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.txt --output-json docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.json`
5. `docker compose -f infra/docker-compose.yml --profile demo-stack up -d backend`
6. `curl -i -H "X-Trace-Id: 11111111-1111-1111-1111-111111111111" http://localhost:8080/actuator/health`

검증 결과:
- PostgreSQL/Redis 컨테이너 healthy 확인
- Flyway `v1..v11` 적용/검증 완료
- pgvector extension 사용 가능 확인
- DB smoke: PASS (`SELECT 1`, extension, 테이블 존재, temp write/read/rollback)
- 백엔드 기동 시 fail-closed 보안 동작 유지
  - `X-Trace-Id` 없이 health 조회: 409
  - `X-Trace-Id` 포함: 200 + status UP

증적 아티팩트:
- `docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.txt`
- `docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.json`
- `docs/review/mvp_verification_pack/artifacts/backend_bootrun_postgres_output.txt`
- `docs/review/mvp_verification_pack/artifacts/continuation_utf8_strict_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/utf8_full_scan_ratchet_gate.txt`

## 2) 현재 DB 상태 요약

- 결론: 로컬 Docker 재현성은 확보됨
- 스키마: Flyway 관리 하에 일관 적용 가능
- 벡터 기반 검색 기반: `vector` extension + 기본 ivfflat 인덱스 기반 준비 완료
- 안전성: trace header 강제, fail-closed, tenant/RBAC 불변조건 유지

## 3) 프로젝트 구동/완성을 위해 필요한 DB 프로세스(권장 우선순위)

### P0. 부트스트랩/헬스 프로세스 (항상)
- 목적: 신규 개발자/운영자 환경에서 동일하게 부팅
- 실행: `up -> flyway -> smoke`
- 기준: smoke PASS 아니면 앱 기동 금지

### P0. 마이그레이션 거버넌스 (항상)
- 목적: 스키마 drift 방지
- 규칙:
1. 수동 DDL 금지, Flyway SQL만 허용
2. 마이그레이션은 idempotent/재실행 가능하게 작성
3. PostgreSQL 전용 문법은 전용 location에 분리 유지

### P0. 테넌트 격리 쿼리 점검 (항상)
- 목적: `tenant_key` 누락 쿼리로 인한 보안 결함 차단
- 프로세스:
1. Mapper SQL 리뷰 시 tenant 조건 필수 확인
2. 릴리즈 전 샘플 쿼리 audit 실행

샘플 점검 쿼리:
```sql
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name IN ('tenant_key', 'tenant_id')
ORDER BY table_name, column_name;
```

### P0. 백업/복구 리허설 (주 1회 이상)
- 목적: 장애 시 RTO/RPO 보장
- 프로세스:
1. `pg_dump` 백업
2. 빈 인스턴스 복원
3. smoke + 핵심 조회 검증

### P1. 성능 회귀 점검(EXPLAIN baseline)
- 목적: 인덱스 사용 회귀 탐지
- 실행: 주요 조회 3~5개에 대해 EXPLAIN 캡처 및 비교
- 현재 기준 파일: `docs/ops/sql/DB_QUERY_PLAN_SANITY.sql`

샘플 확인 쿼리:
```sql
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_tb_%'
ORDER BY indexname;
```

### P1. pgvector 운영 프로세스
- 목적: 벡터 검색 성능 유지
- 프로세스:
1. 적재량 증가 시 `ANALYZE` 주기 실행
2. ivfflat lists 파라미터 재평가
3. 대량 재적재 시 인덱스 재구축 계획 수립

### P1. 통계/정리(VACUUM/ANALYZE) 프로세스
- 목적: 플래너 품질 유지, bloat 억제
- 프로세스:
1. autovacuum 지표 모니터링
2. 고변경 테이블 수동 `VACUUM (ANALYZE)` 기준 수립

### P1. 데이터 보존/파티셔닝 전략
- 목적: 로그 테이블 무한증가 방지
- 대상: audit/search/stream event 계열
- 프로세스: retention 기간 + 아카이빙 + purge 작업 정의

### P1. 시드/부트 데이터 정책
- 목적: 환경별 동일 테스트 재현
- 프로세스:
1. 최소 tenant/role/기본 정책 시드 정의
2. 운영 시드는 승인 경로 분리

### P2. 운영 점검 쿼리 팩
- 목적: 장애 대응 속도 개선
- 내용:
1. 연결 수/잠금/장기쿼리/대기쿼리 조회
2. 테넌트별 고비용 쿼리 탐지
3. 최근 실패 트랜잭션 로그 조회

### P2. 저장 프로시저/함수 도입 원칙
- 현재 권장: 비즈니스 로직은 애플리케이션(MyBatis) 우선
- 예외적으로 DB 함수 고려 가능한 영역:
1. 복잡한 배치 집계
2. 대량 정합성 보정 작업
- 조건: 도입 시 별도 PR에서 성능/락 영향/롤백 플랜 증빙 필수

## 4) 바로 실행 가능한 다음 액션(실무용)

1. CI에 `db_smoke_test.py`를 선택 프로필로 추가해 nightly 검증 자동화
2. 운영 점검 쿼리 팩(`docs/ops/sql`)을 10개 내외로 표준화
3. 백업/복구 리허설 결과를 아티팩트로 누적 저장
4. 벡터 인덱스 튜닝 기준(데이터 건수별 lists/hnsw 전략) 문서화
