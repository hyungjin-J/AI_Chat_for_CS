#!/usr/bin/env bash
set -euo pipefail

NVMRC_PATH="${1:-.nvmrc}"

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

read_required_version() {
  if [[ ! -f "$NVMRC_PATH" ]]; then
    fail ".nvmrc not found: $NVMRC_PATH"
  fi

  local first_line
  first_line="$(grep -v '^[[:space:]]*#' "$NVMRC_PATH" | grep -v '^[[:space:]]*$' | head -n1 || true)"
  if [[ -z "$first_line" ]]; then
    fail ".nvmrc is empty: $NVMRC_PATH"
  fi

  echo "${first_line#v}" | tr -d '[:space:]'
}

read_current_version() {
  if ! command -v node >/dev/null 2>&1; then
    echo ""
    return
  fi
  node -v 2>/dev/null | sed 's/^v//'
}

load_nvm() {
  if command -v nvm >/dev/null 2>&1; then
    return 0
  fi

  if [[ -n "${NVM_DIR:-}" && -s "${NVM_DIR}/nvm.sh" ]]; then
    # shellcheck source=/dev/null
    . "${NVM_DIR}/nvm.sh"
  fi

  if command -v nvm >/dev/null 2>&1; then
    return 0
  fi

  if [[ -s "${HOME}/.nvm/nvm.sh" ]]; then
    # shellcheck source=/dev/null
    . "${HOME}/.nvm/nvm.sh"
  fi

  command -v nvm >/dev/null 2>&1
}

required="$(read_required_version)"
current="$(read_current_version)"

if [[ "$current" == "$required" ]]; then
  echo "[OK] Node runtime already matches .nvmrc (${required})."
  echo "[NEXT] Continue with: npm ci --prefer-offline --no-audit --fund=false"
  exit 0
fi

if [[ -n "$current" ]]; then
  echo "[ACTION] Node mismatch detected (current=${current} required=${required})."
else
  echo "[ACTION] Node runtime is not available in PATH (required=${required})."
fi

if load_nvm; then
  echo "[ACTION] Trying automatic recovery with nvm install/use..."
  nvm install "$required"
  nvm use "$required"

  after="$(read_current_version)"
  if [[ "$after" == "$required" ]]; then
    echo "[OK] Node runtime switched to ${after}."
    echo "[NEXT] Re-run gate: python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime"
    exit 0
  fi

  fail "Node is still mismatched after nvm use (current=${after} required=${required})"
fi

echo "[ACTION] nvm was not found."
echo "1) Install nvm (macOS/Linux): https://github.com/nvm-sh/nvm#installing-and-updating"
echo "2) Re-open terminal so PATH is refreshed."
echo "3) Run: nvm install ${required}"
echo "4) Run: nvm use ${required}"
echo "5) Re-run gate: python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime"
echo "[ALT] Direct installer fallback: https://nodejs.org/en/download (select v${required})"
exit 1
