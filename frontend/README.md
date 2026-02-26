# Frontend Runtime Bootstrap

## Required Runtime
- Node.js: `22.12.0` (exact)
- npm: `10.9.0` (volta pinned via `package.json`)

## Source of Truth
- Repo root `.nvmrc` = `22.12.0`
- `frontend/.nvmrc` = `22.12.0`
- `frontend/package.json`:
  - `engines.node = 22.12.0`
  - `volta.node = 22.12.0`

## Quick Bootstrap
1. `nvm use 22.12.0`
2. `node -v`
3. `npm -v`
4. `npm ci`

## Runtime Verification
- Repository gate:
```bash
python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime
```
- npm install guard:
  - `frontend/.npmrc` sets `engine-strict=true` so wrong Node major fails early on `npm ci`.

## Daily Commands
- Dev server: `npm run dev`
- Unit tests: `npm run test:run`
- Build: `npm run build`

## Troubleshooting
1. Wrong Node version:
- Run `nvm use 22.12.0`.
- Re-open shell, then verify with `node -v`.
2. Engine mismatch on CI/local:
- Re-run `python scripts/check_node_version.py ... --check-runtime`.
3. Lockfile or install issues:
- Remove `node_modules`, then run `npm ci` again under Node `22.12.0`.

## Unicode Path Workaround
If frontend commands are unstable in non-ASCII workspace paths, run:

```bash
npm run mirror:run
```

Fast smoke-only check (writes fixed artifact):

```bash
npm run mirror:smoke
```
