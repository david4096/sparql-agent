#!/bin/bash
# Integration test runner script for SPARQL Agent
# Provides convenient commands for running different test suites

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Default to all tests
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    smoke)
        print_header "Running Smoke Tests (Basic Connectivity)"
        uv run pytest . -m smoke -v
        ;;

    uniprot)
        print_header "Running UniProt Integration Tests"
        uv run pytest test_uniprot_integration.py -v
        ;;

    rdfportal)
        print_header "Running RDFPortal Integration Tests"
        uv run pytest test_rdfportal_integration.py -v
        ;;

    clinvar)
        print_header "Running ClinVar Integration Tests"
        uv run pytest test_clinvar_integration.py -v
        ;;

    ols4)
        print_header "Running OLS4 API Integration Tests"
        uv run pytest test_ols4_integration.py -v
        ;;

    endpoints)
        print_header "Running All Endpoint Tests"
        uv run pytest -m endpoint -v
        ;;

    workflows)
        print_header "Running Workflow Tests"
        uv run pytest test_nl_to_sparql_workflow.py test_federated_queries.py test_ontology_guided_workflow.py -v
        ;;

    functional)
        print_header "Running Functional Tests (Excluding Slow)"
        uv run pytest -m "functional and not slow" -v
        ;;

    regression)
        print_header "Running Regression Tests"
        uv run pytest -m regression -v
        ;;

    performance)
        print_header "Running Performance Tests"
        print_warning "This may take a while..."
        uv run pytest -m performance -v
        ;;

    fast)
        print_header "Running Fast Tests (Excluding Slow)"
        uv run pytest -m "integration and not slow" -v
        ;;

    error)
        print_header "Running Error Recovery Tests"
        uv run pytest test_error_recovery.py -v
        ;;

    coverage)
        print_header "Running Tests with Coverage"
        uv run pytest . -m integration --cov=sparql_agent --cov-report=html --cov-report=term
        print_success "Coverage report generated in htmlcov/"
        ;;

    parallel)
        print_header "Running Tests in Parallel"
        print_warning "This may trigger rate limits on endpoints!"
        uv run pytest . -m "integration and not slow" -n auto -v
        ;;

    ci)
        print_header "Running CI Test Suite"
        print_warning "Quick test suite suitable for CI/CD"
        uv run pytest -m "smoke or (functional and not slow)" -v --tb=short
        ;;

    all)
        print_header "Running All Integration Tests"
        print_warning "This may take 10-15 minutes..."
        uv run pytest . -m integration -v
        ;;

    help|--help|-h)
        echo "SPARQL Agent Integration Test Runner"
        echo ""
        echo "Usage: ./run_tests.sh [TEST_TYPE]"
        echo ""
        echo "Available test types:"
        echo "  smoke       - Basic connectivity tests (fastest)"
        echo "  uniprot     - UniProt endpoint tests"
        echo "  rdfportal   - RDFPortal endpoint tests"
        echo "  clinvar     - ClinVar endpoint tests"
        echo "  ols4        - OLS4 API integration tests"
        echo "  endpoints   - All endpoint-specific tests"
        echo "  workflows   - End-to-end workflow tests"
        echo "  functional  - Functional tests (excluding slow)"
        echo "  regression  - Regression tests with known queries"
        echo "  performance - Performance and timing tests"
        echo "  fast        - All tests excluding slow ones"
        echo "  error       - Error recovery and resilience tests"
        echo "  coverage    - Run with coverage report"
        echo "  parallel    - Run tests in parallel (may hit rate limits)"
        echo "  ci          - Quick CI-suitable test suite"
        echo "  all         - All integration tests (default, slowest)"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh smoke                  # Quick smoke tests"
        echo "  ./run_tests.sh fast                   # Fast integration tests"
        echo "  ./run_tests.sh uniprot                # Just UniProt tests"
        echo "  ./run_tests.sh coverage               # With coverage report"
        echo ""
        echo "Environment variables:"
        echo "  SKIP_NETWORK_TESTS=true              # Skip network tests"
        echo "  SKIP_SLOW_TESTS=true                 # Skip slow tests"
        echo "  TEST_TIMEOUT=60                      # Query timeout in seconds"
        echo "  MAX_RETRIES=3                        # Max query retries"
        ;;

    *)
        print_error "Unknown test type: $TEST_TYPE"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    print_success "Tests completed successfully!"
else
    print_error "Some tests failed!"
    exit 1
fi
