# DB Backup Restore Runbook

## 1) Purpose and Scope
This runbook defines a repeatable backup/restore rehearsal for the local and CI path:
`pg_dump -> clean volume restore -> flyway validate -> db smoke -> deterministic core queries`.

This document is for operators and reviewers who need deterministic evidence that recovery works from a clean volume baseline.

## 2) RTO and RPO Assumptions
- RTO: 60 minutes
- RPO: 24 hours

These are operational target assumptions for rehearsal and incident response planning.

## 3) Preconditions Checklist
- Docker Desktop is available and running.
- `docker compose` command is available.
- Python 3.10+ is available.
- The working directory is repository root.
- Required free disk is available for temporary dump files.
- Credentials are injected securely and never committed.

## 4) One-Command Procedure (Local and CI)
Run from repository root:

```powershell
python scripts/db_backup_restore_rehearsal.py `
  --compose-file infra/docker-compose.yml `
  --artifact-dir docs/review/mvp_verification_pack/artifacts
```

Expected outputs:
- `docs/review/mvp_verification_pack/artifacts/db_backup_restore_rehearsal_YYYYMMDD.txt`
- `docs/review/mvp_verification_pack/artifacts/db_backup_restore_rehearsal_YYYYMMDD.json`

## 5) Manual Recovery Procedure (Step-by-Step)
1. Reset environment:
```powershell
docker compose -f infra/docker-compose.yml down -v
```
2. Start PostgreSQL and Redis:
```powershell
docker compose -f infra/docker-compose.yml up -d postgres redis
```
3. Apply migrations:
```powershell
docker compose -f infra/docker-compose.yml --profile db-tools run --rm flyway
```
4. Create dump inside container and copy to host:
```powershell
docker compose -f infra/docker-compose.yml exec -T -e PGPASSWORD=local-dev-only-password postgres `
  pg_dump -U aichatbot -d aichatbot -F c -f /tmp/db_backup_restore_source.dump
docker compose -f infra/docker-compose.yml cp postgres:/tmp/db_backup_restore_source.dump tmp/db_backup_restore/manual.dump
```
5. Destroy source and recreate blank instance:
```powershell
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d postgres redis
```
6. Restore dump:
```powershell
docker compose -f infra/docker-compose.yml cp tmp/db_backup_restore/manual.dump postgres:/tmp/db_backup_restore_target.dump
docker compose -f infra/docker-compose.yml exec -T -e PGPASSWORD=local-dev-only-password postgres `
  pg_restore -U aichatbot -d aichatbot --clean --if-exists --no-owner --no-privileges /tmp/db_backup_restore_target.dump
```
7. Validate migration chain and smoke:
```powershell
docker compose -f infra/docker-compose.yml --profile db-tools run --rm flyway `
  -url=jdbc:postgresql://postgres:5432/aichatbot `
  -user=aichatbot `
  -password=local-dev-only-password `
  -connectRetries=30 `
  -locations=filesystem:/flyway/sql,filesystem:/flyway/sql-postgresql `
  validate

python scripts/db_smoke_test.py `
  --method docker-exec `
  --compose-file infra/docker-compose.yml `
  --compose-service postgres `
  --output-txt docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.txt `
  --output-json docs/review/mvp_verification_pack/artifacts/db_local_readiness_smoke.json
```

## 6) Failure Code Response Table
- `COMPOSE_*_FAILED`: Docker compose bootstrap/reset failed.
  - Action: check Docker daemon state and compose logs.
- `FLYWAY_MIGRATE_FAILED` / `FLYWAY_VALIDATE_FAILED`: migration chain failed.
  - Action: inspect flyway output and schema history.
- `PG_DUMP_*` / `PG_RESTORE_*`: backup or restore command failed.
  - Action: verify credentials, dump path, and container permissions.
- `DB_SMOKE_*`: post-restore smoke failed.
  - Action: inspect `db_local_readiness_smoke.json` violations.
- `CORE_QUERY_*`: deterministic seed/index validations failed.
  - Action: inspect seed migrations and index migration coverage.

## 7) Rollback Flow
If restore fails or post-restore verification fails:

```powershell
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d postgres redis
docker compose -f infra/docker-compose.yml --profile db-tools run --rm flyway
python scripts/db_smoke_test.py --method docker-exec --compose-file infra/docker-compose.yml --compose-service postgres
```

This resets to migration-only baseline and confirms minimal readiness before retrying restore.

## 8) Evidence Interpretation
Primary evidence files:
- `db_backup_restore_rehearsal_YYYYMMDD.txt`
- `db_backup_restore_rehearsal_YYYYMMDD.json`

Pass criteria:
- `status=PASS`
- `violation_count=0`
- Core checks (`seed_demo_tenant_exists`, `role_taxonomy_exists`, `foundation_index_exists`) are all `PASS`

Fail criteria:
- `status=FAIL`
- Any violation entry with actionable code/details

## 9) Security Notes
- Dump files are temporary by default and deleted unless `--keep-dump` is set.
- Never commit dump payloads.
- Keep DB credentials and tokens in environment/secret stores only.
- Do not include sensitive payloads in evidence artifacts.

