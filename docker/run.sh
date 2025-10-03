#!/bin/bash
# Docker run script for SPARQL Agent
# Convenient script to run containers with proper configuration

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_NAME="sparql-agent"
IMAGE_NAME="${IMAGE_NAME:-sparql-agent:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-sparql-agent}"
MODE="${MODE:-web}"

# Defaults
PORT="${PORT:-8000}"
DETACH="${DETACH:-true}"
REMOVE="${REMOVE:-true}"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Run SPARQL Agent Docker container with various configurations.

OPTIONS:
    -m, --mode MODE           Run mode: web, mcp, cli (default: web)
    -p, --port PORT           Port to expose (default: 8000 for web, 3000 for mcp)
    -n, --name NAME           Container name (default: sparql-agent)
    -i, --image IMAGE         Docker image (default: sparql-agent:latest)
    --fg                      Run in foreground (don't detach)
    --keep                    Keep container after exit (don't remove)
    --env-file FILE           Load environment from file
    -v, --volume VOLUME       Add volume mount (format: host:container)
    -e, --env VAR=VALUE       Set environment variable
    --debug                   Enable debug mode
    -h, --help                Show this help message

EXAMPLES:
    # Run web server
    $0 --mode web --port 8000

    # Run MCP server
    $0 --mode mcp --port 3000

    # Run interactive CLI
    $0 --mode cli --fg

    # Run with environment file
    $0 --env-file .env

    # Run with custom configuration
    $0 --env ANTHROPIC_API_KEY=sk-ant-xxx --volume ./data:/app/data

EOF
}

# Parse arguments
VOLUMES=()
ENV_VARS=()
ENV_FILE=""

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -n|--name)
                CONTAINER_NAME="$2"
                shift 2
                ;;
            -i|--image)
                IMAGE_NAME="$2"
                shift 2
                ;;
            --fg)
                DETACH="false"
                shift
                ;;
            --keep)
                REMOVE="false"
                shift
                ;;
            --env-file)
                ENV_FILE="$2"
                shift 2
                ;;
            -v|--volume)
                VOLUMES+=("$2")
                shift 2
                ;;
            -e|--env)
                ENV_VARS+=("$2")
                shift 2
                ;;
            --debug)
                ENV_VARS+=("SPARQL_AGENT_DEBUG=true")
                ENV_VARS+=("SPARQL_AGENT_LOG_LEVEL=DEBUG")
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_warn "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
}

# Set default port based on mode
set_default_port() {
    if [ -z "${PORT}" ]; then
        case "$MODE" in
            web|api)
                PORT=8000
                ;;
            mcp)
                PORT=3000
                ;;
            cli)
                PORT=""
                ;;
        esac
    fi
}

# Build docker run command
build_run_command() {
    CMD="docker run"

    # Container options
    if [ "$REMOVE" = "true" ]; then
        CMD="${CMD} --rm"
    fi

    if [ "$DETACH" = "true" ]; then
        CMD="${CMD} -d"
    else
        CMD="${CMD} -it"
    fi

    CMD="${CMD} --name ${CONTAINER_NAME}"

    # Port mapping
    if [ -n "$PORT" ]; then
        CMD="${CMD} -p ${PORT}:${PORT}"
    fi

    # Environment file
    if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
        CMD="${CMD} --env-file ${ENV_FILE}"
        log_info "Loading environment from: ${ENV_FILE}"
    fi

    # Environment variables
    for env in "${ENV_VARS[@]}"; do
        CMD="${CMD} -e ${env}"
    done

    # Set mode
    CMD="${CMD} -e SPARQL_AGENT_MODE=${MODE}"
    if [ -n "$PORT" ]; then
        CMD="${CMD} -e SPARQL_AGENT_PORT=${PORT}"
    fi

    # Volume mounts
    for vol in "${VOLUMES[@]}"; do
        CMD="${CMD} -v ${vol}"
    done

    # Default volumes
    CMD="${CMD} -v $(pwd)/data:/app/data"
    CMD="${CMD} -v $(pwd)/logs:/app/logs"
    CMD="${CMD} -v $(pwd)/cache:/app/.cache"

    # Image
    CMD="${CMD} ${IMAGE_NAME}"

    # Command argument
    CMD="${CMD} ${MODE}"

    echo "$CMD"
}

# Stop existing container
stop_existing() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_warn "Container ${CONTAINER_NAME} already exists. Removing..."
        docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    fi
}

# Create directories
create_directories() {
    log_info "Creating directories..."
    mkdir -p data logs cache
}

# Main execution
main() {
    parse_args "$@"
    set_default_port

    log_info "Starting SPARQL Agent container"
    log_info "Mode: ${MODE}"
    log_info "Image: ${IMAGE_NAME}"
    log_info "Container: ${CONTAINER_NAME}"
    if [ -n "$PORT" ]; then
        log_info "Port: ${PORT}"
    fi

    create_directories
    stop_existing

    # Build and execute command
    RUN_CMD=$(build_run_command)

    log_info "Running command:"
    echo "$RUN_CMD"
    echo

    if eval "$RUN_CMD"; then
        if [ "$DETACH" = "true" ]; then
            log_info "Container started successfully"
            log_info "View logs: docker logs -f ${CONTAINER_NAME}"
            log_info "Stop container: docker stop ${CONTAINER_NAME}"

            if [ -n "$PORT" ]; then
                sleep 2
                case "$MODE" in
                    web|api)
                        log_info "API: http://localhost:${PORT}"
                        log_info "Docs: http://localhost:${PORT}/docs"
                        log_info "Health: http://localhost:${PORT}/health"
                        ;;
                    mcp)
                        log_info "MCP Server: http://localhost:${PORT}"
                        ;;
                esac
            fi
        fi
    else
        log_warn "Container exited"
    fi
}

# Run main
main "$@"
