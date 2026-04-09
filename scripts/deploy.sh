#!/bin/bash
# -*- coding: utf-8 -*-
# Agent-NN Deployment Script - Multi-Environment Deployment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

source "$SCRIPT_DIR/lib/log_utils.sh"
source "$SCRIPT_DIR/lib/docker_utils.sh"
source "$SCRIPT_DIR/lib/status_utils.sh"
source "$SCRIPT_DIR/helpers/common.sh"
source "$SCRIPT_DIR/helpers/docker.sh"

# Deployment-Konfiguration
DEPLOYMENT_TARGET="local"
DEPLOYMENT_ENV="development"
BUILD_IMAGES=true
RUN_TESTS=true
BACKUP_BEFORE_DEPLOY=true
ROLLBACK_ON_FAILURE=true
DEPLOYMENT_STRATEGY="rolling"
HEALTH_CHECK_TIMEOUT=300
DEPLOYMENT_REGISTRY=""
IMAGE_TAG="latest"

# Deployment-Targets
declare -A DEPLOYMENT_TARGETS=(
    [local]="Lokales Development Setup"
    [staging]="Staging Environment" 
    [production]="Production Environment"
    [docker]="Docker Compose Deployment"
    [kubernetes]="Kubernetes Deployment"
    [cloud]="Cloud Platform Deployment"
)

# Environment-spezifische Konfigurationen
declare -A ENV_CONFIGS=(
    [development]="dev"
    [staging]="staging"
    [production]="prod"
    [testing]="test"
)

usage() {
    cat << EOF
Usage: $(basename "$0") [TARGET] [OPTIONS]

Advanced Deployment Script für Agent-NN

TARGETS:
    local               Lokales Development Setup (default)
    staging             Staging Environment
    production          Production Environment  
    docker              Docker Compose Deployment
    kubernetes          Kubernetes Deployment
    cloud               Cloud Platform Deployment

OPTIONS:
    --env ENVIRONMENT   Deployment-Umgebung (dev|staging|prod|test)
    --tag TAG           Image-Tag für Deployment (default: latest)
    --registry URL      Container Registry URL
    --strategy STRATEGY Deployment-Strategie (rolling|blue-green|recreate)
    --no-build          Images nicht neu bauen
    --no-tests          Tests vor Deployment überspringen
    --no-backup         Backup vor Deployment überspringen
    --no-rollback       Automatisches Rollback deaktivieren
    --timeout SECONDS   Health-Check Timeout (default: 300)
    --config FILE       Deployment-Konfigurationsdatei
    --dry-run           Nur Deployment-Plan anzeigen
    --force             Deployment erzwingen (überspringt Checks)
    -h, --help          Diese Hilfe anzeigen

DEPLOYMENT-STRATEGIEN:
    rolling             Schrittweiser Austausch der Services (default)
    blue-green          Parallele Umgebung mit Switch
    recreate            Stoppe alle, dann starte neu

BEISPIELE:
    $(basename "$0") local                          # Lokales Deployment
    $(basename "$0") staging --tag v1.2.3          # Staging mit spezifischem Tag
    $(basename "$0") production --strategy blue-green # Production mit Blue-Green
    $(basename "$0") docker --env prod --no-tests  # Docker ohne Tests
    $(basename "$0") kubernetes --registry ghcr.io # K8s mit Registry

EOF
}

# Deployment-Konfiguration laden
load_deployment_config() {
    local config_file="${1:-$REPO_ROOT/.agentnn/deployment.yml}"
    
    if [[ -f "$config_file" ]]; then
        log_info "Lade Deployment-Konfiguration: $config_file"
        # YAML-Parsing würde hier implementiert werden
        log_debug "Konfigurationsdatei geladen"
    else
        log_debug "Keine Deployment-Konfiguration gefunden, verwende Defaults"
    fi
}

# Pre-Deployment Checks
pre_deployment_checks() {
    log_info "=== PRE-DEPLOYMENT CHECKS ==="
    
    local check_failures=0
    
    # Repository-Status prüfen
    if [[ -d "$REPO_ROOT/.git" ]]; then
        if ! git diff --quiet; then
            log_warn "Uncommitted changes im Repository gefunden"
            if [[ "${FORCE_DEPLOY:-false}" != "true" ]]; then
                log_err "Deployment mit uncommitted changes nicht erlaubt"
                check_failures=$((check_failures + 1))
            fi
        fi
        
        # Tag-Validierung für Production
        if [[ "$DEPLOYMENT_ENV" == "production" && "$IMAGE_TAG" == "latest" ]]; then
            log_warn "Production-Deployment mit 'latest' Tag nicht empfohlen"
            if [[ "${FORCE_DEPLOY:-false}" != "true" ]]; then
                log_err "Verwende spezifischen Tag für Production"
                check_failures=$((check_failures + 1))
            fi
        fi
    fi
    
    # Environment-spezifische Checks
    case "$DEPLOYMENT_TARGET" in
        production)
            # Production-spezifische Validierungen
            if [[ ! -f "$REPO_ROOT/.env.production" ]]; then
                log_err "Production environment file (.env.production) nicht gefunden"
                check_failures=$((check_failures + 1))
            fi
            
            # Backup-Verfügbarkeit prüfen
            if [[ "$BACKUP_BEFORE_DEPLOY" == "true" ]]; then
                if ! command -v pg_dump >/dev/null; then
                    log_warn "pg_dump für Datenbank-Backup nicht verfügbar"
                fi
            fi
            ;;
        kubernetes)
            # Kubernetes-spezifische Checks
            if ! command -v kubectl >/dev/null; then
                log_err "kubectl für Kubernetes-Deployment erforderlich"
                check_failures=$((check_failures + 1))
            fi
            
            if ! kubectl cluster-info >/dev/null 2>&1; then
                log_err "Kubernetes-Cluster nicht erreichbar"
                check_failures=$((check_failures + 1))
            fi
            ;;
        cloud)
            # Cloud-spezifische Checks
            log_warn "Cloud-Deployment noch nicht vollständig implementiert"
            ;;
    esac
    
    # Docker-Verfügbarkeit
    if [[ "$DEPLOYMENT_TARGET" =~ (docker|kubernetes) ]]; then
        if ! check_docker; then
            log_err "Docker für Deployment erforderlich"
            check_failures=$((check_failures + 1))
        fi
    fi
    
    if [[ $check_failures -gt 0 ]]; then
        log_err "Pre-Deployment Checks fehlgeschlagen ($check_failures Fehler)"
        if [[ "${FORCE_DEPLOY:-false}" != "true" ]]; then
            exit 1
        else
            log_warn "Deployment wird trotz Fehlern fortgesetzt (--force aktiviert)"
        fi
    fi
    
    log_ok "Pre-Deployment Checks erfolgreich"
}

# Tests vor Deployment
run_pre_deployment_tests() {
    if [[ "$RUN_TESTS" != "true" ]]; then
        log_info "Tests übersprungen"
        return 0
    fi
    
    log_info "=== PRE-DEPLOYMENT TESTS ==="
    
    cd "$REPO_ROOT" || return 1
    
    # Unit Tests
    if ! "$SCRIPT_DIR/test.sh" unit --quick; then
        log_err "Unit Tests fehlgeschlagen"
        return 1
    fi
    
    # Integration Tests für non-local Deployments
    if [[ "$DEPLOYMENT_TARGET" != "local" ]]; then
        if ! "$SCRIPT_DIR/test.sh" integration; then
            log_err "Integration Tests fehlgeschlagen"
            return 1
        fi
    fi
    
    # Security Checks für Production
    if [[ "$DEPLOYMENT_ENV" == "production" ]]; then
        if command -v bandit >/dev/null; then
            if ! bandit -r . -f json -o /tmp/bandit-report.json; then
                log_warn "Security Issues gefunden - siehe /tmp/bandit-report.json"
            fi
        fi
    fi
    
    log_ok "Pre-Deployment Tests erfolgreich"
}

# Images bauen
build_deployment_images() {
    if [[ "$BUILD_IMAGES" != "true" ]]; then
        log_info "Image-Build übersprungen"
        return 0
    fi
    
    log_info "=== IMAGE BUILD ==="
    
    cd "$REPO_ROOT" || return 1
    
    # Frontend bauen
    log_info "Baue Frontend..."
    if ! "$SCRIPT_DIR/build_frontend.sh"; then
        log_err "Frontend-Build fehlgeschlagen"
        return 1
    fi
    
    # Docker Images bauen
    case "$DEPLOYMENT_TARGET" in
        docker|kubernetes|cloud)
            log_info "Baue Docker Images..."
            
            # Basis-Image
            local base_image="agent-nn:${IMAGE_TAG}"
            if ! docker build -t "$base_image" -f Dockerfile .; then
                log_err "Docker-Build fehlgeschlagen"
                return 1
            fi
            
            # Registry Push
            if [[ -n "$DEPLOYMENT_REGISTRY" ]]; then
                push_images_to_registry
            fi
            ;;
    esac
    
    log_ok "Images erfolgreich gebaut"
}

# Images zu Registry pushen
push_images_to_registry() {
    log_info "Pushe Images zu Registry: $DEPLOYMENT_REGISTRY"
    
    local images=("agent-nn:${IMAGE_TAG}")
    
    for image in "${images[@]}"; do
        local registry_image="$DEPLOYMENT_REGISTRY/$image"
        
        if docker tag "$image" "$registry_image"; then
            if docker push "$registry_image"; then
                log_ok "Image gepusht: $registry_image"
            else
                log_err "Push fehlgeschlagen: $registry_image"
                return 1
            fi
        else
            log_err "Tagging fehlgeschlagen: $image -> $registry_image"
            return 1
        fi
    done
}

# Backup erstellen
create_deployment_backup() {
    if [[ "$BACKUP_BEFORE_DEPLOY" != "true" ]]; then
        log_info "Backup übersprungen"
        return 0
    fi
    
    log_info "=== DEPLOYMENT BACKUP ==="
    
    local backup_dir="$REPO_ROOT/backups/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Konfigurationsdateien sichern
    local config_files=(".env" "docker-compose.yml")
    for file in "${config_files[@]}"; do
        if [[ -f "$REPO_ROOT/$file" ]]; then
            cp "$REPO_ROOT/$file" "$backup_dir/"
            log_debug "Backup: $file"
        fi
    done
    
    # Datenbank-Backup (falls verfügbar)
    if docker ps --format "{{.Names}}" | grep -q postgres; then
        log_info "Erstelle Datenbank-Backup..."
        if docker exec "$(docker ps --format "{{.Names}}" | grep postgres | head -1)" \
           pg_dumpall -U postgres > "$backup_dir/database-backup.sql"; then
            log_ok "Datenbank-Backup erstellt"
        else
            log_warn "Datenbank-Backup fehlgeschlagen"
        fi
    fi
    
    # Status-Informationen speichern
    cat > "$backup_dir/deployment-info.json" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "target": "$DEPLOYMENT_TARGET",
    "environment": "$DEPLOYMENT_ENV",
    "image_tag": "$IMAGE_TAG",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')"
}
EOF
    
    log_ok "Backup erstellt: $backup_dir"
    export BACKUP_DIR="$backup_dir"
}

# Lokales Deployment
deploy_local() {
    log_info "=== LOKALES DEPLOYMENT ==="
    
    # Environment-Datei vorbereiten
    if [[ ! -f "$REPO_ROOT/.env" ]] && [[ -f "$REPO_ROOT/.env.example" ]]; then
        cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
        log_info ".env aus Beispiel erstellt"
    fi
    
    # Services starten
    case "$DEPLOYMENT_STRATEGY" in
        rolling)
            # Services schrittweise neustarten
            log_info "Starte Services mit Rolling Strategy..."
            
            # Standard Services
            if [[ -f "$REPO_ROOT/docker-compose.yml" ]]; then
                docker_compose_up "$REPO_ROOT/docker-compose.yml" "--build" "-d"
            fi
            
            ;;
        recreate)
            log_info "Starte Services mit Recreate Strategy..."
            
            # Alle Services stoppen
            if [[ -f "$REPO_ROOT/docker-compose.yml" ]]; then
                docker_compose_down "$REPO_ROOT/docker-compose.yml"
            fi
            if [[ -f "$REPO_ROOT/docker-compose.yml" ]]; then
                docker_compose_up "$REPO_ROOT/docker-compose.yml" "--build" "-d"
            fi
            ;;
    esac
    
    # Health Check
    perform_health_check
}

# Docker Deployment
deploy_docker() {
    log_info "=== DOCKER DEPLOYMENT ==="
    
    # Environment-spezifische Compose-Datei
    local compose_file="docker-compose.yml"
    if [[ -f "$REPO_ROOT/docker-compose.${DEPLOYMENT_ENV}.yml" ]]; then
        compose_file="docker-compose.${DEPLOYMENT_ENV}.yml"
    fi
    
    cd "$REPO_ROOT" || return 1
    
    case "$DEPLOYMENT_STRATEGY" in
        rolling)
            log_info "Rolling Deployment..."
            docker compose -f "$compose_file" up -d --build
            ;;
        blue-green)
            log_info "Blue-Green Deployment..."
            deploy_blue_green_docker "$compose_file"
            ;;
        recreate)
            log_info "Recreate Deployment..."
            docker compose -f "$compose_file" down
            docker compose -f "$compose_file" up -d --build
            ;;
    esac
    
    perform_health_check
}

# Blue-Green Deployment für Docker
deploy_blue_green_docker() {
    local compose_file="$1"
    
    # Neue "Green" Umgebung starten
    log_info "Starte Green Environment..."
    
    # Temporäre Compose-Datei mit anderen Ports erstellen
    local green_compose="/tmp/docker-compose-green.yml"
    sed 's/3000:3000/3001:3000/g; s/8000:8000/8001:8000/g' "$compose_file" > "$green_compose"
    
    if docker compose -f "$green_compose" up -d --build; then
        log_ok "Green Environment gestartet"
        
        # Health Check für Green
        if health_check_service "http://localhost:3001" && health_check_service "http://localhost:8001/health"; then
            log_ok "Green Environment ist gesund"
            
            # Blue Environment stoppen
            log_info "Stoppe Blue Environment..."
            docker compose -f "$compose_file" down
            
            # Green zu Blue wechseln
            log_info "Wechsle Green zu Blue..."
            docker compose -f "$compose_file" up -d
            docker compose -f "$green_compose" down
            
            log_ok "Blue-Green Deployment abgeschlossen"
        else
            log_err "Green Environment Health Check fehlgeschlagen"
            docker compose -f "$green_compose" down
            return 1
        fi
    else
        log_err "Green Environment konnte nicht gestartet werden"
        return 1
    fi
    
    rm -f "$green_compose"
}

# Kubernetes Deployment
deploy_kubernetes() {
    log_info "=== KUBERNETES DEPLOYMENT ==="
    
    local k8s_dir="$REPO_ROOT/k8s"
    if [[ ! -d "$k8s_dir" ]]; then
        log_err "Kubernetes-Manifeste nicht gefunden: $k8s_dir"
        return 1
    fi
    
    cd "$k8s_dir" || return 1
    
    # Namespace erstellen falls nicht vorhanden
    local namespace="agent-nn-${DEPLOYMENT_ENV}"
    if ! kubectl get namespace "$namespace" >/dev/null 2>&1; then
        kubectl create namespace "$namespace"
        log_info "Namespace erstellt: $namespace"
    fi
    
    # ConfigMaps und Secrets
    if [[ -f "configmap.yml" ]]; then
        kubectl apply -f configmap.yml -n "$namespace"
    fi
    
    if [[ -f "secrets.yml" ]]; then
        kubectl apply -f secrets.yml -n "$namespace"
    fi
    
    # Deployment-Strategie
    case "$DEPLOYMENT_STRATEGY" in
        rolling)
            log_info "Rolling Update Deployment..."
            kubectl apply -f . -n "$namespace"
            kubectl rollout status deployment/agent-nn -n "$namespace" --timeout="${HEALTH_CHECK_TIMEOUT}s"
            ;;
        blue-green)
            log_info "Blue-Green Deployment..."
            deploy_blue_green_k8s "$namespace"
            ;;
    esac
    
    # Service-Endpoints anzeigen
    kubectl get services -n "$namespace"
}

# Blue-Green Deployment für Kubernetes
deploy_blue_green_k8s() {
    local namespace="$1"
    
    # Green Deployment erstellen
    log_info "Erstelle Green Deployment..."
    
    # Labels für Green-Version setzen
    sed 's/version: blue/version: green/g' deployment.yml > deployment-green.yml
    
    if kubectl apply -f deployment-green.yml -n "$namespace"; then
        kubectl rollout status deployment/agent-nn-green -n "$namespace" --timeout="${HEALTH_CHECK_TIMEOUT}s"
        
        # Health Check für Green
        if health_check_k8s_service "$namespace" "agent-nn-green"; then
            log_ok "Green Deployment ist gesund"
            
            # Service auf Green umleiten
            kubectl patch service agent-nn -n "$namespace" -p '{"spec":{"selector":{"version":"green"}}}'
            
            # Blue Deployment entfernen
            kubectl delete deployment agent-nn-blue -n "$namespace" 2>/dev/null || true
            
            # Green zu Blue umbenennen
            kubectl patch deployment agent-nn-green -n "$namespace" -p '{"metadata":{"name":"agent-nn-blue"},"spec":{"selector":{"matchLabels":{"version":"blue"}},"template":{"metadata":{"labels":{"version":"blue"}}}}}'
            
            log_ok "Blue-Green Deployment abgeschlossen"
        else
            log_err "Green Deployment Health Check fehlgeschlagen"
            kubectl delete deployment agent-nn-green -n "$namespace"
            return 1
        fi
    else
        log_err "Green Deployment fehlgeschlagen"
        return 1
    fi
    
    rm -f deployment-green.yml
}

# Health Checks durchführen
perform_health_check() {
    log_info "=== HEALTH CHECKS ==="
    
    local health_endpoints=()
    
    case "$DEPLOYMENT_TARGET" in
        local|docker)
            health_endpoints=(
                "http://localhost:3000:Frontend"
                "http://localhost:8000/health:API"
            )
            
            # MCP Services falls verfügbar
            for port in 8001 8002 8003 8004 8005; do
                health_endpoints+=("http://localhost:$port/health:MCP-$port")
            done
            ;;
        kubernetes)
            # Kubernetes Service Health Checks
            local namespace="agent-nn-${DEPLOYMENT_ENV}"
            if ! health_check_k8s_service "$namespace" "agent-nn"; then
                return 1
            fi
            ;;
    esac
    
    local healthy_services=0
    local total_services=${#health_endpoints[@]}
    
    for endpoint_info in "${health_endpoints[@]}"; do
        local url="${endpoint_info%%:*}"
        local name="${endpoint_info##*:}"
        
        if health_check_service "$url"; then
            log_ok "$name ist gesund ($url)"
            healthy_services=$((healthy_services + 1))
        else
            log_warn "$name antwortet nicht ($url)"
        fi
    done
    
    if [[ $healthy_services -eq $total_services ]]; then
        log_ok "Alle Services sind gesund ($healthy_services/$total_services)"
        return 0
    elif [[ $healthy_services -gt 0 ]]; then
        log_warn "$healthy_services/$total_services Services sind gesund"
        return 1
    else
        log_err "Keine Services antworten"
        return 1
    fi
}

# Einzelner Health Check
health_check_service() {
    local url="$1"
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f -s --max-time 5 "$url" >/dev/null 2>&1; then
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 10
    done
    
    return 1
}

# Kubernetes Service Health Check
health_check_k8s_service() {
    local namespace="$1"
    local service="$2"
    
    # Warte auf Ready Pods
    if kubectl wait --for=condition=ready pod -l app="$service" -n "$namespace" --timeout="${HEALTH_CHECK_TIMEOUT}s"; then
        return 0
    else
        return 1
    fi
}

# Rollback durchführen
perform_rollback() {
    if [[ "$ROLLBACK_ON_FAILURE" != "true" ]]; then
        log_warn "Rollback deaktiviert"
        return 0
    fi
    
    log_warn "=== ROLLBACK ==="
    
    if [[ -z "${BACKUP_DIR:-}" ]]; then
        log_err "Kein Backup für Rollback verfügbar"
        return 1
    fi
    
    log_info "Stelle System aus Backup wieder her: $BACKUP_DIR"
    
    # Konfigurationsdateien wiederherstellen
    local config_files=(".env" "docker-compose.yml")
    for file in "${config_files[@]}"; do
        if [[ -f "$BACKUP_DIR/$file" ]]; then
            cp "$BACKUP_DIR/$file" "$REPO_ROOT/"
            log_debug "Wiederhergestellt: $file"
        fi
    done
    
    # Services neu starten
    case "$DEPLOYMENT_TARGET" in
        local|docker)
            # Services mit alten Konfigurationen neustarten
            if [[ -f "$REPO_ROOT/docker-compose.yml" ]]; then
                docker compose down
                docker compose up -d
            fi
            ;;
        kubernetes)
            # Kubernetes Rollback
            local namespace="agent-nn-${DEPLOYMENT_ENV}"
            kubectl rollout undo deployment/agent-nn -n "$namespace"
            ;;
    esac
    
    log_ok "Rollback abgeschlossen"
}

# Post-Deployment Aktionen
post_deployment_actions() {
    log_info "=== POST-DEPLOYMENT ==="
    
    # Deployment-Informationen speichern
    local deployment_info="$REPO_ROOT/.agentnn/last-deployment.json"
    mkdir -p "$(dirname "$deployment_info")"
    
    cat > "$deployment_info" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "target": "$DEPLOYMENT_TARGET",
    "environment": "$DEPLOYMENT_ENV",
    "image_tag": "$IMAGE_TAG",
    "strategy": "$DEPLOYMENT_STRATEGY",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')",
    "success": true
}
EOF
    
    # Cleanup alter Backups (behalte letzte 5)
    if [[ -d "$REPO_ROOT/backups" ]]; then
        cd "$REPO_ROOT/backups" || return 0
        ls -t | tail -n +6 | xargs -r rm -rf
    fi
    
    # Deployment-Notification (falls konfiguriert)
    send_deployment_notification
    
    log_ok "Deployment erfolgreich abgeschlossen"
}

# Deployment-Benachrichtigung senden
send_deployment_notification() {
    # Placeholder für Notification-System (Slack, Email, etc.)
    log_debug "Deployment-Benachrichtigung würde hier gesendet werden"
}

# Deployment-Plan anzeigen
show_deployment_plan() {
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                             DEPLOYMENT PLAN                                 ║"
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    printf "║  Target:        %-60s ║\n" "$DEPLOYMENT_TARGET"
    printf "║  Environment:   %-60s ║\n" "$DEPLOYMENT_ENV"
    printf "║  Strategy:      %-60s ║\n" "$DEPLOYMENT_STRATEGY"
    printf "║  Image Tag:     %-60s ║\n" "$IMAGE_TAG"
    printf "║  Build Images:  %-60s ║\n" "$BUILD_IMAGES"
    printf "║  Run Tests:     %-60s ║\n" "$RUN_TESTS"
    printf "║  Create Backup: %-60s ║\n" "$BACKUP_BEFORE_DEPLOY"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo
    echo "Deployment-Schritte:"
    echo "1. Pre-Deployment Checks"
    echo "2. Tests ausführen"
    echo "3. Images bauen"
    echo "4. Backup erstellen"
    echo "5. Deployment durchführen"
    echo "6. Health Checks"
    echo "7. Post-Deployment Aktionen"
    echo
}

# Hauptfunktion
main() {
    local dry_run=false
    local force_deploy=false
    local config_file=""
    
    # Parameter parsen
    while [[ $# -gt 0 ]]; do
        case $1 in
            local|staging|production|docker|kubernetes|cloud)
                DEPLOYMENT_TARGET="$1"
                shift
                ;;
            --env)
                DEPLOYMENT_ENV="$2"
                shift 2
                ;;
            --tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            --registry)
                DEPLOYMENT_REGISTRY="$2"
                shift 2
                ;;
            --strategy)
                DEPLOYMENT_STRATEGY="$2"
                shift 2
                ;;
            --no-build)
                BUILD_IMAGES=false
                shift
                ;;
            --no-tests)
                RUN_TESTS=false
                shift
                ;;
            --no-backup)
                BACKUP_BEFORE_DEPLOY=false
                shift
                ;;
            --no-rollback)
                ROLLBACK_ON_FAILURE=false
                shift
                ;;
            --timeout)
                HEALTH_CHECK_TIMEOUT="$2"
                shift 2
                ;;
            --config)
                config_file="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --force)
                force_deploy=true
                export FORCE_DEPLOY=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_err "Unbekannte Option: $1"
                usage >&2
                exit 1
                ;;
        esac
    done
    
    # Konfiguration laden
    load_deployment_config "$config_file"
    
    # Dry-Run: Nur Plan anzeigen
    if [[ "$dry_run" == "true" ]]; then
        show_deployment_plan
        exit 0
    fi
    
    log_info "Starte Deployment: $DEPLOYMENT_TARGET ($DEPLOYMENT_ENV)"
    
    # Deployment-Pipeline
    local deployment_success=false
    
    {
        pre_deployment_checks &&
        run_pre_deployment_tests &&
        build_deployment_images &&
        create_deployment_backup &&
        
        case "$DEPLOYMENT_TARGET" in
            local)
                deploy_local
                ;;
            docker)
                deploy_docker
                ;;
            kubernetes)
                deploy_kubernetes
                ;;
            staging|production)
                # Staging/Production verwenden Docker oder K8s
                if command -v kubectl >/dev/null && kubectl cluster-info >/dev/null 2>&1; then
                    deploy_kubernetes
                else
                    deploy_docker
                fi
                ;;
            cloud)
                log_err "Cloud-Deployment noch nicht implementiert"
                exit 1
                ;;
            *)
                log_err "Unbekanntes Deployment-Target: $DEPLOYMENT_TARGET"
                exit 1
                ;;
        esac &&
        
        post_deployment_actions &&
        deployment_success=true
        
    } || {
        log_err "Deployment fehlgeschlagen"
        perform_rollback
        exit 1
    }
    
    if [[ "$deployment_success" == "true" ]]; then
        echo
        echo "🎉 Deployment erfolgreich abgeschlossen!"
        echo "   Target: $DEPLOYMENT_TARGET"
        echo "   Environment: $DEPLOYMENT_ENV"
        echo "   Tag: $IMAGE_TAG"
        echo
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
