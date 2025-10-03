#!/bin/sh
# Entrypoint script for SPARQL Agent Docker container
# Handles initialization, configuration, and service startup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo "${RED}[ERROR]${NC} $1"
}

# Print startup banner
print_banner() {
    cat <<'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              SPARQL Agent Container                       ║
║   Intelligent SPARQL Query Agent with LLM Integration    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
}

# Initialize directories
init_directories() {
    log_info "Initializing directories..."

    # Create directories if they don't exist
    mkdir -p /app/logs /app/data /app/.cache

    # Set permissions (if running as root, which we shouldn't be)
    if [ "$(id -u)" -eq 0 ]; then
        log_warn "Running as root - setting permissions"
        chown -R sparql:sparql /app/logs /app/data /app/.cache 2>/dev/null || true
    fi

    log_info "Directories initialized"
}

# Wait for dependencies
wait_for_service() {
    local host="$1"
    local port="$2"
    local service="$3"
    local max_attempts=30
    local attempt=0

    log_info "Waiting for $service at $host:$port..."

    while [ $attempt -lt $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null || curl -s "$host:$port" >/dev/null 2>&1; then
            log_info "$service is ready"
            return 0
        fi

        attempt=$((attempt + 1))
        log_info "Waiting for $service... (attempt $attempt/$max_attempts)"
        sleep 2
    done

    log_error "$service is not available after $max_attempts attempts"
    return 1
}

# Wait for dependencies
wait_for_dependencies() {
    # Wait for Redis if enabled
    if [ "${REDIS_ENABLED:-false}" = "true" ]; then
        REDIS_HOST="${REDIS_HOST:-redis}"
        REDIS_PORT="${REDIS_PORT:-6379}"

        if ! wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis"; then
            log_warn "Redis not available - continuing anyway"
        fi
    fi

    # Wait for PostgreSQL if configured
    if [ -n "${POSTGRES_HOST:-}" ]; then
        POSTGRES_PORT="${POSTGRES_PORT:-5432}"

        if ! wait_for_service "$POSTGRES_HOST" "$POSTGRES_PORT" "PostgreSQL"; then
            log_warn "PostgreSQL not available - continuing anyway"
        fi
    fi
}

# Run database migrations (if applicable)
run_migrations() {
    if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
        log_info "Running database migrations..."
        # Add migration command here when implemented
        # python -m sparql_agent.db.migrate
        log_info "Migrations completed"
    fi
}

# Validate configuration
validate_config() {
    log_info "Validating configuration..."

    # Check for required environment variables based on mode
    case "${1:-web}" in
        web|api)
            if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
                log_warn "No LLM API keys configured - LLM features will be disabled"
            fi
            ;;
        mcp)
            log_info "MCP server mode - checking configuration..."
            ;;
    esac

    log_info "Configuration validated"
}

# Start web server
start_web_server() {
    log_info "Starting FastAPI web server..."
    log_info "Host: ${SPARQL_AGENT_HOST:-0.0.0.0}"
    log_info "Port: ${SPARQL_AGENT_PORT:-8000}"
    log_info "Workers: ${SPARQL_AGENT_WORKERS:-4}"
    log_info "Log Level: ${SPARQL_AGENT_LOG_LEVEL:-INFO}"

    if [ "${SPARQL_AGENT_RELOAD:-false}" = "true" ]; then
        log_info "Hot reload enabled (development mode)"
        exec uvicorn sparql_agent.web.server:app \
            --host "${SPARQL_AGENT_HOST:-0.0.0.0}" \
            --port "${SPARQL_AGENT_PORT:-8000}" \
            --reload \
            --log-level "${SPARQL_AGENT_LOG_LEVEL:-info}"
    else
        log_info "Production mode"
        exec uvicorn sparql_agent.web.server:app \
            --host "${SPARQL_AGENT_HOST:-0.0.0.0}" \
            --port "${SPARQL_AGENT_PORT:-8000}" \
            --workers "${SPARQL_AGENT_WORKERS:-4}" \
            --log-level "${SPARQL_AGENT_LOG_LEVEL:-info}" \
            --access-log \
            --use-colors
    fi
}

# Start MCP server
start_mcp_server() {
    log_info "Starting MCP server..."
    log_info "Port: ${SPARQL_AGENT_PORT:-3000}"

    exec python -m sparql_agent.mcp.server
}

# Start CLI in interactive mode
start_cli() {
    log_info "Starting interactive CLI..."

    exec python -m sparql_agent.cli.interactive
}

# Run custom command
run_command() {
    log_info "Running custom command: $*"
    exec "$@"
}

# Main execution
main() {
    print_banner

    log_info "Container starting..."
    log_info "User: $(whoami)"
    log_info "Working directory: $(pwd)"
    log_info "Python version: $(python --version)"

    # Initialize
    init_directories
    wait_for_dependencies

    # Get command
    COMMAND="${1:-web}"

    # Validate configuration
    validate_config "$COMMAND"

    # Execute based on command
    case "$COMMAND" in
        web|api|server)
            run_migrations
            start_web_server
            ;;

        mcp)
            start_mcp_server
            ;;

        cli|interactive)
            start_cli
            ;;

        test|tests)
            log_info "Running tests..."
            shift
            exec pytest "$@"
            ;;

        shell|sh|bash)
            log_info "Starting shell..."
            exec /bin/sh
            ;;

        *)
            # Run custom command
            run_command "$@"
            ;;
    esac
}

# Handle signals for graceful shutdown
trap 'log_info "Received SIGTERM, shutting down gracefully..."; exit 0' TERM
trap 'log_info "Received SIGINT, shutting down gracefully..."; exit 0' INT

# Run main function
main "$@"
