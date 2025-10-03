#!/bin/bash
# Post-deployment health check script
# Usage: ./health-check.sh --url <url> [options]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${LOG_FILE:-/tmp/sparql-agent-health-$(date +%Y%m%d-%H%M%S).log}"

# Default values
URL=""
RETRIES=5
INTERVAL=30
TIMEOUT=10
EXPECTED_STATUS=200

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
Usage: $0 --url <url> [options]

Options:
    --url URL           Service URL to check
    --retries N         Number of retries (default: 5)
    --interval SEC      Interval between retries in seconds (default: 30)
    --timeout SEC       Request timeout in seconds (default: 10)
    --status CODE       Expected HTTP status code (default: 200)

Examples:
    $0 --url https://example.com/health
    $0 --url https://api.example.com --retries 10 --interval 15

EOF
    exit 1
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --url)
                URL="$2"
                shift 2
                ;;
            --retries)
                RETRIES="$2"
                shift 2
                ;;
            --interval)
                INTERVAL="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --status)
                EXPECTED_STATUS="$2"
                shift 2
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

    if [[ -z "$URL" ]]; then
        log_error "URL is required"
        usage
    fi
}

# Check if curl is available
check_dependencies() {
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
}

# Basic health check
check_health_endpoint() {
    local url="$1"
    local attempt="$2"

    log "Health check attempt $attempt/$RETRIES: $url"

    local response=$(curl -s -w "\n%{http_code}" -o /tmp/health-response.txt \
        --connect-timeout "$TIMEOUT" \
        --max-time "$TIMEOUT" \
        "$url" 2>&1) || {
        log_error "Failed to connect to $url"
        return 1
    }

    local http_code=$(echo "$response" | tail -n1)
    local body=$(cat /tmp/health-response.txt)

    log "HTTP Status: $http_code"

    if [[ "$http_code" == "$EXPECTED_STATUS" ]]; then
        log "Health check passed (HTTP $http_code)"
        return 0
    else
        log_warn "Health check failed (HTTP $http_code, expected $EXPECTED_STATUS)"
        log "Response body: $body"
        return 1
    fi
}

# Check API endpoints
check_api_endpoints() {
    local base_url="$1"

    log "Checking API endpoints..."

    # Check health endpoint
    if ! curl -sf -m "$TIMEOUT" "${base_url}/health" > /dev/null; then
        log_warn "Health endpoint check failed"
        return 1
    fi
    log "Health endpoint: OK"

    # Check metrics endpoint
    if ! curl -sf -m "$TIMEOUT" "${base_url}/metrics" > /dev/null; then
        log_warn "Metrics endpoint check failed"
        return 1
    fi
    log "Metrics endpoint: OK"

    # Check readiness endpoint
    if ! curl -sf -m "$TIMEOUT" "${base_url}/ready" > /dev/null; then
        log_warn "Readiness endpoint check failed"
        return 1
    fi
    log "Readiness endpoint: OK"

    return 0
}

# Check service performance
check_performance() {
    local url="$1"

    log "Checking service performance..."

    local start_time=$(date +%s%N)
    local response=$(curl -s -w "%{time_total}" -o /dev/null "$url")
    local end_time=$(date +%s%N)

    local response_time=$(echo "scale=3; ($end_time - $start_time) / 1000000000" | bc)

    log "Response time: ${response_time}s"

    # Check if response time is acceptable (< 5 seconds)
    if (( $(echo "$response_time > 5" | bc -l) )); then
        log_warn "Response time is high: ${response_time}s"
        return 1
    fi

    log "Performance check passed"
    return 0
}

# Check service functionality
check_functionality() {
    local base_url="$1"

    log "Checking service functionality..."

    # Test SPARQL query endpoint
    local query_endpoint="${base_url}/api/query"
    local test_query='SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 1'

    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$test_query\"}" \
        -m "$TIMEOUT" \
        "$query_endpoint")

    if [[ $? -eq 0 ]]; then
        log "Functionality check passed"
        return 0
    else
        log_warn "Functionality check failed"
        return 1
    fi
}

# Check database connectivity
check_database() {
    local base_url="$1"

    log "Checking database connectivity..."

    local db_endpoint="${base_url}/health/db"

    if curl -sf -m "$TIMEOUT" "$db_endpoint" > /dev/null; then
        log "Database connectivity: OK"
        return 0
    else
        log_warn "Database connectivity check failed"
        return 1
    fi
}

# Check external dependencies
check_dependencies_health() {
    local base_url="$1"

    log "Checking external dependencies..."

    local deps_endpoint="${base_url}/health/dependencies"

    local response=$(curl -s -m "$TIMEOUT" "$deps_endpoint")

    if [[ $? -eq 0 ]]; then
        log "External dependencies: OK"
        echo "$response" | jq . 2>/dev/null || echo "$response"
        return 0
    else
        log_warn "External dependencies check failed"
        return 1
    fi
}

# Comprehensive health check
comprehensive_check() {
    local url="$1"
    local base_url=$(echo "$url" | sed 's|/health||')

    log "Running comprehensive health checks..."

    local failed_checks=0

    # Basic health
    if ! check_health_endpoint "$url" 1; then
        ((failed_checks++))
    fi

    # API endpoints
    if ! check_api_endpoints "$base_url"; then
        ((failed_checks++))
    fi

    # Performance
    if ! check_performance "$url"; then
        ((failed_checks++))
    fi

    # Functionality (optional, may not be available in all environments)
    check_functionality "$base_url" || true

    # Database (optional)
    check_database "$base_url" || true

    # Dependencies (optional)
    check_dependencies_health "$base_url" || true

    if [[ $failed_checks -gt 0 ]]; then
        log_error "Comprehensive health check failed ($failed_checks checks failed)"
        return 1
    fi

    log "All comprehensive health checks passed"
    return 0
}

# Main health check with retries
main() {
    parse_args "$@"
    check_dependencies

    log "Starting health checks for: $URL"
    log "Configuration: retries=$RETRIES, interval=${INTERVAL}s, timeout=${TIMEOUT}s"

    local attempt=1
    while [[ $attempt -le $RETRIES ]]; do
        if check_health_endpoint "$URL" "$attempt"; then
            log "Service is healthy after $attempt attempt(s)"

            # Run comprehensive checks on final success
            comprehensive_check "$URL"

            log "All health checks completed successfully"
            log "Log file: $LOG_FILE"
            exit 0
        fi

        if [[ $attempt -lt $RETRIES ]]; then
            log "Waiting ${INTERVAL}s before retry..."
            sleep "$INTERVAL"
        fi

        ((attempt++))
    done

    log_error "Health check failed after $RETRIES attempts"
    log_error "Service may not be ready or is unhealthy"
    log "Log file: $LOG_FILE"
    exit 1
}

# Run main function
main "$@"
