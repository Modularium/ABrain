#!/bin/bash
# -*- coding: utf-8 -*-
# Verbesserte Docker Helper Funktionen für den canonical services/*-Stack

set -euo pipefail

# Only set HELPERS_DIR if it's not already set
if [[ -z "${HELPERS_DIR:-}" ]]; then
    HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# Repository-Wurzel ableiten, falls nicht gesetzt
if [[ -z "${REPO_ROOT:-}" ]]; then
    REPO_ROOT="$(cd "$HELPERS_DIR/../.." && pwd)"
fi

# Source common.sh from the helpers directory
source "$HELPERS_DIR/common.sh"

# Globale Docker-Variablen
DOCKER_COMPOSE_COMMAND=""
DOCKER_COMPOSE_VERSION=""

# Standard-Services Konfiguration
declare -A STANDARD_SERVICES=(
    [api]="agent-api:8000:Agent API Gateway"
    [frontend]="agent-frontend:3000:Agent Frontend"
    [postgres]="postgres:5432:PostgreSQL Database"
    [redis]="redis:6379:Redis Cache"
    [prometheus]="prometheus:9090:Prometheus Monitoring"
)

find_compose_file() {
    local name="${1:-docker-compose.yml}"
    local prefer_type="${2:-standard}"  # standard|mcp|all

    local search_paths=()
    
    case "$prefer_type" in
        mcp)
            search_paths=()
            ;;
        standard)
            search_paths=(
                "$REPO_ROOT/docker-compose.yml"
                "$REPO_ROOT/docker-compose.yaml"
                "$REPO_ROOT/deploy/docker-compose.yml"
                "$REPO_ROOT/deploy/docker-compose.yaml"
                "$REPO_ROOT/docker/docker-compose.yml"
                "$REPO_ROOT/docker/docker-compose.yaml"
            )
            ;;
        all)
            search_paths=(
                "$REPO_ROOT/$name"
                "$REPO_ROOT/mcp/$name"
                "$REPO_ROOT/deploy/$name"
                "$REPO_ROOT/docker/$name"
            )
            ;;
    esac

    # Erweiterte Suche für spezifische Dateien
    if [[ "$name" != "docker-compose.yml" ]]; then
        search_paths+=("$REPO_ROOT/$name")
    fi

    for f in "${search_paths[@]}"; do
        if [ -f "$f" ]; then
            echo "$f"
            return 0
        fi
    done

    # Wenn Standard-Datei nicht existiert, nach Alternativen suchen
    if [[ "$name" == "docker-compose.yml" ]]; then
        local pattern
        case "$prefer_type" in
            mcp) pattern="$REPO_ROOT/nonexistent-mcp-compose*.yml" ;;
            *) pattern="$REPO_ROOT/docker-compose*.yml" ;;
        esac
        
        mapfile -t alternatives < <(find "$(dirname "$pattern")" -maxdepth 1 -name "$(basename "$pattern")" 2>/dev/null)
        
        if [[ ${#alternatives[@]} -gt 0 ]]; then
            if [[ ${#alternatives[@]} -gt 1 ]]; then
                log_warn "Mehrere Compose-Dateien gefunden: ${alternatives[*]}"
                log_warn "Verwende erste Datei: ${alternatives[0]}"
            else
                log_info "Verwende Compose-Datei ${alternatives[0]}"
            fi
            echo "${alternatives[0]}"
            return 0
        fi
    fi

    if [ -f "$REPO_ROOT/${name}.example" ]; then
        log_err "Docker Compose Datei nicht gefunden: $name"
        log_err "Erstelle sie aus ${name}.example"
    else
        log_err "Docker Compose Datei nicht gefunden: $name"
        log_err "Suchpfade: ${search_paths[*]}"
    fi
    return 1
}

detect_docker_compose() {
    log_info "Erkenne Docker Compose..."
    
    # Prüfe Docker Compose Plugin (neuere Variante)
    if docker compose version &>/dev/null; then
        DOCKER_COMPOSE_COMMAND="docker compose"
        DOCKER_COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "unknown")
        log_ok "Docker Compose Plugin erkannt (v$DOCKER_COMPOSE_VERSION)"
        return 0
    fi
    
    # Prüfe Docker Compose Classic (ältere Variante)
    if command -v docker-compose &>/dev/null; then
        DOCKER_COMPOSE_COMMAND="docker-compose"
        DOCKER_COMPOSE_VERSION=$(docker-compose version --short 2>/dev/null || echo "unknown")
        log_ok "Docker Compose Classic erkannt (v$DOCKER_COMPOSE_VERSION)"
        return 0
    fi
    
    log_err "Docker Compose nicht gefunden!"
    log_err "Bitte installiere Docker Compose:"
    log_err "  - Plugin: https://docs.docker.com/compose/install/"
    log_err "  - Classic: pip install docker-compose"
    return 1
}

check_docker() {
    log_info "Prüfe Docker-Installation..."
    
    # Docker Command prüfen
    if ! check_command docker "Docker"; then
        log_err "Docker ist nicht installiert. Siehe: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    # Docker Daemon prüfen
    if ! docker info &>/dev/null; then
        log_err "Docker-Daemon ist nicht erreichbar"
        log_err "Stelle sicher, dass Docker läuft und dein Benutzer in der docker-Gruppe ist"
        log_err "  sudo systemctl start docker"
        log_err "  sudo usermod -aG docker \$USER"
        log_err "  newgrp docker"
        return 1
    fi

    if [[ ! -S /var/run/docker.sock ]]; then
        log_warn "docker.sock nicht verfügbar oder keine Berechtigung"
    fi
    
    log_ok "Docker ist verfügbar ($(docker --version))"
    
    # Docker Compose erkennen
    detect_docker_compose
    
    return 0
}

docker_compose_up() {
    local compose_file="${1:-docker-compose.yml}"
    local build_flag="${2:-}"
    local detach_flag="${3:--d}"
    local service_type="${4:-standard}"  # standard|mcp
    
    if [[ -z "$DOCKER_COMPOSE_COMMAND" ]]; then
        if ! detect_docker_compose; then
            return 1
        fi
    fi
    
    compose_file=$(find_compose_file "$compose_file" "$service_type") || return 1
    
    log_info "Starte Docker-Services mit $DOCKER_COMPOSE_COMMAND..."
    log_debug "Compose-Datei: $compose_file"
    log_debug "Service-Typ: $service_type"
    log_debug "Build-Flag: ${build_flag:-none}"
    log_debug "Detach-Flag: $detach_flag"
    
    local cmd="$DOCKER_COMPOSE_COMMAND"
    if [[ "$(basename "$compose_file")" != "docker-compose.yml" ]] || [[ "$(dirname "$compose_file")" != "$PWD" ]]; then
        cmd="$cmd -f $compose_file"
    fi
    
    cmd="$cmd up"
    if [[ -n "$build_flag" ]]; then
        cmd="$cmd $build_flag"
    fi
    if [[ -n "$detach_flag" ]]; then
        cmd="$cmd $detach_flag"
    fi
    
    log_debug "Führe aus: $cmd"
    
    # Wechsle ins korrekte Verzeichnis für relative Pfade
    local original_dir="$PWD"
    cd "$(dirname "$compose_file")" || return 1
    
    if eval "$(basename "$DOCKER_COMPOSE_COMMAND") ${cmd#*compose }"; then
        cd "$original_dir"
        log_ok "Docker-Services gestartet"
        
        # Warte kurz und zeige Service-Status
        sleep 3
        show_service_status "$compose_file" "$service_type"
        return 0
    else
        cd "$original_dir"
        log_err "Fehler beim Starten der Docker-Services"
        return 1
    fi
}

docker_compose_down() {
    local compose_file="${1:-docker-compose.yml}"
    local service_type="${2:-standard}"
    
    if [[ -z "$DOCKER_COMPOSE_COMMAND" ]]; then
        if ! detect_docker_compose; then
            return 1
        fi
    fi
    
    compose_file=$(find_compose_file "$compose_file" "$service_type") || return 1

    log_info "Stoppe Docker-Services..."
    
    local cmd="$DOCKER_COMPOSE_COMMAND"
    if [[ "$(basename "$compose_file")" != "docker-compose.yml" ]] || [[ "$(dirname "$compose_file")" != "$PWD" ]]; then
        cmd="$cmd -f $compose_file"
    fi
    cmd="$cmd down"
    
    # Wechsle ins korrekte Verzeichnis für relative Pfade
    local original_dir="$PWD"
    cd "$(dirname "$compose_file")" || return 1
    
    if eval "$(basename "$DOCKER_COMPOSE_COMMAND") ${cmd#*compose }"; then
        cd "$original_dir"
        log_ok "Docker-Services gestoppt"
        return 0
    else
        cd "$original_dir"
        log_warn "Fehler beim Stoppen der Docker-Services"
        return 1
    fi
}

# Service-Status anzeigen
show_service_status() {
    local compose_file="${1:-docker-compose.yml}"
    local service_type="${2:-standard}"
    
    log_info "Service-Status:"
    
    # Docker Compose ps verwenden falls verfügbar
    local original_dir="$PWD"
    cd "$(dirname "$compose_file")" || return 1
    
    if $DOCKER_COMPOSE_COMMAND ps --format table 2>/dev/null; then
        cd "$original_dir"
        return 0
    fi
    
    cd "$original_dir"
    
    # Fallback: Standard docker ps
    echo "Container-Status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "label=com.docker.compose.project" 2>/dev/null || \
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10
}

# Health-Check für Services
check_service_health() {
    local service_type="${1:-standard}"
    local timeout="${2:-30}"
    
    local services_map
    case "$service_type" in
        mcp)
            log_warn "Legacy MCP health checks are disabled"
            return 1
            ;;
        *)
            declare -n services_map=STANDARD_SERVICES
            ;;
    esac
    
    log_info "Prüfe Service-Health ($service_type)..."
    
    local healthy_count=0
    local total_count=${#services_map[@]}
    
    for service_key in "${!services_map[@]}"; do
        local service_info="${services_map[$service_key]}"
        local service_name="${service_info%%:*}"
        local service_port="${service_info#*:}"
        service_port="${service_port%%:*}"
        local service_desc="${service_info##*:}"
        
        local health_url="http://localhost:${service_port}/health"
        
        log_debug "Prüfe $service_desc: $health_url"
        
        if timeout "$timeout" bash -c "until curl -f -s '$health_url' >/dev/null 2>&1; do sleep 1; done" 2>/dev/null; then
            log_ok "$service_desc erreichbar ($health_url)"
            healthy_count=$((healthy_count + 1))
        else
            log_warn "$service_desc nicht erreichbar ($health_url)"
        fi
    done
    
    log_info "Health-Check: $healthy_count/$total_count Services gesund"
    
    if [[ $healthy_count -eq $total_count ]]; then
        return 0
    else
        return 1
    fi
}

# LEGACY (disabled): not part of canonical runtime
start_mcp_services() {
    log_err "Legacy MCP runtime is disabled; use the canonical services/* stack"
    return 1
}

stop_mcp_services() {
    log_warn "Legacy MCP runtime is disabled; nothing to stop"
    return 1
}

# Standard Services
start_standard_services() {
    log_info "Starte Standard Services..."
    
    local compose
    if compose=$(find_compose_file "docker-compose.yml" "standard"); then
        docker_compose_up "$compose" "" "-d" "standard"
    else
        log_err "Standard docker-compose.yml nicht gefunden"
        return 1
    fi
}

stop_standard_services() {
    log_info "Stoppe Standard Services..."
    
    local compose
    if compose=$(find_compose_file "docker-compose.yml" "standard"); then
        docker_compose_down "$compose" "standard"
    else
        log_warn "Standard docker-compose.yml nicht gefunden"
        return 1
    fi
}

# Alle Services verwalten
start_all_services() {
    log_info "Starte alle Services..."
    
    # Standard Services zuerst
    if start_standard_services; then
        log_ok "Standard Services gestartet"
    else
        log_warn "Standard Services konnten nicht gestartet werden"
    fi
    
    # Gesamt Health-Check
    sleep 5
    check_service_health "standard" 30 || true
}

stop_all_services() {
    log_info "Stoppe alle Services..."
    
    stop_standard_services || true
    
    log_ok "Alle Services gestoppt"
}

# Service-Logs anzeigen
show_service_logs() {
    local service_type="${1:-standard}"
    local service_name="${2:-}"
    local lines="${3:-50}"
    
    local compose_file
    if compose_file=$(find_compose_file "docker-compose.yml" "$service_type"); then
        local original_dir="$PWD"
        cd "$(dirname "$compose_file")" || return 1
        
        if [[ -n "$service_name" ]]; then
            $DOCKER_COMPOSE_COMMAND logs --tail="$lines" -f "$service_name"
        else
            $DOCKER_COMPOSE_COMMAND logs --tail="$lines" -f
        fi
        
        cd "$original_dir"
    else
        log_err "Compose-Datei für $service_type nicht gefunden"
        return 1
    fi
}

# Cleanup-Funktion
cleanup_docker_resources() {
    log_info "Bereinige Docker-Ressourcen..."
    
    # Stoppe alle Services
    stop_all_services
    
    # Entferne verwaiste Container
    if docker container prune -f >/dev/null 2>&1; then
        log_debug "Verwaiste Container entfernt"
    fi
    
    # Entferne unbenutzte Images (optional)
    if docker image prune -f >/dev/null 2>&1; then
        log_debug "Unbenutzte Images entfernt"
    fi
    
    # Entferne unbenutzte Volumes (vorsichtig)
    local volumes=(
        "${PWD##*/}_postgres_data"
        "${PWD##*/}_vector_data"
        "${PWD##*/}_redis_data"
    )
    
    for vol in "${volumes[@]}"; do
        if docker volume ls -q | grep -q "^${vol}$"; then
            docker volume rm "$vol" 2>/dev/null || true
            log_debug "Volume entfernt: $vol"
        fi
    done
    
    log_ok "Docker-Ressourcen bereinigt"
}

# Repariere find_compose_file falls es Probleme gibt
find_compose_file_fixed() {
    local name="${1:-docker-compose.yml}"
    local prefer_type="${2:-standard}"
    local search_paths=()
    case "$prefer_type" in
        mcp)
            search_paths=()
            ;;
        *)
            search_paths=(
                "$REPO_ROOT/docker-compose.yml"
                "$REPO_ROOT/docker-compose.yaml"
                "$REPO_ROOT/deploy/docker-compose.yml"
            )
            ;;
    esac
    for f in "${search_paths[@]}"; do
        if [ -f "$f" ]; then
            echo "$f"
            return 0
        fi
    done
    log_err "Docker Compose Datei nicht gefunden: $name"
    return 1
}

if declare -f find_compose_file >/dev/null; then
    find_compose_file() {
        find_compose_file_fixed "$@"
    }
fi
export -f find_compose_file detect_docker_compose check_docker
export -f docker_compose_up docker_compose_down show_service_status
export -f check_service_health start_mcp_services stop_mcp_services
export -f start_standard_services stop_standard_services

export -f start_all_services stop_all_services show_service_logs
export -f cleanup_docker_resources
