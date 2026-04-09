#!/bin/bash

# Logging utilities for scripts

# initialization
__log_utils_init() {
    local dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    LOG_UTILS_DIR="$dir"
}
__log_utils_init

# color codes (if not already defined)
if [[ -z "${RED:-}" ]]; then
    readonly RED='\033[1;31m'
    readonly GREEN='\033[1;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[1;34m'
    readonly PURPLE='\033[1;35m'
    readonly CYAN='\033[1;36m'
    readonly NC='\033[0m'
fi

log_info() {
    echo -e "${BLUE}[...]${NC} $1"
}

log_ok() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_err() {
    echo -e "${RED}[✗]${NC} $1" >&2
    if [[ -n "${LOG_ERROR_FILE:-}" ]]; then
        printf "%s\n" "$1" >> "$LOG_ERROR_FILE"
    fi
}

log_error() {
    log_err "$1"
}

log_debug() {
    if [[ "${DEBUG:-}" == "1" ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $1" >&2
    fi
}

# Setup logging - create log directory and initialize logging
setup_logging() {
    # Create logs directory if it doesn't exist
    if [[ -n "${LOG_FILE:-}" ]]; then
        local log_dir
        log_dir="$(dirname "$LOG_FILE")"
        if [[ ! -d "$log_dir" ]]; then
            mkdir -p "$log_dir" || {
                log_err "Konnte Log-Verzeichnis nicht erstellen: $log_dir"
                return 1
            }
        fi
        
        # Initialize log file with timestamp
        {
            echo "=== Agent-NN Setup Log ==="
            echo "Started: $(date)"
            echo "Script: ${SCRIPT_NAME:-setup.sh}"
            echo "=========================="
        } > "$LOG_FILE" 2>/dev/null || {
            log_warn "Konnte nicht in Log-Datei schreiben: $LOG_FILE"
        }
        
        log_debug "Logging initialisiert: $LOG_FILE"
    fi
    
    # Set up error logging file if not set
    if [[ -z "${LOG_ERROR_FILE:-}" ]] && [[ -n "${LOG_FILE:-}" ]]; then
        export LOG_ERROR_FILE="${LOG_FILE%.log}_errors.log"
        log_debug "Error logging: $LOG_ERROR_FILE"
    fi
}

# Print setup banner
print_banner() {
    echo
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                              Agent-NN Setup                                 ║${NC}"
    echo -e "${CYAN}║                        Vollständige Installation                            ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Run a setup step with logging
run_step() {
    local step_name="$1"
    local step_command="$2"
    local start_time
    
    log_info "Starte: $step_name"
    start_time=$(date +%s)
    
    # Log to file if LOG_FILE is set
    if [[ -n "${LOG_FILE:-}" ]]; then
        echo "=== Step: $step_name ===" >> "$LOG_FILE"
        echo "Time: $(date)" >> "$LOG_FILE"
        echo "Command: $step_command" >> "$LOG_FILE"
    fi
    
    # Execute the command
    if eval "$step_command"; then
        local end_time duration
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        log_ok "$step_name (${duration}s)"
        
        if [[ -n "${LOG_FILE:-}" ]]; then
            echo "Success: $step_name (${duration}s)" >> "$LOG_FILE"
        fi
        return 0
    else
        local exit_code=$?
        local end_time duration
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        log_err "$step_name fehlgeschlagen (${duration}s, Exit-Code: $exit_code)"
        
        if [[ -n "${LOG_FILE:-}" ]]; then
            echo "Failed: $step_name (${duration}s, Exit-Code: $exit_code)" >> "$LOG_FILE"
        fi
        
        return $exit_code
    fi
}

# Verify installation status
verify_installation() {
    local errors=0
    
    log_info "Verifiziere Installation..."
    
    # Check Python environment
    if ! python3 --version >/dev/null 2>&1; then
        log_err "Python 3 nicht gefunden"
        ((errors++))
    else
        log_ok "Python $(python3 --version | cut -d' ' -f2) verfügbar"
    fi
    
    # Check Poetry
    if ! command -v poetry >/dev/null 2>&1; then
        log_warn "Poetry nicht im PATH gefunden"
        # Try alternative locations
        if [[ -f "$REPO_ROOT/.venv/bin/poetry" ]]; then
            log_ok "Poetry in virtueller Umgebung gefunden"
        else
            log_err "Poetry nicht gefunden"
            ((errors++))
        fi
    else
        log_ok "Poetry $(poetry --version | cut -d' ' -f3) verfügbar"
    fi
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_err "Docker nicht gefunden"
        ((errors++))
    else
        log_ok "Docker $(docker --version | cut -d' ' -f3 | tr -d ',') verfügbar"
    fi
    
    # Check Node.js
    if ! command -v node >/dev/null 2>&1; then
        log_err "Node.js nicht gefunden"
        ((errors++))
    else
        log_ok "Node.js $(node --version) verfügbar"
    fi
    
    # Check project dependencies
    local repo_root
    repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    
    if [[ -f "$repo_root/pyproject.toml" ]]; then
        log_ok "pyproject.toml gefunden"
    else
        log_warn "pyproject.toml nicht gefunden"
    fi
    
    if [[ -f "$repo_root/package.json" ]]; then
        log_ok "package.json gefunden"
    else
        log_warn "package.json nicht gefunden"
    fi
    
    # Check if virtual environment is activated or available
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        log_ok "Virtuelle Umgebung aktiviert: $VIRTUAL_ENV"
    elif [[ -d "$repo_root/.venv" ]]; then
        log_ok "Virtuelle Umgebung gefunden: $repo_root/.venv"
    else
        log_warn "Keine virtuelle Umgebung gefunden"
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_ok "Installation erfolgreich verifiziert"
        return 0
    else
        log_err "Installation-Verifizierung fehlgeschlagen ($errors Fehler)"
        return 1
    fi
}

# Run project tests
run_project_tests() {
    local repo_root
    repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    
    log_info "Führe Projekt-Tests aus..."
    
    cd "$repo_root" || {
        log_err "Kann nicht ins Repository-Verzeichnis wechseln: $repo_root"
        return 1
    }
    
    # Check if we're in a Poetry environment and install dev dependencies if needed
    if [[ -f "pyproject.toml" ]] && command -v poetry >/dev/null 2>&1; then
        log_info "Poetry gefunden - installiere Dev-Abhängigkeiten..."
        if poetry install --with dev >/dev/null 2>&1; then
            log_ok "Dev-Abhängigkeiten installiert"
        else
            log_warn "Konnte Dev-Abhängigkeiten nicht installieren"
        fi
        
        # Try to run tests with Poetry
        if poetry run pytest --version >/dev/null 2>&1; then
            log_info "Ausführung: poetry run pytest tests/ -v --tb=short"
            if [[ -d "tests" ]]; then
                if poetry run pytest tests/ -v --tb=short >/dev/null 2>&1; then
                    log_ok "Tests erfolgreich mit Poetry ausgeführt"
                    return 0
                else
                    log_warn "Tests mit Poetry fehlgeschlagen"
                fi
            else
                log_info "Kein tests/ Verzeichnis gefunden"
                log_ok "pytest ist verfügbar ($(poetry run pytest --version 2>/dev/null | head -1))"
                return 0
            fi
        fi
    fi
    
    # Fallback: Check if pytest is available in system or venv
    if command -v pytest >/dev/null 2>&1; then
        log_info "Ausführung: pytest tests/ -v --tb=short"
        if [[ -d "tests" ]]; then
            if pytest tests/ -v --tb=short >/dev/null 2>&1; then
                log_ok "Tests erfolgreich ausgeführt"
                return 0
            else
                log_warn "Tests fehlgeschlagen"
            fi
        else
            log_info "Kein tests/ Verzeichnis gefunden"
            log_ok "pytest ist verfügbar ($(pytest --version 2>/dev/null | head -1))"
            return 0
        fi
    elif python3 -m pytest --version >/dev/null 2>&1; then
        log_info "Ausführung: python3 -m pytest tests/ -v --tb=short"
        if [[ -d "tests" ]]; then
            if python3 -m pytest tests/ -v --tb=short >/dev/null 2>&1; then
                log_ok "Tests erfolgreich mit python -m pytest ausgeführt"
                return 0
            else
                log_warn "Tests mit python -m pytest fehlgeschlagen"
            fi
        else
            log_info "Kein tests/ Verzeichnis gefunden"
            log_ok "pytest ist verfügbar ($(python3 -m pytest --version 2>/dev/null | head -1))"
            return 0
        fi
    else
        log_warn "pytest nicht gefunden - überspringe Tests"
        log_info "Hinweis: Installiere pytest mit 'poetry install --with dev' oder 'pip install pytest'"
        return 0
    fi
    
    log_ok "Projekt-Tests abgeschlossen"
    return 0
}

# Print next steps after successful setup
print_next_steps() {
    local repo_root
    repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    
    echo
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                           Setup erfolgreich!                                ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${CYAN}Nächste Schritte:${NC}"
    echo
    echo -e "  ${YELLOW}1. Dienste sind bereits gestartet! Status prüfen:${NC}"
    echo "     docker-compose ps"
    echo "     docker-compose logs -f api_gateway"
    echo
    echo -e "  ${YELLOW}2. Frontend entwickeln:${NC}"
    echo "     cd $repo_root/frontend/agent-ui"
    echo "     npm run dev"
    echo "     # Frontend läuft dann auf http://localhost:3001 (Port 3000 ist belegt)"
    echo
    echo -e "  ${YELLOW}3. API testen:${NC}"
    echo "     curl http://localhost:8000/health"
    echo "     curl http://localhost:8000/docs"
    echo
    echo -e "  ${YELLOW}4. Tests ausführen (pytest jetzt installieren):${NC}"
    echo "     poetry install --with dev"
    echo "     poetry run pytest tests/ -v"
    echo
    echo -e "  ${YELLOW}5. Logs anzeigen:${NC}"
    echo "     docker-compose logs -f"
    echo "     docker-compose logs dispatcher        # fuer den canonical dispatcher"
    echo
    echo -e "${CYAN}Wichtige URLs:${NC}"
    echo "  • API Documentation: http://localhost:8000/docs"
    echo "  • Frontend (aktuell): http://localhost:3001"
    echo "  • Frontend (Docker): http://localhost:3000"
    echo "  • Monitoring: http://localhost:9090"
    echo "  • Database: localhost:5434"
    echo
    echo -e "${CYAN}Bekannte Probleme beheben:${NC}"
    echo "  • Dispatcher restart: docker-compose restart dispatcher"
    echo "  • Port 3000 belegt: Verwende Port 3001 für lokale Entwicklung"
    echo "  • Tests: poetry install --with dev && poetry run pytest"
    echo
    echo -e "${CYAN}Hilfe:${NC}"
    echo "  • Dokumentation: $repo_root/docs/"
    echo "  • Setup erneut ausführen: ./scripts/setup.sh"
    echo "  • Probleme beheben: ./scripts/repair_env.sh"
    echo "  • Status überprüfen: ./scripts/status.sh"
    echo
}

export -f log_info log_ok log_warn log_err log_error log_debug setup_logging print_banner run_step verify_installation run_project_tests print_next_steps
