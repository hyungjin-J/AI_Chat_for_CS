# Windows Node/npm Lock Runbook

## Purpose
Standard response for intermittent `npm ci` slowness/failure on Windows caused by file locks and environment drift.

## Typical Symptoms
- `EPERM` / `EBUSY` during `npm ci` or package extraction.
- `node_modules` cleanup stuck or very slow.
- Retrying the same command produces different outcomes.

## Likely Causes (Hypothesis)
- Real-time antivirus scanner holding package files.
- Long path or deep dependency path pressure.
- Parallel process contention (`npm`, IDE indexer, watcher, test runner).
- Corrupted cache or partially written `node_modules`.

## Standard Command Policy
Use the same install flags in local and CI:

```powershell
npm ci --prefer-offline --no-audit --fund=false
```

## Standard Recovery Steps
1. Stop concurrent Node processes (test runners, watchers, local dev servers).
2. Remove install artifacts.
```powershell
if (Test-Path frontend\\node_modules) { Remove-Item -Recurse -Force frontend\\node_modules }
```
3. Clean npm cache and retry with standard flags.
```powershell
npm cache verify
cd frontend
npm ci --prefer-offline --no-audit --fund=false
```
4. Optional helper (retry 3 times with same flags and guidance output).
```powershell
powershell -ExecutionPolicy Bypass -File scripts/frontend_install_retry.ps1 -MaxAttempts 3
```
5. If lock persists, restart terminal and run again.
6. If still blocked, reboot once and retry before escalating.
7. If recurring, move the install flow to WSL2 or short local path and re-run from clean workspace.

## Optional OS-Level Mitigations
- Keep repository path short (avoid deeply nested folders).
- Exclude project folder from real-time antivirus scanning if enterprise policy allows.
- Ensure Windows long path support is enabled by IT policy where applicable.
- Prefer WSL2 for dependency-heavy installs when Windows endpoint controls repeatedly lock files.

## Escalation Record (Minimum)
- Timestamp (KST)
- Command used
- Exact error code/message
- Retry count
- Whether reboot/cache-clean was applied

Do not include tokens, secrets, private keys, or PII in escalation logs.
