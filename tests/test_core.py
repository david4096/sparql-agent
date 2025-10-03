"""
Tests for core module: base classes, types, and exceptions.

This module contains comprehensive tests for the core abstractions, data types,
and exception hierarchy.
"""

import pytest
from datetime import datetime
from sparql_agent.core.base import (
    SPARQLEndpoint,
    OntologyProvider,
    SchemaDiscoverer,
    QueryGenerator,
    LLMProvider,
    ResultFormatter,
)
from sparql_agent.core.types import (
    QueryStatus,
    OWLPropertyType,
    OWLRestrictionType,
    OWLClass,
    OWLProperty,
    OntologyInfo,
    EndpointInfo,
    SchemaInfo,
    QueryResult,
    LLMResponse,
    GeneratedQuery,
    FormattedResult,
)
from sparql_agent.core.exceptions import (
    SPARQLAgentError,
    EndpointError,
    EndpointConnectionError,
    QueryError,
    QuerySyntaxError,
    SchemaError,
    OntologyError,
    LLMError,
    FormattingError,
)


# =============================================================================
# Tests for Base Classes
# =============================================================================


class TestBaseAbstractClasses:
    """Tests for abstract base classes."""

    def test_sparql_endpoint_is_abstract(self):
        """Test that SPARQLEndpoint cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SPARQLEndpoint(EndpointInfo(url="http://test.org"))

    def test_ontology_provider_is_abstract(self):
        """Test that OntologyProvider cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            OntologyProvider()

    def test_schema_discoverer_is_abstract(self, mock_sparql_endpoint):
        """Test that SchemaDiscoverer cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SchemaDiscoverer(mock_sparql_endpoint)

    def test_query_generator_is_abstract(
        self, mock_llm_provider, sample_schema_info
    ):
        """Test that QueryGenerator cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            QueryGenerator(mock_llm_provider, sample_schema_info)

    def test_llm_provider_is_abstract(self):
        """Test that LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            LLMProvider("test-model")

    def test_result_formatter_is_abstract(self):
        """Test that ResultFormatter cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ResultFormatter()


# =============================================================================
# Tests for Types - Enums
# =============================================================================


class TestEnums:
    """Tests for enum types."""

    def test_query_status_enum(self):
        """Test QueryStatus enum values."""
        assert QueryStatus.SUCCESS.value == "success"
        assert QueryStatus.FAILED.value == "failed"
        assert QueryStatus.TIMEOUT.value == "timeout"
        assert QueryStatus.INVALID.value == "invalid"
        assert QueryStatus.PENDING.value == "pending"

    def test_owl_property_type_enum(self):
        """Test OWLPropertyType enum values."""
        assert OWLPropertyType.OBJECT_PROPERTY.value == "object_property"
        assert OWLPropertyType.DATATYPE_PROPERTY.value == "datatype_property"
        assert OWLPropertyType.ANNOTATION_PROPERTY.value == "annotation_property"
        assert OWLPropertyType.FUNCTIONAL.value == "functional"

    def test_owl_restriction_type_enum(self):
        """Test OWLRestrictionType enum values."""
        assert OWLRestrictionType.SOME_VALUES_FROM.value == "some_values_from"
        assert OWLRestrictionType.ALL_VALUES_FROM.value == "all_values_from"
        assert OWLRestrictionType.MIN_CARDINALITY.value == "min_cardinality"


# =============================================================================
# Tests for Types - OWL Classes and Properties
# =============================================================================


class TestOWLClass:
    """Tests for OWLClass dataclass."""

    def test_owl_class_creation(self):
        """Test creating an OWLClass instance."""
        owl_class = OWLClass(
            uri="http://example.org/Person",
            label=["Person", "Human"],
            comment=["A human being"],
        )
        assert owl_class.uri == "http://example.org/Person"
        assert "Person" in owl_class.label
        assert owl_class.is_deprecated is False

    def test_owl_class_get_primary_label(self):
        """Test getting primary label from OWLClass."""
        owl_class = OWLClass(
            uri="http://example.org/Person",
            label=["Person", "Human"],
        )
        assert owl_class.get_primary_label() == "Person"

    def test_owl_class_get_primary_label_fallback(self):
        """Test fallback when no label exists."""
        owl_class = OWLClass(uri="http://example.org/ontology#Person")
        assert owl_class.get_primary_label() == "Person"

    def test_owl_class_get_primary_comment(self):
        """Test getting primary comment."""
        owl_class = OWLClass(
            uri="http://example.org/Person",
            comment=["A human being", "Another comment"],
        )
        assert owl_class.get_primary_comment() == "A human being"

    def test_owl_class_get_primary_comment_none(self):
        """Test getting comment when none exists."""
        owl_class = OWLClass(uri="http://example.org/Person")
        assert owl_class.get_primary_comment() is None


class TestOWLProperty:
    """Tests for OWLProperty dataclass."""

    def test_owl_property_creation(self):
        """Test creating an OWLProperty instance."""
        owl_property = OWLProperty(
            uri="http://example.org/name",
            label=["name"],
            property_type=OWLPropertyType.DATATYPE_PROPERTY,
            is_functional=True,
        )
        assert owl_property.uri == "http://example.org/name"
        assert owl_property.is_functional is True
        assert owl_property.is_transitive is False

    def test_owl_property_get_primary_label(self):
        """Test getting primary label from OWLProperty."""
        owl_property = OWLProperty(
            uri="http://example.org/name",
            label=["name", "fullName"],
        )
        assert owl_property.get_primary_label() == "name"

    def test_owl_property_domain_and_range(self):
        """Test property domain and range."""
        owl_property = OWLProperty(
            uri="http://example.org/worksFor",
            domain=["http://example.org/Person"],
            range=["http://example.org/Organization"],
        )
        assert "http://example.org/Person" in owl_property.domain
        assert "http://example.org/Organization" in owl_property.range


# =============================================================================
# Tests for Types - Ontology Info
# =============================================================================


class TestOntologyInfo:
    """Tests for OntologyInfo dataclass."""

    def test_ontology_info_creation(self, sample_owl_class, sample_owl_property):
        """Test creating OntologyInfo."""
        ontology = OntologyInfo(
            uri="http://example.org/ontology",
            title="Test Ontology",
            classes={sample_owl_class.uri: sample_owl_class},
            properties={sample_owl_property.uri: sample_owl_property},
        )
        assert ontology.uri == "http://example.org/ontology"
        assert len(ontology.classes) == 1
        assert len(ontology.properties) == 1

    def test_get_class_by_label(self, sample_ontology_info):
        """Test finding class by label."""
        owl_class = sample_ontology_info.get_class_by_label("Person")
        assert owl_class is not None
        assert owl_class.uri == "http://example.org/Person"

    def test_get_class_by_label_case_insensitive(self, sample_ontology_info):
        """Test case-insensitive label search."""
        owl_class = sample_ontology_info.get_class_by_label("person")
        assert owl_class is not None

    def test_get_class_by_label_not_found(self, sample_ontology_info):
        """Test when class label is not found."""
        owl_class = sample_ontology_info.get_class_by_label("NonExistent")
        assert owl_class is None

    def test_get_property_by_label(self, sample_ontology_info):
        """Test finding property by label."""
        owl_property = sample_ontology_info.get_property_by_label("name")
        assert owl_property is not None
        assert owl_property.uri == "http://example.org/name"

    def test_get_subclasses(self, sample_owl_class):
        """Test getting subclasses of a class."""
        # Create a parent class
        parent = OWLClass(uri="http://example.org/Agent")
        child = OWLClass(
            uri="http://example.org/Person",
            subclass_of=["http://example.org/Agent"],
        )

        ontology = OntologyInfo(
            uri="http://example.org/ontology",
            classes={
                parent.uri: parent,
                child.uri: child,
            },
        )

        subclasses = ontology.get_subclasses("http://example.org/Agent")
        assert "http://example.org/Person" in subclasses

    def test_get_superclasses(self):
        """Test getting superclasses of a class."""
        grandparent = OWLClass(uri="http://example.org/Thing")
        parent = OWLClass(
            uri="http://example.org/Agent",
            subclass_of=["http://example.org/Thing"],
        )
        child = OWLClass(
            uri="http://example.org/Person",
            subclass_of=["http://example.org/Agent"],
        )

        ontology = OntologyInfo(
            uri="http://example.org/ontology",
            classes={
                grandparent.uri: grandparent,
                parent.uri: parent,
                child.uri: child,
            },
        )

        # Non-recursive
        superclasses = ontology.get_superclasses("http://example.org/Person")
        assert "http://example.org/Agent" in superclasses

        # Recursive
        superclasses = ontology.get_superclasses(
            "http://example.org/Person", recursive=True
        )
        assert "http://example.org/Agent" in superclasses
        assert "http://example.org/Thing" in superclasses


# =============================================================================
# Tests for Types - Query Results
# =============================================================================


class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_successful_query_result(self, sample_query_result):
        """Test successful query result."""
        assert sample_query_result.is_success is True
        assert sample_query_result.is_empty is False
        assert sample_query_result.row_count == 2

    def test_failed_query_result(self):
        """Test failed query result."""
        result = QueryResult(
            status=QueryStatus.FAILED,
            error_message="Query execution failed",
        )
        assert result.is_success is False
        assert result.error_message == "Query execution failed"

    def test_empty_query_result(self):
        """Test empty query result."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            data=[],
            row_count=0,
        )
        assert result.is_success is True
        assert result.is_empty is True


class TestSchemaInfo:
    """Tests for SchemaInfo dataclass."""

    def test_schema_info_creation(self, sample_schema_info):
        """Test creating SchemaInfo."""
        assert len(sample_schema_info.classes) == 2
        assert len(sample_schema_info.properties) == 2
        assert sample_schema_info.ontology is not None

    def test_get_most_common_classes(self, sample_schema_info):
        """Test getting most common classes."""
        common = sample_schema_info.get_most_common_classes(limit=1)
        assert len(common) == 1
        assert common[0][0] == "http://example.org/Person"
        assert common[0][1] == 50

    def test_get_most_common_properties(self, sample_schema_info):
        """Test getting most common properties."""
        common = sample_schema_info.get_most_common_properties(limit=2)
        assert len(common) == 2
        assert common[0][1] >= common[1][1]  # Sorted by count


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_llm_response_creation(self, sample_llm_response):
        """Test creating LLMResponse."""
        assert sample_llm_response.model == "claude-3-sonnet-20240229"
        assert sample_llm_response.tokens_used == 150
        assert sample_llm_response.finish_reason == "stop"

    def test_llm_response_cost_calculation(self):
        """Test cost calculation in response."""
        response = LLMResponse(
            content="Test",
            model="test-model",
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.001,
        )
        assert response.cost == 0.001


class TestGeneratedQuery:
    """Tests for GeneratedQuery dataclass."""

    def test_generated_query_creation(self, sample_generated_query):
        """Test creating GeneratedQuery."""
        assert sample_generated_query.confidence == 0.95
        assert sample_generated_query.used_ontology is True
        assert len(sample_generated_query.ontology_classes) > 0

    def test_generated_query_with_validation_errors(self):
        """Test generated query with validation errors."""
        query = GeneratedQuery(
            query="INVALID QUERY",
            natural_language="Test",
            validation_errors=["Syntax error at line 1"],
        )
        assert len(query.validation_errors) == 1


# =============================================================================
# Tests for Exceptions
# =============================================================================


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_base_exception(self):
        """Test base SPARQLAgentError."""
        error = SPARQLAgentError("Test error", {"key": "value"})
        assert str(error) == "Test error (key=value)"
        assert error.details["key"] == "value"

    def test_endpoint_error_hierarchy(self):
        """Test endpoint error inheritance."""
        assert issubclass(EndpointError, SPARQLAgentError)
        assert issubclass(EndpointConnectionError, EndpointError)

    def test_query_error_hierarchy(self):
        """Test query error inheritance."""
        assert issubclass(QueryError, SPARQLAgentError)
        assert issubclass(QuerySyntaxError, QueryError)

    def test_schema_error_hierarchy(self):
        """Test schema error inheritance."""
        assert issubclass(SchemaError, SPARQLAgentError)

    def test_ontology_error_hierarchy(self):
        """Test ontology error inheritance."""
        assert issubclass(OntologyError, SPARQLAgentError)

    def test_llm_error_hierarchy(self):
        """Test LLM error inheritance."""
        assert issubclass(LLMError, SPARQLAgentError)

    def test_formatting_error_hierarchy(self):
        """Test formatting error inheritance."""
        assert issubclass(FormattingError, SPARQLAgentError)

    def test_exception_with_details(self):
        """Test exception with details."""
        error = QuerySyntaxError(
            "Invalid SPARQL syntax",
            {"line": 5, "column": 10}
        )
        assert "line=5" in str(error)
        assert "column=10" in str(error)

    def test_exception_without_details(self):
        """Test exception without details."""
        error = QuerySyntaxError("Invalid SPARQL syntax")
        assert str(error) == "Invalid SPARQL syntax"
        assert error.details == {}

    def test_catch_all_sparql_agent_errors(self):
        """Test catching all system errors."""
        errors = [
            EndpointConnectionError("Connection failed"),
            QuerySyntaxError("Syntax error"),
            SchemaError("Schema error"),
            OntologyError("Ontology error"),
            LLMError("LLM error"),
        ]

        for error in errors:
            try:
                raise error
            except SPARQLAgentError as e:
                assert isinstance(e, SPARQLAgentError)


# =============================================================================
# Tests for Type Validation
# =============================================================================


class TestTypeValidation:
    """Tests for type validation and constraints."""

    def test_endpoint_info_defaults(self):
        """Test EndpointInfo default values."""
        endpoint = EndpointInfo(url="http://test.org/sparql")
        assert endpoint.timeout == 30
        assert endpoint.supports_update is False
        assert endpoint.version == "1.1"

    def test_query_result_properties(self):
        """Test QueryResult computed properties."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            data=[{"name": "Alice"}],
            row_count=1,
        )
        assert result.is_success
        assert not result.is_empty

    def test_formatted_result_creation(self, sample_query_result):
        """Test FormattedResult creation."""
        formatted = FormattedResult(
            format_type="table",
            content="| name | age |\n|------|-----|\n| Alice | 30 |",
            original_result=sample_query_result,
            summary="Found 2 people",
        )
        assert formatted.format_type == "table"
        assert formatted.summary == "Found 2 people"


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestTypeIntegration:
    """Integration tests for types working together."""

    def test_schema_info_with_ontology(
        self, sample_schema_info, sample_ontology_info
    ):
        """Test SchemaInfo integrated with OntologyInfo."""
        assert sample_schema_info.ontology == sample_ontology_info
        assert len(sample_schema_info.ontology.classes) > 0

    def test_generated_query_with_schema(
        self, sample_generated_query, sample_schema_info
    ):
        """Test GeneratedQuery using SchemaInfo."""
        # Verify generated query uses classes from schema
        for class_uri in sample_generated_query.ontology_classes:
            assert class_uri in [
                c.uri for c in sample_schema_info.ontology.classes.values()
            ]
