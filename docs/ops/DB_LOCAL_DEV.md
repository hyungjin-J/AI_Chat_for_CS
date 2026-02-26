# DB_LOCAL_DEV

## 목적
로컬에서 PostgreSQL + pgvector + Redis + Flyway를 Docker Compose로 재현하고,
스키마/인덱스/벡터 확장/기본 연결 상태를 동일한 절차로 검증하기 위한 운영 가이드입니다.

## 사전 준비
- Docker Desktop (Linux container mode)
- Python 3.10+
- 작업 위치: 저장소 루트

## 1) 컨테이너 기동
```powershell
docker compose -f infra/docker-compose.yml up -d postgres redis
docker compose -f infra/docker-compose.yml ps
```

기대 상태:
- `aichatbot-postgres`: `healthy`
- `aichatbot-redis`: `healthy`

## 2) 마이그레이션 적용 (Flyway)
```powershell
docker compose -f infra/docker-compose.yml --profile db-tools run --rm flyway
```

기대 로그:
- `Successfully validated ... migrations`
- `Schema "public" is up to date` 또는 초기 1회 `Migrating schema ...`

## 3) DB 스모크 테스트
```powershell
python scripts/db_smoke_test.py `
  --method docker-exec `
  --compose-file infra/docker-compose.yml `
  --compose-service postgres `
  --output-txt docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.json
```

PASS 기준:
- `SELECT 1` 성공
- `vector` extension 존재
- 기대 테이블 존재 (`tb_tenant`, `tb_message`, `tb_kb_chunk_embedding`, `flyway_schema_history` 등)
- 임시 쓰기/읽기 + rollback 성공

## 4) (선택) 백엔드 컨테이너 기동 확인
```powershell
docker compose -f infra/docker-compose.yml --profile demo-stack up -d backend
```

헬스 체크 주의:
- 본 프로젝트는 `X-Trace-Id` 헤더가 없으면 fail-closed로 409를 반환할 수 있습니다.
- 아래처럼 헤더를 포함해서 확인합니다.

```powershell
curl.exe -i -H "X-Trace-Id: 11111111-1111-1111-1111-111111111111" http://localhost:8080/actuator/health
```

기대 상태:
- HTTP 200
- `{"status":"UP"...}`

종료:
```powershell
docker compose -f infra/docker-compose.yml stop backend
```

## 5) (선택) 쿼리 플랜 sanity 확인
```powershell
Get-Content docs/ops/sql/DB_QUERY_PLAN_SANITY.sql -Raw | `
  docker compose -f infra/docker-compose.yml exec -T postgres `
    psql -U aichatbot -d aichatbot
```

## 트러블슈팅

### 포트 충돌 (5432/6379)
```powershell
netstat -ano | findstr :5432
netstat -ano | findstr :6379
```

### 볼륨 초기화가 필요할 때
```powershell
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d postgres redis
docker compose -f infra/docker-compose.yml --profile db-tools run --rm flyway
```

### collation version mismatch 경고
증상 예시:
- `database ... has a collation version mismatch`

조치:
1. 로컬 개발 환경에서는 위 `down -v` 후 재기동/재마이그레이션으로 해결
2. 지속 시 컨테이너/이미지 버전 정합성 재확인

### pgvector extension missing
- `postgres` 이미지가 `pgvector/pgvector:pg16`인지 확인
- Flyway 로그에서 `V11__pgvector_enablement` 적용 여부 확인

### 마이그레이션 실패
```powershell
docker compose -f infra/docker-compose.yml exec -T postgres `
  psql -U aichatbot -d aichatbot -c "SELECT installed_rank, version, description, success FROM flyway_schema_history ORDER BY installed_rank;"
```

## 정리
권장 검증 순서:
1. `up -d`
2. `flyway`
3. `db_smoke_test.py`
4. (선택) backend health + query plan sanity

## 6) Operational diagnostics SQL queries
Run the standard diagnostics set:

```powershell
Get-Content docs/ops/sql/DB_OPS_DIAGNOSTICS.sql -Raw | `
  docker compose -f infra/docker-compose.yml exec -T postgres `
    psql -U aichatbot -d aichatbot
```

Save output to an artifact file:

```powershell
$artifact = "docs/review/mvp_verification_pack/artifacts/db_ops_diagnostics_$(Get-Date -Format yyyyMMdd_HHmmss).txt"
Get-Content docs/ops/sql/DB_OPS_DIAGNOSTICS.sql -Raw | `
  docker compose -f infra/docker-compose.yml exec -T postgres `
    psql -U aichatbot -d aichatbot | Tee-Object -FilePath $artifact
```

## 7) PGVECTOR IVFFlat operations and benchmark
- Operations guide:
  - `docs/ops/PGVECTOR_OPERATIONS.md`
- Local benchmark script:
  - `scripts/vector_recall_latency_bench.py`

Create a baseline artifact:

```powershell
python scripts/vector_recall_latency_bench.py `
  --method docker-exec `
  --compose-file infra/docker-compose.yml `
  --compose-service postgres `
  --database aichatbot `
  --db-user aichatbot `
  --tenant-id 00000000-0000-0000-0000-000000000001 `
  --top-k 10 `
  --query-count 30 `
  --probe-values 1,2,4,8,16,32 `
  --output-txt docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_20260226.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_20260226.json
```

Compare current run against baseline delta policy:

```powershell
python scripts/vector_recall_latency_bench.py `
  --method docker-exec `
  --compose-file infra/docker-compose.yml `
  --compose-service postgres `
  --database aichatbot `
  --db-user aichatbot `
  --tenant-id 00000000-0000-0000-0000-000000000001 `
  --top-k 10 `
  --query-count 30 `
  --probe-values 1,2,4,8,16,32 `
  --baseline-json docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_baseline.json `
  --max-recall-drop 0.03 `
  --max-p95-regression-ratio 1.30 `
  --output-txt docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_20260226.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/vector_recall_latency_bench_20260226.json
```

## 8) CI Nightly reproducibility (`db-repro-nightly.yml`)
The same clean-volume reproducibility path runs in GitHub Actions nightly and manual dispatch:
- Workflow: `.github/workflows/db-repro-nightly.yml`
- Triggers:
  - `schedule`: `0 17 * * *` (KST 02:00)
  - `workflow_dispatch`

Execution order is fixed:
1. `docker compose -f infra/docker-compose.yml down -v`
2. `docker compose -f infra/docker-compose.yml up -d postgres redis`
3. `docker compose -f infra/docker-compose.yml --profile db-tools run --rm flyway`
4. `python scripts/db_smoke_test.py --method docker-exec ...`
5. `docker compose -f infra/docker-compose.yml --profile demo-stack up -d backend`
6. fail-closed health checks:
  - without `X-Trace-Id` -> `409`
  - with `X-Trace-Id` -> `200`

Nightly artifacts (always uploaded, even on failure):
- `docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.txt`
- `docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.json`
- `docs/review/mvp_verification_pack/artifacts/db_backend_health_without_trace_raw.txt`
- `docs/review/mvp_verification_pack/artifacts/db_backend_health_with_trace_raw.txt`
- `docs/review/mvp_verification_pack/artifacts/db_backend_health_trace_gate.txt`
- `docs/review/mvp_verification_pack/artifacts/db_backend_health_trace_gate.json`
- `docs/review/mvp_verification_pack/artifacts/db_readiness_compose_ps.txt`
- `docs/review/mvp_verification_pack/artifacts/db_readiness_flyway_output.txt`
- `docs/review/mvp_verification_pack/artifacts/db_readiness_compose_logs.txt`

Operational note:
- This nightly is monitoring-only and does not add PR merge-block enforcement.
- Failures are still explicit at workflow level (red run state) and traceable by uploaded artifacts.
