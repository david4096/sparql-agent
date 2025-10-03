#!/bin/bash
# Rollback script for failed deployments
# Usage: ./rollback.sh --environment <env> [--provider <provider>]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${LOG_FILE:-/tmp/sparql-agent-rollback-$(date +%Y%m%d-%H%M%S).log}"

# Default values
ENVIRONMENT="${ENVIRONMENT:-staging}"
PROVIDER="aws"
AUTO_CONFIRM=false

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*" | tee -a "$LOG_FILE"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --yes)
            AUTO_CONFIRM=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Rollback AWS deployment
rollback_aws() {
    log "Rolling back AWS deployment..."

    local cluster="sparql-agent-${ENVIRONMENT}"
    local service="sparql-agent"

    # Get previous task definition
    local current_task=$(aws ecs describe-services \
        --cluster "$cluster" \
        --services "$service" \
        --query 'services[0].taskDefinition' \
        --output text)

    local previous_task=$(aws ecs list-task-definitions \
        --family-prefix "sparql-agent-${ENVIRONMENT}" \
        --sort DESC \
        --max-items 2 \
        --query 'taskDefinitionArns[1]' \
        --output text)

    log "Current task: $current_task"
    log "Rolling back to: $previous_task"

    # Update service to previous task definition
    aws ecs update-service \
        --cluster "$cluster" \
        --service "$service" \
        --task-definition "$previous_task" \
        --force-new-deployment

    # Wait for rollback to complete
    aws ecs wait services-stable \
        --cluster "$cluster" \
        --services "$service"

    log "AWS rollback completed"
}

# Rollback GCP deployment
rollback_gcp() {
    log "Rolling back GCP deployment..."

    local service="sparql-agent-${ENVIRONMENT}"
    local region="${GCP_REGION:-us-central1}"

    # Get previous revision
    local revisions=$(gcloud run revisions list \
        --service "$service" \
        --region "$region" \
        --limit 2 \
        --format 'value(name)')

    local previous_revision=$(echo "$revisions" | tail -n1)

    log "Rolling back to revision: $previous_revision"

    # Update traffic to previous revision
    gcloud run services update-traffic "$service" \
        --region "$region" \
        --to-revisions="${previous_revision}=100"

    log "GCP rollback completed"
}

# Rollback Azure deployment
rollback_azure() {
    log "Rolling back Azure deployment..."

    local resource_group="sparql-agent-${ENVIRONMENT}"
    local container="sparql-agent"

    # Get previous image from backup
    local backup_file="${BACKUP_DIR}/azure-deployment-${ENVIRONMENT}-previous.json"

    if [[ -f "$backup_file" ]]; then
        local previous_image=$(jq -r '.image' "$backup_file")

        log "Rolling back to image: $previous_image"

        az container create \
            --resource-group "$resource_group" \
            --name "$container" \
            --image "$previous_image" \
            --restart-policy Always

        log "Azure rollback completed"
    else
        log_error "No backup found for rollback"
        exit 1
    fi
}

# Rollback Kubernetes deployment
rollback_kubernetes() {
    log "Rolling back Kubernetes deployment..."

    local namespace="$ENVIRONMENT"
    local deployment="sparql-agent"

    # Rollback using kubectl
    kubectl rollout undo deployment/"$deployment" \
        --namespace "$namespace"

    # Wait for rollback
    kubectl rollout status deployment/"$deployment" \
        --namespace "$namespace"

    log "Kubernetes rollback completed"
}

# Main
main() {
    log "Starting rollback for environment: $ENVIRONMENT"
    log "Provider: $PROVIDER"

    if [[ "$AUTO_CONFIRM" != "true" ]]; then
        log_warn "This will rollback the deployment. Continue? (yes/no)"
        read -r response
        if [[ "$response" != "yes" ]]; then
            log "Rollback cancelled"
            exit 0
        fi
    fi

    case $PROVIDER in
        aws)
            rollback_aws
            ;;
        gcp)
            rollback_gcp
            ;;
        azure)
            rollback_azure
            ;;
        kubernetes)
            rollback_kubernetes
            ;;
        *)
            log_error "Unknown provider: $PROVIDER"
            exit 1
            ;;
    esac

    # Run health checks
    log "Running health checks after rollback..."
    "${SCRIPT_DIR}/health-check.sh" --url "$(get_service_url)" --retries 5

    log "Rollback completed successfully"
    log "Log file: $LOG_FILE"
}

# Helper to get service URL
get_service_url() {
    case $PROVIDER in
        aws)
            aws elbv2 describe-load-balancers \
                --names "sparql-agent-${ENVIRONMENT}" \
                --query 'LoadBalancers[0].DNSName' \
                --output text
            ;;
        gcp)
            gcloud run services describe "sparql-agent-${ENVIRONMENT}" \
                --region "${GCP_REGION:-us-central1}" \
                --format 'value(status.url)'
            ;;
        *)
            echo "http://localhost:8000"
            ;;
    esac
}

main
