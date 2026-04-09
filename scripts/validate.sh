#!/bin/bash
#!/bin/bash
# -*- coding: utf-8 -*-
# Umfassendes Validierungs-Script für Agent-NN

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

source "$SCRIPT_DIR/lib/log_utils.sh"
source "$SCRIPT_DIR/lib/env_check.sh"
source "$SCRIPT_DIR/lib/docker_utils.sh"
source "$SCRIPT_DIR/lib/install_utils.sh"
source "$SCRIPT_DIR/lib/status_utils.sh"
source "$SCRIPT_DIR/helpers/common.sh"
source "$SCRIPT_DIR/helpers/env.sh"
source "$SCRIPT_DIR/helpers/docker.sh"

# Validierungs-Konfiguration
VALIDATION_TIMEOUT=30
DETAILED_OUTPUT=false
FIX_ISSUES=false
CHECK_SERVICES=true
CHECK_DEPENDENCIES=true
CHECK_CONFIGURATION=true
CHECK_PERMISSIONS=true

# Validierungs-Kategorien
declare -A VALIDATION_CATEGORIES=(
    [system]="System-Abhängigkeiten und Basis-Tools"
    [python]="Python-Umgebung und Pakete" 
    [node]="Node.js und Frontend-Abhängigkeiten"
    [docker]="Docker und Container-Services"
    [mcp]="MCP Services und Konfiguration"
    [config]="Konfigurationsdateien und Umgebungsvariablen"
    [permissions]="Dateiberechtigungen und Zugriffe"
    [network]="Netzwerk und Port-Verfügbarkeit"
)

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] [CATEGORIES...]

Umfassendes Validierungs-Script für Agent-NN Installation

OPTIONS:
    --detailed          Detaillierte Ausgabe mit Debug-Informationen
    --fix               Versuche automatisch Probleme zu beheben
    --no-services       Überspringe Service-Checks
    --no-deps           Überspringe Abhängigkeits-Checks  
    --no-config         Überspringe Konfigurationsprüfung
    --no-permissions    Überspringe Berechtigungs-Checks
    --timeout SECONDS   Timeout für Service-Checks (default: 30)
    --format FORMAT     Ausgabeformat (text|json|summary)
    -h, --help          Diese Hilfe anzeigen

CATEGORIES:
    system              System-Abhängigkeiten
    python              Python-Umgebung
    node                Node.js und Frontend
    docker              Docker und Services
    mcp                 MCP Services
    config              Konfigurationsdateien
    permissions         Dateiberechtigungen
    network             Netzwerk und Ports
    
    all                 Alle Kategorien (default)

BEISPIELE:
    $(basename "$0")                    # Vollständige Validierung
    $(basename "$0") --detailed --fix   # Mit Details und Auto-Fix
    $(basename "$0") docker mcp         # Nur Docker und MCP prüfen
    $(basename "$0") --no-services      # Ohne Service-Checks

EOF
}

# Globale Validierungs-Statistiken
declare -A VALIDATION_STATS=(
    [total]=0
    [passed]=0
    [failed]=0
    [warnings]=0
    [fixed]=0
)

# Validierungs-Ergebnis verwalten
add_validation_result() {
    local category="$1"
    local test_name="$2"
    local status="$3"  # passed|failed|warning|fixed
    local message="$4"
    
    VALIDATION_STATS[total]=$((${VALIDATION_STATS[total]} + 1))
    
    # Initialize the status counter if it doesn't exist
    if [[ -z "${VALIDATION_STATS[$status]:-}" ]]; then
        VALIDATION_STATS[$status]=0
    fi
    VALIDATION_STATS[$status]=$((${VALIDATION_STATS[$status]} + 1))
    
    case "$status" in
        passed)
            log_ok "[$category] $test_name: $message"
            ;;
        failed)
            log_err "[$category] $test_name: $message"
            ;;
        warning)
            log_warn "[$category] $test_name: $message"
            ;;
        fixed)
            log_info "[$category] $test_name: $message (behoben)"
            ;;
    esac
    
    if [[ "$DETAILED_OUTPUT" == "true" ]]; then
        log_debug "Details für $test_name: $message"
    fi
}

# System-Validierung
validate_system() {
    log_info "=== SYSTEM-VALIDIERUNG ==="
    
    # Betriebssystem prüfen
    local os_info
    if os_info=$(lsb_release -d 2>/dev/null || cat /etc/os-release 2>/dev/null | head -1); then
        add_validation_result "system" "OS-Erkennung" "passed" "$os_info"
    else
        add_validation_result "system" "OS-Erkennung" "warning" "Betriebssystem nicht erkannt"
    fi
    
    # Basis-Tools prüfen
    local required_tools=(curl wget git bash)
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" >/dev/null; then
            local version
            version=$("$tool" --version 2>/dev/null | head -1 || echo "Version unbekannt")
            add_validation_result "system" "$tool" "passed" "$version"
        else
            add_validation_result "system" "$tool" "failed" "Nicht installiert"
            
            if [[ "$FIX_ISSUES" == "true" ]]; then
                if install_packages "$tool"; then
                    add_validation_result "system" "$tool" "fixed" "Automatisch installiert"
                fi
            fi
        fi
    done
    
    # Speicher und Disk-Space prüfen
    local memory_gb
    memory_gb=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $memory_gb -ge 4 ]]; then
        add_validation_result "system" "Arbeitsspeicher" "passed" "${memory_gb}GB verfügbar"
    else
        add_validation_result "system" "Arbeitsspeicher" "warning" "Nur ${memory_gb}GB - mindestens 4GB empfohlen"
    fi
    
    local disk_space
    disk_space=$(df -h "$REPO_ROOT" | awk 'NR==2{print $4}')
    add_validation_result "system" "Festplattenspeicher" "passed" "$disk_space verfügbar"
}

# Python-Validierung
validate_python() {
    log_info "=== PYTHON-VALIDIERUNG ==="
    
    # Python-Version prüfen
    if command -v python3 >/dev/null; then
        local py_version
        py_version=$(python3 --version)
        
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
            add_validation_result "python" "Python-Version" "passed" "$py_version"
        else
            add_validation_result "python" "Python-Version" "failed" "$py_version - mindestens 3.9 erforderlich"
        fi
    else
        add_validation_result "python" "Python-Installation" "failed" "Python3 nicht gefunden"
    fi
    
    # pip prüfen
    if command -v pip >/dev/null || python3 -m pip --version >/dev/null 2>&1; then
        local pip_version
        pip_version=$(python3 -m pip --version 2>/dev/null || pip --version 2>/dev/null)
        add_validation_result "python" "pip" "passed" "$pip_version"
    else
        add_validation_result "python" "pip" "failed" "pip nicht verfügbar"
    fi
    
    # Poetry prüfen
    if command -v poetry >/dev/null; then
        local poetry_version
        poetry_version=$(poetry --version 2>/dev/null || echo "Version unbekannt")
        add_validation_result "python" "Poetry" "passed" "$poetry_version"
        
        # Poetry-Konfiguration prüfen
        cd "$REPO_ROOT" || return 1
        if [[ -f "pyproject.toml" ]]; then
            if poetry check 2>/dev/null; then
                add_validation_result "python" "Poetry-Konfiguration" "passed" "pyproject.toml valide"
            else
                add_validation_result "python" "Poetry-Konfiguration" "failed" "pyproject.toml Probleme"
            fi
        fi
        
        # Virtual Environment prüfen
        if [[ -d ".venv" ]]; then
            add_validation_result "python" "Virtual Environment" "passed" ".venv Verzeichnis existiert"
        else
            add_validation_result "python" "Virtual Environment" "warning" ".venv nicht gefunden - 'poetry install' ausführen"
            
            if [[ "$FIX_ISSUES" == "true" ]]; then
                if poetry install >/dev/null 2>&1; then
                    add_validation_result "python" "Virtual Environment" "fixed" "Dependencies installiert"
                fi
            fi
        fi
    else
        add_validation_result "python" "Poetry" "failed" "Poetry nicht installiert"
    fi
    
    # Python-Module prüfen
    local required_modules=(requests fastapi uvicorn sqlalchemy)
    for module in "${required_modules[@]}"; do
        if poetry run python -c "import $module" 2>/dev/null; then
            add_validation_result "python" "Module-$module" "passed" "Importierbar"
        else
            add_validation_result "python" "Module-$module" "warning" "Nicht verfügbar"
        fi
    done
}

# Node.js-Validierung
validate_node() {
    log_info "=== NODE.JS-VALIDIERUNG ==="
    
    # Node.js Version prüfen
    if command -v node >/dev/null; then
        local node_version
        node_version=$(node --version)
        local major_version
        major_version=$(echo "$node_version" | sed 's/v//' | cut -d. -f1)
        
        if [[ $major_version -ge 18 ]]; then
            add_validation_result "node" "Node.js-Version" "passed" "$node_version"
        else
            add_validation_result "node" "Node.js-Version" "failed" "$node_version - mindestens v18 erforderlich"
        fi
    else
        add_validation_result "node" "Node.js" "failed" "Node.js nicht installiert"
    fi
    
    # npm prüfen
    if command -v npm >/dev/null; then
        local npm_version
        npm_version=$(npm --version)
        add_validation_result "node" "npm" "passed" "v$npm_version"
    else
        add_validation_result "node" "npm" "failed" "npm nicht installiert"
    fi
    
    # Frontend-Verzeichnis prüfen
    local frontend_dir="$REPO_ROOT/frontend/agent-ui"
    if [[ -d "$frontend_dir" ]]; then
        add_validation_result "node" "Frontend-Verzeichnis" "passed" "$frontend_dir existiert"
        
        # package.json prüfen
        if [[ -f "$frontend_dir/package.json" ]]; then
            add_validation_result "node" "package.json" "passed" "Frontend package.json gefunden"
            
            # node_modules prüfen
            if [[ -d "$frontend_dir/node_modules" ]]; then
                add_validation_result "node" "node_modules" "passed" "Dependencies installiert"
            else
                add_validation_result "node" "node_modules" "warning" "Frontend dependencies nicht installiert"
                
                if [[ "$FIX_ISSUES" == "true" ]]; then
                    cd "$frontend_dir" || return 1
                    if npm ci >/dev/null 2>&1 || npm install >/dev/null 2>&1; then
                        add_validation_result "node" "node_modules" "fixed" "Dependencies installiert"
                    fi
                    cd "$REPO_ROOT" || return 1
                fi
            fi
            
            # Build-Output prüfen
            local dist_dir="$REPO_ROOT/frontend/dist"
            if [[ -f "$dist_dir/index.html" ]]; then
                add_validation_result "node" "Frontend-Build" "passed" "Build-Output verfügbar"
            else
                add_validation_result "node" "Frontend-Build" "warning" "Frontend nicht gebaut"
            fi
        else
            add_validation_result "node" "package.json" "failed" "package.json nicht gefunden"
        fi
    else
        add_validation_result "node" "Frontend-Verzeichnis" "failed" "Frontend-Verzeichnis nicht gefunden"
    fi
}

# Docker-Validierung
validate_docker() {
    log_info "=== DOCKER-VALIDIERUNG ==="
    
    # Docker prüfen
    if command -v docker >/dev/null; then
        local docker_version
        docker_version=$(docker --version)
        add_validation_result "docker" "Docker-Installation" "passed" "$docker_version"
        
        # Docker-Daemon prüfen
        if docker info >/dev/null 2>&1; then
            add_validation_result "docker" "Docker-Daemon" "passed" "Docker läuft"
            
            # Docker-Berechtigungen prüfen
            if docker ps >/dev/null 2>&1; then
                add_validation_result "docker" "Docker-Berechtigungen" "passed" "Benutzer kann Docker verwenden"
            else
                add_validation_result "docker" "Docker-Berechtigungen" "failed" "Keine Docker-Berechtigung"
                
                if [[ "$FIX_ISSUES" == "true" ]]; then
                    if sudo usermod -aG docker "$USER" 2>/dev/null; then
                        add_validation_result "docker" "Docker-Berechtigungen" "fixed" "Benutzer zur docker-Gruppe hinzugefügt (Neuanmeldung erforderlich)"
                    fi
                fi
            fi
        else
            add_validation_result "docker" "Docker-Daemon" "failed" "Docker-Daemon läuft nicht"
        fi
    else
        add_validation_result "docker" "Docker-Installation" "failed" "Docker nicht installiert"
    fi
    
    # Docker Compose prüfen
    if docker compose version >/dev/null 2>&1; then
        local compose_version
        compose_version=$(docker compose version --short 2>/dev/null || echo "unknown")
        add_validation_result "docker" "Docker-Compose" "passed" "Plugin v$compose_version"
    elif command -v docker-compose >/dev/null; then
        local compose_version
        compose_version=$(docker-compose version --short 2>/dev/null || echo "unknown")
        add_validation_result "docker" "Docker-Compose" "passed" "Classic v$compose_version"
    else
        add_validation_result "docker" "Docker-Compose" "failed" "Docker Compose nicht verfügbar"
    fi
    
    # Compose-Dateien prüfen
    local compose_files=(
        "$REPO_ROOT/docker-compose.yml"
    )
    
    for compose_file in "${compose_files[@]}"; do
        local file_name
        file_name=$(basename "$(dirname "$compose_file")")/$(basename "$compose_file")
        if [[ -f "$compose_file" ]]; then
            add_validation_result "docker" "Compose-$file_name" "passed" "Compose-Datei gefunden"
            
            # Compose-Datei validieren
            if docker-compose -f "$compose_file" config >/dev/null 2>&1; then
                add_validation_result "docker" "Compose-$file_name-Syntax" "passed" "Syntax korrekt"
            else
                add_validation_result "docker" "Compose-$file_name-Syntax" "failed" "Syntax-Fehler"
            fi
        else
            add_validation_result "docker" "Compose-$file_name" "warning" "Compose-Datei nicht gefunden"
        fi
    done
}

# LEGACY (disabled): not part of canonical runtime
validate_mcp() {
    log_info "=== MCP-VALIDIERUNG ==="
    add_validation_result "mcp" "Legacy-Status" "warning" "Legacy-MCP ist deaktiviert und kein canonical runtime path"
}

# Konfiguration-Validierung
validate_configuration() {
    log_info "=== KONFIGURATIONS-VALIDIERUNG ==="
    
    # .env Hauptdatei
    if [[ -f "$REPO_ROOT/.env" ]]; then
        add_validation_result "config" "Haupt-.env" "passed" ".env Datei vorhanden"
        
        # Wichtige Variablen prüfen
        local required_vars=(DATABASE_URL LLM_BACKEND)
        for var in "${required_vars[@]}"; do
            if grep -q "^${var}=" "$REPO_ROOT/.env"; then
                add_validation_result "config" "Var-$var" "passed" "$var definiert"
            else
                add_validation_result "config" "Var-$var" "warning" "$var nicht gesetzt"
            fi
        done
    else
        add_validation_result "config" "Haupt-.env" "warning" ".env Datei fehlt"
        
        if [[ "$FIX_ISSUES" == "true" && -f "$REPO_ROOT/.env.example" ]]; then
            cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
            add_validation_result "config" "Haupt-.env" "fixed" ".env aus Beispiel erstellt"
        fi
    fi
    
    # pyproject.toml
    if [[ -f "$REPO_ROOT/pyproject.toml" ]]; then
        add_validation_result "config" "pyproject.toml" "passed" "Python-Konfiguration vorhanden"
        
        if command -v poetry >/dev/null && poetry check >/dev/null 2>&1; then
            add_validation_result "config" "pyproject-syntax" "passed" "pyproject.toml valide"
        else
            add_validation_result "config" "pyproject-syntax" "warning" "pyproject.toml Probleme"
        fi
    else
        add_validation_result "config" "pyproject.toml" "failed" "pyproject.toml fehlt"
    fi
    
    # Frontend-Konfiguration
    local frontend_config="$REPO_ROOT/frontend/agent-ui/package.json"
    if [[ -f "$frontend_config" ]]; then
        add_validation_result "config" "Frontend-config" "passed" "Frontend package.json vorhanden"
    else
        add_validation_result "config" "Frontend-config" "failed" "Frontend package.json fehlt"
    fi
}

# Berechtigungen-Validierung
validate_permissions() {
    log_info "=== BERECHTIGUNGS-VALIDIERUNG ==="
    
    # Repository-Berechtigungen
    if [[ -w "$REPO_ROOT" ]]; then
        add_validation_result "permissions" "Repository-Schreibrecht" "passed" "Repository beschreibbar"
    else
        add_validation_result "permissions" "Repository-Schreibrecht" "failed" "Keine Schreibberechtigung für Repository"
    fi
    
    # Script-Ausführungsrechte
    local scripts=("$SCRIPT_DIR/setup.sh" "$SCRIPT_DIR/start_docker.sh" "$SCRIPT_DIR/start_mcp.sh")
    for script in "${scripts[@]}"; do
        if [[ -x "$script" ]]; then
            add_validation_result "permissions" "Script-$(basename "$script")" "passed" "Ausführbar"
        else
            add_validation_result "permissions" "Script-$(basename "$script")" "warning" "Nicht ausführbar"
            
            if [[ "$FIX_ISSUES" == "true" ]]; then
                chmod +x "$script" 2>/dev/null && \
                add_validation_result "permissions" "Script-$(basename "$script")" "fixed" "Ausführungsrecht gesetzt"
            fi
        fi
    done
    
    # Docker Socket-Berechtigung
    if [[ -S /var/run/docker.sock ]]; then
        if [[ -r /var/run/docker.sock ]]; then
            add_validation_result "permissions" "Docker-Socket" "passed" "Docker Socket lesbar"
        else
            add_validation_result "permissions" "Docker-Socket" "failed" "Keine Berechtigung für Docker Socket"
        fi
    else
        add_validation_result "permissions" "Docker-Socket" "warning" "Docker Socket nicht gefunden"
    fi
}

# Netzwerk-Validierung
validate_network() {
    log_info "=== NETZWERK-VALIDIERUNG ==="
    
    # Internet-Verbindung
    if curl -f -s --max-time 10 https://google.com >/dev/null 2>&1; then
        add_validation_result "network" "Internet-Verbindung" "passed" "Internet erreichbar"
    else
        add_validation_result "network" "Internet-Verbindung" "failed" "Keine Internet-Verbindung"
    fi
    
    # Port-Verfügbarkeit prüfen
    local important_ports=(3000 8000 8001 8002 8003 8004 8005 5432 6379)
    for port in "${important_ports[@]}"; do
        if check_port "$port"; then
            add_validation_result "network" "Port-$port" "passed" "Port $port verfügbar"
        else
            add_validation_result "network" "Port-$port" "warning" "Port $port belegt"
        fi
    done
    
    # DNS-Auflösung
    if nslookup google.com >/dev/null 2>&1; then
        add_validation_result "network" "DNS-Auflösung" "passed" "DNS funktioniert"
    else
        add_validation_result "network" "DNS-Auflösung" "warning" "DNS-Probleme"
    fi
}

# Zusammenfassung anzeigen
show_validation_summary() {
    echo
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                           VALIDIERUNGS-ZUSAMMENFASSUNG                      ║"
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    printf "║  Gesamt:      %3d Tests                                                      ║\n" "${VALIDATION_STATS[total]}"
    printf "║  ✅ Bestanden: %3d Tests                                                      ║\n" "${VALIDATION_STATS[passed]}"
    printf "║  ❌ Fehlgeschlagen: %3d Tests                                                 ║\n" "${VALIDATION_STATS[failed]}"
    printf "║  ⚠️  Warnungen: %3d Tests                                                     ║\n" "${VALIDATION_STATS[warnings]}"
    if [[ "${VALIDATION_STATS[fixed]}" -gt 0 ]]; then
        printf "║  🔧 Behoben:   %3d Tests                                                      ║\n" "${VALIDATION_STATS[fixed]}"
    fi
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo
    
    # Bewertung
    local total_issues=$((${VALIDATION_STATS[failed]} + ${VALIDATION_STATS[warnings]}))
    if [[ $total_issues -eq 0 ]]; then
        log_ok "🎉 Alle Validierungen erfolgreich! System ist bereit."
        return 0
    elif [[ ${VALIDATION_STATS[failed]} -eq 0 ]]; then
        log_warn "⚠️ System funktionsfähig, aber mit ${VALIDATION_STATS[warnings]} Warnungen."
        return 1
    else
        log_err "❌ System hat ${VALIDATION_STATS[failed]} kritische Probleme."
        return 2
    fi
}

# Hauptfunktion
main() {
    local categories=()
    local output_format="text"
    
    # Parameter parsen
    while [[ $# -gt 0 ]]; do
        case $1 in
            --detailed)
                DETAILED_OUTPUT=true
                shift
                ;;
            --fix)
                FIX_ISSUES=true
                shift
                ;;
            --no-services)
                CHECK_SERVICES=false
                shift
                ;;
            --no-deps)
                CHECK_DEPENDENCIES=false
                shift
                ;;
            --no-config)
                CHECK_CONFIGURATION=false
                shift
                ;;
            --no-permissions)
                CHECK_PERMISSIONS=false
                shift
                ;;
            --timeout)
                VALIDATION_TIMEOUT="$2"
                shift 2
                ;;
            --format)
                output_format="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            system|python|node|docker|mcp|config|permissions|network)
                categories+=("$1")
                shift
                ;;
            all)
                categories=(system python node docker mcp config permissions network)
                shift
                ;;
            *)
                log_err "Unbekannte Option: $1"
                usage >&2
                exit 1
                ;;
        esac
    done
    
    # Standard-Kategorien falls keine angegeben
    if [[ ${#categories[@]} -eq 0 ]]; then
        categories=(system python node docker mcp config permissions network)
    fi
    
    log_info "Starte Validierung für: ${categories[*]}"
    if [[ "$FIX_ISSUES" == "true" ]]; then
        log_info "Auto-Fix aktiviert"
    fi
    echo
    
    # Validierungen ausführen
    for category in "${categories[@]}"; do
        case "$category" in
            system) validate_system ;;
            python) validate_python ;;
            node) validate_node ;;
            docker) validate_docker ;;
            mcp) validate_mcp ;;
            config) validate_configuration ;;
            permissions) validate_permissions ;;
            network) validate_network ;;
            *)
                log_warn "Unbekannte Kategorie: $category"
                ;;
        esac
        echo
    done
    
    # Zusammenfassung anzeigen
    show_validation_summary
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
