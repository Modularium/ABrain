#!/bin/bash
# -*- coding: utf-8 -*-
# ABrain Setup Script - Vollständige Installation und Konfiguration
# Verbesserte Version fuer den canonical services/*-Stack

set -euo pipefail

# Skript-Verzeichnis und Helpers laden
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

require_source() {
    local file="$1"
    local label="${2:-Hilfsdatei}"

    if [[ ! -f "$file" ]]; then
        printf 'ABrain setup error: fehlende %s: %s\n' "$label" "$file" >&2
        printf 'Das Setup benoetigt die historischen Verzeichnisse scripts/lib und scripts/helpers in vollstaendiger Form.\n' >&2
        printf 'Die ABrain-CLI selbst bleibt nutzbar, aber "abrain setup" kann in diesem Repository-Checkout nicht starten.\n' >&2
        exit 1
    fi

    # shellcheck disable=SC1090
    source "$file"
}

require_source "$SCRIPT_DIR/lib/log_utils.sh" "Logging-Hilfsdatei"
require_source "$SCRIPT_DIR/lib/spinner_utils.sh" "Spinner-Hilfsdatei"
require_source "$SCRIPT_DIR/helpers/common.sh" "Common-Hilfsdatei"
require_source "$SCRIPT_DIR/helpers/env.sh" "Environment-Hilfsdatei"
require_source "$SCRIPT_DIR/helpers/docker.sh" "Docker-Hilfsdatei"
require_source "$SCRIPT_DIR/helpers/frontend.sh" "Frontend-Hilfsdatei"

require_source "$SCRIPT_DIR/lib/env_check.sh" "Environment-Check-Hilfsdatei"
require_source "$SCRIPT_DIR/lib/docker_utils.sh" "Docker-Utils-Hilfsdatei"
require_source "$SCRIPT_DIR/lib/frontend_build.sh" "Frontend-Build-Hilfsdatei"
require_source "$SCRIPT_DIR/lib/install_utils.sh" "Installations-Hilfsdatei"
require_source "$SCRIPT_DIR/lib/menu_utils.sh" "Menue-Hilfsdatei"
require_source "$SCRIPT_DIR/lib/args_parser.sh" "Argument-Parser-Hilfsdatei"
require_source "$SCRIPT_DIR/lib/config_utils.sh" "Konfigurations-Hilfsdatei"
require_source "$SCRIPT_DIR/lib/preset_utils.sh" "Preset-Hilfsdatei"
# Utility functions
return_to_main_menu() {
    local delay="${1:-0}"
    if [[ $delay -gt 0 ]]; then
        echo
        echo "Drücke Enter oder warte ${delay}s..."
        read -r -t "$delay" -s || true
    fi
    clear
}

clean_environment() {
    log_info "Bereinige Entwicklungsumgebung..."
    
    # Stop und entferne Docker Container
    if [[ -f "$REPO_ROOT/docker-compose.yml" ]]; then
        log_info "Stoppe Docker Services..."
        docker-compose -f "$REPO_ROOT/docker-compose.yml" down --volumes --remove-orphans 2>/dev/null || true
    fi
    
    # Entferne Python Virtual Environment
    if [[ -d "$REPO_ROOT/.venv" ]]; then
        log_info "Entferne Python Virtual Environment..."
        rm -rf "$REPO_ROOT/.venv"
    fi
    
    # Entferne Node Modules
    if [[ -d "$REPO_ROOT/frontend/node_modules" ]]; then
        log_info "Entferne Node Modules..."
        rm -rf "$REPO_ROOT/frontend/node_modules"
    fi
    
    # Entferne Build-Artefakte
    local build_dirs=(
        "$REPO_ROOT/frontend/dist"
        "$REPO_ROOT/frontend/build"
        "$REPO_ROOT/dist"
        "$REPO_ROOT/build"
        "$REPO_ROOT/__pycache__"
        "$REPO_ROOT/.pytest_cache"
        "$REPO_ROOT/.coverage"
    )
    
    for dir in "${build_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            log_info "Entferne: $dir"
            rm -rf "$dir"
        fi
    done
    
    # Entferne Log-Dateien (aber behalte das logs-Verzeichnis)
    if [[ -d "$REPO_ROOT/logs" ]]; then
        log_info "Bereinige Log-Dateien..."
        find "$REPO_ROOT/logs" -name "*.log" -type f -delete 2>/dev/null || true
    fi
    
    # Entferne temporäre Konfigurationsdateien
    if [[ -f "$REPO_ROOT/.abrain_config" ]]; then
        log_info "Entferne temporäre ABrain-Konfiguration..."
        rm -f "$REPO_ROOT/.abrain_config"
    fi

    if [[ -f "$REPO_ROOT/.agentnn_config" ]]; then
        log_info "Entferne Legacy-Konfiguration..."
        rm -f "$REPO_ROOT/.agentnn_config"
    fi
    
    log_ok "Umgebung bereinigt"
}

show_current_config() {
    echo
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        Aktuelle Konfiguration                               ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo
    
    echo "🔧 Setup-Konfiguration:"
    echo "   Poetry-Methode: ${POETRY_METHOD:-nicht gesetzt}"
    echo "   Auto-Modus: ${AUTO_MODE:-false}"
    echo "   Frontend bauen: ${BUILD_FRONTEND:-true}"
    echo "   Docker starten: ${START_DOCKER:-true}"
    echo "   Historische MCP-Laufzeit aktiv: ${START_MCP:-false}"
    echo "   Preset: ${PRESET:-keines}"
    echo
    
    echo "📁 Verzeichnisse:"
    echo "   Repository: $REPO_ROOT"
    echo "   Script-Verzeichnis: $SCRIPT_DIR"
    echo "   Log-Datei: ${LOG_FILE:-nicht gesetzt}"
    echo
    
    echo "🌐 Umgebung:"
    echo "   Python: $(python3 --version 2>/dev/null || echo 'nicht gefunden')"
    echo "   Node.js: $(node --version 2>/dev/null || echo 'nicht gefunden')"
    echo "   Docker: $(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',' || echo 'nicht gefunden')"
    echo "   Poetry: $(poetry --version 2>/dev/null | cut -d' ' -f3 || echo 'nicht gefunden')"
    echo
    
    echo "📊 Status-Dateien:"
    if [[ -f "$PROJECT_CONFIG_FILE" ]]; then
        echo "   Projekt-Config: $PROJECT_CONFIG_FILE (vorhanden)"
        if [[ -s "$PROJECT_CONFIG_FILE" ]]; then
            echo "   Gespeicherte Werte:"
            while IFS='=' read -r key value; do
                [[ "$key" =~ ^[[:space:]]*# ]] && continue
                [[ -n "$key" ]] && echo "     $key = $value"
            done < "$PROJECT_CONFIG_FILE"
        fi
    else
        echo "   Projekt-Config: $PROJECT_CONFIG_FILE (nicht vorhanden)"
    fi
    
    if [[ -f "$STATUS_FILE" ]]; then
        echo "   Status-Datei: $STATUS_FILE (vorhanden)"
    else
        echo "   Status-Datei: ${STATUS_FILE:-nicht gesetzt} (nicht vorhanden)"
    fi
    
    echo
}

# Poetry-Method initialisieren
POETRY_METHOD="${POETRY_METHOD:-venv}"
export POETRY_METHOD
require_source "$SCRIPT_DIR/lib/status_utils.sh" "Status-Hilfsdatei"

# Globale Variablen
SCRIPT_NAME="$(basename "$0")"
LOG_FILE="$REPO_ROOT/logs/setup.log"
BUILD_FRONTEND=true
START_DOCKER=true
START_MCP=false
VERBOSE=false
INSTALL_HEAVY=false
WITH_DOCKER=false
AUTO_MODE=false
RUN_MODE="full"
EXIT_ON_FAIL=false
RECOVERY_MODE=false
LOG_ERROR_FILE=""
SUDO_CMD=""
PRESET=""
SETUP_TIMEOUT=300  # 5 Minuten Timeout für einzelne Schritte

usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

ABrain Setup Script - Vollständige Installation und Konfiguration

OPTIONS:
    -h, --help              Diese Hilfe anzeigen
    -v, --verbose           Ausführliche Ausgabe aktivieren
    --no-frontend           Frontend-Build überspringen
    --skip-docker           Docker-Start überspringen
    --check-only            Nur Umgebungsprüfung durchführen
    --check                 Nur Validierung ausführen und beenden
    --install-heavy         Zusätzliche Heavy-Dependencies installieren
    --with-docker          Abbruch wenn docker-compose.yml fehlt
    --with-sudo            Paketinstallation mit sudo ausführen
    --auto-install         Fehlende Abhängigkeiten automatisch installieren
    --full                  Komplettes Setup ohne Nachfragen
    --minimal               Nur Python-Abhängigkeiten installieren
    --no-docker             Setup ohne Docker-Schritte
    --exit-on-fail          Bei Fehlern sofort abbrechen
    --recover               Fehlgeschlagenes Setup wiederaufnehmen
    --preset <name>         Vordefinierte Einstellungen laden (dev|ci|minimal)
    --clean                 Entwicklungsumgebung zurücksetzen
    --timeout <seconds>     Timeout für Benutzer-Eingaben (default: 300)

BEISPIELE:
    $SCRIPT_NAME                    # Vollständiges Setup
    $SCRIPT_NAME --check-only       # Nur Umgebungsprüfung
    $SCRIPT_NAME --skip-docker      # Setup ohne Docker-Start
    $SCRIPT_NAME --auto-install    # Keine Rückfragen bei Abhängigkeitsinstallation

VORAUSSETZUNGEN:
    - Python 3.9+
    - Node.js 18+
    - Docker & Docker Compose
    - Poetry
    - Git

EOF
}

# Verbesserte interaktive Menü-Funktion
interactive_menu() {
    local options=(
        "💡 Schnellstart (Vollständige Installation)"
        "🧱 Systemabhängigkeiten (Docker, Node.js, Python)"
        "🐍 Python & Poetry (Nur Python-Umgebung)"
        "🎨 Frontend bauen (React-Frontend)"
        "🐳 Docker-Services (Standard Services starten)"
        "🔗 Legacy MCP-Services (disabled)"
        "🧪 Tests & CI (Testlauf)"
        "🔁 Reparatur (Umgebung reparieren)"
        "📊 Status anzeigen (Systemstatus)"
        "⚙️ Konfiguration anzeigen"
        "🧹 Umgebung bereinigen"
        "❌ Beenden"
    )
    
    local count=${#options[@]}
    local choice=""
    local attempts=0
    local max_attempts=3
    
    while [[ $attempts -lt $max_attempts ]]; do
        echo "╔══════════════════════════════════════════════════════════════════════════════╗"
        echo "║                               ABrain Setup                                  ║"
        echo "╠══════════════════════════════════════════════════════════════════════════════╣"
        echo "║  Wähle eine Aktion:                                                         ║"
        echo "╠══════════════════════════════════════════════════════════════════════════════╣"
        
        for i in "${!options[@]}"; do
            printf "║  [%2d] %-69s ║\n" "$((i + 1))" "${options[$i]}"
        done
        
        echo "╚══════════════════════════════════════════════════════════════════════════════╝"
        echo
        
        # Prüfe ob whiptail verfügbar ist
        if command -v whiptail >/dev/null 2>&1 && [[ -t 0 ]] && [[ -t 1 ]]; then
            local menu_items=()
            for i in "${!options[@]}"; do
                menu_items+=("$((i + 1))" "${options[$i]}")
            done
            
            if choice=$(whiptail --title "ABrain Setup" --menu "Aktion wählen:" 20 78 12 "${menu_items[@]}" 3>&1 1>&2 2>&3); then
                case $choice in
                    1) RUN_MODE="full" ;;
                    2) RUN_MODE="system" ;;
                    3) RUN_MODE="python" ;;
                    4) RUN_MODE="frontend" ;;
                    5) RUN_MODE="docker" ;;
                    6) RUN_MODE="mcp" ;;
                    7) RUN_MODE="test" ;;
                    8) RUN_MODE="repair" ;;
                    9) RUN_MODE="status" ;;
                    10) RUN_MODE="show_config" ;;
                    11) RUN_MODE="clean" ;;
                    12) RUN_MODE="exit" ;;
                    *) RUN_MODE="exit" ;;
                esac
                return 0
            else
                RUN_MODE="exit"
                return 0
            fi
        else
            # Fallback zu normaler Eingabe
            choice=$(safe_menu_input "Auswahl [1-${count}]: " 30 "1")
            
            case $choice in
                1) RUN_MODE="full"; break ;;
                2) RUN_MODE="system"; break ;;
                3) RUN_MODE="python"; break ;;
                4) RUN_MODE="frontend"; break ;;
                5) RUN_MODE="docker"; break ;;
                6) RUN_MODE="mcp"; break ;;
                7) RUN_MODE="test"; break ;;
                8) RUN_MODE="repair"; break ;;
                9) RUN_MODE="status"; break ;;
                10) RUN_MODE="show_config"; break ;;
                11) RUN_MODE="clean"; break ;;
                12) RUN_MODE="exit"; break ;;
                ""|q|Q) RUN_MODE="exit"; break ;;
                *)
                    attempts=$((attempts + 1))
                    log_warn "Ungültige Auswahl: $choice"
                    if [[ $attempts -ge $max_attempts ]]; then
                        log_warn "Zu viele ungültige Eingaben. Verwende Schnellstart."
                        RUN_MODE="full"
                        break
                    fi
                    echo "Bitte wähle eine Zahl zwischen 1 und $count."
                    echo "Drücke Enter für Schnellstart oder q zum Beenden."
                    sleep 2
                    ;;
            esac
        fi
    done
    
    if [[ -z "$RUN_MODE" ]]; then
        RUN_MODE="full"
    fi
    
    log_info "Gewählte Aktion: $RUN_MODE"
}

# Verbesserte Poetry-Installation mit System-Paket-Fix
install_poetry_fixed() {
    log_info "Installiere Poetry mit verbesserter Methode..."
    
    # Prüfe und installiere python3-venv falls nötig
    if ! python3 -m venv --help &>/dev/null; then
        log_info "python3-venv fehlt - installiere System-Paket..."
        require_sudo_if_needed || return 1
        
        if command -v apt-get >/dev/null; then
            $SUDO_CMD apt-get update -y >/dev/null 2>&1
            $SUDO_CMD apt-get install -y python3-venv python3-pip >/dev/null 2>&1
        elif command -v yum >/dev/null; then
            $SUDO_CMD yum install -y python3-venv python3-pip >/dev/null 2>&1
        elif command -v dnf >/dev/null; then
            $SUDO_CMD dnf install -y python3-venv python3-pip >/dev/null 2>&1
        else
            log_err "Kann python3-venv nicht installieren - unbekannter Paketmanager"
            return 1
        fi
    fi
    
    # Versuche Poetry über verschiedene Methoden zu installieren
    case "${POETRY_METHOD:-venv}" in
        system)
            python3 -m pip install --break-system-packages poetry >/dev/null 2>&1
            ;;
        venv)
            if python3 -m venv "$REPO_ROOT/.venv"; then
                source "$REPO_ROOT/.venv/bin/activate"
                pip install poetry >/dev/null 2>&1

                # Füge zu .bashrc hinzu falls nicht vorhanden
                if ! grep -Eq "abrain_repo_venv|agentnn_repo_venv" "$HOME/.bashrc" 2>/dev/null; then
                    echo "# ABrain venv" >> "$HOME/.bashrc"
                    echo "source $REPO_ROOT/.venv/bin/activate # abrain_repo_venv" >> "$HOME/.bashrc"
                fi
            else
                return 1
            fi
            ;;
        pipx)
            if ! command -v pipx >/dev/null; then
                require_sudo_if_needed || return 1
                $SUDO_CMD apt-get install -y pipx >/dev/null 2>&1
            fi
            pipx install poetry >/dev/null 2>&1
            ;;
    esac
}

# Verbesserte ensure_poetry Funktion
ensure_poetry_improved() {
    ensure_pip || return 1
    
    # Prüfe ob Poetry bereits verfügbar ist
    if check_poetry_available; then 
        return 0
    fi
    
    # Im Auto-Modus: Verwende verbesserte Installation
    if [[ "$AUTO_MODE" == "true" ]]; then
        log_info "Auto-Modus: Installiere Poetry mit verbesserter Methode..."
        POETRY_METHOD="venv"
        export POETRY_METHOD
        save_config_value "POETRY_METHOD" "$POETRY_METHOD"
        install_poetry_fixed || return 1
    else
        # Interaktive Installation
        save_config_value "POETRY_INSTALL_ATTEMPTED" "true"
        install_poetry_interactive || return 130
    fi
    
    if ! check_poetry_available; then
        echo "[✗] Poetry konnte nicht installiert werden."
        return 130
    fi
    return 0
}

# LEGACY (disabled): not part of canonical runtime
start_mcp_services() {
    log_err "Legacy MCP runtime is disabled; use docker-compose.yml and services/*"
    return 1
}

# Erweiterte Preset-Anwendung
apply_preset_improved() {
    local preset="$1"
    validate_preset "$preset" || return 1
    PRESET="$preset"
    case "$preset" in
        dev)
            RUN_MODE="full"
            BUILD_FRONTEND=true
            START_DOCKER=true
            START_MCP=false
            ;;
        ci)
            RUN_MODE="test"
            BUILD_FRONTEND=false
            START_DOCKER=false
            START_MCP=false
            ;;
        minimal)
            RUN_MODE="python"
            BUILD_FRONTEND=false
            START_DOCKER=false
            START_MCP=false
            ;;
        mcp)
            log_err "Preset 'mcp' ist deaktiviert; canonical runtime ist services/*"
            return 1
            ;;
    esac
}

# Verbesserte Docker-Compose Erkennung
find_docker_compose_improved() {
    local search_paths=(
        "$REPO_ROOT/docker-compose.yml"
        "$REPO_ROOT/docker-compose.yaml"
        "$REPO_ROOT/deploy/docker-compose.yml"
        "$REPO_ROOT/deploy/docker-compose.yaml"
        "$REPO_ROOT/docker/docker-compose.yml"
        "$REPO_ROOT/docker/docker-compose.yaml"
    )
    
    for file in "${search_paths[@]}"; do
        if [[ -f "$file" ]]; then
            echo "$file"
            return 0
        fi
    done
    
    # Suche nach alternativen Compose-Dateien
    local alternatives
    mapfile -t alternatives < <(find "$REPO_ROOT" -maxdepth 2 -name 'docker-compose*.yml' -o -name 'docker-compose*.yaml' 2>/dev/null)
    
    if [[ ${#alternatives[@]} -gt 0 ]]; then
        if [[ ${#alternatives[@]} -gt 1 ]]; then
            log_warn "Mehrere Compose-Dateien gefunden:"
            for file in "${alternatives[@]}"; do
                log_warn "  - $file"
            done
            log_info "Verwende erste Datei: ${alternatives[0]}"
        fi
        echo "${alternatives[0]}"
        return 0
    fi
    
    return 1
}

# Verbesserte Argument-Behandlung
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                export DEBUG=1
                shift
                ;;
            --no-frontend)
                BUILD_FRONTEND=false
                shift
                ;;
            --skip-docker)
                START_DOCKER=false
                shift
                ;;
            --with-mcp)
                log_err "--with-mcp ist deaktiviert; canonical runtime ist services/*"
                exit 1
                ;;
            --check-only)
                BUILD_FRONTEND=false
                START_DOCKER=false
                START_MCP=false
                RUN_MODE="check"
                shift
                ;;
            --check)
                RUN_MODE="check"
                BUILD_FRONTEND=false
                START_DOCKER=false
                START_MCP=false
                shift
                ;;
            --install-heavy)
                INSTALL_HEAVY=true
                shift
                ;;
            --with-docker)
                WITH_DOCKER=true
                shift
                ;;
            --with-sudo)
                SUDO_CMD="sudo"
                shift
                ;;
            --full)
                AUTO_MODE=true
                RUN_MODE="full"
                shift
                ;;
            --minimal)
                START_DOCKER=false
                START_MCP=false
                BUILD_FRONTEND=false
                AUTO_MODE=true
                RUN_MODE="python"
                shift
                ;;
            --no-docker)
                START_DOCKER=false
                START_MCP=false
                shift
                ;;
            --exit-on-fail)
                EXIT_ON_FAIL=true
                shift
                ;;
            --recover)
                RECOVERY_MODE=true
                AUTO_MODE=true
                shift
                ;;
            --auto-install)
                AUTO_MODE=true
                shift
                ;;
            --preset)
                shift
                PRESET="$1"
                apply_preset_improved "$PRESET" || {
                    log_err "Unbekanntes Preset: $PRESET"
                    exit 1
                }
                shift
                ;;
            --timeout)
                shift
                SETUP_TIMEOUT="$1"
                shift
                ;;
            --clean)
                clean_environment
                exit 0
                ;;
            *)
                log_err "Unbekannte Option: $1"
                usage >&2
                exit 1
                ;;
        esac
    done
}

# Setup-Initialisierung
setup_initialization() {
    setup_error_handling
    ensure_utf8
    setup_logging
    load_config || true
    load_project_config || true
    ensure_config_file_exists

    # Ensure POETRY_METHOD is initialized
    POETRY_METHOD=$(load_config_value "POETRY_METHOD" "venv")
    if [ -z "$POETRY_METHOD" ]; then
        log_info "🔧 Kein gespeicherter Wert für POETRY_METHOD – verwende Default: venv"
        POETRY_METHOD="venv"
        save_config_value "POETRY_METHOD" "$POETRY_METHOD"
    fi
    export POETRY_METHOD
}

# Haupt-Setup-Ausführung
execute_setup_mode() {
    local mode="$1"
    
    case "$mode" in
        python)
            run_step "Python-Abhängigkeiten" install_python_dependencies
            ;;
        frontend)
            run_step "Frontend-Build" build_frontend
            ;;
        docker)
            local compose_file
            if compose_file=$(find_docker_compose_improved); then
                run_step "Docker-Services" "docker_compose_up \"$compose_file\""
            else
                log_err "Keine Docker-Compose-Datei gefunden"
                return 1
            fi
            ;;
        mcp)
            log_err "Legacy MCP runtime ist deaktiviert"
            return 1
            ;;
        system)
            run_step "System-Abhängigkeiten" "${SCRIPT_DIR}/install_dependencies.sh ${SUDO_CMD:+--with-sudo} --auto-install"
            ;;
        repair)
            run_step "Repariere" "${SCRIPT_DIR}/repair_env.sh"
            ;;
        show_config)
            show_current_config
            ;;
        test)
            run_step "Tests" run_project_tests
            ;;
        check)
            run_step "Validierung" "bash ${SCRIPT_DIR}/validate.sh" && exit 0
            ;;
        status)
            run_step "Status-Prüfung" "${SCRIPT_DIR}/status.sh" && exit 0
            ;;
        clean)
            clean_environment
            ;;
        full)
            # Vollständiges Setup
            log_info "=== PYTHON-ABHÄNGIGKEITEN ==="
            run_step "Python-Abhängigkeiten" install_python_dependencies

            if [[ "$BUILD_FRONTEND" == "true" ]]; then
                log_info "=== FRONTEND-BUILD ==="
                run_step "Frontend-Build" build_frontend
                cd "$REPO_ROOT"
            fi

            if [[ "$START_DOCKER" == "true" ]]; then
                log_info "=== DOCKER-SERVICES ==="
                local compose_file
                if compose_file=$(find_docker_compose_improved); then
                    run_step "Docker-Services" "docker_compose_up \"$compose_file\""
                elif [[ "$WITH_DOCKER" == "true" ]]; then
                    log_err "Docker Compose Datei nicht gefunden. Setup abgebrochen."
                    exit 1
                fi
            fi

            if [[ "$START_MCP" == "true" ]]; then
                log_err "Legacy MCP runtime ist deaktiviert"
                return 1
            fi

            log_info "=== VERIFIZIERUNG ==="
            run_step "Verifizierung" verify_installation || log_warn "Verifizierung mit Problemen abgeschlossen"

            run_step "Tests" run_project_tests || true
            update_status "last_setup" "$(date -u +%FT%TZ)" "$REPO_ROOT/.abrain/status.json"
            print_next_steps
            ;;
        *)
            log_err "Unbekannter Modus: $mode"
            return 1
            ;;
    esac
}

# Haupt-Funktion
main() {
    local original_args=("$@")
    local arg_count=$#
    
    setup_initialization
    parse_arguments "$@"
    export SUDO_CMD AUTO_MODE

    while true; do
        if [[ $arg_count -eq 0 ]]; then
            echo "📦 Gewählte Installationsmethode: ${POETRY_METHOD:-nicht gesetzt}"
            interactive_menu
            [[ "$RUN_MODE" == "exit" ]] && break
        fi

        # Banner anzeigen
        print_banner

        STATUS_FILE="$REPO_ROOT/.abrain/status.json"
        ensure_status_file "$STATUS_FILE"
        if [[ -n "$PRESET" ]]; then
            log_preset "$PRESET" "$STATUS_FILE"
        fi

        cd "$REPO_ROOT" || {
            log_err "Kann nicht ins Repository-Verzeichnis wechseln: $REPO_ROOT"
            exit 1
        }

        # Umgebungsprüfung
        log_info "=== UMGEBUNGSPRÜFUNG ==="
        if ! mapfile -t missing_pkgs < <(check_environment); then
            if [[ ${#missing_pkgs[@]} -gt 0 ]]; then
                log_warn "Fehlende Pakete: ${missing_pkgs[*]}"
                for pkg in "${missing_pkgs[@]}"; do
                    prompt_and_install_if_missing "$pkg" || true
                done
            fi
        fi

        # Verbesserte Komponenten-Installation
        run_step "Prüfe Docker" ensure_docker; [[ $? -eq 130 ]] && { RUN_MODE=""; arg_count=0; return_to_main_menu; continue; }
        run_step "Prüfe Node.js" ensure_node; [[ $? -eq 130 ]] && { RUN_MODE=""; arg_count=0; return_to_main_menu; continue; }
        run_step "Prüfe Python" ensure_python; [[ $? -eq 130 ]] && { RUN_MODE=""; arg_count=0; return_to_main_menu; continue; }
        run_step "Prüfe Poetry" ensure_poetry_improved; [[ $? -eq 130 ]] && { RUN_MODE=""; arg_count=0; return_to_main_menu; continue; }
        run_step "Prüfe Tools" ensure_python_tools; [[ $? -eq 130 ]] && { RUN_MODE=""; arg_count=0; return_to_main_menu; continue; }

        # Setup-Modus ausführen
        execute_setup_mode "$RUN_MODE"

        if [[ $arg_count -eq 0 ]]; then
            return_to_main_menu 3
        fi

        if [[ $arg_count -gt 0 ]]; then
            break
        fi
        RUN_MODE=""
    done
}

# Script ausführen falls direkt aufgerufen
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
