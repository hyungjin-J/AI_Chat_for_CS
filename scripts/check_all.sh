#!/usr/bin/env bash
set -euo pipefail

if ! command -v pwsh >/dev/null 2>&1; then
  echo "pwsh not found. Use scripts/check_all.ps1 on Windows or install PowerShell 7."
  exit 1
fi

pwsh -ExecutionPolicy Bypass -File scripts/check_all.ps1

