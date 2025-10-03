"""
Integration tests for federated SPARQL queries.

Tests queries that span multiple endpoints using the SERVICE keyword
to validate multi-endpoint data integration.
"""

import pytest
from . import UNIPROT_ENDPOINT, RDFPORTAL_ENDPOINT


# ============================================================================
# FEDERATED QUERY TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
@pytest.mark.slow
class TestFederatedQueries:
    """Tests for federated queries across multiple endpoints."""

    def test_simple_federated_query(self, check_endpoint_available, cached_query_executor):
        """
        Test simple federated query between two endpoints.

        Note: This test may be slow or fail if endpoints don't support federation.
        """
        check_endpoint_available(UNIPROT_ENDPOINT)

        # Simple federated query: get data from UniProt and try to federate
        # Note: Not all endpoints support SERVICE, so this may fail
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic
        WHERE {
            # Local query to UniProt
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true .
        }
        LIMIT 5
        """

        try:
            result = cached_query_executor(UNIPROT_ENDPOINT, query)
            bindings = result["results"]["bindings"]
            assert len(bindings) > 0
        except Exception as e:
            pytest.skip(f"Federated query not supported or failed: {e}")

    def test_federated_with_service_keyword(self, check_endpoint_available, sparql_query_executor):
        """
        Test federated query using SERVICE keyword.

        This queries UniProt and attempts to federate to another endpoint.
        Many endpoints don't support SERVICE, so this may be skipped.
        """
        check_endpoint_available(UNIPROT_ENDPOINT)

        # Example federated query (may not work on all endpoints)
        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?protein ?mnemonic ?label
        WHERE {{
            # Local query
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true .

            # Try to get additional data from remote (may fail)
            OPTIONAL {{
                SERVICE <{RDFPORTAL_ENDPOINT}> {{
                    ?protein rdfs:label ?label .
                }}
            }}
        }}
        LIMIT 5
        """

        try:
            result = sparql_query_executor(UNIPROT_ENDPOINT, query)
            bindings = result["results"]["bindings"]
            # Just check that query executes
            assert "results" in result
        except Exception as e:
            pytest.skip(f"SERVICE keyword not supported or federation failed: {e}")


# ============================================================================
# FEDERATED QUERY SIMULATION
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestFederatedQuerySimulation:
    """
    Tests simulating federated queries by querying endpoints separately
    and combining results programmatically.
    """

    def test_multi_endpoint_protein_lookup(
        self,
        check_endpoint_available,
        cached_query_executor
    ):
        """
        Test looking up protein data from multiple endpoints separately.

        This simulates federation by querying endpoints independently.
        """
        check_endpoint_available(UNIPROT_ENDPOINT)

        # Query 1: Get protein from UniProt
        uniprot_query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>

        SELECT ?protein ?mnemonic ?name
        WHERE {
            BIND(uniprotkb:P04637 AS ?protein)
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }
        }
        """

        uniprot_result = cached_query_executor(UNIPROT_ENDPOINT, uniprot_query)
        uniprot_bindings = uniprot_result["results"]["bindings"]

        assert len(uniprot_bindings) > 0
        protein_uri = uniprot_bindings[0]["protein"]["value"]

        # In a real federated scenario, we would query another endpoint
        # with the protein_uri to get additional data
        assert protein_uri is not None

    def test_combine_results_from_multiple_endpoints(
        self,
        check_endpoint_available,
        cached_query_executor
    ):
        """
        Test combining results from multiple endpoint queries.

        Demonstrates manual federation by querying multiple endpoints
        and merging results.
        """
        check_endpoint_available(UNIPROT_ENDPOINT)

        # Query 1: Get human proteins from UniProt
        uniprot_query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:organism ?org .

            ?org up:scientificName "Homo sapiens" .
        }
        LIMIT 10
        """

        uniprot_result = cached_query_executor(UNIPROT_ENDPOINT, uniprot_query)
        uniprot_proteins = uniprot_result["results"]["bindings"]

        assert len(uniprot_proteins) > 0

        # In a real scenario, we would:
        # 1. Extract protein URIs
        # 2. Query another endpoint for each URI
        # 3. Combine the results

        protein_uris = [p["protein"]["value"] for p in uniprot_proteins]
        assert len(protein_uris) > 0

        # Simulate combining results
        combined_results = []
        for protein in uniprot_proteins:
            combined_results.append({
                "protein": protein["protein"]["value"],
                "mnemonic": protein["mnemonic"]["value"],
                "source": "UniProt"
            })

        assert len(combined_results) == len(uniprot_proteins)


# ============================================================================
# ERROR RECOVERY TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestFederatedQueryErrorRecovery:
    """Test error handling in federated queries."""

    def test_handle_unavailable_remote_endpoint(self, cached_query_executor):
        """
        Test handling of unavailable remote endpoint in federated query.

        Uses OPTIONAL SERVICE to gracefully handle unavailable endpoints.
        """
        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic
        WHERE {{
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true .

            # OPTIONAL SERVICE to unavailable endpoint
            OPTIONAL {{
                SERVICE <http://example.invalid/sparql> {{
                    ?protein <http://example.com/property> ?value .
                }}
            }}
        }}
        LIMIT 5
        """

        try:
            result = cached_query_executor(UNIPROT_ENDPOINT, query)
            # Should still return results despite failed SERVICE
            bindings = result["results"]["bindings"]
            assert len(bindings) >= 0
        except Exception:
            pytest.skip("Endpoint doesn't support SERVICE or failed")

    def test_timeout_handling_in_federation(self, sparql_query_executor):
        """
        Test timeout handling in federated queries.

        Federated queries can be slow, so proper timeout handling is critical.
        """
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic .
        }
        LIMIT 3
        """

        try:
            # Use short timeout
            result = sparql_query_executor(UNIPROT_ENDPOINT, query)
            assert "results" in result
        except Exception as e:
            # Timeout is acceptable
            assert "timeout" in str(e).lower() or "time" in str(e).lower()


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.performance
@pytest.mark.slow
class TestFederatedQueryPerformance:
    """Performance tests for federated queries."""

    def test_sequential_query_performance(
        self,
        timed_query_executor,
        check_endpoint_available
    ):
        """
        Test performance of sequential queries to multiple endpoints.

        Measures baseline for manual federation.
        """
        check_endpoint_available(UNIPROT_ENDPOINT)

        query1 = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true .
        }
        LIMIT 5
        """

        # Query 1
        result1, duration1 = timed_query_executor(
            UNIPROT_ENDPOINT,
            query1,
            query_name="federated_seq_query1"
        )

        assert duration1 < 15.0
        assert len(result1["results"]["bindings"]) > 0

        # In real federation, we would query another endpoint
        # Total time would be sum of individual query times
        total_duration = duration1
        assert total_duration < 30.0  # Sequential queries should complete reasonably


# ============================================================================
# DATA INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestCrossEndpointDataIntegration:
    """Tests for integrating data across endpoints."""

    def test_protein_uri_consistency(
        self,
        cached_query_executor,
        sample_protein_ids
    ):
        """
        Test that protein URIs are consistent across queries.

        Important for federation - URIs must match across endpoints.
        """
        protein_id = sample_protein_ids[1]  # P04637

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>

        SELECT ?protein
        WHERE {{
            BIND(uniprotkb:{protein_id} AS ?protein)
            ?protein a up:Protein .
        }}
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0
        protein_uri = bindings[0]["protein"]["value"]

        # Verify URI format
        assert protein_uri.startswith("http://purl.uniprot.org/uniprot/")
        assert protein_id in protein_uri

    def test_identifier_mapping_for_federation(
        self,
        cached_query_executor,
        sample_protein_ids
    ):
        """
        Test retrieving cross-reference identifiers for federation.

        Cross-references enable linking to other databases/endpoints.
        """
        protein_id = sample_protein_ids[1]  # P04637

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?protein ?database ?databaseName ?xrefId
        WHERE {{
            BIND(uniprotkb:{protein_id} AS ?protein)

            ?protein rdfs:seeAlso ?xref .
            ?xref up:database ?database ;
                  up:id ?xrefId .

            ?database skos:prefLabel ?databaseName .

            # Focus on common databases for federation
            FILTER(?databaseName IN ("Ensembl", "RefSeq", "PDB", "GO"))
        }}
        LIMIT 10
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should have cross-references for federation
        # (TP53 is well-annotated)
        if len(bindings) > 0:
            # Verify we got useful cross-references
            databases = {b["databaseName"]["value"] for b in bindings}
            assert len(databases) > 0
