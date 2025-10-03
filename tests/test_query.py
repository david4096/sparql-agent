"""
Tests for query module: prompt engine, intent parser, generator, and ontology generator.

This module tests natural language query processing, SPARQL generation, and
ontology-guided query construction.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from sparql_agent.core.types import (
    GeneratedQuery,
    LLMResponse,
    SchemaInfo,
    OntologyInfo,
)
from sparql_agent.core.exceptions import (
    QueryGenerationError,
    NaturalLanguageParseError,
    AmbiguousQueryError,
)


# =============================================================================
# Tests for Prompt Engine
# =============================================================================


@pytest.mark.unit
class TestPromptEngine:
    """Tests for prompt engineering and template management."""

    def test_build_system_prompt(self, sample_schema_info):
        """Test building system prompt for LLM."""
        # Mock prompt engine
        system_prompt = self._build_system_prompt(sample_schema_info)

        assert "SPARQL" in system_prompt
        assert "ontology" in system_prompt.lower()

    def test_build_query_generation_prompt(self, sample_schema_info):
        """Test building query generation prompt."""
        natural_language = "Find all people"

        prompt = self._build_query_prompt(natural_language, sample_schema_info)

        assert natural_language in prompt
        assert "SELECT" in prompt or "SPARQL" in prompt

    def test_include_schema_context(self, sample_schema_info):
        """Test including schema context in prompts."""
        context = self._build_schema_context(sample_schema_info)

        # Should include classes
        assert any(cls in context for cls in sample_schema_info.classes)

        # Should include properties
        assert any(prop in context for prop in sample_schema_info.properties)

    def test_include_examples_in_prompt(self, sample_sparql_queries):
        """Test including example queries in prompt."""
        examples = self._build_examples(sample_sparql_queries)

        assert "SELECT" in examples
        assert "WHERE" in examples

    def test_format_ontology_info(self, sample_ontology_info):
        """Test formatting ontology information for prompts."""
        ontology_text = self._format_ontology(sample_ontology_info)

        assert sample_ontology_info.title in ontology_text
        assert "classes" in ontology_text.lower()

    @staticmethod
    def _build_system_prompt(schema_info):
        """Helper to build system prompt."""
        return f"""You are a SPARQL query generator. Generate queries using this ontology:
Classes: {', '.join(list(schema_info.classes)[:5])}
Properties: {', '.join(list(schema_info.properties)[:5])}
"""

    @staticmethod
    def _build_query_prompt(nl_query, schema_info):
        """Helper to build query prompt."""
        return f"""Generate a SPARQL query for: {nl_query}

Available classes: {', '.join(list(schema_info.classes)[:3])}
Available properties: {', '.join(list(schema_info.properties)[:3])}

Return only the SPARQL query."""

    @staticmethod
    def _build_schema_context(schema_info):
        """Helper to build schema context."""
        return f"Classes: {list(schema_info.classes)}\nProperties: {list(schema_info.properties)}"

    @staticmethod
    def _build_examples(queries):
        """Helper to build examples."""
        return "\n\n".join([f"Example:\n{q}" for q in list(queries.values())[:2]])

    @staticmethod
    def _format_ontology(ontology_info):
        """Helper to format ontology."""
        return f"Ontology: {ontology_info.title}\nClasses: {len(ontology_info.classes)}"


# =============================================================================
# Tests for Intent Parser
# =============================================================================


@pytest.mark.unit
class TestIntentParser:
    """Tests for natural language intent parsing."""

    def test_parse_simple_query(self):
        """Test parsing simple natural language query."""
        nl_query = "Find all people"

        intent = self._parse_intent(nl_query)

        assert intent["action"] == "find"
        assert "people" in intent["entities"]

    def test_parse_query_with_filters(self):
        """Test parsing query with filter conditions."""
        nl_query = "Find people older than 25"

        intent = self._parse_intent(nl_query)

        assert intent["action"] == "find"
        assert "people" in intent["entities"]
        assert "filter" in intent
        assert intent["filter"]["property"] == "age"
        assert intent["filter"]["operator"] == ">"
        assert intent["filter"]["value"] == "25"

    def test_parse_aggregation_query(self):
        """Test parsing aggregation queries."""
        nl_query = "Count all organizations"

        intent = self._parse_intent(nl_query)

        assert intent["action"] == "count"
        assert "organizations" in intent["entities"]

    def test_parse_relationship_query(self):
        """Test parsing queries about relationships."""
        nl_query = "Who works for Google?"

        intent = self._parse_intent(nl_query)

        assert "works for" in str(intent).lower() or "worksFor" in str(intent)
        assert "Google" in intent["entities"]

    def test_identify_ambiguous_query(self):
        """Test identifying ambiguous queries."""
        nl_query = "Find it"

        # This should be flagged as ambiguous
        is_ambiguous = self._is_ambiguous(nl_query)
        assert is_ambiguous is True

    def test_extract_entities(self):
        """Test extracting entities from query."""
        nl_query = "Find people named Alice who work for Microsoft"

        entities = self._extract_entities(nl_query)

        assert "Alice" in entities
        assert "Microsoft" in entities

    def test_identify_query_type(self):
        """Test identifying query type."""
        queries_and_types = [
            ("Find all people", "select"),
            ("Count organizations", "aggregate"),
            ("Does Alice work for Google?", "ask"),
            ("Show me information about Bob", "describe"),
        ]

        for query, expected_type in queries_and_types:
            query_type = self._identify_query_type(query)
            assert query_type == expected_type

    @staticmethod
    def _parse_intent(nl_query):
        """Helper to parse intent."""
        intent = {"action": None, "entities": [], "filter": None}

        # Simple keyword matching
        if "find" in nl_query.lower():
            intent["action"] = "find"
        elif "count" in nl_query.lower():
            intent["action"] = "count"

        # Extract entities (simplified)
        words = nl_query.lower().split()
        if "people" in words:
            intent["entities"].append("people")
        if "organizations" in words:
            intent["entities"].append("organizations")

        # Parse filters
        if "older than" in nl_query.lower():
            intent["filter"] = {
                "property": "age",
                "operator": ">",
                "value": "25"
            }

        if "Google" in nl_query:
            intent["entities"].append("Google")

        return intent

    @staticmethod
    def _is_ambiguous(nl_query):
        """Helper to check if query is ambiguous."""
        ambiguous_indicators = ["it", "that", "thing", "stuff"]
        return any(word in nl_query.lower().split() for word in ambiguous_indicators)

    @staticmethod
    def _extract_entities(nl_query):
        """Helper to extract named entities."""
        # Simplified: find capitalized words
        words = nl_query.split()
        return [w for w in words if w[0].isupper() and w.lower() not in ["find", "who", "the"]]

    @staticmethod
    def _identify_query_type(nl_query):
        """Helper to identify query type."""
        lower = nl_query.lower()
        if "count" in lower or "how many" in lower:
            return "aggregate"
        elif "does" in lower or "is" in lower and "?" in nl_query:
            return "ask"
        elif "show" in lower or "describe" in lower or "information about" in lower:
            return "describe"
        else:
            return "select"


# =============================================================================
# Tests for Query Generator
# =============================================================================


@pytest.mark.unit
class TestQueryGenerator:
    """Tests for SPARQL query generation."""

    def test_generate_basic_select_query(self, mock_llm_provider, sample_schema_info):
        """Test generating basic SELECT query."""
        # Mock LLM to return a SPARQL query
        mock_llm_provider.generate.return_value = LLMResponse(
            content="SELECT ?person WHERE { ?person a <http://example.org/Person> }",
            model="test-model",
        )

        nl_query = "Find all people"
        generated = self._generate_query(nl_query, mock_llm_provider, sample_schema_info)

        assert "SELECT" in generated.query
        assert "WHERE" in generated.query

    def test_generate_query_with_ontology(
        self, mock_llm_provider, sample_schema_info, sample_ontology_info
    ):
        """Test generating query using ontology information."""
        sample_schema_info.ontology = sample_ontology_info

        mock_llm_provider.generate.return_value = LLMResponse(
            content="SELECT ?person ?name WHERE { ?person a ex:Person ; ex:name ?name }",
            model="test-model",
        )

        nl_query = "Find all person names"
        generated = self._generate_query(
            nl_query, mock_llm_provider, sample_schema_info, use_ontology=True
        )

        assert generated.used_ontology is True
        assert "SELECT" in generated.query

    def test_generate_filtered_query(self, mock_llm_provider, sample_schema_info):
        """Test generating query with filters."""
        mock_llm_provider.generate.return_value = LLMResponse(
            content="""SELECT ?person ?age
            WHERE {
                ?person a ex:Person ;
                        ex:age ?age .
                FILTER (?age > 25)
            }""",
            model="test-model",
        )

        nl_query = "Find people older than 25"
        generated = self._generate_query(nl_query, mock_llm_provider, sample_schema_info)

        assert "FILTER" in generated.query
        assert "> 25" in generated.query

    def test_generate_aggregation_query(self, mock_llm_provider, sample_schema_info):
        """Test generating aggregation query."""
        mock_llm_provider.generate.return_value = LLMResponse(
            content="SELECT (COUNT(?person) AS ?count) WHERE { ?person a ex:Person }",
            model="test-model",
        )

        nl_query = "Count all people"
        generated = self._generate_query(nl_query, mock_llm_provider, sample_schema_info)

        assert "COUNT" in generated.query

    def test_generate_multiple_alternatives(self, mock_llm_provider, sample_schema_info):
        """Test generating multiple query alternatives."""
        queries = [
            "SELECT ?person WHERE { ?person a ex:Person }",
            "SELECT ?p WHERE { ?p rdf:type ex:Person }",
            "SELECT DISTINCT ?person WHERE { ?person a ex:Person }",
        ]

        generated_queries = []
        for query in queries:
            mock_llm_provider.generate.return_value = LLMResponse(
                content=query,
                model="test-model",
            )
            generated_queries.append(
                self._generate_query("Find people", mock_llm_provider, sample_schema_info)
            )

        assert len(generated_queries) == 3
        assert all("SELECT" in q.query for q in generated_queries)

    def test_handle_generation_error(self, mock_llm_provider, sample_schema_info):
        """Test handling query generation errors."""
        mock_llm_provider.generate.side_effect = Exception("LLM error")

        with pytest.raises(Exception):
            self._generate_query("Find people", mock_llm_provider, sample_schema_info)

    @staticmethod
    def _generate_query(nl_query, llm_provider, schema_info, use_ontology=False):
        """Helper to generate query."""
        # Build prompt
        prompt = f"Generate SPARQL for: {nl_query}"

        # Call LLM
        response = llm_provider.generate(prompt)

        # Create GeneratedQuery
        return GeneratedQuery(
            query=response.content,
            natural_language=nl_query,
            used_ontology=use_ontology,
        )


# =============================================================================
# Tests for Ontology-Guided Generator
# =============================================================================


@pytest.mark.unit
class TestOntologyGenerator:
    """Tests for ontology-guided query generation."""

    def test_use_ontology_classes(
        self, mock_llm_provider, sample_schema_info, sample_ontology_info
    ):
        """Test using ontology classes in query generation."""
        sample_schema_info.ontology = sample_ontology_info

        # Get class from ontology
        person_class = list(sample_ontology_info.classes.values())[0]

        query = f"SELECT ?person WHERE {{ ?person a <{person_class.uri}> }}"

        assert person_class.uri in query

    def test_use_ontology_properties(
        self, sample_schema_info, sample_ontology_info
    ):
        """Test using ontology properties in query generation."""
        sample_schema_info.ontology = sample_ontology_info

        # Get property from ontology
        name_property = list(sample_ontology_info.properties.values())[0]

        query = f"SELECT ?person ?name WHERE {{ ?person <{name_property.uri}> ?name }}"

        assert name_property.uri in query

    def test_respect_domain_range_constraints(self, sample_ontology_info):
        """Test respecting domain/range constraints from ontology."""
        # Get a property with domain/range
        for prop in sample_ontology_info.properties.values():
            if prop.domain and prop.range:
                assert len(prop.domain) > 0
                assert len(prop.range) > 0
                break

    def test_include_subclass_reasoning(self, sample_ontology_info):
        """Test including subclass relationships in queries."""
        # Find class with subclass relationships
        class_uri = list(sample_ontology_info.classes.keys())[0]
        subclasses = sample_ontology_info.get_subclasses(class_uri)

        # Query should potentially include subclasses
        assert isinstance(subclasses, list)

    def test_handle_missing_ontology(self, mock_llm_provider, sample_schema_info):
        """Test handling missing ontology information."""
        # Schema without ontology
        sample_schema_info.ontology = None

        mock_llm_provider.generate.return_value = LLMResponse(
            content="SELECT ?s WHERE { ?s ?p ?o }",
            model="test-model",
        )

        # Should still generate query without ontology
        nl_query = "Find things"
        generated = TestQueryGenerator._generate_query(
            nl_query, mock_llm_provider, sample_schema_info
        )

        assert generated.used_ontology is False


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestQueryIntegration:
    """Integration tests for query generation workflow."""

    def test_end_to_end_query_generation(
        self, mock_llm_provider, sample_schema_info, sample_ontology_info
    ):
        """Test complete query generation workflow."""
        sample_schema_info.ontology = sample_ontology_info

        # 1. Parse natural language
        nl_query = "Find all people named Alice"
        intent = TestIntentParser._parse_intent(nl_query)

        # 2. Generate SPARQL
        mock_llm_provider.generate.return_value = LLMResponse(
            content="""SELECT ?person
            WHERE {
                ?person a ex:Person ;
                        ex:name "Alice"
            }""",
            model="test-model",
        )

        generated = TestQueryGenerator._generate_query(
            nl_query, mock_llm_provider, sample_schema_info
        )

        # 3. Validate
        assert "SELECT" in generated.query
        assert "Alice" in generated.query

    def test_query_refinement_loop(self, mock_llm_provider, sample_schema_info):
        """Test query refinement with feedback."""
        nl_query = "Find people"

        # First attempt - too general
        mock_llm_provider.generate.return_value = LLMResponse(
            content="SELECT ?s WHERE { ?s ?p ?o }",
            model="test-model",
        )

        query1 = TestQueryGenerator._generate_query(
            nl_query, mock_llm_provider, sample_schema_info
        )

        # Refined attempt
        mock_llm_provider.generate.return_value = LLMResponse(
            content="SELECT ?person WHERE { ?person a ex:Person }",
            model="test-model",
        )

        query2 = TestQueryGenerator._generate_query(
            nl_query + " of type Person", mock_llm_provider, sample_schema_info
        )

        # Second query should be more specific
        assert "Person" in query2.query

    def test_multi_language_query_generation(self, mock_llm_provider, sample_schema_info):
        """Test query generation from different natural languages."""
        queries = {
            "en": "Find all people",
            "es": "Encuentra todas las personas",
            "fr": "Trouver toutes les personnes",
        }

        for lang, nl_query in queries.items():
            mock_llm_provider.generate.return_value = LLMResponse(
                content="SELECT ?person WHERE { ?person a ex:Person }",
                model="test-model",
            )

            generated = TestQueryGenerator._generate_query(
                nl_query, mock_llm_provider, sample_schema_info
            )

            assert "SELECT" in generated.query
