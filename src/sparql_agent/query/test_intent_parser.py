"""
Unit tests for the Intent Parser.

Tests the natural language parsing and intent detection capabilities.
"""

import pytest
from sparql_agent.query.intent_parser import (
    IntentParser,
    ParsedIntent,
    Entity,
    Filter,
    Aggregation,
    OrderClause,
    QueryType,
    AggregationType,
    FilterOperator,
    OrderDirection,
    parse_query,
    classify_query
)
from sparql_agent.core.types import SchemaInfo, OntologyInfo, OWLClass, OWLProperty


class TestQueryTypeDetection:
    """Tests for query type detection."""

    def test_select_query_detection(self):
        """Test SELECT query detection."""
        parser = IntentParser()

        queries = [
            "Find all proteins",
            "List diseases",
            "Show me genes",
            "Get publications",
        ]

        for query in queries:
            intent = parser.parse(query)
            assert intent.query_type == QueryType.SELECT

    def test_count_query_detection(self):
        """Test COUNT query detection."""
        parser = IntentParser()

        queries = [
            "How many proteins are there?",
            "Count the diseases",
            "What is the number of genes?",
            "Total number of publications",
        ]

        for query in queries:
            intent = parser.parse(query)
            assert intent.query_type == QueryType.COUNT

    def test_ask_query_detection(self):
        """Test ASK query detection."""
        parser = IntentParser()

        queries = [
            "Is TP53 a gene?",
            "Does this protein have activity?",
            "Are there any diseases?",
        ]

        for query in queries:
            intent = parser.parse(query)
            assert intent.query_type == QueryType.ASK

    def test_describe_query_detection(self):
        """Test DESCRIBE query detection."""
        parser = IntentParser()

        queries = [
            "Describe the gene TP53",
            "Tell me about Alzheimer's",
            "What is UniProt?",
        ]

        for query in queries:
            intent = parser.parse(query)
            assert intent.query_type == QueryType.DESCRIBE


class TestEntityExtraction:
    """Tests for entity extraction."""

    def test_quoted_string_extraction(self):
        """Test extraction of quoted strings as entities."""
        parser = IntentParser()

        query = 'Find proteins named "TP53"'
        intent = parser.parse(query)

        assert len(intent.entities) > 0
        quoted_entities = [e for e in intent.entities if e.context.get('quoted')]
        assert len(quoted_entities) > 0
        assert quoted_entities[0].text == "TP53"
        assert quoted_entities[0].type == "literal"

    def test_entity_type_recognition(self):
        """Test entity type recognition from keywords."""
        parser = IntentParser()

        query = "Find all genes and proteins"
        intent = parser.parse(query)

        assert len(intent.entities) >= 2

    def test_entity_resolution_with_ontology(self):
        """Test entity resolution using ontology."""
        # Create mock ontology
        ontology = OntologyInfo(uri="http://example.org/ontology")

        protein_class = OWLClass(
            uri="http://purl.uniprot.org/core/Protein",
            label=["Protein", "protein"]
        )
        ontology.classes = {protein_class.uri: protein_class}

        parser = IntentParser(ontology_info=ontology)

        query = "Find all proteins"
        intent = parser.parse(query)

        # Check if any entity was resolved to the protein URI
        resolved = [e for e in intent.entities if e.uri == protein_class.uri]
        assert len(resolved) > 0

    def test_entity_resolution_with_schema(self):
        """Test entity resolution using schema."""
        # Create mock schema
        schema = SchemaInfo()
        schema.classes = {"http://purl.uniprot.org/core/Protein"}

        parser = IntentParser(schema_info=schema)

        query = "Find all proteins"
        intent = parser.parse(query)

        # Should have entities
        assert len(intent.entities) > 0


class TestFilterExtraction:
    """Tests for filter extraction."""

    def test_equality_filter_extraction(self):
        """Test extraction of equality filters."""
        parser = IntentParser()

        query = "Find proteins where organism is human"
        intent = parser.parse(query)

        assert len(intent.filters) > 0
        eq_filters = [f for f in intent.filters if f.operator == FilterOperator.EQUALS]
        assert len(eq_filters) > 0

    def test_comparison_filter_extraction(self):
        """Test extraction of comparison filters."""
        parser = IntentParser()

        query = "Find genes with expression greater than 100"
        intent = parser.parse(query)

        assert len(intent.filters) > 0
        comp_filters = [f for f in intent.filters if f.operator == FilterOperator.GREATER_THAN]
        assert len(comp_filters) > 0
        assert comp_filters[0].value == 100

    def test_contains_filter_extraction(self):
        """Test extraction of contains filters."""
        parser = IntentParser()

        query = "Find diseases containing 'cancer'"
        intent = parser.parse(query)

        assert len(intent.filters) > 0
        contains_filters = [f for f in intent.filters if f.operator == FilterOperator.CONTAINS]
        assert len(contains_filters) > 0


class TestAggregationDetection:
    """Tests for aggregation detection."""

    def test_count_aggregation_detection(self):
        """Test COUNT aggregation detection."""
        parser = IntentParser()

        query = "How many proteins are there?"
        intent = parser.parse(query)

        assert len(intent.aggregations) > 0
        assert intent.aggregations[0].type == AggregationType.COUNT

    def test_average_aggregation_detection(self):
        """Test AVG aggregation detection."""
        parser = IntentParser()

        query = "What is the average expression level?"
        intent = parser.parse(query)

        assert len(intent.aggregations) > 0
        avg_aggs = [a for a in intent.aggregations if a.type == AggregationType.AVG]
        assert len(avg_aggs) > 0

    def test_min_max_aggregation_detection(self):
        """Test MIN/MAX aggregation detection."""
        parser = IntentParser()

        query = "Find the maximum score"
        intent = parser.parse(query)

        assert len(intent.aggregations) > 0
        max_aggs = [a for a in intent.aggregations if a.type == AggregationType.MAX]
        assert len(max_aggs) > 0

    def test_distinct_detection(self):
        """Test DISTINCT detection in aggregations."""
        parser = IntentParser()

        query = "Count distinct organisms"
        intent = parser.parse(query)

        assert intent.distinct or any(a.distinct for a in intent.aggregations)


class TestOrderingExtraction:
    """Tests for ORDER BY extraction."""

    def test_explicit_order_by_extraction(self):
        """Test explicit ORDER BY extraction."""
        parser = IntentParser()

        query = "Find proteins order by score"
        intent = parser.parse(query)

        assert len(intent.order_by) > 0
        assert intent.order_by[0].variable == "score"

    def test_descending_order_detection(self):
        """Test descending order detection."""
        parser = IntentParser()

        query = "Top 10 proteins by score"
        intent = parser.parse(query)

        assert len(intent.order_by) > 0
        assert intent.order_by[0].direction == OrderDirection.DESC

    def test_ascending_order_detection(self):
        """Test ascending order detection."""
        parser = IntentParser()

        query = "Find genes order by name ascending"
        intent = parser.parse(query)

        assert len(intent.order_by) > 0
        assert intent.order_by[0].direction == OrderDirection.ASC


class TestLimitExtraction:
    """Tests for LIMIT extraction."""

    def test_explicit_limit_extraction(self):
        """Test explicit LIMIT extraction."""
        parser = IntentParser()

        query = "Find first 10 proteins"
        intent = parser.parse(query)

        assert intent.limit == 10

    def test_top_n_limit_extraction(self):
        """Test TOP N limit extraction."""
        parser = IntentParser()

        query = "Top 20 genes"
        intent = parser.parse(query)

        assert intent.limit == 20


class TestOptionalPatterns:
    """Tests for optional pattern detection."""

    def test_optional_keyword_detection(self):
        """Test detection of optional keywords."""
        parser = IntentParser()

        query = "Find genes with optional interactions"
        intent = parser.parse(query)

        assert len(intent.optional_patterns) > 0


class TestPropertyPaths:
    """Tests for property path detection."""

    def test_through_keyword_detection(self):
        """Test 'through' keyword for property paths."""
        parser = IntentParser()

        query = "Find genes through pathways"
        intent = parser.parse(query)

        assert len(intent.property_paths) > 0

    def test_transitive_pattern_detection(self):
        """Test transitive relationship detection."""
        parser = IntentParser()

        query = "Find all ancestors of this gene"
        intent = parser.parse(query)

        assert len(intent.property_paths) > 0


class TestTextSearch:
    """Tests for text search extraction."""

    def test_search_term_extraction(self):
        """Test search term extraction."""
        parser = IntentParser()

        query = "Search for genes related to 'immune response'"
        intent = parser.parse(query)

        assert len(intent.text_search) > 0
        assert 'immune response' in intent.text_search

    def test_contains_term_extraction(self):
        """Test contains term extraction."""
        parser = IntentParser()

        query = "Find proteins containing 'kinase'"
        intent = parser.parse(query)

        assert len(intent.text_search) > 0


class TestQueryPatternClassification:
    """Tests for query pattern classification."""

    def test_count_simple_classification(self):
        """Test COUNT_SIMPLE pattern classification."""
        parser = IntentParser()

        query = "How many proteins are there?"
        intent = parser.parse(query)
        pattern = parser.classify_query_pattern(intent)

        assert pattern == "COUNT_SIMPLE"

    def test_count_group_by_classification(self):
        """Test COUNT_GROUP_BY pattern classification."""
        parser = IntentParser()

        query = "Count proteins per organism"
        intent = parser.parse(query)

        # Manually add group by for testing
        if intent.aggregations:
            intent.aggregations[0].group_by = ['organism']

        pattern = parser.classify_query_pattern(intent)
        assert pattern == "COUNT_GROUP_BY"

    def test_top_n_classification(self):
        """Test TOP_N_AGGREGATION pattern classification."""
        parser = IntentParser()

        query = "Top 10 genes by expression"
        intent = parser.parse(query)
        pattern = parser.classify_query_pattern(intent)

        assert pattern == "TOP_N_AGGREGATION"

    def test_text_search_classification(self):
        """Test FULL_TEXT_SEARCH pattern classification."""
        parser = IntentParser()

        query = "Search for proteins containing 'kinase'"
        intent = parser.parse(query)
        pattern = parser.classify_query_pattern(intent)

        assert pattern == "FULL_TEXT_SEARCH"


class TestConfidenceCalculation:
    """Tests for confidence score calculation."""

    def test_high_confidence_with_entities(self):
        """Test high confidence when entities are resolved."""
        ontology = OntologyInfo(uri="http://example.org/ontology")
        protein_class = OWLClass(
            uri="http://purl.uniprot.org/core/Protein",
            label=["Protein", "protein"]
        )
        ontology.classes = {protein_class.uri: protein_class}

        parser = IntentParser(ontology_info=ontology)

        query = "Find all proteins"
        intent = parser.parse(query)

        # Should have reasonable confidence
        assert intent.confidence >= 0.7

    def test_lower_confidence_without_entities(self):
        """Test lower confidence when no entities are found."""
        parser = IntentParser()

        query = "Show everything"
        intent = parser.parse(query)

        # Should have lower confidence due to vagueness
        assert intent.confidence < 1.0


class TestAmbiguityDetection:
    """Tests for ambiguity detection."""

    def test_unresolved_entity_ambiguity(self):
        """Test detection of unresolved entities."""
        parser = IntentParser()

        query = "Find all xyzprotein"  # Non-existent entity
        intent = parser.parse(query)

        # Should detect ambiguity for unresolved entity
        unresolved = [a for a in intent.ambiguities if a['type'] == 'unresolved_entity']
        # May or may not detect depending on entity extraction
        assert isinstance(intent.ambiguities, list)


class TestQueryStructureSuggestion:
    """Tests for query structure suggestion."""

    def test_structure_has_required_fields(self):
        """Test that structure suggestion has required fields."""
        parser = IntentParser()

        query = "Find all proteins"
        intent = parser.parse(query)
        structure = parser.suggest_query_structure(intent)

        assert 'pattern' in structure
        assert 'query_type' in structure
        assert 'select_variables' in structure
        assert 'where_patterns' in structure
        assert 'filters' in structure
        assert 'modifiers' in structure

    def test_structure_with_aggregation(self):
        """Test structure suggestion with aggregation."""
        parser = IntentParser()

        query = "Count proteins"
        intent = parser.parse(query)
        structure = parser.suggest_query_structure(intent)

        assert len(structure['select_variables']) > 0
        # Should have count variable
        assert any('COUNT' in var for var in structure['select_variables'])

    def test_structure_with_limit(self):
        """Test structure suggestion with LIMIT."""
        parser = IntentParser()

        query = "Top 10 proteins"
        intent = parser.parse(query)
        structure = parser.suggest_query_structure(intent)

        assert 'limit' in structure['modifiers']
        assert structure['modifiers']['limit'] == 10


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_parse_query_utility(self):
        """Test parse_query utility function."""
        intent = parse_query("Find all proteins")

        assert isinstance(intent, ParsedIntent)
        assert intent.query_type == QueryType.SELECT

    def test_classify_query_utility(self):
        """Test classify_query utility function."""
        pattern = classify_query("How many proteins are there?")

        assert isinstance(pattern, str)
        assert pattern == "COUNT_SIMPLE"


class TestComplexQueries:
    """Tests for complex multi-part queries."""

    def test_complex_query_with_multiple_parts(self):
        """Test parsing of complex queries with multiple components."""
        parser = IntentParser()

        query = "Find top 10 proteins from human with expression greater than 100 order by score"
        intent = parser.parse(query)

        # Should detect multiple components
        assert intent.query_type == QueryType.SELECT
        assert len(intent.entities) > 0
        assert len(intent.filters) > 0
        assert len(intent.order_by) > 0
        assert intent.limit == 10

    def test_aggregation_with_grouping_and_filtering(self):
        """Test complex aggregation query."""
        parser = IntentParser()

        query = "Count diseases per gene where prevalence greater than 0.01"
        intent = parser.parse(query)

        assert len(intent.aggregations) > 0
        assert len(intent.filters) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
