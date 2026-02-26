# Node22 Unicode Workspace Repro Guide

## Why this exists

On some environments, Node 22 frontend workflows (`npm ci`, `npm run test:run`, `npm run build`)
can become unstable when the repository path contains non-ASCII characters.

Observed context:
- Runtime target: Node `22.12.0`
- Workspace example: path includes Korean characters

This does not change product behavior; it only affects local developer reproducibility.

## Quick check

```bash
python scripts/check_workspace_path_ascii.py --path .
```

- `status=PASS`: current path is ASCII-only.
- `status=WARNING`: run frontend checks from an ASCII mirror path.

## One-command helper (cross-platform, recommended)

Canonical runner (SSOT):

```bash
python scripts/mirror_and_run_frontend.py --source-root .
```

Thin wrappers:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts/mirror_and_run_frontend.ps1
```

```bash
# macOS / Linux
bash scripts/mirror_and_run_frontend.sh
```

Behavior:
- Detects non-ASCII workspace path via `scripts/check_workspace_path_ascii.py` (warning-only).
- Mirrors repo to ASCII temp path when needed.
- Runs Node bootstrap from `.nvmrc` unless skipped.
- Auto-detects package manager by lockfile (`pnpm`/`yarn`/`npm`, fail-closed on conflicts).
- Runs frontend commands in order: install -> `test:run` -> build.

## npm scripts (frontend)

```bash
cd frontend
npm run mirror:run
npm run mirror:smoke
```

- `mirror:run`: full chain
- `mirror:smoke`: fast verification only, writes fixed artifact:
  `docs/review/mvp_verification_pack/artifacts/node22_unicode_mirror_helper_smoke.txt`

## Useful options

```bash
# Always mirror (even when source path is ASCII)
python scripts/mirror_and_run_frontend.py --source-root . --force-mirror

# Custom mirror root (must be ASCII-only)
python scripts/mirror_and_run_frontend.py --source-root . --mirror-root /tmp/AI_Chatbot_ascii_workspace

# Smoke mode
python scripts/mirror_and_run_frontend.py \
  --source-root . \
  --force-mirror \
  --skip-node-bootstrap --skip-install --skip-tests --skip-build \
  --smoke-artifact-path docs/review/mvp_verification_pack/artifacts/node22_unicode_mirror_helper_smoke.txt
```

## CI guidance

CI should continue to use `.nvmrc` and `scripts/check_node_version.py --check-runtime`.
Do not add hard failures based on workspace Unicode path in CI.
