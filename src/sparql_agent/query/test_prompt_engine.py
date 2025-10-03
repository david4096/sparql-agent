"""
Unit tests for the Prompt Engineering and Template System.
"""

import pytest
from pathlib import Path

from ..core.types import SchemaInfo, OntologyInfo, OWLClass, OWLProperty, OWLPropertyType
from ..schema.ontology_mapper import OntologyMapper
from .prompt_engine import (
    PromptEngine,
    PromptTemplate,
    PromptContext,
    FewShotExample,
    QueryScenario,
    create_prompt_engine,
    quick_prompt
)


class TestPromptContext:
    """Tests for PromptContext class."""

    def test_basic_context_creation(self):
        """Test creating a basic prompt context."""
        context = PromptContext(
            user_query="Find all proteins",
            available_prefixes={"up": "http://purl.uniprot.org/core/"}
        )

        assert context.user_query == "Find all proteins"
        assert "up" in context.available_prefixes
        assert context.scenario == QueryScenario.BASIC

    def test_ontology_context_generation(self):
        """Test ontology context generation."""
        ontology_info = OntologyInfo(
            uri="http://example.org/onto",
            title="Test Ontology",
            description="A test ontology"
        )

        # Add class
        test_class = OWLClass(
            uri="http://example.org/onto/TestClass",
            label=["Test Class"],
            comment=["A test class for testing"]
        )
        ontology_info.classes[test_class.uri] = test_class

        context = PromptContext(
            user_query="Test query",
            ontology_info=ontology_info
        )

        ontology_context = context.get_ontology_context()

        assert "Test Ontology" in ontology_context
        assert "A test ontology" in ontology_context
        assert "Test Class" in ontology_context

    def test_schema_summary_generation(self):
        """Test schema summary generation."""
        schema_info = SchemaInfo()
        schema_info.class_counts = {
            "http://example.org/Class1": 1000,
            "http://example.org/Class2": 500
        }
        schema_info.property_counts = {
            "http://example.org/prop1": 2000,
            "http://example.org/prop2": 1500
        }

        context = PromptContext(
            user_query="Test query",
            schema_info=schema_info
        )

        summary = context.get_schema_summary()

        assert "Most Common Classes" in summary
        assert "1,000 instances" in summary
        assert "Most Common Properties" in summary

    def test_prefix_declarations_generation(self):
        """Test PREFIX declarations generation."""
        context = PromptContext(
            user_query="Test query",
            available_prefixes={
                "up": "http://purl.uniprot.org/core/",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
            }
        )

        declarations = context.get_prefix_declarations()

        assert "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>" in declarations
        assert "PREFIX up: <http://purl.uniprot.org/core/>" in declarations

    def test_examples_formatting(self):
        """Test example queries formatting."""
        context = PromptContext(
            user_query="Test query",
            example_queries=[
                {
                    "question": "Find all proteins",
                    "sparql": "SELECT ?s WHERE { ?s a up:Protein }"
                },
                {
                    "question": "Count proteins",
                    "sparql": "SELECT (COUNT(?s) AS ?count) WHERE { ?s a up:Protein }"
                }
            ]
        )

        formatted = context.get_examples_formatted()

        assert "Example 1:" in formatted
        assert "Find all proteins" in formatted
        assert "Example 2:" in formatted
        assert "Count proteins" in formatted


class TestFewShotExample:
    """Tests for FewShotExample class."""

    def test_basic_example_creation(self):
        """Test creating a few-shot example."""
        example = FewShotExample(
            question="Find all proteins",
            sparql="SELECT ?s WHERE { ?s a up:Protein }",
            scenario=QueryScenario.BASIC,
            difficulty=1,
            tags=["protein", "basic"]
        )

        assert example.question == "Find all proteins"
        assert example.scenario == QueryScenario.BASIC
        assert example.difficulty == 1
        assert "protein" in example.tags

    def test_example_with_explanation(self):
        """Test example with explanation."""
        example = FewShotExample(
            question="Count proteins",
            sparql="SELECT (COUNT(?s) AS ?count) WHERE { ?s a up:Protein }",
            explanation="Use COUNT aggregate to count instances",
            scenario=QueryScenario.AGGREGATION
        )

        assert example.explanation is not None
        assert "COUNT" in example.explanation


class TestPromptTemplate:
    """Tests for PromptTemplate class."""

    def test_basic_template_creation(self):
        """Test creating a basic template."""
        template = PromptTemplate(scenario=QueryScenario.BASIC)
        assert template.scenario == QueryScenario.BASIC

    def test_custom_template_string(self):
        """Test creating template from string."""
        template_str = "Generate SPARQL for: {{ user_query }}"
        template = PromptTemplate(template_string=template_str)

        context = PromptContext(user_query="Find proteins")
        result = template.render(context)

        assert "Generate SPARQL for: Find proteins" in result

    def test_basic_template_rendering(self):
        """Test rendering basic template."""
        template = PromptTemplate(scenario=QueryScenario.BASIC)

        context = PromptContext(
            user_query="Find all proteins",
            available_prefixes={"up": "http://purl.uniprot.org/core/"}
        )

        result = template.render(context)

        assert "Find all proteins" in result
        assert "PREFIX" in result
        assert "SPARQL" in result

    def test_aggregation_template(self):
        """Test aggregation template."""
        template = PromptTemplate(scenario=QueryScenario.AGGREGATION)

        context = PromptContext(
            user_query="Count proteins by organism"
        )

        result = template.render(context)

        assert "Count proteins by organism" in result
        assert "COUNT" in result or "aggregation" in result.lower()

    def test_complex_join_template(self):
        """Test complex join template."""
        template = PromptTemplate(scenario=QueryScenario.COMPLEX_JOIN)

        context = PromptContext(
            user_query="Find genes and their diseases"
        )

        result = template.render(context)

        assert "Find genes and their diseases" in result
        assert "join" in result.lower()

    def test_full_text_template(self):
        """Test full-text search template."""
        template = PromptTemplate(scenario=QueryScenario.FULL_TEXT)

        context = PromptContext(
            user_query="Search for genes related to cancer"
        )

        result = template.render(context)

        assert "Search for genes related to cancer" in result
        assert "search" in result.lower() or "text" in result.lower()


class TestPromptEngine:
    """Tests for PromptEngine class."""

    def test_engine_creation(self):
        """Test creating prompt engine."""
        engine = create_prompt_engine()
        assert engine is not None
        assert isinstance(engine, PromptEngine)

    def test_default_examples_loaded(self):
        """Test that default examples are loaded."""
        engine = create_prompt_engine()

        basic_examples = engine.get_examples(QueryScenario.BASIC)
        assert len(basic_examples) > 0

        agg_examples = engine.get_examples(QueryScenario.AGGREGATION)
        assert len(agg_examples) > 0

    def test_add_custom_example(self):
        """Test adding custom example."""
        engine = create_prompt_engine()

        initial_count = len(engine.get_examples(QueryScenario.BASIC))

        custom_example = FewShotExample(
            question="Test question",
            sparql="SELECT ?s WHERE { ?s ?p ?o }",
            scenario=QueryScenario.BASIC
        )

        engine.add_example(custom_example)

        new_count = len(engine.get_examples(QueryScenario.BASIC))
        assert new_count == initial_count + 1

    def test_get_examples_with_filters(self):
        """Test getting examples with filters."""
        engine = create_prompt_engine()

        # Get examples with difficulty filter
        easy_examples = engine.get_examples(
            QueryScenario.BASIC,
            max_difficulty=2
        )

        for example in easy_examples:
            assert example.difficulty <= 2

    def test_scenario_detection_aggregation(self):
        """Test detecting aggregation queries."""
        engine = create_prompt_engine()

        queries = [
            "Count the number of proteins",
            "What is the average molecular weight?",
            "How many genes are there?",
            "Sum of all values"
        ]

        for query in queries:
            scenario = engine.detect_scenario(query)
            assert scenario == QueryScenario.AGGREGATION, f"Failed for: {query}"

    def test_scenario_detection_full_text(self):
        """Test detecting full-text search queries."""
        engine = create_prompt_engine()

        queries = [
            "Search for genes containing BRCA",
            "Find all proteins similar to kinase",
            "Look for diseases related to cancer"
        ]

        for query in queries:
            scenario = engine.detect_scenario(query)
            assert scenario == QueryScenario.FULL_TEXT, f"Failed for: {query}"

    def test_scenario_detection_complex_join(self):
        """Test detecting complex join queries."""
        engine = create_prompt_engine()

        queries = [
            "Find genes and their associated diseases",
            "Show proteins linked to pathways",
            "Get variants connected to genes"
        ]

        for query in queries:
            scenario = engine.detect_scenario(query)
            assert scenario == QueryScenario.COMPLEX_JOIN, f"Failed for: {query}"

    def test_scenario_detection_basic(self):
        """Test detecting basic queries."""
        engine = create_prompt_engine()

        queries = [
            "List all proteins",
            "Show me genes",
            "Get diseases"
        ]

        for query in queries:
            scenario = engine.detect_scenario(query)
            assert scenario == QueryScenario.BASIC, f"Failed for: {query}"

    def test_build_context(self):
        """Test building prompt context."""
        engine = create_prompt_engine()

        schema_info = SchemaInfo()
        schema_info.namespaces = {"up": "http://purl.uniprot.org/core/"}

        context = engine.build_context(
            user_query="Find all proteins",
            schema_info=schema_info,
            use_examples=True,
            max_examples=3
        )

        assert context.user_query == "Find all proteins"
        assert "up" in context.available_prefixes
        assert len(context.example_queries) <= 3
        # Common prefixes should be added
        assert "rdf" in context.available_prefixes
        assert "rdfs" in context.available_prefixes

    def test_generate_prompt_basic(self):
        """Test generating a basic prompt."""
        engine = create_prompt_engine()

        prompt = engine.generate_prompt(
            user_query="Find all proteins from human"
        )

        assert prompt is not None
        assert "Find all proteins from human" in prompt
        assert "SPARQL" in prompt

    def test_generate_prompt_with_schema(self):
        """Test generating prompt with schema."""
        engine = create_prompt_engine()

        schema_info = SchemaInfo()
        schema_info.class_counts = {
            "http://example.org/Protein": 1000
        }

        prompt = engine.generate_prompt(
            user_query="Find proteins",
            schema_info=schema_info
        )

        assert "Find proteins" in prompt
        assert "1,000" in prompt

    def test_generate_prompt_with_ontology(self):
        """Test generating prompt with ontology."""
        engine = create_prompt_engine()

        ontology_info = OntologyInfo(
            uri="http://example.org/onto",
            title="Test Ontology"
        )

        prompt = engine.generate_prompt(
            user_query="Find proteins",
            ontology_info=ontology_info
        )

        assert "Find proteins" in prompt
        assert "Test Ontology" in prompt

    def test_generate_prompt_specific_scenario(self):
        """Test generating prompt for specific scenario."""
        engine = create_prompt_engine()

        prompt = engine.generate_prompt(
            user_query="Count proteins",
            scenario=QueryScenario.AGGREGATION
        )

        assert "Count proteins" in prompt
        assert "aggregation" in prompt.lower() or "COUNT" in prompt

    def test_generate_prompt_without_examples(self):
        """Test generating prompt without examples."""
        engine = create_prompt_engine()

        prompt = engine.generate_prompt(
            user_query="Find proteins",
            use_examples=False
        )

        assert "Find proteins" in prompt
        # Should not contain example section
        assert "Example 1:" not in prompt

    def test_generate_multi_scenario_prompts(self):
        """Test generating prompts for multiple scenarios."""
        engine = create_prompt_engine()

        scenarios = [QueryScenario.BASIC, QueryScenario.AGGREGATION]
        prompts = engine.generate_multi_scenario_prompts(
            user_query="Find proteins",
            scenarios=scenarios
        )

        assert len(prompts) == 2
        assert QueryScenario.BASIC in prompts
        assert QueryScenario.AGGREGATION in prompts
        assert "Find proteins" in prompts[QueryScenario.BASIC]
        assert "Find proteins" in prompts[QueryScenario.AGGREGATION]

    def test_generate_prompt_with_constraints(self):
        """Test generating prompt with constraints."""
        engine = create_prompt_engine()

        prompt = engine.generate_prompt(
            user_query="Find proteins",
            constraints={
                "LIMIT": 100,
                "timeout": 30
            }
        )

        assert "Find proteins" in prompt
        assert "100" in prompt
        assert "30" in prompt


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_quick_prompt(self):
        """Test quick_prompt utility."""
        prompt = quick_prompt("Find all proteins")

        assert prompt is not None
        assert "Find all proteins" in prompt
        assert "SPARQL" in prompt

    def test_quick_prompt_with_schema(self):
        """Test quick_prompt with schema."""
        schema_info = SchemaInfo()
        schema_info.namespaces = {"up": "http://purl.uniprot.org/core/"}

        prompt = quick_prompt(
            user_query="Find proteins",
            schema_info=schema_info
        )

        assert "Find proteins" in prompt
        assert "up:" in prompt or "http://purl.uniprot.org/core/" in prompt


class TestIntegration:
    """Integration tests."""

    def test_end_to_end_basic_query(self):
        """Test complete workflow for basic query."""
        # Create components
        engine = create_prompt_engine()
        schema_info = SchemaInfo()
        schema_info.namespaces = {
            "up": "http://purl.uniprot.org/core/",
            "taxon": "http://purl.uniprot.org/taxonomy/"
        }
        schema_info.class_counts = {
            "http://purl.uniprot.org/core/Protein": 500000
        }

        # Generate prompt
        prompt = engine.generate_prompt(
            user_query="Find all human proteins",
            schema_info=schema_info,
            use_examples=True,
            max_examples=2
        )

        # Verify prompt contains expected elements
        assert "Find all human proteins" in prompt
        assert "PREFIX" in prompt
        assert "up:" in prompt or "http://purl.uniprot.org/core/" in prompt
        assert "500,000" in prompt

    def test_end_to_end_with_ontology(self):
        """Test complete workflow with ontology."""
        # Create components
        engine = create_prompt_engine()
        mapper = OntologyMapper()

        ontology_info = OntologyInfo(
            uri="http://purl.uniprot.org/core/",
            title="UniProt Core Ontology"
        )

        protein_class = OWLClass(
            uri="http://purl.uniprot.org/core/Protein",
            label=["Protein"],
            comment=["A biological macromolecule"]
        )
        ontology_info.classes[protein_class.uri] = protein_class

        # Generate prompt
        prompt = engine.generate_prompt(
            user_query="Find proteins with enzymatic activity",
            ontology_info=ontology_info,
            use_examples=True
        )

        # Verify
        assert "Find proteins with enzymatic activity" in prompt
        assert "UniProt Core Ontology" in prompt
        assert "Protein" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
