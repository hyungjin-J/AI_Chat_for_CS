# Node22 Unicode Workspace Repro Guide

## Why this exists

On some Windows environments, Node 22 frontend workflows (`npm ci`, `npm run test:run`, `npm run build`)
can become unstable when the repository path contains non-ASCII characters.

Observed context:
- Date: 2026-02-23
- Runtime target: Node `22.12.0`
- Workspace example: path includes Korean characters

This does not change product behavior; it only affects local developer reproducibility.

## Quick check

```powershell
python scripts/check_workspace_path_ascii.py --path .
```

- `status=PASS`: current path is ASCII-only.
- `status=WARNING`: move to ASCII-only temp path for frontend runs.

## One-command helper (Windows, recommended)

Use this helper first. It keeps CI behavior unchanged (warning-only path check), but
automates local mirror-and-run when needed.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/mirror_and_run_frontend.ps1
```

Behavior:
- Detects non-ASCII workspace path via `scripts/check_workspace_path_ascii.py` (warning-only).
- Mirrors repo to ASCII temp path when needed.
- Runs `scripts/bootstrap_node_from_nvmrc.ps1`.
- Runs frontend commands in order: `npm ci`, `npm run test:run`, `npm run build`.

Useful options:

```powershell
# Always mirror (even when source path is ASCII)
powershell -ExecutionPolicy Bypass -File scripts/mirror_and_run_frontend.ps1 -ForceMirror

# Custom mirror root (must be ASCII-only path)
powershell -ExecutionPolicy Bypass -File scripts/mirror_and_run_frontend.ps1 -MirrorRoot C:\Temp\AI_Chatbot_ascii_workspace

# Smoke mode: verify mirror path handling only, skip node/npm steps
powershell -ExecutionPolicy Bypass -File scripts/mirror_and_run_frontend.ps1 `
  -ForceMirror `
  -SkipNodeBootstrap -SkipInstall -SkipTests -SkipBuild `
  -SmokeArtifactPath docs/review/mvp_verification_pack/artifacts/node22_unicode_mirror_helper_smoke.txt
```

## Manual workaround (Windows fallback)

```powershell
$src = (Resolve-Path .).Path
$dst = Join-Path $env:TEMP "AI_Chatbot_ascii_workspace"
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
robocopy $src $dst /MIR /XD .git node_modules .gradle dist build target out .idea .vscode
Push-Location $dst\\frontend
npm ci --prefer-offline --no-audit --fund=false
npm run test:run
npm run build
Pop-Location
```

## Recommended local workaround (macOS/Linux)

```bash
src="$(pwd)"
dst="/tmp/AI_Chatbot_ascii_workspace"
rm -rf "$dst"
rsync -a --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.gradle' \
  --exclude 'dist' \
  --exclude 'build' \
  --exclude 'target' \
  --exclude 'out' \
  --exclude '.idea' \
  --exclude '.vscode' \
  "$src/" "$dst/"
cd "$dst/frontend"
npm ci --prefer-offline --no-audit --fund=false
npm run test:run
npm run build
```

## CI guidance

CI should continue to use `.nvmrc` and `scripts/check_node_version.py --check-runtime`.
Do not add hard failures based on workspace Unicode path in CI.
