#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[compat] bootstrap_node_22.sh is deprecated. Use scripts/bootstrap_node_from_nvmrc.sh."
"${SCRIPT_DIR}/bootstrap_node_from_nvmrc.sh" "${1:-.nvmrc}"
