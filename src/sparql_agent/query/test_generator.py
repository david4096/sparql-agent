"""
Test and demonstration of SPARQL Generator capabilities.

This module provides comprehensive tests for the SPARQLGenerator class,
demonstrating template-based, LLM-based, and hybrid generation strategies.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from ..core.types import SchemaInfo, OntologyInfo, OWLClass, OWLProperty, EndpointInfo
from ..core.exceptions import QueryGenerationError
from ..llm.client import LLMClient, LLMResponse, TokenUsage, GenerationMetrics
from .generator import (
    SPARQLGenerator,
    SPARQLValidator,
    GenerationStrategy,
    GenerationContext,
    QueryTemplate,
    ValidationResult,
    ConfidenceLevel,
    create_generator,
    quick_generate
)
from .prompt_engine import QueryScenario


class TestSPARQLValidator(unittest.TestCase):
    """Test SPARQL validation functionality."""

    def setUp(self):
        self.validator = SPARQLValidator()

    def test_valid_simple_query(self):
        """Test validation of a simple valid query."""
        query = """
        PREFIX ex: <http://example.org/>
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o .
        }
        LIMIT 10
        """
        result = self.validator.validate(query)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.syntax_errors), 0)

    def test_missing_query_form(self):
        """Test detection of missing query form."""
        query = """
        PREFIX ex: <http://example.org/>
        WHERE {
            ?s ?p ?o .
        }
        """
        result = self.validator.validate(query)
        self.assertFalse(result.is_valid)
        self.assertTrue(any('query form' in err.lower() for err in result.syntax_errors))

    def test_unbalanced_braces(self):
        """Test detection of unbalanced braces."""
        query = """
        SELECT ?s
        WHERE {
            ?s ?p ?o .
        """
        result = self.validator.validate(query)
        self.assertFalse(result.is_valid)
        self.assertTrue(any('braces' in err.lower() for err in result.syntax_errors))

    def test_missing_prefix_detection(self):
        """Test detection of missing PREFIX declarations."""
        query = """
        SELECT ?person
        WHERE {
            ?person rdf:type ex:Person .
        }
        """
        result = self.validator.validate(query)
        self.assertTrue(len(result.missing_prefixes) > 0)
        self.assertIn('ex', result.missing_prefixes)

    def test_complexity_scoring(self):
        """Test query complexity scoring."""
        simple_query = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10"
        complex_query = """
        SELECT ?gene (COUNT(?variant) AS ?count)
        WHERE {
            ?gene a :Gene .
            OPTIONAL {
                ?variant :associatedWith ?gene .
                FILTER(?variant > 100)
            }
            UNION {
                ?gene :hasFunction ?function .
            }
        }
        GROUP BY ?gene
        ORDER BY DESC(?count)
        """

        simple_result = self.validator.validate(simple_query)
        complex_result = self.validator.validate(complex_query)

        self.assertLess(simple_result.complexity_score, complex_result.complexity_score)
        self.assertGreater(complex_result.complexity_score, 3.0)

    def test_optimization_suggestions(self):
        """Test generation of optimization suggestions."""
        # Query without LIMIT
        query = """
        SELECT ?s ?o
        WHERE {
            ?s rdf:type ?o .
        }
        """
        result = self.validator.validate(query)
        self.assertTrue(any('LIMIT' in sugg for sugg in result.suggestions))


class TestSPARQLGeneratorTemplate(unittest.TestCase):
    """Test template-based query generation."""

    def setUp(self):
        self.generator = SPARQLGenerator(enable_validation=False)

        # Create mock schema info
        self.schema = SchemaInfo(
            classes={"http://example.org/Person", "http://example.org/Gene"},
            properties={"http://example.org/name", "http://example.org/age"},
            namespaces={
                "ex": "http://example.org/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
            }
        )

    def test_list_instances_template(self):
        """Test template for listing instances."""
        result = self.generator.generate(
            natural_language="list all persons",
            schema_info=self.schema,
            strategy=GenerationStrategy.TEMPLATE
        )

        self.assertIsNotNone(result.query)
        self.assertIn("SELECT", result.query.upper())
        self.assertGreater(result.confidence, 0.5)
        self.assertEqual(result.metadata.get('strategy'), 'template')

    def test_count_instances_template(self):
        """Test template for counting instances."""
        result = self.generator.generate(
            natural_language="how many persons",
            schema_info=self.schema,
            strategy=GenerationStrategy.TEMPLATE
        )

        self.assertIsNotNone(result.query)
        self.assertIn("COUNT", result.query.upper())
        self.assertGreater(result.confidence, 0.5)

    def test_custom_template(self):
        """Test adding and using custom templates."""
        custom_template = QueryTemplate(
            name="custom_test",
            pattern=r"test pattern",
            sparql_template="SELECT ?s WHERE { ?s a {class_uri} }",
            required_context=["class_uri"],
            confidence=0.9
        )

        self.generator.add_template(custom_template)

        # Verify template was added
        self.assertIn(custom_template, self.generator.templates)


class TestSPARQLGeneratorLLM(unittest.TestCase):
    """Test LLM-based query generation."""

    def setUp(self):
        # Create mock LLM client
        self.mock_llm = Mock(spec=LLMClient)
        self.generator = SPARQLGenerator(
            llm_client=self.mock_llm,
            enable_validation=False
        )

        self.schema = SchemaInfo(
            classes={"http://example.org/Protein"},
            namespaces={"ex": "http://example.org/"}
        )

    def test_llm_generation(self):
        """Test LLM-based query generation."""
        # Mock LLM response
        mock_response = LLMResponse(
            content="""```sparql
PREFIX ex: <http://example.org/>
SELECT ?protein ?name
WHERE {
    ?protein a ex:Protein .
    ?protein ex:name ?name .
}
LIMIT 100
```""",
            model="gpt-4",
            provider="openai",
            finish_reason="stop",
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            metrics=GenerationMetrics(latency_ms=500, tokens_per_second=30)
        )

        self.mock_llm.generate_text.return_value = mock_response

        result = self.generator.generate(
            natural_language="Find all proteins with their names",
            schema_info=self.schema,
            strategy=GenerationStrategy.LLM
        )

        self.assertIsNotNone(result.query)
        self.assertIn("SELECT", result.query)
        self.assertIn("Protein", result.query)
        self.mock_llm.generate_text.assert_called_once()

    def test_llm_response_extraction(self):
        """Test SPARQL extraction from various LLM response formats."""
        # Test code block format
        response1 = "```sparql\nSELECT * WHERE { ?s ?p ?o }\n```"
        extracted1 = self.generator._extract_sparql_from_llm_response(response1)
        self.assertIn("SELECT", extracted1)

        # Test plain format
        response2 = "SELECT * WHERE { ?s ?p ?o }"
        extracted2 = self.generator._extract_sparql_from_llm_response(response2)
        self.assertIn("SELECT", extracted2)

        # Test with PREFIX
        response3 = "PREFIX ex: <http://example.org/>\nSELECT * WHERE { ?s ?p ?o }"
        extracted3 = self.generator._extract_sparql_from_llm_response(response3)
        self.assertIn("PREFIX", extracted3)


class TestSPARQLGeneratorHybrid(unittest.TestCase):
    """Test hybrid query generation strategy."""

    def setUp(self):
        self.mock_llm = Mock(spec=LLMClient)
        self.generator = SPARQLGenerator(
            llm_client=self.mock_llm,
            enable_validation=False
        )

        self.schema = SchemaInfo(
            classes={"http://example.org/Gene"},
            properties={"http://example.org/name"},
            namespaces={"ex": "http://example.org/"}
        )

    def test_hybrid_with_template_validation(self):
        """Test hybrid generation with template and LLM validation."""
        # Mock LLM response for validation
        mock_response = LLMResponse(
            content="PREFIX ex: <http://example.org/>\nSELECT ?gene ?name WHERE { ?gene a ex:Gene . ?gene ex:name ?name . } LIMIT 100",
            model="gpt-4",
            provider="openai",
            finish_reason="stop",
            usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
            metrics=GenerationMetrics(latency_ms=300, tokens_per_second=25)
        )

        self.mock_llm.generate_text.return_value = mock_response

        result = self.generator.generate(
            natural_language="list all genes",
            schema_info=self.schema,
            strategy=GenerationStrategy.HYBRID
        )

        self.assertIsNotNone(result.query)
        self.assertIn("SELECT", result.query)


class TestSPARQLGeneratorValidation(unittest.TestCase):
    """Test query validation and optimization features."""

    def setUp(self):
        self.generator = SPARQLGenerator(
            enable_validation=True,
            enable_optimization=True
        )

        self.schema = SchemaInfo(
            classes={"http://example.org/Person"},
            namespaces={
                "ex": "http://example.org/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            }
        )

    def test_validation_enabled(self):
        """Test that validation is performed when enabled."""
        result = self.generator.generate(
            natural_language="list all persons",
            schema_info=self.schema,
            strategy=GenerationStrategy.TEMPLATE
        )

        self.assertIn('validation', result.metadata)
        validation_info = result.metadata['validation']
        self.assertIn('is_valid', validation_info)
        self.assertIn('complexity_score', validation_info)

    def test_missing_prefix_addition(self):
        """Test automatic addition of missing prefixes."""
        # Create a query with missing prefixes
        with patch.object(
            self.generator,
            '_generate_template',
            return_value=Mock(
                query="SELECT ?s WHERE { ?s rdf:type ex:Person }",
                natural_language="test",
                confidence=0.8,
                metadata={}
            )
        ):
            result = self.generator.generate(
                natural_language="list all persons",
                schema_info=self.schema,
                strategy=GenerationStrategy.TEMPLATE
            )

            # Check that prefixes were added
            self.assertIn("PREFIX", result.query)


class TestSPARQLGeneratorContextAwareness(unittest.TestCase):
    """Test context-aware features of generator."""

    def setUp(self):
        self.generator = SPARQLGenerator(enable_validation=False)

        # Create rich schema with ontology
        self.schema = SchemaInfo(
            classes={
                "http://purl.uniprot.org/core/Protein",
                "http://purl.uniprot.org/core/Organism"
            },
            properties={
                "http://purl.uniprot.org/core/organism",
                "http://purl.uniprot.org/core/recommendedName"
            },
            namespaces={
                "up": "http://purl.uniprot.org/core/",
                "taxon": "http://purl.uniprot.org/taxonomy/"
            }
        )

        self.ontology = OntologyInfo(
            uri="http://purl.uniprot.org/core/",
            title="UniProt Core Ontology",
            classes={
                "http://purl.uniprot.org/core/Protein": OWLClass(
                    uri="http://purl.uniprot.org/core/Protein",
                    label=["Protein"],
                    comment=["A protein entity"]
                )
            },
            properties={
                "http://purl.uniprot.org/core/organism": OWLProperty(
                    uri="http://purl.uniprot.org/core/organism",
                    label=["organism"],
                    comment=["The organism that the protein comes from"]
                )
            },
            namespaces={
                "up": "http://purl.uniprot.org/core/"
            }
        )

    def test_vocabulary_hint_extraction(self):
        """Test extraction of vocabulary hints from natural language."""
        hints = self.generator._extract_vocabulary_hints(
            "find all proteins from organisms",
            self.schema,
            self.ontology
        )

        self.assertIn("classes", hints)
        self.assertGreater(len(hints["classes"]), 0)

    def test_scenario_detection(self):
        """Test automatic scenario detection."""
        # Test aggregation scenario
        context1 = self.generator._build_context(
            natural_language="count the number of proteins",
            schema_info=self.schema,
            ontology_info=None,
            endpoint_info=None,
            strategy=GenerationStrategy.AUTO,
            scenario=None,
            constraints={}
        )
        self.assertEqual(context1.scenario, QueryScenario.AGGREGATION)

        # Test full-text scenario
        context2 = self.generator._build_context(
            natural_language="search for proteins containing cancer",
            schema_info=self.schema,
            ontology_info=None,
            endpoint_info=None,
            strategy=GenerationStrategy.AUTO,
            scenario=None,
            constraints={}
        )
        self.assertEqual(context2.scenario, QueryScenario.FULL_TEXT)

    def test_strategy_selection(self):
        """Test automatic strategy selection."""
        # Simple query should prefer template
        simple_context = GenerationContext(
            natural_language="list all proteins",
            schema_info=self.schema,
            strategy=GenerationStrategy.AUTO
        )
        simple_context.scenario = QueryScenario.BASIC

        # Complex query should prefer LLM (if available)
        complex_context = GenerationContext(
            natural_language="compare protein functions across different organisms",
            schema_info=self.schema,
            strategy=GenerationStrategy.AUTO
        )
        complex_context.scenario = QueryScenario.COMPLEX_JOIN

        selected_simple = self.generator._select_strategy(simple_context)
        selected_complex = self.generator._select_strategy(complex_context)

        # Simple should be template, complex should be template (no LLM available)
        self.assertEqual(selected_simple, GenerationStrategy.TEMPLATE)
        # Without LLM client, defaults to TEMPLATE
        self.assertEqual(selected_complex, GenerationStrategy.TEMPLATE)


class TestSPARQLGeneratorStatistics(unittest.TestCase):
    """Test statistics and monitoring features."""

    def setUp(self):
        self.generator = SPARQLGenerator(enable_validation=False)
        self.schema = SchemaInfo(
            classes={"http://example.org/Test"},
            namespaces={"ex": "http://example.org/"}
        )

    def test_statistics_tracking(self):
        """Test that generation statistics are tracked."""
        initial_stats = self.generator.get_statistics()
        initial_count = initial_stats['total_generated']

        # Generate a query
        self.generator.generate(
            natural_language="list all tests",
            schema_info=self.schema,
            strategy=GenerationStrategy.TEMPLATE
        )

        updated_stats = self.generator.get_statistics()
        self.assertEqual(
            updated_stats['total_generated'],
            initial_count + 1
        )
        self.assertEqual(
            updated_stats['template_used'],
            initial_stats['template_used'] + 1
        )


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""

    def test_create_generator(self):
        """Test create_generator utility."""
        generator = create_generator(enable_validation=True)
        self.assertIsInstance(generator, SPARQLGenerator)
        self.assertTrue(generator.enable_validation)

    def test_quick_generate(self):
        """Test quick_generate utility."""
        schema = SchemaInfo(
            classes={"http://example.org/Person"},
            namespaces={"ex": "http://example.org/"}
        )

        query = quick_generate(
            natural_language="list all persons",
            schema_info=schema
        )

        self.assertIsInstance(query, str)
        self.assertIn("SELECT", query.upper())


# Example usage demonstrations
def demonstrate_basic_usage():
    """Demonstrate basic generator usage."""
    print("=" * 70)
    print("SPARQL Generator - Basic Usage Examples")
    print("=" * 70)

    # Create generator
    generator = create_generator()

    # Create sample schema
    schema = SchemaInfo(
        classes={
            "http://purl.uniprot.org/core/Protein",
            "http://purl.obolibrary.org/obo/GO_0008150"  # GO biological process
        },
        properties={
            "http://purl.uniprot.org/core/organism",
            "http://purl.uniprot.org/core/recommendedName"
        },
        namespaces={
            "up": "http://purl.uniprot.org/core/",
            "obo": "http://purl.obolibrary.org/obo/"
        }
    )

    # Example 1: Simple listing query
    print("\nExample 1: List Query")
    print("-" * 70)
    result1 = generator.generate(
        "list all proteins",
        schema_info=schema,
        strategy=GenerationStrategy.TEMPLATE
    )
    print(f"Query: {result1.query}")
    print(f"Confidence: {result1.confidence}")
    print(f"Strategy: {result1.metadata.get('strategy')}")

    # Example 2: Aggregation query
    print("\nExample 2: Aggregation Query")
    print("-" * 70)
    result2 = generator.generate(
        "how many proteins are there",
        schema_info=schema,
        strategy=GenerationStrategy.TEMPLATE
    )
    print(f"Query: {result2.query}")
    print(f"Confidence: {result2.confidence}")

    # Example 3: With validation
    print("\nExample 3: With Validation")
    print("-" * 70)
    generator_with_validation = SPARQLGenerator(enable_validation=True)
    result3 = generator_with_validation.generate(
        "find proteins from human",
        schema_info=schema,
        strategy=GenerationStrategy.TEMPLATE
    )
    print(f"Query: {result3.query}")
    if 'validation' in result3.metadata:
        validation = result3.metadata['validation']
        print(f"Valid: {validation['is_valid']}")
        print(f"Complexity: {validation['complexity_score']}")
        if validation.get('suggestions'):
            print(f"Suggestions: {validation['suggestions']}")

    # Statistics
    print("\nGeneration Statistics:")
    print("-" * 70)
    stats = generator.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    # Run demonstrations
    demonstrate_basic_usage()

    print("\n" + "=" * 70)
    print("Running Unit Tests")
    print("=" * 70 + "\n")

    # Run unit tests
    unittest.main(argv=[''], verbosity=2, exit=False)
