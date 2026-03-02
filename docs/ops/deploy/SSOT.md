# Deployment SSOT

## Scope
- This repository standardizes production-like deployment to exactly one source of truth:
  - `infra/compose/production/docker-compose.prod.yml`

## Decision
- Adopted SSOT: Docker Compose (production profile)
- Rejected for now: Helm/Kubernetes chart in this repository

## Why
- `infra/` already existed and is actively used in CI/dev flows.
- A single compose SSOT keeps deploy/rollback/diagnostic commands deterministic in one path.
- Optional dependencies (OpenSearch, Ollama) are handled via compose profiles without creating a second deployment system.

## Command Contract
- Baseline stack:
  - `docker compose -f infra/compose/production/docker-compose.prod.yml up -d`
- Optional profiles:
  - `docker compose -f infra/compose/production/docker-compose.prod.yml --profile search --profile llm-local up -d`

## Rollback Contract
- Pin image/app version by git tag or release branch, then re-run the same compose file.
- Do not switch deployment mechanism during incident response.
- Use the same compose file for:
  - deploy
  - rollback
  - smoke diagnosis

## Non-SSOT Notice
- `infra/docker-compose.yml` and `infra/docker-compose.ollama.yml` remain for local/dev compatibility.
- Production reproducibility SSOT is only `infra/compose/production/docker-compose.prod.yml`.
