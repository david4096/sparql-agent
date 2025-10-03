#!/bin/bash
# Development script for SPARQL Agent
# Quick start for development environment with docker-compose

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
COMPOSE_FILE="docker-compose.dev.yml"
PROJECT_NAME="sparql-agent-dev"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
}

print_usage() {
    cat <<EOF
Usage: $0 [COMMAND] [OPTIONS]

Manage SPARQL Agent development environment.

COMMANDS:
    up              Start development environment
    down            Stop development environment
    restart         Restart services
    logs            View service logs
    shell           Open shell in API container
    test            Run tests
    build           Rebuild containers
    clean           Clean up everything
    ps              Show running services
    status          Show service status

OPTIONS:
    --profile PROFILE  Enable profile (tools, jupyter, testing, database)
    --scale N          Scale API servers
    -f                 Follow logs
    -h, --help         Show this help message

EXAMPLES:
    # Start basic development environment
    $0 up

    # Start with all tools
    $0 up --profile tools --profile jupyter

    # View logs
    $0 logs -f

    # Run tests
    $0 test

    # Open shell
    $0 shell

    # Clean everything
    $0 clean

EOF
}

# Check environment
check_environment() {
    if [ ! -f ".env" ]; then
        log_warn ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_info "Created .env file. Please update with your API keys."
        else
            log_warn "No .env.example found. Creating minimal .env..."
            cat > .env <<EOF
# SPARQL Agent Development Environment
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
LLM_PROVIDER=anthropic
LOG_LEVEL=DEBUG
EOF
            log_info "Created minimal .env file. Please add your API keys."
        fi
    fi
}

# Create directories
create_directories() {
    log_info "Creating development directories..."
    mkdir -p dev-data dev-logs dev-cache notebooks htmlcov
}

# Start services
start_services() {
    local profiles=()

    while [[ $# -gt 0 ]]; do
        case $1 in
            --profile)
                profiles+=(--profile "$2")
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    log_section "Starting Development Environment"

    create_directories
    check_environment

    log_info "Starting services..."

    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" \
        "${profiles[@]}" up -d

    log_info "Waiting for services to be ready..."
    sleep 3

    log_section "Development Environment Ready"

    # Show service URLs
    show_service_urls
}

# Stop services
stop_services() {
    log_section "Stopping Development Environment"

    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down

    log_info "Services stopped"
}

# Restart services
restart_services() {
    log_section "Restarting Services"

    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" restart

    log_info "Services restarted"
}

# View logs
view_logs() {
    local follow_flag=""

    if [[ "$*" == *"-f"* ]]; then
        follow_flag="-f"
    fi

    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs $follow_flag "$@"
}

# Open shell
open_shell() {
    log_info "Opening shell in API container..."

    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" \
        exec sparql-agent-api /bin/sh
}

# Run tests
run_tests() {
    log_section "Running Tests"

    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" \
        run --rm sparql-agent-api pytest -v "$@"
}

# Build containers
build_containers() {
    log_section "Building Containers"

    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" build --no-cache

    log_info "Containers built successfully"
}

# Clean up
clean_up() {
    log_section "Cleaning Up"

    log_warn "This will remove all containers, volumes, and development data."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v
        rm -rf dev-data dev-logs dev-cache htmlcov .pytest_cache

        log_info "Cleanup complete"
    else
        log_info "Cleanup cancelled"
    fi
}

# Show process status
show_status() {
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
}

# Show service URLs
show_service_urls() {
    echo -e "\n${BLUE}Service URLs:${NC}"
    echo -e "  ${GREEN}API Server:${NC}       http://localhost:8000"
    echo -e "  ${GREEN}API Docs:${NC}         http://localhost:8000/docs"
    echo -e "  ${GREEN}API Health:${NC}       http://localhost:8000/health"
    echo -e "  ${GREEN}MCP Server:${NC}       http://localhost:3000"
    echo -e "  ${GREEN}Redis Commander:${NC}  http://localhost:8081"

    # Check if profiles are enabled
    if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps | grep -q "jupyter"; then
        echo -e "  ${GREEN}Jupyter Lab:${NC}      http://localhost:8888"
    fi

    if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps | grep -q "adminer"; then
        echo -e "  ${GREEN}Adminer (DB):${NC}     http://localhost:8082"
    fi

    if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps | grep -q "mailhog"; then
        echo -e "  ${GREEN}Mailhog:${NC}          http://localhost:8025"
    fi

    echo -e "\n${BLUE}Commands:${NC}"
    echo -e "  ${GREEN}View logs:${NC}        $0 logs -f"
    echo -e "  ${GREEN}Run tests:${NC}        $0 test"
    echo -e "  ${GREEN}Open shell:${NC}       $0 shell"
    echo -e "  ${GREEN}Stop services:${NC}    $0 down"
    echo
}

# Main execution
main() {
    if [ $# -eq 0 ]; then
        print_usage
        exit 0
    fi

    COMMAND=$1
    shift

    case "$COMMAND" in
        up|start)
            start_services "$@"
            ;;
        down|stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            view_logs "$@"
            ;;
        shell|sh|bash)
            open_shell
            ;;
        test|tests)
            run_tests "$@"
            ;;
        build|rebuild)
            build_containers
            ;;
        clean|cleanup)
            clean_up
            ;;
        ps|status)
            show_status
            ;;
        urls)
            show_service_urls
            ;;
        -h|--help|help)
            print_usage
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            print_usage
            exit 1
            ;;
    esac
}

# Run main
main "$@"
