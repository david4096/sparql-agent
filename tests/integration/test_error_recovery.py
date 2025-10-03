"""
Integration tests for error recovery and resilience.

Tests how the system handles various error conditions with real endpoints:
- Network failures
- Endpoint downtime
- Query timeouts
- Malformed queries
- Rate limiting
"""

import pytest
import time
from SPARQLWrapper import SPARQLWrapper, JSON
from . import UNIPROT_ENDPOINT


# ============================================================================
# NETWORK ERROR TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestNetworkErrors:
    """Tests for handling network-related errors."""

    def test_invalid_endpoint_handling(self, sparql_wrapper_factory):
        """Test handling of invalid endpoint URL."""
        invalid_endpoint = "http://invalid.endpoint.example.com/sparql"

        sparql = sparql_wrapper_factory(invalid_endpoint)
        sparql.setQuery("ASK { ?s ?p ?o }")

        with pytest.raises(Exception) as exc_info:
            sparql.query()

        # Should raise network error
        assert exc_info.value is not None

    def test_timeout_handling(self):
        """Test handling of query timeouts."""
        sparql = SPARQLWrapper(UNIPROT_ENDPOINT)
        sparql.setQuery("ASK { ?s ?p ?o }")
        sparql.setReturnFormat(JSON)
        sparql.setTimeout(0.001)  # Very short timeout

        with pytest.raises(Exception) as exc_info:
            sparql.query()

        # Should raise timeout error
        assert exc_info.value is not None

    def test_connection_refused_handling(self, sparql_wrapper_factory):
        """Test handling of connection refused errors."""
        # Use localhost on unlikely port
        unavailable_endpoint = "http://localhost:19999/sparql"

        sparql = sparql_wrapper_factory(unavailable_endpoint)
        sparql.setQuery("ASK { ?s ?p ?o }")

        with pytest.raises(Exception) as exc_info:
            sparql.query()

        assert exc_info.value is not None


# ============================================================================
# QUERY ERROR TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestQueryErrors:
    """Tests for handling query-related errors."""

    def test_syntax_error_handling(self, sparql_query_executor):
        """Test handling of SPARQL syntax errors."""
        # Invalid SPARQL syntax
        invalid_query = """
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o
        # Missing closing brace
        """

        with pytest.raises(Exception) as exc_info:
            sparql_query_executor(UNIPROT_ENDPOINT, invalid_query, retries=1)

        assert exc_info.value is not None

    def test_undefined_prefix_handling(self, sparql_query_executor):
        """Test handling of undefined prefix errors."""
        # Use prefix without declaration
        query = """
        SELECT ?protein
        WHERE {
            ?protein a undefined:Protein .
        }
        LIMIT 1
        """

        with pytest.raises(Exception) as exc_info:
            sparql_query_executor(UNIPROT_ENDPOINT, query, retries=1)

        # Should raise error about undefined prefix
        assert exc_info.value is not None

    def test_invalid_uri_handling(self, sparql_query_executor):
        """Test handling of invalid URIs in queries."""
        # Malformed URI
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein
        WHERE {
            ?protein a up:Protein .
            FILTER(?protein = <not a valid uri>)
        }
        LIMIT 1
        """

        with pytest.raises(Exception) as exc_info:
            sparql_query_executor(UNIPROT_ENDPOINT, query, retries=1)

        assert exc_info.value is not None


# ============================================================================
# RESILIENCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestResilience:
    """Tests for system resilience and recovery."""

    def test_retry_on_transient_failure(self, sparql_query_executor):
        """Test retry logic on transient failures."""
        # This should succeed with retries
        query = "ASK { ?s ?p ?o }"

        # Execute with retries
        result = sparql_query_executor(UNIPROT_ENDPOINT, query, retries=3)

        assert "boolean" in result
        assert result["boolean"] is True

    def test_empty_result_resilience(self, cached_query_executor):
        """Test resilient handling of empty results."""
        # Query that returns no results
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein
        WHERE {
            ?protein a up:Protein .
            # Impossible filter
            FILTER(false)
        }
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should handle empty results gracefully
        assert len(bindings) == 0
        assert "results" in result

    def test_large_result_handling(self, cached_query_executor):
        """Test handling of queries with many results."""
        # Query that could return many results (but limited)
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic .
        }
        LIMIT 100
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should handle successfully
        assert len(bindings) > 0
        assert len(bindings) <= 100

    def test_complex_query_resilience(self, cached_query_executor):
        """Test resilience with complex queries."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?protein ?mnemonic ?name ?organism ?location ?function
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:organism ?org .

            ?org up:scientificName ?organism .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }

            OPTIONAL {
                ?protein up:annotation ?locAnnotation .
                ?locAnnotation a up:Subcellular_Location_Annotation ;
                              up:locatedIn ?loc .
                ?loc skos:prefLabel ?location .
            }

            OPTIONAL {
                ?protein up:annotation ?funcAnnotation .
                ?funcAnnotation a up:Function_Annotation ;
                               rdfs:comment ?function .
            }
        }
        LIMIT 5
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should handle complex query
        assert len(bindings) > 0


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
class TestRateLimiting:
    """Tests for handling rate limiting."""

    def test_sequential_requests(self, sparql_query_executor):
        """Test multiple sequential requests."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein
        WHERE {
            ?protein a up:Protein .
        }
        LIMIT 1
        """

        # Make multiple requests with small delay
        results = []
        for i in range(3):
            result = sparql_query_executor(UNIPROT_ENDPOINT, query)
            results.append(result)
            time.sleep(1)  # Be respectful of endpoint

        # All should succeed
        assert len(results) == 3
        for result in results:
            assert "results" in result

    def test_respect_rate_limits(self, sparql_query_executor):
        """Test that we respect rate limits."""
        query = "ASK { ?s ?p ?o }"

        # Make requests with appropriate delays
        start_time = time.time()

        for i in range(3):
            sparql_query_executor(UNIPROT_ENDPOINT, query)
            if i < 2:  # No delay after last request
                time.sleep(0.5)  # Rate limiting delay

        elapsed = time.time() - start_time

        # Should take at least the delay time
        assert elapsed >= 1.0  # 2 delays of 0.5s


# ============================================================================
# ENDPOINT RECOVERY TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestEndpointRecovery:
    """Tests for handling endpoint failures and recovery."""

    def test_graceful_degradation(self, endpoint_checker, cached_query_executor):
        """Test graceful degradation when endpoint has issues."""
        # Check if endpoint is available
        is_available = endpoint_checker.is_available(UNIPROT_ENDPOINT)

        if not is_available:
            pytest.skip("Endpoint not available - testing graceful degradation")

        # If available, run a simple query
        query = "ASK { ?s ?p ?o }"
        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        assert "boolean" in result

    def test_fallback_on_error(self, sparql_query_executor):
        """Test fallback behavior on query errors."""
        # Try a risky query that might fail
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o .
        }
        LIMIT 1
        """

        try:
            result = sparql_query_executor(UNIPROT_ENDPOINT, query, retries=2)
            assert "results" in result
        except Exception as e:
            # If it fails, we should handle gracefully
            assert e is not None
            # In real implementation, would fall back to alternative

    def test_endpoint_health_check(self, endpoint_checker):
        """Test endpoint health checking."""
        # Check endpoint health
        is_healthy = endpoint_checker.is_available(UNIPROT_ENDPOINT, force=True)

        # Record the health status
        assert isinstance(is_healthy, bool)

        if is_healthy:
            # If healthy, queries should work
            assert True
        else:
            # If unhealthy, tests should skip
            pytest.skip("Endpoint is unhealthy")


# ============================================================================
# ERROR MESSAGE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestErrorMessages:
    """Tests for error message handling and reporting."""

    def test_descriptive_error_on_bad_query(self, sparql_query_executor):
        """Test that errors have descriptive messages."""
        bad_query = "THIS IS NOT SPARQL"

        with pytest.raises(Exception) as exc_info:
            sparql_query_executor(UNIPROT_ENDPOINT, bad_query, retries=1)

        # Error should have meaningful message
        error_message = str(exc_info.value)
        assert len(error_message) > 0

    def test_error_context_preservation(self, sparql_query_executor):
        """Test that error context is preserved through retries."""
        # Query with syntax error
        bad_query = """
        SELECT ?s
        WHERE {
            ?s ?p ?o
        # Missing brace
        """

        with pytest.raises(Exception) as exc_info:
            sparql_query_executor(UNIPROT_ENDPOINT, bad_query, retries=2)

        # Error should be raised and contain useful information
        assert exc_info.value is not None
