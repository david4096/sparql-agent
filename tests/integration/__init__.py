"""
Integration tests for SPARQL Agent with real endpoints.

This package contains integration tests that interact with real SPARQL endpoints
to validate the full functionality of the SPARQL Agent system.

Test Categories:
    - Endpoint-specific tests: Test against specific public endpoints
    - End-to-end workflows: Complete feature workflows
    - Error recovery: Handling endpoint failures and edge cases
    - Performance: Response time and reliability monitoring

Markers:
    @pytest.mark.integration: Full system integration tests
    @pytest.mark.network: Requires internet connectivity
    @pytest.mark.slow: Long-running tests (>5 seconds)
    @pytest.mark.endpoint: Specific endpoint tests

Usage:
    # Run all integration tests
    uv run pytest tests/integration/ -m integration

    # Run only fast integration tests
    uv run pytest tests/integration/ -m "integration and not slow"

    # Run endpoint-specific tests
    uv run pytest tests/integration/ -m endpoint

    # Skip network tests
    uv run pytest tests/integration/ -m "not network"
"""

__all__ = [
    "UNIPROT_ENDPOINT",
    "RDFPORTAL_ENDPOINT",
    "OLS4_API_ENDPOINT",
    "CLINVAR_ENDPOINT",
    "TEST_TIMEOUT",
    "MAX_RETRIES",
]

# Test endpoint configurations
UNIPROT_ENDPOINT = "https://sparql.uniprot.org/sparql"
RDFPORTAL_ENDPOINT = "https://rdfportal.org/sparql"
OLS4_API_ENDPOINT = "https://www.ebi.ac.uk/ols4/api"
CLINVAR_ENDPOINT = "https://sparql.omics.ai/blazegraph/namespace/clinvar/sparql"

# Test configuration
TEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
CACHE_TTL = 3600  # 1 hour
