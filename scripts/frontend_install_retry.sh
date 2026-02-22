#!/usr/bin/env bash
set -euo pipefail

MAX_ATTEMPTS="${1:-3}"
FRONTEND_DIR="${2:-frontend}"
CMD=(npm ci --prefer-offline --no-audit --fund=false)

if [[ ! "$MAX_ATTEMPTS" =~ ^[0-9]+$ ]] || [[ "$MAX_ATTEMPTS" -lt 1 ]]; then
  echo "[FAIL] max attempts must be >= 1" >&2
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "[FAIL] frontend directory not found: $FRONTEND_DIR" >&2
  exit 1
fi

for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
  echo "[attempt ${attempt}/${MAX_ATTEMPTS}] ${CMD[*]}"
  if (cd "$FRONTEND_DIR" && "${CMD[@]}"); then
    echo "[OK] frontend install completed."
    exit 0
  fi

  echo "[WARN] npm ci failed on attempt ${attempt}."
  if [[ "$attempt" -lt "$MAX_ATTEMPTS" ]]; then
    echo "[ACTION] Retrying after short delay..."
    sleep 2
  fi
done

echo "[FAIL] npm ci failed after ${MAX_ATTEMPTS} attempts." >&2
echo "Recommended next actions:"
echo "1) bash scripts/bootstrap_node_from_nvmrc.sh"
echo "2) Remove frontend/node_modules and retry install."
echo "3) npm cache verify"
echo "4) Follow docs/ops/runbook_windows_node_npm_lock.md (Windows) or local platform runbook."
exit 1
