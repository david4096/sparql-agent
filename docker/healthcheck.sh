#!/bin/sh
# Health check script for SPARQL Agent container
# Returns 0 if healthy, 1 if unhealthy

set -e

# Configuration
HOST="${SPARQL_AGENT_HOST:-0.0.0.0}"
PORT="${SPARQL_AGENT_PORT:-8000}"
MODE="${SPARQL_AGENT_MODE:-web}"
TIMEOUT=5

# Health check for web server
check_web_health() {
    # Try to hit the health endpoint
    if command -v curl >/dev/null 2>&1; then
        response=$(curl -f -s -o /dev/null -w "%{http_code}" \
            --max-time "$TIMEOUT" \
            "http://localhost:${PORT}/health" 2>/dev/null)

        if [ "$response" = "200" ]; then
            return 0
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q -O /dev/null -T "$TIMEOUT" \
            "http://localhost:${PORT}/health" 2>/dev/null; then
            return 0
        fi
    fi

    return 1
}

# Health check for MCP server
check_mcp_health() {
    # Check if the process is running
    if pgrep -f "sparql_agent.mcp.server" >/dev/null 2>&1; then
        return 0
    fi

    return 1
}

# Main health check
case "$MODE" in
    web|api|server)
        check_web_health
        exit $?
        ;;

    mcp)
        check_mcp_health
        exit $?
        ;;

    *)
        # Unknown mode - check if any Python process is running
        if pgrep -f "python" >/dev/null 2>&1; then
            exit 0
        fi
        exit 1
        ;;
esac
