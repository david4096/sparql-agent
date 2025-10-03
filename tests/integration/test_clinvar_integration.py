"""
Integration tests for ClinVar SPARQL endpoint.

Tests real queries against ClinVar data to validate clinical variant data access.
Note: This assumes a ClinVar SPARQL endpoint. Adjust endpoint URL as needed.
"""

import pytest
from . import CLINVAR_ENDPOINT


# ============================================================================
# SMOKE TESTS - Basic Connectivity
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.smoke
class TestClinVarSmoke:
    """Smoke tests for ClinVar endpoint connectivity."""

    def test_endpoint_available_or_skip(self, endpoint_checker):
        """Test if ClinVar endpoint is available, skip if not."""
        if not endpoint_checker.is_available(CLINVAR_ENDPOINT):
            pytest.skip(f"ClinVar endpoint {CLINVAR_ENDPOINT} is not available")

    def test_simple_ask_query(self, sparql_query_executor, endpoint_checker):
        """Test simple ASK query."""
        if not endpoint_checker.is_available(CLINVAR_ENDPOINT):
            pytest.skip("ClinVar endpoint not available")

        query = "ASK { ?s ?p ?o }"
        result = sparql_query_executor(CLINVAR_ENDPOINT, query)
        assert "boolean" in result


# ============================================================================
# FUNCTIONAL TESTS - Variant Queries
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestClinVarVariants:
    """Functional tests for variant queries."""

    def test_list_variants(self, cached_query_executor, endpoint_checker):
        """Test listing variants."""
        if not endpoint_checker.is_available(CLINVAR_ENDPOINT):
            pytest.skip("ClinVar endpoint not available")

        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?variant ?label
        WHERE {
            ?variant a ?type .
            OPTIONAL { ?variant rdfs:label ?label . }
        }
        LIMIT 10
        """

        result = cached_query_executor(CLINVAR_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0

    def test_search_pathogenic_variants(self, cached_query_executor, endpoint_checker):
        """Test searching for pathogenic variants."""
        if not endpoint_checker.is_available(CLINVAR_ENDPOINT):
            pytest.skip("ClinVar endpoint not available")

        query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?variant ?significance ?label
        WHERE {
            ?variant ?significance ?label .
            FILTER(CONTAINS(LCASE(STR(?significance)), "pathogenic"))
        }
        LIMIT 10
        """

        result = cached_query_executor(CLINVAR_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should have some results if endpoint has pathogenic variants
        # Don't assert on count as it depends on endpoint data
        assert isinstance(bindings, list)


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.performance
class TestClinVarPerformance:
    """Performance tests for ClinVar endpoint."""

    def test_simple_query_performance(self, timed_query_executor, endpoint_checker):
        """Test performance of simple query."""
        if not endpoint_checker.is_available(CLINVAR_ENDPOINT):
            pytest.skip("ClinVar endpoint not available")

        query = """
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o .
        }
        LIMIT 10
        """

        result, duration = timed_query_executor(
            CLINVAR_ENDPOINT,
            query,
            query_name="clinvar_simple_query"
        )

        assert duration < 20.0
        assert len(result["results"]["bindings"]) > 0
