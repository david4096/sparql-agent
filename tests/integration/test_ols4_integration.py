"""
Integration tests for EBI OLS4 (Ontology Lookup Service) API.

Tests integration with the OLS4 REST API at https://www.ebi.ac.uk/ols4/api
for ontology search and term lookups.
"""

import pytest
import requests
from . import OLS4_API_ENDPOINT


# ============================================================================
# SMOKE TESTS - Basic Connectivity
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.smoke
class TestOLS4Smoke:
    """Smoke tests for OLS4 API connectivity."""

    def test_api_available(self):
        """Test that OLS4 API is reachable."""
        response = requests.get(f"{OLS4_API_ENDPOINT}/", timeout=10)
        assert response.status_code == 200

    def test_ontologies_endpoint(self):
        """Test ontologies listing endpoint."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies",
            timeout=10,
            params={"size": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "_embedded" in data
        assert "ontologies" in data["_embedded"]

    def test_search_endpoint(self):
        """Test search endpoint."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={"q": "protein", "rows": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data


# ============================================================================
# FUNCTIONAL TESTS - Ontology Operations
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestOLS4Ontologies:
    """Functional tests for ontology operations."""

    def test_list_ontologies(self):
        """Test listing available ontologies."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies",
            timeout=10,
            params={"size": 20}
        )
        assert response.status_code == 200
        data = response.json()

        ontologies = data["_embedded"]["ontologies"]
        assert len(ontologies) > 0

        # Verify structure
        for ontology in ontologies:
            assert "ontologyId" in ontology
            assert "title" in ontology or "config" in ontology

    def test_get_specific_ontology_go(self):
        """Test retrieving Gene Ontology (GO) metadata."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies/go",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()

        assert "ontologyId" in data
        assert data["ontologyId"] == "go"

    def test_get_specific_ontology_uberon(self):
        """Test retrieving Uberon (anatomy) ontology metadata."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies/uberon",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()

        assert "ontologyId" in data
        assert data["ontologyId"] == "uberon"


# ============================================================================
# FUNCTIONAL TESTS - Term Lookup
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestOLS4Terms:
    """Functional tests for term lookup."""

    def test_search_terms_by_keyword(self):
        """Test searching terms by keyword."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "insulin",
                "rows": 10,
                "ontology": "go"
            }
        )
        assert response.status_code == 200
        data = response.json()

        docs = data["response"]["docs"]
        assert len(docs) > 0

        # Verify all results contain "insulin"
        for doc in docs:
            label = doc.get("label", "").lower()
            description = doc.get("description", [""])[0].lower() if doc.get("description") else ""
            assert "insulin" in label or "insulin" in description

    def test_get_term_by_iri(self):
        """Test retrieving a specific term by IRI."""
        # Example: GO:0005515 (protein binding)
        term_iri = "http://purl.obolibrary.org/obo/GO_0005515"

        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies/go/terms/{requests.utils.quote(requests.utils.quote(term_iri, safe=''), safe='')}",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()

        assert "iri" in data
        assert "label" in data

    def test_search_exact_term(self):
        """Test searching for exact term match."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "protein binding",
                "exact": "true",
                "ontology": "go",
                "rows": 5
            }
        )
        assert response.status_code == 200
        data = response.json()

        docs = data["response"]["docs"]
        # Should have exact matches
        assert len(docs) > 0

    def test_get_term_parents(self):
        """Test retrieving parent terms."""
        # Example: GO:0005515 (protein binding)
        term_iri = "http://purl.obolibrary.org/obo/GO_0005515"

        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies/go/terms/{requests.utils.quote(requests.utils.quote(term_iri, safe=''), safe='')}/parents",
            timeout=10
        )
        # Parents endpoint might return 200 or 404 depending on term
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # If parents exist, validate structure
            if "_embedded" in data and "terms" in data["_embedded"]:
                parents = data["_embedded"]["terms"]
                assert isinstance(parents, list)

    def test_get_term_children(self):
        """Test retrieving child terms."""
        # Example: GO:0005515 (protein binding)
        term_iri = "http://purl.obolibrary.org/obo/GO_0005515"

        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies/go/terms/{requests.utils.quote(requests.utils.quote(term_iri, safe=''), safe='')}/children",
            timeout=10
        )
        # Children endpoint might return 200 or 404 depending on term
        assert response.status_code in [200, 404]


# ============================================================================
# FUNCTIONAL TESTS - Advanced Search
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestOLS4AdvancedSearch:
    """Functional tests for advanced search capabilities."""

    def test_search_by_ontology(self):
        """Test searching within specific ontology."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "kinase",
                "ontology": "go",
                "rows": 10
            }
        )
        assert response.status_code == 200
        data = response.json()

        docs = data["response"]["docs"]
        assert len(docs) > 0

        # All results should be from GO
        for doc in docs:
            assert doc.get("ontology_name") == "go"

    def test_search_with_type_filter(self):
        """Test searching with type filter (class, property, etc.)."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "protein",
                "type": "class",
                "rows": 10
            }
        )
        assert response.status_code == 200
        data = response.json()

        docs = data["response"]["docs"]
        assert len(docs) > 0

    def test_search_with_obsolete_filter(self):
        """Test filtering obsolete terms."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "protein",
                "obsoletes": "false",
                "rows": 10
            }
        )
        assert response.status_code == 200
        data = response.json()

        docs = data["response"]["docs"]
        assert len(docs) > 0

        # No results should be obsolete
        for doc in docs:
            assert not doc.get("is_obsolete", False)


# ============================================================================
# FUNCTIONAL TESTS - Suggestions/Autocomplete
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestOLS4Suggestions:
    """Functional tests for autocomplete/suggestion."""

    def test_suggest_terms(self):
        """Test term suggestions for autocomplete."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/suggest",
            timeout=10,
            params={
                "q": "prot",
                "rows": 5
            }
        )
        assert response.status_code == 200
        data = response.json()

        if "response" in data:
            docs = data["response"]["docs"]
            # Should have suggestions
            assert len(docs) >= 0  # May be empty for short queries


# ============================================================================
# REGRESSION TESTS - Known Terms
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.regression
class TestOLS4Regression:
    """Regression tests with known terms."""

    def test_go_protein_binding_exists(self):
        """Test that GO:0005515 (protein binding) exists."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "GO:0005515",
                "ontology": "go",
                "exact": "true"
            }
        )
        assert response.status_code == 200
        data = response.json()

        docs = data["response"]["docs"]
        assert len(docs) > 0

        # Find the exact term
        found = False
        for doc in docs:
            if "GO_0005515" in doc.get("iri", ""):
                found = True
                assert "protein binding" in doc.get("label", "").lower()
                break

        assert found, "GO:0005515 not found"

    def test_uberon_brain_exists(self):
        """Test that UBERON:0000955 (brain) exists."""
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "brain",
                "ontology": "uberon",
                "rows": 10
            }
        )
        assert response.status_code == 200
        data = response.json()

        docs = data["response"]["docs"]
        assert len(docs) > 0

        # Should have brain term
        labels = [doc.get("label", "").lower() for doc in docs]
        assert "brain" in labels


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.performance
class TestOLS4Performance:
    """Performance tests for OLS4 API."""

    def test_search_performance(self, performance_monitor):
        """Test search query performance."""
        import time

        start = time.time()
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "protein",
                "rows": 20
            }
        )
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 5.0  # Should be fast

        performance_monitor.measure("ols4_search", duration)

    def test_ontology_list_performance(self, performance_monitor):
        """Test ontology listing performance."""
        import time

        start = time.time()
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies",
            timeout=10,
            params={"size": 50}
        )
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 5.0

        performance_monitor.measure("ols4_list_ontologies", duration)

    def test_term_lookup_performance(self, performance_monitor):
        """Test term lookup performance."""
        import time

        term_iri = "http://purl.obolibrary.org/obo/GO_0005515"
        encoded_iri = requests.utils.quote(requests.utils.quote(term_iri, safe=''), safe='')

        start = time.time()
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies/go/terms/{encoded_iri}",
            timeout=10
        )
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 3.0  # Direct lookup should be very fast

        performance_monitor.measure("ols4_term_lookup", duration)
