# _backup Policy

## Current Policy (Repository Standard)
- `_backup/` payloads are **not tracked in git**.
- Use one of the following instead of committing raw backup files:
  - git tags/releases
  - CI artifacts
  - external object storage

## Allowed Tracked Files
- `_backup/README.md`
- `_backup/.gitkeep`

## If Team Requires In-Repo Retention (Alternative)
- Store only compressed archives (`.zip`)
- Keep only the most recent **N** snapshots (recommended: N=3)
- Document retention period and owner in this file
- Never store secrets/PII in backup payloads
