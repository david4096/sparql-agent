"""
Unit tests for federated SPARQL query functionality.

Run tests with:
    pytest test_federated.py -v
    pytest test_federated.py::TestFederatedQueryBuilder -v
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List

from .federated import (
    FederatedQueryBuilder,
    CrossDatasetExamples,
    ResultMerger,
    ResilientFederatedExecutor,
    QueryOptimizationHints,
    OptimizationStrategy,
    EndpointCapabilities,
    FederatedQueryError,
    BIOMEDICAL_ENDPOINTS,
    FEDERATED_PREFIXES,
    get_federated_prefix_string,
)

from ..core.types import QueryResult, QueryStatus


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def query_builder():
    """Create a FederatedQueryBuilder instance."""
    return FederatedQueryBuilder(
        enable_optimization=True,
        cache_results=True,
        timeout=60
    )


@pytest.fixture
def cross_dataset_examples():
    """Create a CrossDatasetExamples instance."""
    return CrossDatasetExamples()


@pytest.fixture
def result_merger():
    """Create a ResultMerger instance."""
    return ResultMerger()


@pytest.fixture
def resilient_executor():
    """Create a ResilientFederatedExecutor instance."""
    return ResilientFederatedExecutor(
        max_retries=2,
        retry_delay=0.1,  # Short delay for tests
        allow_partial_results=True
    )


@pytest.fixture
def sample_query_results():
    """Create sample query results for testing merging."""
    result1 = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {"protein": "P12345", "name": "Protein A"},
            {"protein": "P67890", "name": "Protein B"},
        ],
        variables=["protein", "name"],
        row_count=2
    )

    result2 = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {"protein": "P12345", "pdbId": "1ABC"},
            {"protein": "P99999", "pdbId": "2XYZ"},
        ],
        variables=["protein", "pdbId"],
        row_count=2
    )

    return result1, result2


# =============================================================================
# TEST FEDERATED QUERY BUILDER
# =============================================================================

class TestFederatedQueryBuilder:
    """Tests for FederatedQueryBuilder class."""

    def test_initialization(self, query_builder):
        """Test builder initialization."""
        assert query_builder.enable_optimization is True
        assert query_builder.cache_results is True
        assert query_builder.timeout == 60

    def test_build_service_clause_basic(self, query_builder):
        """Test building a basic SERVICE clause."""
        patterns = [
            "?protein a up:Protein .",
            "?protein up:name 'BRCA1' ."
        ]

        clause = query_builder.build_service_clause(
            "https://sparql.uniprot.org/sparql",
            patterns,
            use_optional=False,
            silent=True
        )

        assert "SERVICE SILENT" in clause
        assert "https://sparql.uniprot.org/sparql" in clause
        assert "?protein a up:Protein" in clause
        assert "?protein up:name 'BRCA1'" in clause

    def test_build_service_clause_optional(self, query_builder):
        """Test building an OPTIONAL SERVICE clause."""
        patterns = ["?s ?p ?o ."]

        clause = query_builder.build_service_clause(
            "https://example.org/sparql",
            patterns,
            use_optional=True,
            silent=True
        )

        assert "OPTIONAL" in clause
        assert "SERVICE SILENT" in clause

    def test_build_service_clause_not_silent(self, query_builder):
        """Test building a non-silent SERVICE clause."""
        patterns = ["?s ?p ?o ."]

        clause = query_builder.build_service_clause(
            "https://example.org/sparql",
            patterns,
            use_optional=False,
            silent=False
        )

        assert "SERVICE SILENT" not in clause
        assert "SERVICE <" in clause

    def test_build_federated_query_basic(self, query_builder):
        """Test building a basic federated query."""
        query = query_builder.build_federated_query(
            select_vars=["?protein", "?name"],
            services={
                "https://sparql.uniprot.org/sparql": [
                    "?protein a up:Protein .",
                    "?protein up:name ?name ."
                ]
            },
            limit=10
        )

        assert "SELECT ?protein ?name" in query
        assert "SERVICE SILENT <https://sparql.uniprot.org/sparql>" in query
        assert "LIMIT 10" in query
        assert "WHERE {" in query

    def test_build_federated_query_with_filters(self, query_builder):
        """Test building a query with filters."""
        query = query_builder.build_federated_query(
            select_vars=["?protein", "?name"],
            services={
                "https://sparql.uniprot.org/sparql": [
                    "?protein a up:Protein .",
                    "?protein up:name ?name ."
                ]
            },
            filters=[
                'FILTER(REGEX(?name, "BRCA", "i"))'
            ],
            limit=10
        )

        assert "FILTER(REGEX(?name" in query

    def test_build_federated_query_with_order_by(self, query_builder):
        """Test building a query with ORDER BY."""
        query = query_builder.build_federated_query(
            select_vars=["?protein", "?name"],
            services={
                "https://sparql.uniprot.org/sparql": [
                    "?protein a up:Protein .",
                    "?protein up:name ?name ."
                ]
            },
            order_by=["?name"],
            limit=10
        )

        assert "ORDER BY ?name" in query

    def test_build_federated_query_multiple_services(self, query_builder):
        """Test building a query with multiple services."""
        query = query_builder.build_federated_query(
            select_vars=["?protein", "?name", "?disease"],
            services={
                "https://sparql.uniprot.org/sparql": [
                    "?protein a up:Protein .",
                    "?protein up:name ?name ."
                ],
                "https://query.wikidata.org/sparql": [
                    "?disease wdt:P31 wd:Q12136 .",
                    "?disease rdfs:label ?diseaseName ."
                ]
            },
            limit=20
        )

        assert "SERVICE SILENT <https://sparql.uniprot.org/sparql>" in query
        assert "SERVICE SILENT <https://query.wikidata.org/sparql>" in query
        assert "LIMIT 20" in query

    def test_estimate_query_cost(self, query_builder):
        """Test query cost estimation."""
        services = {
            "https://sparql.uniprot.org/sparql": ["?s ?p ?o ."] * 3,
            "https://query.wikidata.org/sparql": ["?s ?p ?o ."] * 2
        }

        cost = query_builder.estimate_query_cost(services)

        assert "estimated_time_seconds" in cost
        assert "service_count" in cost
        assert "pattern_count" in cost
        assert "complexity_score" in cost
        assert "recommended_timeout" in cost

        assert cost["service_count"] == 2
        assert cost["pattern_count"] == 5
        assert cost["estimated_time_seconds"] > 0

    def test_optimization_with_hints(self, query_builder):
        """Test query optimization with hints."""
        hints = QueryOptimizationHints(
            strategies=[OptimizationStrategy.MINIMIZE_TRANSFER],
            estimated_selectivity={
                "endpoint1": 0.1,
                "endpoint2": 0.5
            }
        )

        services = {
            "endpoint1": ["pattern1"],
            "endpoint2": ["pattern2"]
        }

        optimized = query_builder._optimize_service_order(services, hints)

        # Should order by selectivity (most selective first)
        keys = list(optimized.keys())
        assert keys[0] == "endpoint1"  # Lower selectivity value = first


# =============================================================================
# TEST CROSS-DATASET EXAMPLES
# =============================================================================

class TestCrossDatasetExamples:
    """Tests for CrossDatasetExamples class."""

    def test_protein_disease_associations(self, cross_dataset_examples):
        """Test protein-disease association query generation."""
        query = cross_dataset_examples.protein_disease_associations(
            gene_name="BRCA1",
            limit=20
        )

        assert "SELECT" in query
        assert "BRCA1" in query
        assert "SERVICE" in query
        assert "https://sparql.uniprot.org/sparql" in query
        assert "LIMIT 20" in query
        assert "up:Disease_Annotation" in query

    def test_structure_function_integration(self, cross_dataset_examples):
        """Test structure-function integration query."""
        query = cross_dataset_examples.protein_structure_function_integration(
            protein_id="P38398",
            limit=10
        )

        assert "SELECT" in query
        assert "P38398" in query
        assert "SERVICE" in query
        assert "up:Domain_Annotation" in query
        assert "up:Function_Annotation" in query
        assert "PDB" in query

    def test_gene_ontology_protein_expression(self, cross_dataset_examples):
        """Test GO term protein expression query."""
        query = cross_dataset_examples.gene_ontology_protein_expression(
            go_term="GO:0005634",
            taxon_id="9606",
            limit=50
        )

        assert "SELECT" in query
        assert "GO_0005634" in query  # Normalized format
        assert "9606" in query
        assert "up:classifiedWith" in query

    def test_taxonomic_phylogenetic_protein_families(self, cross_dataset_examples):
        """Test taxonomic protein family query."""
        query = cross_dataset_examples.taxonomic_phylogenetic_protein_families(
            protein_family="Kinase",
            root_taxon="33208",
            limit=100
        )

        assert "SELECT" in query
        assert "Kinase" in query
        assert "33208" in query
        assert "rdfs:subClassOf*" in query  # Transitive hierarchy

    def test_chemical_protein_interaction_network(self, cross_dataset_examples):
        """Test chemical-protein interaction query."""
        query = cross_dataset_examples.chemical_protein_interaction_network(
            compound_name="Imatinib",
            activity_threshold=100.0,
            limit=50
        )

        assert "SELECT" in query
        assert "Imatinib" in query
        assert "100.0" in query or "100" in query
        assert "cco:" in query or "chembl" in query

    def test_precision_medicine_variant_drug_response(self, cross_dataset_examples):
        """Test pharmacogenomics variant query."""
        query = cross_dataset_examples.precision_medicine_variant_drug_response(
            gene_symbol="CYP2D6",
            limit=30
        )

        assert "SELECT" in query
        assert "CYP2D6" in query
        assert "up:Natural_Variant_Annotation" in query
        assert "9606" in query  # Human

    def test_systems_biology_pathway_integration(self, cross_dataset_examples):
        """Test pathway integration query."""
        query = cross_dataset_examples.systems_biology_pathway_integration(
            pathway_name="Apoptosis",
            organism="Homo sapiens",
            limit=100
        )

        assert "SELECT" in query
        assert "Apoptosis" in query
        assert "Homo sapiens" in query
        assert "up:Pathway_Annotation" in query


# =============================================================================
# TEST RESULT MERGER
# =============================================================================

class TestResultMerger:
    """Tests for ResultMerger class."""

    def test_merge_with_union_basic(self, result_merger, sample_query_results):
        """Test basic UNION merge."""
        result1, result2 = sample_query_results

        merged = result_merger.merge_with_union([result1, result2])

        assert merged.is_success
        assert merged.row_count == 4  # 2 + 2
        assert "protein" in merged.variables
        assert "name" in merged.variables
        assert "pdbId" in merged.variables

    def test_merge_with_union_deduplicate(self, result_merger):
        """Test UNION merge with deduplication."""
        result1 = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {"protein": "P12345", "name": "Protein A"},
                {"protein": "P67890", "name": "Protein B"},
            ],
            variables=["protein", "name"],
            row_count=2
        )

        result2 = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {"protein": "P12345", "name": "Protein A"},  # Duplicate
                {"protein": "P99999", "name": "Protein C"},
            ],
            variables=["protein", "name"],
            row_count=2
        )

        merged = result_merger.merge_with_union([result1, result2], deduplicate=True)

        assert merged.row_count == 3  # Duplicate removed

    def test_merge_with_join_inner(self, result_merger, sample_query_results):
        """Test inner JOIN merge."""
        result1, result2 = sample_query_results

        merged = result_merger.merge_with_join(
            [result1, result2],
            join_keys=["protein"],
            join_type="inner"
        )

        assert merged.is_success
        assert merged.row_count == 1  # Only P12345 matches
        assert "protein" in merged.variables
        assert "name" in merged.variables
        assert "pdbId" in merged.variables

        # Check that the joined row has all fields
        binding = merged.bindings[0]
        assert binding["protein"] == "P12345"
        assert binding["name"] == "Protein A"
        assert binding["pdbId"] == "1ABC"

    def test_merge_with_join_left(self, result_merger, sample_query_results):
        """Test left JOIN merge."""
        result1, result2 = sample_query_results

        merged = result_merger.merge_with_join(
            [result1, result2],
            join_keys=["protein"],
            join_type="left"
        )

        assert merged.is_success
        assert merged.row_count == 2  # All from left

    def test_merge_with_join_full(self, result_merger, sample_query_results):
        """Test full outer JOIN merge."""
        result1, result2 = sample_query_results

        merged = result_merger.merge_with_join(
            [result1, result2],
            join_keys=["protein"],
            join_type="full"
        )

        assert merged.is_success
        # Should have: P12345 (matched), P67890 (left only), P99999 (right only)
        assert merged.row_count >= 2

    def test_handle_missing_optional_data(self, result_merger):
        """Test filling missing optional data."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {"protein": "P12345", "name": "Protein A", "pdbId": "1ABC"},
                {"protein": "P67890", "name": "Protein B"},  # Missing pdbId
            ],
            variables=["protein", "name", "pdbId"],
            row_count=2
        )

        filled = result_merger.handle_missing_optional_data(
            result,
            optional_vars=["pdbId"],
            default_value="N/A"
        )

        assert filled.bindings[1]["pdbId"] == "N/A"


# =============================================================================
# TEST RESILIENT EXECUTOR
# =============================================================================

class TestResilientFederatedExecutor:
    """Tests for ResilientFederatedExecutor class."""

    def test_initialization(self, resilient_executor):
        """Test executor initialization."""
        assert resilient_executor.max_retries == 2
        assert resilient_executor.retry_delay == 0.1
        assert resilient_executor.allow_partial_results is True

    def test_execute_with_fallback_success(self, resilient_executor):
        """Test successful execution without fallback."""
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o . } LIMIT 10"

        result = resilient_executor.execute_with_fallback(query)

        assert result.status == QueryStatus.SUCCESS

    def test_execute_with_fallback_uses_fallback(self, resilient_executor):
        """Test that fallback is used when primary fails."""
        # This is a placeholder test - actual implementation would need
        # to mock endpoint failures
        primary_query = "INVALID QUERY"
        fallback_query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o . } LIMIT 10"

        # In actual test with mocking:
        # result = resilient_executor.execute_with_fallback(
        #     primary_query,
        #     [fallback_query]
        # )
        # assert result.metadata.get("fallback_used") is True


# =============================================================================
# TEST CONFIGURATION AND UTILITIES
# =============================================================================

class TestConfiguration:
    """Tests for configuration and utilities."""

    def test_biomedical_endpoints_registry(self):
        """Test biomedical endpoints registry."""
        assert "uniprot" in BIOMEDICAL_ENDPOINTS
        assert "pdb" in BIOMEDICAL_ENDPOINTS
        assert "wikidata" in BIOMEDICAL_ENDPOINTS

        uniprot = BIOMEDICAL_ENDPOINTS["uniprot"]
        assert uniprot.url == "https://sparql.uniprot.org/sparql"
        assert uniprot.timeout > 0

    def test_federated_prefixes(self):
        """Test federated prefixes dictionary."""
        assert "up" in FEDERATED_PREFIXES
        assert "pdb" in FEDERATED_PREFIXES
        assert "wd" in FEDERATED_PREFIXES
        assert "wdt" in FEDERATED_PREFIXES

        assert FEDERATED_PREFIXES["up"] == "http://purl.uniprot.org/core/"

    def test_get_federated_prefix_string(self):
        """Test prefix string generation."""
        prefix_string = get_federated_prefix_string()

        assert "PREFIX up:" in prefix_string
        assert "PREFIX pdb:" in prefix_string
        assert "PREFIX wd:" in prefix_string
        assert prefix_string.endswith("\n\n")

    def test_endpoint_capabilities(self):
        """Test EndpointCapabilities dataclass."""
        caps = EndpointCapabilities(
            supports_federation=True,
            max_query_complexity=70,
            reliability_score=0.95
        )

        assert caps.supports_federation is True
        assert caps.max_query_complexity == 70
        assert caps.reliability_score == 0.95

    def test_query_optimization_hints(self):
        """Test QueryOptimizationHints dataclass."""
        hints = QueryOptimizationHints(
            strategies=[OptimizationStrategy.MINIMIZE_TRANSFER],
            service_priority=["endpoint1", "endpoint2"],
            estimated_selectivity={"endpoint1": 0.1}
        )

        assert OptimizationStrategy.MINIMIZE_TRANSFER in hints.strategies
        assert hints.service_priority[0] == "endpoint1"
        assert hints.estimated_selectivity["endpoint1"] == 0.1


# =============================================================================
# TEST OPTIMIZATION STRATEGIES
# =============================================================================

class TestOptimizationStrategies:
    """Tests for query optimization strategies."""

    def test_optimization_strategy_enum(self):
        """Test OptimizationStrategy enum."""
        assert OptimizationStrategy.MINIMIZE_TRANSFER.value == "minimize_transfer"
        assert OptimizationStrategy.EARLY_FILTERING.value == "early_filtering"
        assert OptimizationStrategy.SERVICE_ORDERING.value == "service_ordering"

    def test_add_result_limit_per_service(self, query_builder):
        """Test adding limit to service patterns."""
        patterns = ["?s ?p ?o ."]
        limited = query_builder.add_result_limit_per_service(patterns, 100)

        assert "LIMIT 100" in " ".join(limited)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""

    def test_complete_workflow(self, query_builder, cross_dataset_examples):
        """Test complete workflow from query generation to execution."""
        # Generate query
        query = cross_dataset_examples.protein_disease_associations("BRCA1", 10)

        assert query is not None
        assert "SELECT" in query
        assert "SERVICE" in query

        # Estimate cost
        services = {
            "https://sparql.uniprot.org/sparql": 5,
            "https://query.wikidata.org/sparql": 3
        }
        cost = query_builder.estimate_query_cost(services)

        assert cost["estimated_time_seconds"] > 0

    def test_query_generation_for_all_examples(self, cross_dataset_examples):
        """Test that all example queries can be generated without errors."""
        queries = [
            cross_dataset_examples.protein_disease_associations("BRCA1", 10),
            cross_dataset_examples.protein_structure_function_integration("P38398", 10),
            cross_dataset_examples.gene_ontology_protein_expression("GO:0005634", "9606", 10),
            cross_dataset_examples.taxonomic_phylogenetic_protein_families("Kinase", "33208", 10),
            cross_dataset_examples.chemical_protein_interaction_network("Imatinib", 100.0, 10),
            cross_dataset_examples.precision_medicine_variant_drug_response("CYP2D6", 10),
            cross_dataset_examples.systems_biology_pathway_integration("Apoptosis", "Homo sapiens", 10),
        ]

        for query in queries:
            assert query is not None
            assert "SELECT" in query
            assert "WHERE" in query


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
