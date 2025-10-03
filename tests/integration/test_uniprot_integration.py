"""
Integration tests for UniProt SPARQL endpoint.

Tests real queries against the UniProt SPARQL endpoint at https://sparql.uniprot.org/sparql
to validate functionality with actual biological data.
"""

import pytest
from . import UNIPROT_ENDPOINT


# ============================================================================
# SMOKE TESTS - Basic Connectivity
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.smoke
class TestUniProtSmoke:
    """Smoke tests for basic UniProt endpoint connectivity."""

    def test_endpoint_available(self, check_endpoint_available):
        """Test that UniProt endpoint is reachable."""
        check_endpoint_available(UNIPROT_ENDPOINT)

    def test_simple_ask_query(self, sparql_query_executor):
        """Test simple ASK query."""
        query = "ASK { ?s ?p ?o }"
        result = sparql_query_executor(UNIPROT_ENDPOINT, query)
        assert "boolean" in result
        assert result["boolean"] is True

    def test_count_proteins(self, sparql_query_executor):
        """Test counting proteins (with LIMIT for speed)."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        SELECT (COUNT(?protein) AS ?count)
        WHERE {
            ?protein a up:Protein .
        }
        LIMIT 1000
        """
        result = sparql_query_executor(UNIPROT_ENDPOINT, query)
        assert "results" in result
        assert "bindings" in result["results"]
        assert len(result["results"]["bindings"]) > 0

        count = int(result["results"]["bindings"][0]["count"]["value"])
        assert count > 0


# ============================================================================
# FUNCTIONAL TESTS - Protein Queries
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestUniProtProteinQueries:
    """Functional tests for protein-related queries."""

    def test_get_protein_by_accession(self, cached_query_executor, sample_protein_ids):
        """Test retrieving protein by UniProt accession."""
        protein_id = sample_protein_ids[1]  # P04637 (TP53)

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>

        SELECT ?protein ?mnemonic ?name
        WHERE {{
            BIND(uniprotkb:{protein_id} AS ?protein)
            ?protein a up:Protein .
            ?protein up:mnemonic ?mnemonic .
            OPTIONAL {{
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }}
        }}
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0
        assert "mnemonic" in bindings[0]
        # TP53 should have mnemonic containing P53
        assert "P53" in bindings[0]["mnemonic"]["value"].upper()

    def test_search_proteins_by_name(self, cached_query_executor):
        """Test searching proteins by name."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic ?name
        WHERE {
            ?protein a up:Protein .
            ?protein up:mnemonic ?mnemonic .
            ?protein up:recommendedName ?recName .
            ?recName up:fullName ?name .

            FILTER(CONTAINS(LCASE(?name), "insulin"))
        }
        LIMIT 10
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0
        # All results should contain "insulin" in name
        for binding in bindings:
            assert "insulin" in binding["name"]["value"].lower()

    def test_get_human_proteins_by_gene(self, cached_query_executor):
        """Test finding human proteins by gene name."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?protein ?mnemonic ?geneName ?proteinName
        WHERE {
            ?protein a up:Protein .
            ?protein up:mnemonic ?mnemonic .
            ?protein up:organism ?organism .
            ?organism up:scientificName "Homo sapiens" .

            ?protein up:encodedBy ?gene .
            ?gene skos:prefLabel ?geneName .
            FILTER(REGEX(?geneName, "^BRCA1$", "i"))

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?proteinName .
            }
        }
        LIMIT 5
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0
        # All results should have BRCA1 gene
        for binding in bindings:
            assert binding["geneName"]["value"].upper() == "BRCA1"

    def test_get_protein_sequence(self, cached_query_executor, sample_protein_ids):
        """Test retrieving protein sequence."""
        protein_id = sample_protein_ids[3]  # P01308 (Insulin)

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?protein ?sequence ?length ?mass
        WHERE {{
            BIND(uniprotkb:{protein_id} AS ?protein)

            ?protein up:sequence ?seq .
            ?seq rdf:value ?sequence ;
                 up:length ?length ;
                 up:mass ?mass .
        }}
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0
        binding = bindings[0]

        # Validate sequence data
        assert "sequence" in binding
        assert len(binding["sequence"]["value"]) > 0
        assert "length" in binding
        assert int(binding["length"]["value"]) > 0
        assert "mass" in binding
        assert int(binding["mass"]["value"]) > 0

    def test_get_proteins_by_taxonomy(self, cached_query_executor, sample_taxonomy_ids):
        """Test retrieving proteins by organism taxonomy."""
        taxon_id = sample_taxonomy_ids[0]  # Human (9606)

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uptaxon: <http://purl.uniprot.org/taxonomy/>

        SELECT ?protein ?mnemonic ?name
        WHERE {{
            ?protein a up:Protein .
            ?protein up:mnemonic ?mnemonic .
            ?protein up:organism/up:taxon uptaxon:{taxon_id} .
            ?protein up:reviewed true .

            OPTIONAL {{
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }}
        }}
        LIMIT 20
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0
        assert len(bindings) <= 20


# ============================================================================
# FUNCTIONAL TESTS - Annotations
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestUniProtAnnotations:
    """Functional tests for protein annotations."""

    def test_get_protein_function(self, cached_query_executor, sample_protein_ids):
        """Test retrieving protein function annotations."""
        protein_id = sample_protein_ids[1]  # P04637 (TP53)

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?protein ?functionText
        WHERE {{
            BIND(uniprotkb:{protein_id} AS ?protein)

            ?protein up:annotation ?functionAnnotation .
            ?functionAnnotation a up:Function_Annotation ;
                               rdfs:comment ?functionText .
        }}
        LIMIT 5
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # TP53 should have function annotations
        assert len(bindings) > 0

    def test_get_protein_go_terms(self, cached_query_executor, sample_protein_ids):
        """Test retrieving Gene Ontology annotations."""
        protein_id = sample_protein_ids[1]  # P04637 (TP53)

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?protein ?goTerm ?goLabel
        WHERE {{
            BIND(uniprotkb:{protein_id} AS ?protein)

            ?protein up:classifiedWith ?goTerm .
            ?goTerm rdfs:label ?goLabel .
            FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
        }}
        LIMIT 10
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # TP53 should have GO annotations
        assert len(bindings) > 0

    def test_get_protein_disease_associations(self, cached_query_executor, sample_protein_ids):
        """Test retrieving disease associations."""
        protein_id = sample_protein_ids[1]  # P04637 (TP53)

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?protein ?disease ?diseaseLabel
        WHERE {{
            BIND(uniprotkb:{protein_id} AS ?protein)

            ?protein up:annotation ?diseaseAnnotation .
            ?diseaseAnnotation a up:Disease_Annotation ;
                              up:disease ?disease .

            OPTIONAL {{ ?disease skos:prefLabel ?diseaseLabel . }}
        }}
        LIMIT 5
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # TP53 is associated with various cancers
        assert len(bindings) > 0

    def test_get_protein_subcellular_location(self, cached_query_executor, sample_protein_ids):
        """Test retrieving subcellular location."""
        protein_id = sample_protein_ids[1]  # P04637 (TP53)

        query = f"""
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?protein ?location ?locationLabel
        WHERE {{
            BIND(uniprotkb:{protein_id} AS ?protein)

            ?protein up:annotation ?locAnnotation .
            ?locAnnotation a up:Subcellular_Location_Annotation .

            OPTIONAL {{
                ?locAnnotation up:locatedIn ?location .
                ?location skos:prefLabel ?locationLabel .
            }}
        }}
        LIMIT 5
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should have location data
        assert len(bindings) > 0


# ============================================================================
# FUNCTIONAL TESTS - Cross-References
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.functional
class TestUniProtCrossReferences:
    """Functional tests for cross-references."""

    def test_get_protein_cross_references(self, cached_query_executor, sample_protein_ids):
        """Test retrieving cross-references to external databases."""
        protein_id = sample_protein_ids[1]  # P04637 (TP53)

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
        }}
        LIMIT 20
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        # Should have multiple cross-references
        assert len(bindings) > 0

    def test_get_proteins_with_pdb_structures(self, cached_query_executor):
        """Test finding proteins with PDB structures."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?protein ?mnemonic ?pdbId
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     rdfs:seeAlso ?pdb .

            ?pdb up:database <http://purl.uniprot.org/database/PDB> ;
                 up:id ?pdbId .
        }
        LIMIT 10
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) > 0
        # All results should have PDB IDs
        for binding in bindings:
            assert "pdbId" in binding
            assert len(binding["pdbId"]["value"]) == 4  # PDB IDs are 4 characters


# ============================================================================
# REGRESSION TESTS - Known Good Queries
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.regression
class TestUniProtRegression:
    """Regression tests with known good queries and expected results."""

    def test_insulin_protein_exists(self, cached_query_executor):
        """Test that human insulin protein (P01308) exists with expected data."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>

        SELECT ?protein ?mnemonic ?name ?organism
        WHERE {
            BIND(uniprotkb:P01308 AS ?protein)

            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:organism ?org .

            ?org up:scientificName ?organism .

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }
        }
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) == 1
        binding = bindings[0]

        # Validate known data
        assert "INS" in binding["mnemonic"]["value"].upper()
        assert "Homo sapiens" in binding["organism"]["value"]

    def test_hemoglobin_sequence_length(self, cached_query_executor):
        """Test that hemoglobin beta (P68871) has expected sequence length."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>

        SELECT ?protein ?length
        WHERE {
            BIND(uniprotkb:P68871 AS ?protein)

            ?protein up:sequence ?seq .
            ?seq up:length ?length .
        }
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) == 1
        binding = bindings[0]

        # Hemoglobin beta chain is 147 amino acids
        length = int(binding["length"]["value"])
        assert 145 <= length <= 150  # Allow small variation


# ============================================================================
# PERFORMANCE TESTS - Response Time Monitoring
# ============================================================================

@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.performance
@pytest.mark.slow
class TestUniProtPerformance:
    """Performance tests for response time monitoring."""

    def test_simple_query_performance(self, timed_query_executor):
        """Test performance of simple protein query."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic .
        }
        LIMIT 10
        """

        result, duration = timed_query_executor(
            UNIPROT_ENDPOINT,
            query,
            query_name="simple_protein_query"
        )

        assert duration < 10.0  # Should complete in under 10 seconds
        assert len(result["results"]["bindings"]) == 10

    def test_complex_query_performance(self, timed_query_executor):
        """Test performance of complex query with multiple joins."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?protein ?mnemonic ?name ?geneName ?organism
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic ;
                     up:reviewed true ;
                     up:organism ?org .

            ?org up:scientificName ?organism .
            FILTER(?organism = "Homo sapiens")

            OPTIONAL {
                ?protein up:recommendedName ?recName .
                ?recName up:fullName ?name .
            }

            OPTIONAL {
                ?protein up:encodedBy ?gene .
                ?gene skos:prefLabel ?geneName .
            }
        }
        LIMIT 50
        """

        result, duration = timed_query_executor(
            UNIPROT_ENDPOINT,
            query,
            query_name="complex_human_proteins"
        )

        assert duration < 30.0  # Should complete in under 30 seconds
        assert len(result["results"]["bindings"]) > 0

    def test_aggregation_query_performance(self, timed_query_executor):
        """Test performance of aggregation query."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?organism (COUNT(?protein) AS ?count)
        WHERE {
            ?protein a up:Protein ;
                     up:organism ?org .
            ?org up:scientificName ?organism .
        }
        GROUP BY ?organism
        ORDER BY DESC(?count)
        LIMIT 10
        """

        result, duration = timed_query_executor(
            UNIPROT_ENDPOINT,
            query,
            query_name="organism_counts"
        )

        assert duration < 60.0  # Aggregation can take longer
        assert len(result["results"]["bindings"]) > 0
