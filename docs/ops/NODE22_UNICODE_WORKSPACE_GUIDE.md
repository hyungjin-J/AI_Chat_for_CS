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

## Recommended local workaround (Windows)

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
