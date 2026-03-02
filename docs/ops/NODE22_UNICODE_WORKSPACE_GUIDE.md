# Node22 Unicode Workspace Guide

## Purpose
When the repository path contains non-ASCII characters, frontend toolchains can fail intermittently on some Node/npm/pnpm/yarn setups.
This helper mirrors the workspace to an ASCII-only path and runs frontend tasks from there.

## Quick Start (Smoke-First)
```bash
python scripts/mirror_and_run_frontend.py --source-root .
```

Default task is `smoke`, so this command is fast and deterministic.

## Task Mode
Use one flag to select execution mode:

```bash
python scripts/mirror_and_run_frontend.py --source-root . --task smoke
python scripts/mirror_and_run_frontend.py --source-root . --task test
python scripts/mirror_and_run_frontend.py --source-root . --task build
python scripts/mirror_and_run_frontend.py --source-root . --task dev
```

Task mapping:
- `smoke`: preflight only (no install/test/build/dev)
- `test`: install + `test:run`
- `build`: install + `build`
- `dev`: install + `dev`

Compatibility flag:
- `--smoke` remains supported as a legacy alias for `--task smoke`

## Package Manager Auto Detection
The helper auto-detects package manager in `frontend/`:
1. `pnpm-lock.yaml` -> `pnpm`
2. `yarn.lock` -> `yarn`
3. `package-lock.json` -> `npm`
4. fallback to `frontend/package.json` `packageManager`

If multiple lockfiles exist, it fails closed.

## Mirror Behavior
- Non-ASCII path detected -> mirror to ASCII path automatically.
- Logs explain why mirroring is required and print the mirror target path.

Advanced override:
```bash
python scripts/mirror_and_run_frontend.py --source-root . --task smoke --no-mirror
```

`--no-mirror` is allowed, but the helper prints loud warnings because Unicode-path failures may reappear.

## Node Version Diagnostics
Node checks are warning-only, but diagnostics are explicit:
- expected version from `.nvmrc`
- current `node -v` runtime value

Manual fix example:
```bash
nvm install <version-from-.nvmrc>
nvm use <version-from-.nvmrc>
```

Validation command:
```bash
python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime
```

## Evidence Artifact Contract
Each run writes one deterministic artifact:
- `docs/review/mvp_verification_pack/artifacts/node22_unicode_mirror_helper_<task>.txt`

Examples:
- `node22_unicode_mirror_helper_smoke.txt`
- `node22_unicode_mirror_helper_test.txt`
- `node22_unicode_mirror_helper_build.txt`
- `node22_unicode_mirror_helper_dev.txt`

Optional override:
```bash
python scripts/mirror_and_run_frontend.py --artifact-path <custom-path>
```

Legacy compatibility:
- `--smoke-artifact-path` is still supported.

## Windows Wrapper
```powershell
powershell -ExecutionPolicy Bypass -File scripts/mirror_and_run_frontend.ps1 -SourceRoot . -Task smoke
```

Wrapper keeps compatibility with `-Smoke` and now also supports `-Task` and `-NoMirror`.
