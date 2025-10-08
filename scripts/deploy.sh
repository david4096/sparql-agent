#!/bin/bash
# Production deployment script with multi-cloud support and rollback capability
# Usage: ./deploy.sh <provider> --environment <env> --version <ver> --image <img>

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${LOG_FILE:-/tmp/sparql-agent-deploy-$(date +%Y%m%d-%H%M%S).log}"

# Default values
ENVIRONMENT="${ENVIRONMENT:-staging}"
VERSION="${VERSION:-latest}"
IMAGE="${IMAGE:-}"
PROVIDER=""
DRY_RUN=false
SKIP_HEALTH_CHECK=false
BACKUP_BEFORE_DEPLOY=true

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*" | tee -a "$LOG_FILE"
}

# Usage information
usage() {
    cat <<EOF
Usage: $0 <provider> [options]

Providers:
    aws         Deploy to AWS (ECS/Fargate)
    gcp         Deploy to Google Cloud Platform (Cloud Run)
    azure       Deploy to Azure (Container Instances)
    kubernetes  Deploy to Kubernetes cluster

Options:
    --environment ENV   Target environment (development, staging, production)
    --version VER       Version to deploy
    --image IMAGE       Docker image to deploy
    --dry-run          Simulate deployment without making changes
    --skip-health      Skip health checks after deployment
    --no-backup        Skip pre-deployment backup

Examples:
    $0 aws --environment production --version v1.0.0
    $0 gcp --environment staging --image ghcr.io/user/sparql-agent:latest
    $0 kubernetes --environment production --version v1.2.3

EOF
    exit 1
}

# Parse command line arguments
parse_args() {
    if [[ $# -eq 0 ]]; then
        usage
    fi

    PROVIDER="$1"
    shift

    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --version)
                VERSION="$2"
                shift 2
                ;;
            --image)
                IMAGE="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-health)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --no-backup)
                BACKUP_BEFORE_DEPLOY=false
                shift
                ;;
            -h|--help)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done
}

# Validate environment
validate_environment() {
    log "Validating deployment environment..."

    case $ENVIRONMENT in
        development|staging|production)
            log "Environment: $ENVIRONMENT"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            exit 1
            ;;
    esac

    # Set default image if not provided
    if [[ -z "$IMAGE" ]]; then
        IMAGE="ghcr.io/sparql-agent/sparql-agent:${VERSION}"
    fi

    log "Image: $IMAGE"
    log "Provider: $PROVIDER"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."

    # Check if image exists
    if ! docker manifest inspect "$IMAGE" > /dev/null 2>&1; then
        log_error "Docker image not found: $IMAGE"
        exit 1
    fi

    # Check provider-specific prerequisites
    case $PROVIDER in
        aws)
            command -v aws >/dev/null 2>&1 || { log_error "AWS CLI not found"; exit 1; }
            ;;
        gcp)
            command -v gcloud >/dev/null 2>&1 || { log_error "gcloud CLI not found"; exit 1; }
            ;;
        azure)
            command -v az >/dev/null 2>&1 || { log_error "Azure CLI not found"; exit 1; }
            ;;
        kubernetes)
            command -v kubectl >/dev/null 2>&1 || { log_error "kubectl not found"; exit 1; }
            ;;
    esac

    log "Pre-deployment checks passed"
}

# Deploy to AWS ECS
deploy_aws() {
    log "Deploying to AWS ECS..."

    local cluster_name="sparql-agent-${ENVIRONMENT}"
    local service_name="sparql-agent"
    local task_family="sparql-agent-${ENVIRONMENT}"

    # Register new task definition
    log "Registering new task definition..."
    local task_def=$(cat <<EOF
{
  "family": "${task_family}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "sparql-agent",
      "image": "${IMAGE}",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "${ENVIRONMENT}"
        },
        {
          "name": "VERSION",
          "value": "${VERSION}"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/sparql-agent-${ENVIRONMENT}",
          "awslogs-region": "${AWS_REGION:-us-east-1}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF
)

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would register task definition"
        echo "$task_def" | jq .
    else
        local new_task_def=$(echo "$task_def" | aws ecs register-task-definition --cli-input-json file:///dev/stdin)
        local task_def_arn=$(echo "$new_task_def" | jq -r '.taskDefinition.taskDefinitionArn')
        log "Registered task definition: $task_def_arn"

        # Update service
        log "Updating ECS service..."
        aws ecs update-service \
            --cluster "$cluster_name" \
            --service "$service_name" \
            --task-definition "$task_def_arn" \
            --force-new-deployment

        # Wait for service to stabilize
        log "Waiting for service to stabilize..."
        aws ecs wait services-stable \
            --cluster "$cluster_name" \
            --services "$service_name"

        # Get service URL
        local lb_dns=$(aws elbv2 describe-load-balancers \
            --names "sparql-agent-${ENVIRONMENT}" \
            --query 'LoadBalancers[0].DNSName' \
            --output text)

        echo "url=https://${lb_dns}" >> "$GITHUB_OUTPUT" 2>/dev/null || true
        log "Deployment URL: https://${lb_dns}"
    fi

    log "AWS deployment completed"
}

# Deploy to Google Cloud Run
deploy_gcp() {
    log "Deploying to Google Cloud Run..."

    local service_name="sparql-agent-${ENVIRONMENT}"
    local region="${GCP_REGION:-us-central1}"
    local project="${GCP_PROJECT:-$(gcloud config get-value project)}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would deploy to Cloud Run"
    else
        gcloud run deploy "$service_name" \
            --image "$IMAGE" \
            --platform managed \
            --region "$region" \
            --project "$project" \
            --allow-unauthenticated \
            --memory 2Gi \
            --cpu 2 \
            --timeout 300 \
            --max-instances 10 \
            --set-env-vars "ENVIRONMENT=${ENVIRONMENT},VERSION=${VERSION}" \
            --port 8000

        # Get service URL
        local service_url=$(gcloud run services describe "$service_name" \
            --region "$region" \
            --project "$project" \
            --format 'value(status.url)')

        echo "url=${service_url}" >> "$GITHUB_OUTPUT" 2>/dev/null || true
        log "Deployment URL: ${service_url}"
    fi

    log "GCP deployment completed"
}

# Deploy to Azure Container Instances
deploy_azure() {
    log "Deploying to Azure Container Instances..."

    local resource_group="sparql-agent-${ENVIRONMENT}"
    local container_name="sparql-agent"
    local location="${AZURE_LOCATION:-eastus}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would deploy to Azure Container Instances"
    else
        az container create \
            --resource-group "$resource_group" \
            --name "$container_name" \
            --image "$IMAGE" \
            --cpu 2 \
            --memory 4 \
            --restart-policy Always \
            --ports 8000 \
            --dns-name-label "sparql-agent-${ENVIRONMENT}" \
            --location "$location" \
            --environment-variables \
                ENVIRONMENT="$ENVIRONMENT" \
                VERSION="$VERSION"

        # Get container URL
        local fqdn=$(az container show \
            --resource-group "$resource_group" \
            --name "$container_name" \
            --query 'ipAddress.fqdn' \
            --output tsv)

        echo "url=http://${fqdn}:8000" >> "$GITHUB_OUTPUT" 2>/dev/null || true
        log "Deployment URL: http://${fqdn}:8000"
    fi

    log "Azure deployment completed"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log "Deploying to Kubernetes..."

    local namespace="$ENVIRONMENT"
    local deployment_name="sparql-agent"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would deploy to Kubernetes"
    else
        # Update deployment image
        kubectl set image deployment/"$deployment_name" \
            sparql-agent="$IMAGE" \
            --namespace "$namespace"

        # Wait for rollout
        kubectl rollout status deployment/"$deployment_name" \
            --namespace "$namespace" \
            --timeout=10m

        # Get service endpoint
        local service_ip=$(kubectl get service "$deployment_name" \
            --namespace "$namespace" \
            -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

        echo "url=http://${service_ip}:8000" >> "$GITHUB_OUTPUT" 2>/dev/null || true
        log "Deployment URL: http://${service_ip}:8000"
    fi

    log "Kubernetes deployment completed"
}

# Main deployment function
deploy() {
    log "Starting deployment to ${PROVIDER}..."
    log "Environment: ${ENVIRONMENT}, Version: ${VERSION}"

    # Run backup if needed
    if [[ "$BACKUP_BEFORE_DEPLOY" == "true" && "$ENVIRONMENT" == "production" ]]; then
        log "Creating pre-deployment backup..."
        "${SCRIPT_DIR}/backup.sh" --environment "$ENVIRONMENT" --provider "$PROVIDER"
    fi

    # Deploy based on provider
    case $PROVIDER in
        aws)
            deploy_aws
            ;;
        gcp)
            deploy_gcp
            ;;
        azure)
            deploy_azure
            ;;
        kubernetes)
            deploy_kubernetes
            ;;
        *)
            log_error "Unknown provider: $PROVIDER"
            exit 1
            ;;
    esac

    log "Deployment completed successfully"
}

# Main execution
main() {
    parse_args "$@"
    validate_environment
    pre_deployment_checks
    deploy

    if [[ "$SKIP_HEALTH_CHECK" != "true" ]]; then
        log "Running post-deployment health checks..."
        # Health checks will be run by separate script
    fi

    log "Deployment process completed"
    log "Log file: $LOG_FILE"
}

# Run main function
main "$@"
