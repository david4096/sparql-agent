"""
Integration tests for RDFPortal SPARQL endpoint.

Tests real queries against the RDFPortal endpoint at https://rdfportal.org/sparql
to validate functionality with biomedical research data.
"""

import pytest
from . import RDFPORTAL_ENDPOINT


# ============================================================================
# SMOKE TESTS - Basic Connectivity
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.smoke
class TestRDFPortalSmoke:
    """Smoke tests for basic RDFPortal endpoint connectivity."""

    def test_endpoint_available(self, check_endpoint_available):
        """Test that RDFPortal endpoint is reachable."""
        check_endpoint_available(RDFPORTAL_ENDPOINT)

    def test_simple_ask_query(self, sparql_query_executor):
        """Test simple ASK query."""
        query = "ASK { ?s ?p ?o }"
        result = sparql_query_executor(RDFPORTAL_ENDPOINT, query)
        assert "boolean" in result
        assert result["boolean"] is True

    def test_count_triples(self, sparql_query_executor):
        """Test counting triples (with LIMIT for speed)."""
        query = """
        SELECT (COUNT(*) AS ?count)
        WHERE {
            ?s ?p ?o .
        }
        LIMIT 1000
        """
        result = sparql_query_executor(RDFPORTAL_ENDPOINT, query)
        assert "results" in result
        assert "bindings" in result["results"]


# ============================================================================
# FUNCTIONAL TESTS - Dataset Discovery
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestRDFPortalDatasets:
    """Functional tests for dataset discovery."""

    def test_list_datasets(self, cached_query_executor):
        """Test listing available datasets."""
        query = """
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT ?dataset ?title ?description
        WHERE {
            ?dataset a dcat:Dataset .
            OPTIONAL { ?dataset dcterms:title ?title . }
            OPTIONAL { ?dataset dcterms:description ?description . }
        }
        LIMIT 20
        """

        result = cached_query_executor(RDFPORTAL_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should have datasets
        assert len(bindings) > 0

    def test_get_dataset_metadata(self, cached_query_executor):
        """Test retrieving dataset metadata."""
        query = """
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT ?dataset ?property ?value
        WHERE {
            ?dataset a dcat:Dataset .
            ?dataset ?property ?value .
        }
        LIMIT 50
        """

        result = cached_query_executor(RDFPORTAL_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0


# ============================================================================
# FUNCTIONAL TESTS - Resource Discovery
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestRDFPortalResources:
    """Functional tests for resource discovery."""

    def test_find_resources_by_type(self, cached_query_executor):
        """Test finding resources by RDF type."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?resource ?type ?label
        WHERE {
            ?resource a ?type .
            OPTIONAL { ?resource rdfs:label ?label . }
        }
        LIMIT 20
        """

        result = cached_query_executor(RDFPORTAL_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0

    def test_search_by_label(self, cached_query_executor):
        """Test searching resources by label."""
        query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?resource ?label
        WHERE {
            ?resource rdfs:label ?label .
            FILTER(CONTAINS(LCASE(?label), "disease"))
        }
        LIMIT 10
        """

        result = cached_query_executor(RDFPORTAL_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # All results should contain "disease" in label
        for binding in bindings:
            if "label" in binding:
                assert "disease" in binding["label"]["value"].lower()


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.performance
class TestRDFPortalPerformance:
    """Performance tests for RDFPortal endpoint."""

    def test_simple_query_performance(self, timed_query_executor):
        """Test performance of simple query."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o .
        }
        LIMIT 10
        """

        result, duration = timed_query_executor(
            RDFPORTAL_ENDPOINT,
            query,
            query_name="rdfportal_simple_query"
        )

        assert duration < 15.0
        assert len(result["results"]["bindings"]) > 0
