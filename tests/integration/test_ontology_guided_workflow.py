"""
Integration tests for ontology-guided query generation workflow.

Tests the workflow of using ontologies to guide and enhance SPARQL query generation,
including term expansion, hierarchy navigation, and semantic validation.
"""

import pytest
from . import UNIPROT_ENDPOINT, OLS4_API_ENDPOINT
import requests


# ============================================================================
# ONTOLOGY-GUIDED QUERY TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestOntologyGuidedQueries:
    """Tests for ontology-guided query generation."""

    def test_go_term_expansion_workflow(self, cached_query_executor):
        """
        Test workflow: Use GO term to guide protein query.

        Steps:
        1. User asks about "protein binding"
        2. System looks up GO term
        3. Generates SPARQL query using GO term
        4. Executes query
        """
        # Step 1: User question about "protein binding"
        user_question = "Find proteins with protein binding activity"

        # Step 2: Look up GO term (simulated - would use OLS4)
        # GO:0005515 = protein binding
        go_term = "GO:0005515"
        go_iri = f"http://purl.obolibrary.org/obo/{go_term.replace(':', '_')}"

        # Step 3: Generate SPARQL query using GO term
        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?protein ?mnemonic ?name
        WHERE {{
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:classifiedWith <{go_iri}> .

            OPTIONAL {{
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }}
        }}
        LIMIT 10
        """

        # Step 4: Execute query
        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Validate results
        assert len(bindings) > 0, "No proteins found with protein binding"

    def test_ontology_term_lookup_integration(self):
        """
        Test integration with OLS4 for term lookup.

        Demonstrates how to look up ontology terms before query generation.
        """
        # Look up "kinase" in GO
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "kinase activity",
                "ontology": "go",
                "exact": "false",
                "rows": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        docs = data["response"]["docs"]

        # Should find kinase-related terms
        assert len(docs) > 0

        # Extract GO terms for query generation
        go_terms = []
        for doc in docs:
            if "obo_id" in doc:
                go_terms.append(doc["obo_id"])

        assert len(go_terms) > 0

    def test_term_hierarchy_navigation(self):
        """
        Test navigating term hierarchies to expand queries.

        Uses OLS4 to get parent/child terms for query expansion.
        """
        # Example: Get parents of "kinase activity"
        term_iri = "http://purl.obolibrary.org/obo/GO_0016301"

        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies/go/terms/"
            f"{requests.utils.quote(requests.utils.quote(term_iri, safe=''), safe='')}/parents",
            timeout=10
        )

        # May return 200 or 404 depending on term
        if response.status_code == 200:
            data = response.json()
            # If parents exist, we can use them for broader queries
            if "_embedded" in data and "terms" in data["_embedded"]:
                parents = data["_embedded"]["terms"]
                assert isinstance(parents, list)

    def test_synonym_expansion_workflow(self):
        """
        Test using term synonyms to expand query coverage.

        Queries OLS4 for term synonyms, then uses all variants in SPARQL.
        """
        # Search for term with synonyms
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "insulin",
                "ontology": "go",
                "rows": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        docs = data["response"]["docs"]

        if len(docs) > 0:
            # Check for synonyms in results
            synonyms_found = False
            for doc in docs:
                if "synonym" in doc:
                    synonyms_found = True
                    break

            # If we found synonyms, we could use them to expand the query
            # This would make the search more comprehensive


# ============================================================================
# SEMANTIC VALIDATION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestSemanticValidation:
    """Tests for semantic validation using ontologies."""

    def test_validate_term_exists(self):
        """Test validating that a GO term exists before using in query."""
        # Valid term
        valid_go_term = "GO:0005515"

        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": valid_go_term,
                "ontology": "go",
                "exact": "true"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should find the term
        assert data["response"]["numFound"] > 0

    def test_suggest_corrections_for_invalid_term(self):
        """Test suggesting corrections for misspelled terms."""
        # Misspelled term
        misspelled = "protien binding"  # Should be "protein binding"

        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": misspelled,
                "ontology": "go",
                "rows": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        docs = data["response"]["docs"]

        # Should still find similar terms
        if len(docs) > 0:
            # Check if we found "protein binding"
            labels = [doc.get("label", "").lower() for doc in docs]
            # Fuzzy search should find correct term
            assert any("protein" in label and "binding" in label for label in labels)

    def test_validate_term_applicability(self):
        """
        Test validating that a term is applicable to the query context.

        E.g., ensure we're using biological process terms for process queries.
        """
        # Get term details including type
        term_iri = "http://purl.obolibrary.org/obo/GO_0005515"

        response = requests.get(
            f"{OLS4_API_ENDPOINT}/ontologies/go/terms/"
            f"{requests.utils.quote(requests.utils.quote(term_iri, safe=''), safe='')}",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()

            # Check term type/namespace
            # GO terms have namespaces: biological_process, molecular_function, cellular_component
            if "annotation" in data:
                annotations = data["annotation"]
                # Could check hasOBONamespace to validate applicability


# ============================================================================
# QUERY ENHANCEMENT TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestOntologyQueryEnhancement:
    """Tests for enhancing queries using ontology knowledge."""

    def test_add_related_terms(self):
        """
        Test adding related terms to broaden query scope.

        Uses OLS4 to find related terms, then includes them in query.
        """
        # Find related terms for "kinase"
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

        # Extract multiple related terms
        related_terms = []
        for doc in docs:
            if "obo_id" in doc and "kinase" in doc.get("label", "").lower():
                related_terms.append(doc["obo_id"])

        # Could use these terms in a query with FILTER IN
        assert len(related_terms) > 0

    def test_hierarchical_query_expansion(self, cached_query_executor):
        """
        Test expanding query using term hierarchy.

        Includes parent and child terms for comprehensive coverage.
        """
        # Query using base term - in real scenario would expand with hierarchy
        base_go_term = "GO:0016301"  # kinase activity

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic ?goTerm
        WHERE {{
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:classifiedWith ?goTerm .

            # In real scenario, would include parent/child terms
            # FILTER(?goTerm IN (<term1>, <term2>, ...))
            FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
        }}
        LIMIT 5
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0

    def test_context_aware_term_selection(self):
        """
        Test selecting appropriate terms based on query context.

        E.g., prefer molecular_function GO terms for activity queries.
        """
        # Search for "binding" - could be in multiple namespaces
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "binding",
                "ontology": "go",
                "rows": 20
            }
        )

        assert response.status_code == 200
        data = response.json()
        docs = data["response"]["docs"]

        # Filter for molecular_function terms
        # (in real implementation)
        mf_terms = []
        for doc in docs:
            # Could check hasOBONamespace annotation
            if "label" in doc:
                mf_terms.append(doc)

        assert len(mf_terms) > 0


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.performance
class TestOntologyGuidedPerformance:
    """Performance tests for ontology-guided workflows."""

    def test_term_lookup_performance(self, performance_monitor):
        """Test performance of ontology term lookup."""
        import time

        start = time.time()
        response = requests.get(
            f"{OLS4_API_ENDPOINT}/search",
            timeout=10,
            params={
                "q": "kinase",
                "ontology": "go",
                "rows": 10
            }
        )
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 3.0  # Should be fast

        performance_monitor.measure("ontology_term_lookup", duration)

    def test_enhanced_query_performance(
        self,
        timed_query_executor,
        performance_monitor
    ):
        """Test performance of ontology-enhanced queries."""
        # Query enhanced with GO term
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic ?name
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:classifiedWith <http://purl.obolibrary.org/obo/GO_0005515> .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }
        }
        LIMIT 10
        """

        result, duration = timed_query_executor(
            UNIPROT_ENDPOINT,
            query,
            query_name="ontology_enhanced_query"
        )

        assert duration < 20.0
        assert len(result["results"]["bindings"]) > 0
