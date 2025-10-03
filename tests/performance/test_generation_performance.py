"""
LLM query generation performance benchmarks.

Tests performance of SPARQL query generation from natural language using LLMs.
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
import time

from sparql_agent.query.generator import QueryGenerator
from sparql_agent.query.prompt_engine import PromptEngine
from sparql_agent.llm.anthropic_provider import AnthropicProvider
from sparql_agent.llm.openai_provider import OpenAIProvider


class TestLLMGenerationPerformance:
    """Benchmark tests for LLM query generation."""

    @pytest.fixture
    def mock_anthropic_provider(self) -> AnthropicProvider:
        """Create mock Anthropic provider."""
        provider = Mock(spec=AnthropicProvider)
        provider.generate_query = AsyncMock(return_value={
            "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
            "explanation": "Simple triple pattern query",
            "confidence": 0.95
        })
        return provider

    @pytest.fixture
    def mock_openai_provider(self) -> OpenAIProvider:
        """Create mock OpenAI provider."""
        provider = Mock(spec=OpenAIProvider)
        provider.generate_query = AsyncMock(return_value={
            "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
            "explanation": "Simple triple pattern query",
            "confidence": 0.95
        })
        return provider

    @pytest.fixture
    def prompt_engine(self) -> PromptEngine:
        """Create prompt engine instance."""
        return PromptEngine()

    @pytest.fixture
    def sample_schema(self) -> Dict[str, Any]:
        """Sample schema for query generation."""
        return {
            "classes": [
                {"uri": "http://example.org/Person", "label": "Person"},
                {"uri": "http://example.org/Organization", "label": "Organization"},
            ],
            "properties": [
                {"uri": "http://example.org/name", "label": "name"},
                {"uri": "http://example.org/worksFor", "label": "works for"},
            ]
        }

    def test_simple_query_generation(self, benchmark, mock_anthropic_provider, sample_schema):
        """Benchmark simple query generation from natural language."""
        async def generate():
            return await mock_anthropic_provider.generate_query(
                "Find all people",
                schema=sample_schema
            )

        result = benchmark(asyncio.run, generate())
        assert "query" in result

    def test_complex_query_generation(self, benchmark, mock_anthropic_provider, sample_schema):
        """Benchmark complex query generation with multiple constraints."""
        async def generate():
            return await mock_anthropic_provider.generate_query(
                "Find all people who work for organizations in New York and have published more than 5 papers",
                schema=sample_schema
            )

        result = benchmark(asyncio.run, generate())
        assert "query" in result

    @pytest.mark.parametrize("provider_type", ["anthropic", "openai"])
    def test_provider_comparison(self, benchmark, provider_type, sample_schema):
        """Compare performance across different LLM providers."""
        if provider_type == "anthropic":
            provider = Mock(spec=AnthropicProvider)
        else:
            provider = Mock(spec=OpenAIProvider)

        provider.generate_query = AsyncMock(return_value={
            "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
            "explanation": "Test query",
            "confidence": 0.9
        })

        async def generate():
            return await provider.generate_query("Test query", schema=sample_schema)

        result = benchmark(asyncio.run, generate())
        assert "query" in result


class TestPromptEngineeringPerformance:
    """Benchmark tests for prompt engineering and optimization."""

    @pytest.fixture
    def prompt_engine(self) -> PromptEngine:
        """Create prompt engine instance."""
        return PromptEngine()

    def test_prompt_construction_simple(self, benchmark, prompt_engine):
        """Benchmark simple prompt construction."""
        result = benchmark(
            prompt_engine.build_query_prompt,
            question="Find all entities",
            schema={"classes": [], "properties": []}
        )
        assert len(result) > 0

    def test_prompt_construction_with_examples(self, benchmark, prompt_engine):
        """Benchmark prompt construction with few-shot examples."""
        examples = [
            {
                "question": "Find all people",
                "query": "SELECT ?person WHERE { ?person a :Person }"
            },
            {
                "question": "Find organizations",
                "query": "SELECT ?org WHERE { ?org a :Organization }"
            }
        ]

        result = benchmark(
            prompt_engine.build_query_prompt,
            question="Find all universities",
            schema={"classes": [], "properties": []},
            examples=examples
        )
        assert len(result) > 0

    def test_prompt_construction_with_large_schema(self, benchmark, prompt_engine):
        """Benchmark prompt construction with large schema."""
        large_schema = {
            "classes": [
                {"uri": f"http://example.org/Class{i}", "label": f"Class {i}"}
                for i in range(100)
            ],
            "properties": [
                {"uri": f"http://example.org/prop{i}", "label": f"Property {i}"}
                for i in range(200)
            ]
        }

        result = benchmark(
            prompt_engine.build_query_prompt,
            question="Find all entities",
            schema=large_schema
        )
        assert len(result) > 0


class TestQueryRefinementPerformance:
    """Benchmark tests for iterative query refinement."""

    @pytest.fixture
    def mock_generator(self) -> QueryGenerator:
        """Create mock query generator."""
        generator = Mock(spec=QueryGenerator)
        generator.refine_query = AsyncMock(return_value={
            "query": "REFINED QUERY",
            "improvements": ["Added FILTER", "Optimized JOIN"],
            "confidence": 0.98
        })
        return generator

    def test_single_refinement_iteration(self, benchmark, mock_generator):
        """Benchmark single query refinement iteration."""
        initial_query = "SELECT ?s WHERE { ?s ?p ?o }"
        feedback = "Add filters for better results"

        async def refine():
            return await mock_generator.refine_query(initial_query, feedback)

        result = benchmark(asyncio.run, refine())
        assert "query" in result

    def test_multiple_refinement_iterations(self, benchmark, mock_generator):
        """Benchmark multiple refinement iterations."""
        async def multi_refine():
            query = "SELECT ?s WHERE { ?s ?p ?o }"
            for i in range(3):
                result = await mock_generator.refine_query(
                    query,
                    f"Refinement iteration {i}"
                )
                query = result["query"]
            return result

        result = benchmark(asyncio.run, multi_refine())
        assert "query" in result


class TestBatchGenerationPerformance:
    """Benchmark tests for batch query generation."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider for batch generation."""
        provider = Mock()
        provider.generate_query = AsyncMock(return_value={
            "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o }",
            "confidence": 0.9
        })
        return provider

    def test_sequential_batch_generation(self, benchmark, mock_provider):
        """Benchmark sequential batch query generation."""
        questions = [
            "Find all people",
            "Find all organizations",
            "Find all publications",
            "Find all locations",
            "Find all events"
        ]

        async def generate_batch_sequential():
            results = []
            for question in questions:
                result = await mock_provider.generate_query(question)
                results.append(result)
            return results

        results = benchmark(asyncio.run, generate_batch_sequential())
        assert len(results) == len(questions)

    def test_parallel_batch_generation(self, benchmark, mock_provider):
        """Benchmark parallel batch query generation."""
        questions = [
            "Find all people",
            "Find all organizations",
            "Find all publications",
            "Find all locations",
            "Find all events"
        ]

        async def generate_batch_parallel():
            tasks = [
                mock_provider.generate_query(question)
                for question in questions
            ]
            return await asyncio.gather(*tasks)

        results = benchmark(asyncio.run, generate_batch_parallel())
        assert len(results) == len(questions)


class TestTokenUsageOptimization:
    """Benchmark tests for token usage optimization."""

    def test_schema_compression_performance(self, benchmark):
        """Benchmark schema compression for token efficiency."""
        large_schema = {
            "classes": [
                {
                    "uri": f"http://example.org/LongClassName{i}",
                    "label": f"Very Long Class Label {i}",
                    "description": f"This is a very detailed description for class {i}"
                }
                for i in range(50)
            ]
        }

        def compress_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
            """Compress schema to reduce token count."""
            compressed = {"classes": []}
            for cls in schema["classes"]:
                compressed["classes"].append({
                    "uri": cls["uri"].split("/")[-1],  # Shorten URI
                    "label": cls["label"][:20]  # Truncate label
                })
            return compressed

        result = benchmark(compress_schema, large_schema)
        assert len(result["classes"]) == len(large_schema["classes"])

    def test_prompt_optimization_performance(self, benchmark):
        """Benchmark prompt optimization to reduce tokens."""
        verbose_prompt = """
        You are a highly sophisticated SPARQL query generation assistant.
        Given the following comprehensive schema information and the user's
        detailed natural language question, please generate an optimized
        SPARQL query that accurately retrieves the requested information.
        """

        def optimize_prompt(prompt: str) -> str:
            """Optimize prompt to reduce token count."""
            # Remove extra whitespace
            optimized = " ".join(prompt.split())
            # Shorten common phrases
            replacements = {
                "highly sophisticated": "advanced",
                "comprehensive": "complete",
                "detailed natural language": "natural language",
                "accurately retrieves": "retrieves"
            }
            for old, new in replacements.items():
                optimized = optimized.replace(old, new)
            return optimized

        result = benchmark(optimize_prompt, verbose_prompt)
        assert len(result) < len(verbose_prompt)


class TestResponseParsingPerformance:
    """Benchmark tests for LLM response parsing."""

    @pytest.fixture
    def sample_llm_response(self) -> str:
        """Sample LLM response with query and explanation."""
        return """
        Here is the SPARQL query:

        ```sparql
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?person ?name
        WHERE {
            ?person rdf:type :Person .
            ?person :name ?name .
        }
        LIMIT 100
        ```

        This query finds all people and their names.
        The results are limited to 100 for performance.
        """

    def test_query_extraction_performance(self, benchmark, sample_llm_response):
        """Benchmark query extraction from LLM response."""
        import re

        def extract_query(response: str) -> str:
            """Extract SPARQL query from LLM response."""
            pattern = r"```sparql\n(.*?)\n```"
            match = re.search(pattern, response, re.DOTALL)
            return match.group(1) if match else ""

        result = benchmark(extract_query, sample_llm_response)
        assert "SELECT" in result

    def test_explanation_extraction_performance(self, benchmark, sample_llm_response):
        """Benchmark explanation extraction from LLM response."""
        def extract_explanation(response: str) -> str:
            """Extract explanation from LLM response."""
            lines = response.strip().split("\n")
            explanation_lines = []
            in_code_block = False

            for line in lines:
                if "```" in line:
                    in_code_block = not in_code_block
                elif not in_code_block and line.strip():
                    explanation_lines.append(line.strip())

            return " ".join(explanation_lines)

        result = benchmark(extract_explanation, sample_llm_response)
        assert len(result) > 0
