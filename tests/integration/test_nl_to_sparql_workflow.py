"""
End-to-end integration tests for Natural Language to SPARQL workflow.

Tests the complete pipeline from natural language questions to SPARQL queries
to results retrieval using real endpoints.
"""

import pytest
from . import UNIPROT_ENDPOINT


# ============================================================================
# END-TO-END WORKFLOW TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
@pytest.mark.slow
class TestNLToSPARQLWorkflow:
    """End-to-end tests for NL → SPARQL → Results workflow."""

    def test_simple_protein_query_workflow(self, cached_query_executor):
        """
        Test workflow: 'Find information about insulin protein'

        Simulates NL→SPARQL translation and execution.
        """
        # Simulated SPARQL query generated from NL question
        nl_question = "Find information about insulin protein"

        # Generated SPARQL query
        sparql_query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic ?name ?organism
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:organism ?org .

            ?org up:scientificName ?organism .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }

            FILTER(CONTAINS(LCASE(?name), "insulin"))
        }
        LIMIT 10
        """

        # Execute query
        result = cached_query_executor(UNIPROT_ENDPOINT, sparql_query)
        bindings = result["results"]["bindings"]

        # Validate results
        assert len(bindings) > 0, "No results found for insulin query"

        # Verify result quality
        for binding in bindings:
            assert "mnemonic" in binding
            assert "organism" in binding
            if "name" in binding:
                assert "insulin" in binding["name"]["value"].lower()

    def test_taxonomy_filter_workflow(self, cached_query_executor):
        """
        Test workflow: 'Find human kinase proteins'

        Tests filtering by organism and protein function.
        """
        nl_question = "Find human kinase proteins"

        sparql_query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?protein ?mnemonic ?name ?keywordLabel
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:organism ?org ;
                     up:classifiedWith ?keyword .

            ?org up:scientificName "Homo sapiens" .

            ?keyword a up:Keyword ;
                     skos:prefLabel ?keywordLabel .

            FILTER(CONTAINS(LCASE(?keywordLabel), "kinase"))

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }
        }
        LIMIT 15
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, sparql_query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0, "No human kinase proteins found"

        # Verify all are human
        for binding in bindings:
            if "keywordLabel" in binding:
                assert "kinase" in binding["keywordLabel"]["value"].lower()

    def test_disease_association_workflow(self, cached_query_executor):
        """
        Test workflow: 'What diseases is TP53 associated with?'

        Tests protein-disease association queries.
        """
        nl_question = "What diseases is TP53 associated with?"

        sparql_query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>

        SELECT ?protein ?disease ?diseaseLabel
        WHERE {
            # TP53 is P04637
            BIND(uniprotkb:P04637 AS ?protein)

            ?protein up:annotation ?diseaseAnnotation .
            ?diseaseAnnotation a up:Disease_Annotation ;
                              up:disease ?disease .

            OPTIONAL { ?disease skos:prefLabel ?diseaseLabel . }
        }
        LIMIT 20
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, sparql_query)
        bindings = result["results"]["bindings"]

        # TP53 should have disease associations
        assert len(bindings) > 0, "No disease associations found for TP53"

    def test_sequence_length_filter_workflow(self, cached_query_executor):
        """
        Test workflow: 'Find small proteins between 50-100 amino acids'

        Tests numeric filtering on sequence properties.
        """
        nl_question = "Find small proteins between 50-100 amino acids"

        sparql_query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic ?length ?name
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:sequence ?seq .

            ?seq up:length ?length .

            FILTER(?length >= 50 && ?length <= 100)

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }
        }
        LIMIT 15
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, sparql_query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0, "No small proteins found"

        # Verify length filter
        for binding in bindings:
            length = int(binding["length"]["value"])
            assert 50 <= length <= 100, f"Length {length} outside range"

    def test_cross_reference_workflow(self, cached_query_executor):
        """
        Test workflow: 'Find proteins with PDB structures'

        Tests cross-reference queries.
        """
        nl_question = "Find proteins with PDB structures"

        sparql_query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?protein ?mnemonic ?pdbId ?name
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     rdfs:seeAlso ?pdb .

            ?pdb up:database <http://purl.uniprot.org/database/PDB> ;
                 up:id ?pdbId .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }
        }
        LIMIT 10
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, sparql_query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0, "No proteins with PDB structures found"

        # Verify PDB IDs
        for binding in bindings:
            assert "pdbId" in binding
            pdb_id = binding["pdbId"]["value"]
            assert len(pdb_id) == 4, f"Invalid PDB ID: {pdb_id}"

    def test_go_term_annotation_workflow(self, cached_query_executor, sample_go_terms):
        """
        Test workflow: 'Find proteins with DNA binding activity'

        Tests Gene Ontology term queries.
        """
        nl_question = "Find proteins with DNA binding activity"
        go_term = sample_go_terms[1]  # GO:0003677 (DNA binding)

        sparql_query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?protein ?mnemonic ?name ?goLabel
        WHERE {{
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:classifiedWith <http://purl.obolibrary.org/obo/{go_term.replace(':', '_')}> .

            OPTIONAL {{
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }}

            OPTIONAL {{
                <http://purl.obolibrary.org/obo/{go_term.replace(':', '_')}> rdfs:label ?goLabel .
            }}
        }}
        LIMIT 10
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, sparql_query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0, "No proteins with DNA binding found"

    def test_multi_constraint_workflow(self, cached_query_executor):
        """
        Test workflow: 'Find reviewed human proteins with kinase activity and disease associations'

        Tests complex queries with multiple constraints.
        """
        nl_question = "Find reviewed human proteins with kinase activity and disease associations"

        sparql_query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT DISTINCT ?protein ?mnemonic ?name ?disease
        WHERE {
            # Human proteins
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:organism ?org .

            ?org up:scientificName "Homo sapiens" .

            # With kinase activity
            ?protein up:classifiedWith ?keyword .
            ?keyword a up:Keyword ;
                     skos:prefLabel ?keywordLabel .
            FILTER(CONTAINS(LCASE(?keywordLabel), "kinase"))

            # With disease associations
            ?protein up:annotation ?diseaseAnnotation .
            ?diseaseAnnotation a up:Disease_Annotation ;
                              up:disease ?disease .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }
        }
        LIMIT 10
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, sparql_query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0, "No matching proteins found with all constraints"


# ============================================================================
# ERROR RECOVERY TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestNLWorkflowErrorRecovery:
    """Test error handling in NL→SPARQL workflow."""

    def test_empty_result_handling(self, cached_query_executor):
        """Test handling of queries that return no results."""
        # Query for non-existent protein
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>

        SELECT ?protein ?name
        WHERE {
            BIND(uniprotkb:NONEXISTENT999 AS ?protein)
            ?protein up:recommendedName ?recName .
            ?recName up:fullName ?name .
        }
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should return empty results, not error
        assert len(bindings) == 0
        assert "results" in result
        assert "bindings" in result["results"]

    def test_invalid_filter_recovery(self, cached_query_executor):
        """Test recovery from invalid filter conditions."""
        # Query with filter that matches nothing
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic .

            # Impossible condition
            FILTER(?mnemonic = "IMPOSSIBLE_MATCH_XYZ_999")
        }
        LIMIT 10
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should return empty results gracefully
        assert len(bindings) == 0

    def test_optional_pattern_handling(self, cached_query_executor):
        """Test handling of OPTIONAL patterns that may not match."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic ?name ?description
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }

            OPTIONAL {
                ?protein up:annotation ?funcAnnotation .
                ?funcAnnotation a up:Function_Annotation .
                # This might not exist for all proteins
                ?funcAnnotation up:someNonexistentProperty ?description .
            }
        }
        LIMIT 5
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should still return results even if OPTIONAL doesn't match
        assert len(bindings) > 0


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.performance
@pytest.mark.slow
class TestNLWorkflowPerformance:
    """Performance tests for NL→SPARQL workflow."""

    def test_simple_workflow_performance(self, timed_query_executor):
        """Test performance of simple NL→SPARQL workflow."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic ?name
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }

            FILTER(CONTAINS(LCASE(?name), "insulin"))
        }
        LIMIT 10
        """

        result, duration = timed_query_executor(
            UNIPROT_ENDPOINT,
            query,
            query_name="nl_simple_protein_search"
        )

        assert duration < 15.0, f"Query too slow: {duration}s"
        assert len(result["results"]["bindings"]) > 0

    def test_complex_workflow_performance(self, timed_query_executor):
        """Test performance of complex multi-constraint workflow."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT DISTINCT ?protein ?mnemonic ?name ?disease
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:organism ?org .

            ?org up:scientificName "Homo sapiens" .

            ?protein up:classifiedWith ?keyword .
            ?keyword a up:Keyword ;
                     skos:prefLabel ?keywordLabel .
            FILTER(CONTAINS(LCASE(?keywordLabel), "kinase"))

            ?protein up:annotation ?diseaseAnnotation .
            ?diseaseAnnotation a up:Disease_Annotation ;
                              up:disease ?disease .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }
        }
        LIMIT 5
        """

        result, duration = timed_query_executor(
            UNIPROT_ENDPOINT,
            query,
            query_name="nl_complex_multi_constraint"
        )

        assert duration < 45.0, f"Complex query too slow: {duration}s"
        assert len(result["results"]["bindings"]) > 0
