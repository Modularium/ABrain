#!/usr/bin/env bash
# ABrain setup bootstrap for the current canonical repository layout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="${ABRAIN_VENV_DIR:-$REPO_ROOT/.venv}"
VENV_PYTHON="$VENV_DIR/bin/python"
UI_DIR="$REPO_ROOT/frontend/agent-ui"
VENV_WAS_CREATED=false

COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_RESET='\033[0m'

log_info() {
    printf '%b[INFO]%b %s\n' "$COLOR_BLUE" "$COLOR_RESET" "$1"
}

log_ok() {
    printf '%b[ OK ]%b %s\n' "$COLOR_GREEN" "$COLOR_RESET" "$1"
}

log_warn() {
    printf '%b[WARN]%b %s\n' "$COLOR_YELLOW" "$COLOR_RESET" "$1" >&2
}

log_err() {
    printf '%b[ERR ]%b %s\n' "$COLOR_RED" "$COLOR_RESET" "$1" >&2
}

die() {
    log_err "$1"
    exit 1
}

has_command() {
    command -v "$1" >/dev/null 2>&1
}

run_checked() {
    "$@" || die "Kommando fehlgeschlagen: $*"
}

require_file() {
    local file="$1"
    local label="$2"
    [[ -f "$file" ]] || die "$label nicht gefunden: $file"
}

require_command() {
    local command_name="$1"
    local hint="$2"
    has_command "$command_name" || die "$command_name wird benötigt. $hint"
}

copy_env_template_if_missing() {
    local env_file="$REPO_ROOT/.env"
    local env_example="$REPO_ROOT/.env.example"

    require_file "$env_example" ".env-Vorlage"

    if [[ -f "$env_file" ]]; then
        log_info ".env existiert bereits, Vorlage wird nicht überschrieben"
        return 0
    fi

    run_checked cp "$env_example" "$env_file"
    log_ok ".env aus .env.example erzeugt"
}

ensure_venv() {
    require_command python3 "Installiere Python 3.10 oder neuer."

    if [[ ! -d "$VENV_DIR" ]]; then
        log_info "Erzeuge virtuelle Umgebung unter $VENV_DIR"
        run_checked python3 -m venv "$VENV_DIR"
        VENV_WAS_CREATED=true
        log_ok "Virtuelle Umgebung erstellt"
    else
        log_info "Verwende vorhandene virtuelle Umgebung: $VENV_DIR"
    fi

    [[ -x "$VENV_PYTHON" ]] || die "Python in der virtuellen Umgebung fehlt: $VENV_PYTHON"
}

upgrade_python_bootstrap_tools() {
    ensure_venv
    if [[ "$VENV_WAS_CREATED" != "true" && "${ABRAIN_REFRESH_BOOTSTRAP_TOOLS:-false}" != "true" ]]; then
        log_info "Bootstrap-Tools bereits vorhanden, Upgrade wird übersprungen"
        return 0
    fi
    log_info "Aktualisiere pip/setuptools/wheel"
    run_checked "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
    log_ok "Python-Bootstrap-Tools aktualisiert"
}

install_python_dependencies() {
    ensure_venv
    require_file "$REPO_ROOT/requirements-light.txt" "Python-Abhängigkeitsliste"
    log_info "Installiere Python-Abhängigkeiten aus requirements-light.txt"
    run_checked "$VENV_PYTHON" -m pip install -r "$REPO_ROOT/requirements-light.txt"
    log_ok "Python-Abhängigkeiten installiert"
}

install_cli_entrypoint() {
    ensure_venv
    require_file "$REPO_ROOT/pyproject.toml" "Projektmetadaten"

    log_info "Installiere Build-Backend für editable Install"
    run_checked "$VENV_PYTHON" -m pip install "poetry-core>=1.7.0"

    log_info "Regeneriere lokale editable Installation und den Entry-Point abrain-mcp"
    run_checked "$VENV_PYTHON" -m pip install -e "$REPO_ROOT" --no-deps --no-build-isolation

    [[ -x "$VENV_DIR/bin/abrain-mcp" ]] || die "Console-Entry fehlt nach Installation: $VENV_DIR/bin/abrain-mcp"
    log_ok "Editable Installation und abrain-mcp-Entry-Point sind aktuell"
}

smoke_api_gateway() {
    ensure_venv

    log_info "Prüfe API-Gateway-Import"
    "$VENV_PYTHON" - <<'PY' || die "API-Gateway-Smoke fehlgeschlagen"
from api_gateway.main import app

paths = {route.path for route in app.routes}
required = {"/control-plane/overview", "/control-plane/tasks/run", "/metrics"}
missing = sorted(required - paths)
if missing:
    raise SystemExit(f"Missing API routes: {', '.join(missing)}")
print(app.title)
PY
    log_ok "API-Gateway importierbar"
    printf 'Startpfad: %s\n' "$VENV_PYTHON -m uvicorn api_gateway.main:app --reload"
}

smoke_mcp_v2() {
    ensure_venv

    log_info "Prüfe MCP-v2-Serverlogik"
    "$VENV_PYTHON" - <<'PY' || die "MCP-v2-Smoke fehlgeschlagen"
from interfaces.mcp.server import MCPV2Server

server = MCPV2Server()
init_response = server.handle_message(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "clientInfo": {"name": "setup-smoke"},
        },
    }
)
assert init_response is not None
assert init_response["result"]["serverInfo"]["name"] == "abrain-mcp-v2"
tools_response = server.handle_message(
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
)
assert tools_response is not None
tools = tools_response["result"]["tools"]
assert tools, "No MCP tools exposed"
print(len(tools))
PY
    log_ok "MCP v2 antwortet auf initialize und tools/list"
    printf 'Startpfad: %s\n' "$VENV_PYTHON -m interfaces.mcp.server"
    if [[ -x "$VENV_DIR/bin/abrain-mcp" ]]; then
        printf 'Console-Entry: %s\n' "$VENV_DIR/bin/abrain-mcp"
    fi
}

build_ui() {
    require_command npm "Installiere Node.js 18+ und npm."
    require_file "$UI_DIR/package.json" "Frontend package.json"

    log_info "Installiere Frontend-Abhängigkeiten"
    (
        cd "$UI_DIR"
        run_checked npm ci
        run_checked npm run type-check
        run_checked npm run build
    )
    log_ok "Frontend installiert und gebaut"
    printf 'Dev-Start: %s\n' "(cd $UI_DIR && npm run dev)"
}

show_next_steps() {
    cat <<EOF

ABrain Setup abgeschlossen.

Kanonische Startpfade:
  API Gateway: $VENV_PYTHON -m uvicorn api_gateway.main:app --reload
  MCP v2:      $VENV_PYTHON -m interfaces.mcp.server
  MCP Entry:   $VENV_DIR/bin/abrain-mcp
  UI Dev:      (cd $UI_DIR && npm run dev)
  CLI Help:    $REPO_ROOT/scripts/abrain help
EOF
}

usage() {
    cat <<EOF
ABrain setup bootstrap

Usage:
  $(basename "$0") [env|deps|cli|api|mcp|ui|all|help]

Schritte:
  env    .venv anlegen/verwenden, pip-Tooling aktualisieren, .env aus Vorlage erzeugen
  deps   Python-Abhängigkeiten aus requirements-light.txt installieren
  cli    editable Installation auffrischen und den Entry-Point abrain-mcp erzeugen
  api    API-Gateway importieren und kanonischen Startpfad prüfen
  mcp    MCP-v2-Server über initialize/tools/list smoke-testen
  ui     frontend/agent-ui per npm ci, type-check und build vorbereiten
  all    kompletter Online-Bootstrap in der kanonischen Reihenfolge
  help   diese Hilfe anzeigen

Beispiele:
  ./scripts/setup.sh all
  ./scripts/setup.sh deps
  ./scripts/setup.sh cli
  ./scripts/abrain setup all
EOF
}

run_env() {
    upgrade_python_bootstrap_tools
    copy_env_template_if_missing
}

run_deps() {
    run_env
    install_python_dependencies
}

run_cli() {
    run_deps
    install_cli_entrypoint
}

run_api() {
    smoke_api_gateway
}

run_mcp() {
    smoke_mcp_v2
}

run_ui() {
    build_ui
}

run_all() {
    run_cli
    run_api
    run_mcp
    run_ui
    show_next_steps
}

main() {
    local step="${1:-all}"

    case "$step" in
        env)
            run_env
            ;;
        deps)
            run_deps
            ;;
        cli)
            run_cli
            ;;
        api)
            run_api
            ;;
        mcp)
            run_mcp
            ;;
        ui)
            run_ui
            ;;
        all)
            run_all
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            usage >&2
            die "Unbekannter Setup-Schritt: $step"
            ;;
    esac
}

main "$@"
