#!/usr/bin/env bash
set -euo pipefail

if ! command -v pwsh >/dev/null 2>&1; then
  echo "pwsh not found. Use scripts/check_all.ps1 on Windows or install PowerShell 7."
  exit 1
fi

# Why: verify_all.sh는 기존 호출 경로를 유지하면서 표준 check_all 진입점으로 위임한다.
pwsh -ExecutionPolicy Bypass -File scripts/check_all.ps1

