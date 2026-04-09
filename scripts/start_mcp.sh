#!/bin/bash
# LEGACY (disabled): not part of canonical runtime

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/log_utils.sh"

usage() {
    cat << EOF
Usage: $(basename "$0") [COMMAND]

Legacy MCP runtime management is disabled.
Use the canonical services stack via docker-compose.yml and services/*.
EOF
}

main() {
    if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
        usage
        exit 0
    fi

    log_err "Legacy MCP runtime is disabled and not part of the canonical ABrain stack"
    log_err "Use docker-compose.yml or scripts/start_docker.sh for the services/* runtime"
    exit 1
}

main "$@"
