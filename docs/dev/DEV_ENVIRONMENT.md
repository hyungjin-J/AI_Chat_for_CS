# Development Environment Quick Guide

## Scope
- This page defines Node.js runtime bootstrap steps used by local and CI gates.
- SSOT runtime version is loaded from `.nvmrc` (currently `22.12.0`).

## Fast Recovery for Node Version Mismatch
When `python scripts/check_node_version.py --check-runtime` fails:

1. Confirm target version in `.nvmrc`.
2. Run platform bootstrap script.
3. Re-run the Node check gate.

### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_node_22.ps1
python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime
```

### macOS / Linux
```bash
bash scripts/bootstrap_node_22.sh
python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime
```

## If nvm Is Not Installed
Use one of the following paths and then rerun the bootstrap script:

1. Install nvm and activate it in your shell profile.
  - Windows: `https://github.com/coreybutler/nvm-windows/releases`
  - macOS/Linux: `https://github.com/nvm-sh/nvm#installing-and-updating`
2. Install and switch to `.nvmrc` version.
  - `nvm install 22.12.0`
  - `nvm use 22.12.0`

Alternative fallback (if nvm cannot be used):
- Install exact Node version from `https://nodejs.org/en/download` and verify with `node -v`.

## Local/CI npm Install Option Alignment
To reduce network and lock noise, use the same install flags in local checks and CI:

```bash
npm ci --prefer-offline --no-audit --fund=false
```
