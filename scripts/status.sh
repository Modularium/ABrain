#!/bin/bash
# -*- coding: utf-8 -*-
# Umfassendes Status-Monitoring für Agent-NN

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
STATUS_FILE="$REPO_ROOT/.agentnn/status.json"

source "$SCRIPT_DIR/lib/log_utils.sh"
source "$SCRIPT_DIR/lib/docker_utils.sh"
source "$SCRIPT_DIR/lib/status_utils.sh"
source "$SCRIPT_DIR/helpers/common.sh"
source "$SCRIPT_DIR/helpers/docker.sh"

# Status-Konfiguration
SHOW_DETAILED=false
WATCH_MODE=false
WATCH_INTERVAL=5
OUTPUT_FORMAT="table"  # table|json|summary
CHECK_HEALTH=true
SAVE_REPORT=false

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] [COMPONENTS...]

Umfassendes Status-Monitoring für Agent-NN System

OPTIONS:
    --detailed          Detaillierte Informationen anzeigen
    --watch             Kontinuierliches Monitoring (alle 5s)
    --interval SECONDS  Watch-Intervall (default: 5)
    --format FORMAT     Ausgabeformat (table|json|summary|dashboard)
    --no-health         Health-Checks überspringen
    --save              Status-Report in Datei speichern
    --reset             Status-Daten zurücksetzen
    -h, --help          Diese Hilfe anzeigen

COMPONENTS:
    system              System-Ressourcen und Basis-Services
    docker              Docker und Container-Status
    mcp                 MCP Services Status
    services            Alle Anwendungs-Services
    frontend            Frontend Build und Verfügbarkeit
    database            Datenbank-Verbindungen
    network             Netzwerk und Port-Status
    
    all                 Alle Komponenten (default)

BEISPIELE:
    $(basename "$0")                    # Standard Status-Übersicht
    $(basename "$0") --detailed --save  # Detaillierter Report mit Speichern
    $(basename "$0") --watch            # Live-Monitoring
    $(basename "$0") docker mcp         # Nur Docker und MCP Status
    $(basename "$0") --format json      # JSON-Output

EOF
}

# Globale Status-Sammlung
declare -A COMPONENT_STATUS=()
declare -A COMPONENT_DETAILS=()
declare -A COMPONENT_HEALTH=()

# Status-Utilities
set_component_status() {
    local component="$1"
    local status="$2"      # running|stopped|error|unknown
    local details="$3"
    local health="${4:-unknown}"
    
    COMPONENT_STATUS[$component]="$status"
    COMPONENT_DETAILS[$component]="$details"
    COMPONENT_HEALTH[$component]="$health"
}

get_component_status() {
    local component="$1"
    echo "${COMPONENT_STATUS[$component]:-unknown}"
}

get_status_icon() {
    local status="$1"
    case "$status" in
        running) echo "🟢" ;;
        stopped) echo "🔴" ;;
        error) echo "❌" ;;
        warning) echo "⚠️" ;;
        unknown) echo "⚪" ;;
        *) echo "❓" ;;
    esac
}

get_health_icon() {
    local health="$1"
    case "$health" in
        healthy) echo "💚" ;;
        unhealthy) echo "💔" ;;
        degraded) echo "💛" ;;
        unknown) echo "❔" ;;
        *) echo "❔" ;;
    esac
}

# System-Status prüfen
check_system_status() {
    log_debug "Prüfe System-Status..."
    
    # Basis-System
    local uptime
    uptime=$(uptime -p 2>/dev/null || echo "Unbekannt")
    
    # CPU und Memory
    local cpu_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 2>/dev/null || echo "N/A")
    
    local memory_info
    memory_info=$(free -h | awk '/^Mem:/{printf "%.1f/%.1fGB (%.0f%%)", $3, $2, ($3/$2)*100}' 2>/dev/null || echo "N/A")
    
    # Disk Space
    local disk_usage
    disk_usage=$(df -h "$REPO_ROOT" | awk 'NR==2{printf "%s/%s (%s)", $3, $2, $5}' 2>/dev/null || echo "N/A")
    
    local system_details="Uptime: $uptime | CPU: ${cpu_usage}% | Memory: $memory_info | Disk: $disk_usage"
    
    # Load Average für Health-Bewertung
    local load_avg
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',' 2>/dev/null || echo "0")
    
    local health="healthy"
    if (( $(echo "$load_avg > 2.0" | bc -l 2>/dev/null || echo 0) )); then
        health="degraded"
    fi
    
    set_component_status "system" "running" "$system_details" "$health"
}

# Docker-Status prüfen
check_docker_status() {
    log_debug "Prüfe Docker-Status..."
    
    if ! command -v docker >/dev/null; then
        set_component_status "docker" "error" "Docker nicht installiert" "unhealthy"
        return
    fi
    
    if ! docker info >/dev/null 2>&1; then
        set_component_status "docker" "stopped" "Docker-Daemon läuft nicht" "unhealthy"
        return
    fi
    
    # Container-Status
    local running_containers
    running_containers=$(docker ps --format "table {{.Names}}" --filter "status=running" 2>/dev/null | tail -n +2 | wc -l)
    
    local total_containers
    total_containers=$(docker ps -a --format "table {{.Names}}" 2>/dev/null | tail -n +2 | wc -l)
    
    # Docker-Version
    local docker_version
    docker_version=$(docker --version | cut -d' ' -f3 | tr -d ',' 2>/dev/null || echo "unknown")
    
    local docker_compose_version
    if docker compose version >/dev/null 2>&1; then
        docker_compose_version=$(docker compose version --short 2>/dev/null || echo "unknown")
        docker_compose_version="Plugin v$docker_compose_version"
    elif command -v docker-compose >/dev/null; then
        docker_compose_version=$(docker-compose version --short 2>/dev/null || echo "unknown")
        docker_compose_version="Classic v$docker_compose_version"
    else
        docker_compose_version="nicht verfügbar"
    fi
    
    local docker_details="Version: $docker_version | Compose: $docker_compose_version | Container: $running_containers/$total_containers laufen"
    
    local health="healthy"
    if [[ $running_containers -eq 0 && $total_containers -gt 0 ]]; then
        health="degraded"
    fi
    
    set_component_status "docker" "running" "$docker_details" "$health"
}

# LEGACY (disabled): not part of canonical runtime
check_mcp_status() {
    log_debug "Prüfe Legacy-MCP-Status..."
    set_component_status \
        "mcp" \
        "warning" \
        "Legacy-MCP ist deaktiviert und kein Teil des canonical runtime stack" \
        "unknown"
}

# Standard-Services Status prüfen
check_services_status() {
    log_debug "Prüfe Standard-Services..."
    
    # Standard Docker-Services
    local services_running=0
    local services_total=0
    
    # Prüfe ob Standard compose-Datei existiert
    local compose_file
    if compose_file=$(find_compose_file "docker-compose.yml" "standard" 2>/dev/null); then
        # Standard-Services aus compose-file lesen
        local service_names
        service_names=$(docker compose -f "$compose_file" config --services 2>/dev/null || echo "")
        
        if [[ -n "$service_names" ]]; then
            while IFS= read -r service; do
                services_total=$((services_total + 1))
                if docker compose -f "$compose_file" ps "$service" | grep -q "Up"; then
                    services_running=$((services_running + 1))
                fi
            done <<< "$service_names"
        fi
    fi
    
    # Health-Check für Standard-Services
    local service_health="unknown"
    if [[ "$CHECK_HEALTH" == "true" ]]; then
        local health_endpoints=(
            "8000:/health:API Gateway"
            "3000:/:Frontend"
        )
        
        local healthy_endpoints=0
        for endpoint_info in "${health_endpoints[@]}"; do
            local port="${endpoint_info%%:*}"
            local path="${endpoint_info#*:}"
            path="${path%:*}"
            
            if curl -f -s --max-time 3 "http://localhost:$port$path" >/dev/null 2>&1; then
                healthy_endpoints=$((healthy_endpoints + 1))
            fi
        done
        
        if [[ $healthy_endpoints -eq ${#health_endpoints[@]} ]]; then
            service_health="healthy"
        elif [[ $healthy_endpoints -gt 0 ]]; then
            service_health="degraded" 
        else
            service_health="unhealthy"
        fi
    fi
    
    local services_details="Container: $services_running/$services_total laufen"
    
    if [[ $services_running -eq 0 ]]; then
        set_component_status "services" "stopped" "$services_details" "unhealthy"
    else
        set_component_status "services" "running" "$services_details" "$service_health"
    fi
}

# Frontend-Status prüfen
check_frontend_status() {
    log_debug "Prüfe Frontend-Status..."
    
    local frontend_dir="$REPO_ROOT/frontend/agent-ui"
    local dist_dir="$REPO_ROOT/frontend/dist"
    
    # Build-Status prüfen
    if [[ -f "$dist_dir/index.html" ]]; then
        local build_time
        build_time=$(stat -c %Y "$dist_dir/index.html" 2>/dev/null || echo "0")
        local build_date
        build_date=$(date -d "@$build_time" '+%Y-%m-%d %H:%M' 2>/dev/null || echo "Unbekannt")
        
        # Build-Größe
        local build_size
        build_size=$(du -sh "$dist_dir" 2>/dev/null | cut -f1 || echo "N/A")
        
        local frontend_details="Build: $build_date | Größe: $build_size"
        
        # Health-Check für Frontend
        local frontend_health="unknown"
        if [[ "$CHECK_HEALTH" == "true" ]]; then
            if curl -f -s --max-time 3 "http://localhost:3000" >/dev/null 2>&1; then
                frontend_health="healthy"
            else
                frontend_health="unhealthy"
            fi
        fi
        
        set_component_status "frontend" "running" "$frontend_details" "$frontend_health"
    else
        set_component_status "frontend" "stopped" "Frontend nicht gebaut" "unhealthy"
    fi
}

# Datenbank-Status prüfen
check_database_status() {
    log_debug "Prüfe Datenbank-Status..."
    
    # PostgreSQL prüfen
    local postgres_status="stopped"
    local postgres_details=""
    
    if docker ps --format "{{.Names}}" | grep -q postgres; then
        postgres_status="running"
        
        # DB-Verbindung testen falls .env verfügbar
        if [[ -f "$REPO_ROOT/.env" ]]; then
            local db_url
            db_url=$(grep "^DATABASE_URL=" "$REPO_ROOT/.env" | cut -d= -f2- | tr -d '"' 2>/dev/null || echo "")
            
            if [[ -n "$db_url" ]]; then
                if docker exec -i "$(docker ps --format "{{.Names}}" | grep postgres | head -1)" pg_isready >/dev/null 2>&1; then
                    postgres_details="PostgreSQL: erreichbar"
                else
                    postgres_details="PostgreSQL: Verbindungsfehler"
                fi
            else
                postgres_details="PostgreSQL: Container läuft"
            fi
        else
            postgres_details="PostgreSQL: Container läuft"
        fi
    else
        postgres_details="PostgreSQL: nicht gestartet"
    fi
    
    # Redis prüfen
    local redis_status="stopped"
    local redis_details=""
    
    if docker ps --format "{{.Names}}" | grep -q redis; then
        redis_status="running"
        
        if docker exec -i "$(docker ps --format "{{.Names}}" | grep redis | head -1)" redis-cli ping >/dev/null 2>&1; then
            redis_details="Redis: erreichbar"
        else
            redis_details="Redis: Verbindungsfehler"
        fi
    else
        redis_details="Redis: nicht gestartet"
    fi
    
    local combined_details="$postgres_details | $redis_details"
    
    if [[ "$postgres_status" == "running" && "$redis_status" == "running" ]]; then
        set_component_status "database" "running" "$combined_details" "healthy"
    elif [[ "$postgres_status" == "running" || "$redis_status" == "running" ]]; then
        set_component_status "database" "running" "$combined_details" "degraded"
    else
        set_component_status "database" "stopped" "$combined_details" "unhealthy"
    fi
}

# Netzwerk-Status prüfen
check_network_status() {
    log_debug "Prüfe Netzwerk-Status..."
    
    # Port-Checks
    local important_ports=(3000 8000 8001 8002 8003 8004 8005 5432 6379)
    local ports_in_use=0
    local ports_available=0
    
    for port in "${important_ports[@]}"; do
        if ss -tuln | grep -q ":$port "; then
            ports_in_use=$((ports_in_use + 1))
        else
            ports_available=$((ports_available + 1))
        fi
    done
    
    # Internet-Verbindung
    local internet_status="unknown"
    if curl -f -s --max-time 5 https://google.com >/dev/null 2>&1; then
        internet_status="verfügbar"
    else
        internet_status="nicht verfügbar"
    fi
    
    local network_details="Internet: $internet_status | Ports belegt: $ports_in_use | Ports frei: $ports_available"
    
    local network_health="healthy"
    if [[ "$internet_status" == "nicht verfügbar" ]]; then
        network_health="degraded"
    fi
    
    set_component_status "network" "running" "$network_details" "$network_health"
}

# Status-Tabelle ausgeben
show_status_table() {
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                            AGENT-NN SYSTEM STATUS                           ║"
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    
    # Header
    printf "║ %-12s ║ %-8s ║ %-8s ║ %-44s ║\n" "KOMPONENTE" "STATUS" "HEALTH" "DETAILS"
    echo "╠══════════════╬══════════╬══════════╬══════════════════════════════════════════════╣"
    
    # Komponenten anzeigen
    for component in system docker services mcp frontend database network; do
        if [[ -n "${COMPONENT_STATUS[$component]:-}" ]]; then
            local status="${COMPONENT_STATUS[$component]}"
            local health="${COMPONENT_HEALTH[$component]}"
            local details="${COMPONENT_DETAILS[$component]}"
            
            # Details kürzen falls zu lang
            if [[ ${#details} -gt 44 ]]; then
                details="${details:0:41}..."
            fi
            
            local status_icon
            status_icon=$(get_status_icon "$status")
            local health_icon
            health_icon=$(get_health_icon "$health")
            
            printf "║ %-12s ║ %s %-6s ║ %s %-6s ║ %-44s ║\n" \
                "${component^^}" "$status_icon" "$status" "$health_icon" "$health" "$details"
        fi
    done
    
    echo "╚══════════════╩══════════╩══════════╩══════════════════════════════════════════════╝"
    
    # Zusätzliche Informationen
    echo
    echo "Letzte Aktualisierung: $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Persistente Status-Informationen
    if [[ -f "$STATUS_FILE" ]]; then
        local last_setup
        last_setup=$(get_status_value "last_setup" 2>/dev/null || echo "Unbekannt")
        local preset
        preset=$(get_status_value "preset" 2>/dev/null || echo "Nicht gesetzt")
        
        echo "Letztes Setup: $last_setup"
        echo "Verwendetes Preset: $preset"
    fi
}

# JSON-Output
show_status_json() {
    echo "{"
    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"components\": {"
    
    local first=true
    for component in system docker services mcp frontend database network; do
        if [[ -n "${COMPONENT_STATUS[$component]:-}" ]]; then
            if [[ "$first" == "false" ]]; then
                echo ","
            fi
            first=false
            
            local status="${COMPONENT_STATUS[$component]}"
            local health="${COMPONENT_HEALTH[$component]}"
            local details="${COMPONENT_DETAILS[$component]}"
            
            echo "    \"$component\": {"
            echo "      \"status\": \"$status\","
            echo "      \"health\": \"$health\","
            echo "      \"details\": \"$details\""
            echo -n "    }"
        fi
    done
    
    echo
    echo "  }"
    echo "}"
}

# Dashboard-Ansicht
show_status_dashboard() {
    clear
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│                         🤖 AGENT-NN DASHBOARD                              │"
    echo "├─────────────────────────────────────────────────────────────────────────────┤"
    
    # Schnellübersicht
    local running_components=0
    local total_components=0
    local healthy_components=0
    
    for component in system docker services mcp frontend database network; do
        if [[ -n "${COMPONENT_STATUS[$component]:-}" ]]; then
            total_components=$((total_components + 1))
            
            if [[ "${COMPONENT_STATUS[$component]}" == "running" ]]; then
                running_components=$((running_components + 1))
            fi
            
            if [[ "${COMPONENT_HEALTH[$component]}" == "healthy" ]]; then
                healthy_components=$((healthy_components + 1))
            fi
        fi
    done
    
    printf "│ Status: %d/%d Komponenten laufen | %d/%d gesund | %s     │\n" \
        "$running_components" "$total_components" "$healthy_components" "$total_components" "$(date '+%H:%M:%S')"
    echo "├─────────────────────────────────────────────────────────────────────────────┤"
    
    # Komponenten-Grid
    local row1=(system docker services)
    local row2=(mcp frontend database network)
    
    # Erste Reihe
    printf "│ "
    for component in "${row1[@]}"; do
        if [[ -n "${COMPONENT_STATUS[$component]:-}" ]]; then
            local status_icon
            status_icon=$(get_status_icon "${COMPONENT_STATUS[$component]}")
            printf "%s %-10s   " "$status_icon" "${component^^}"
        fi
    done
    echo "│"
    
    # Zweite Reihe
    printf "│ "
    for component in "${row2[@]}"; do
        if [[ -n "${COMPONENT_STATUS[$component]:-}" ]]; then
            local status_icon
            status_icon=$(get_status_icon "${COMPONENT_STATUS[$component]}")
            printf "%s %-10s   " "$status_icon" "${component^^}"
        fi
    done
    echo "│"
    
    echo "└─────────────────────────────────────────────────────────────────────────────┘"
    
    if [[ "$SHOW_DETAILED" == "true" ]]; then
        echo
        show_status_table
    fi
}

# Watch-Modus
run_watch_mode() {
    log_info "Starte Watch-Modus (Intervall: ${WATCH_INTERVAL}s)"
    log_info "Drücke Ctrl+C zum Beenden"
    
    while true; do
        # Status sammeln
        check_system_status
        check_docker_status
        check_services_status
        check_mcp_status
        check_frontend_status
        check_database_status
        check_network_status
        
        # Dashboard anzeigen
        show_status_dashboard
        
        sleep "$WATCH_INTERVAL"
    done
}

# Status-Report speichern
save_status_report() {
    local report_file="$REPO_ROOT/logs/status-report-$(date +%Y%m%d-%H%M%S).json"
    mkdir -p "$(dirname "$report_file")"
    
    show_status_json > "$report_file"
    log_ok "Status-Report gespeichert: $report_file"
}

# Hauptfunktion
main() {
    local components=()
    
    # Parameter parsen
    while [[ $# -gt 0 ]]; do
        case $1 in
            --detailed)
                SHOW_DETAILED=true
                shift
                ;;
            --watch)
                WATCH_MODE=true
                shift
                ;;
            --interval)
                WATCH_INTERVAL="$2"
                shift 2
                ;;
            --format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            --no-health)
                CHECK_HEALTH=false
                shift
                ;;
            --save)
                SAVE_REPORT=true
                shift
                ;;
            --reset)
                rm -f "$STATUS_FILE" 2>/dev/null || true
                log_ok "Status-Daten zurückgesetzt"
                exit 0
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            system|docker|services|mcp|frontend|database|network)
                components+=("$1")
                shift
                ;;
            all)
                components=(system docker services mcp frontend database network)
                shift
                ;;
            *)
                log_err "Unbekannte Option: $1"
                usage >&2
                exit 1
                ;;
        esac
    done
    
    # Standard-Komponenten falls keine angegeben
    if [[ ${#components[@]} -eq 0 ]]; then
        components=(system docker services mcp frontend database network)
    fi
    
    ensure_status_file "$STATUS_FILE"
    log_last_check "$STATUS_FILE"
    
    # Watch-Modus
    if [[ "$WATCH_MODE" == "true" ]]; then
        trap 'echo; log_info "Watch-Modus beendet"; exit 0' INT
        run_watch_mode
        return
    fi
    
    # Status für angegebene Komponenten sammeln
    for component in "${components[@]}"; do
        case "$component" in
            system) check_system_status ;;
            docker) check_docker_status ;;
            services) check_services_status ;;
            mcp) check_mcp_status ;;
            frontend) check_frontend_status ;;
            database) check_database_status ;;
            network) check_network_status ;;
        esac
    done
    
    # Ausgabe je nach Format
    case "$OUTPUT_FORMAT" in
        table)
            show_status_table
            ;;
        json)
            show_status_json
            ;;
        dashboard)
            show_status_dashboard
            ;;
        summary)
            # Nur Zusammenfassung
            local total=0
            local running=0
            local healthy=0
            
            for component in "${components[@]}"; do
                if [[ -n "${COMPONENT_STATUS[$component]:-}" ]]; then
                    total=$((total + 1))
                    if [[ "${COMPONENT_STATUS[$component]}" == "running" ]]; then
                        running=$((running + 1))
                    fi
                    if [[ "${COMPONENT_HEALTH[$component]}" == "healthy" ]]; then
                        healthy=$((healthy + 1))
                    fi
                fi
            done
            
            echo "Agent-NN Status: $running/$total laufen, $healthy/$total gesund"
            ;;
        *)
            log_err "Unbekanntes Ausgabeformat: $OUTPUT_FORMAT"
            exit 1
            ;;
    esac
    
    # Report speichern falls gewünscht
    if [[ "$SAVE_REPORT" == "true" ]]; then
        save_status_report
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
