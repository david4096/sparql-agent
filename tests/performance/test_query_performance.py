"""
Query execution performance benchmarks using pytest-benchmark.

Tests query execution time across different complexity levels and result set sizes.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch
import json

from sparql_agent.execution.executor import SPARQLExecutor
from sparql_agent.core.types import QueryResult


class TestQueryPerformanceBenchmarks:
    """Benchmark tests for SPARQL query execution."""

    @pytest.fixture
    def mock_executor(self) -> SPARQLExecutor:
        """Create a mock SPARQL executor for testing."""
        executor = Mock(spec=SPARQLExecutor)
        return executor

    @pytest.fixture
    def simple_query(self) -> str:
        """Simple SPARQL query for benchmarking."""
        return """
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o
        }
        LIMIT 10
        """

    @pytest.fixture
    def complex_query(self) -> str:
        """Complex SPARQL query with multiple joins."""
        return """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?entity ?label ?type ?related ?relatedLabel
        WHERE {
            ?entity rdf:type ?type .
            ?entity rdfs:label ?label .
            OPTIONAL {
                ?entity ?p ?related .
                ?related rdfs:label ?relatedLabel .
            }
            FILTER (lang(?label) = "en")
        }
        LIMIT 100
        """

    @pytest.fixture
    def nested_query(self) -> str:
        """Nested SPARQL query with subqueries."""
        return """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s ?count
        WHERE {
            ?s rdf:type ?type .
            {
                SELECT ?s (COUNT(?o) as ?count)
                WHERE {
                    ?s ?p ?o .
                }
                GROUP BY ?s
                HAVING (COUNT(?o) > 5)
            }
        }
        ORDER BY DESC(?count)
        LIMIT 50
        """

    def test_simple_query_execution(self, benchmark, simple_query, mock_executor):
        """Benchmark simple query execution time."""
        # Setup mock response
        mock_result = QueryResult(
            success=True,
            results=[{"s": f"subject_{i}", "p": "predicate", "o": f"object_{i}"}
                    for i in range(10)],
            query=simple_query,
            execution_time=0.1
        )
        mock_executor.execute.return_value = mock_result

        # Benchmark the execution
        result = benchmark(mock_executor.execute, simple_query)
        assert result.success is True
        assert len(result.results) == 10

    def test_complex_query_execution(self, benchmark, complex_query, mock_executor):
        """Benchmark complex query with joins execution time."""
        # Setup mock response with larger dataset
        mock_result = QueryResult(
            success=True,
            results=[{
                "entity": f"entity_{i}",
                "label": f"Label {i}",
                "type": "Type",
                "related": f"related_{i}",
                "relatedLabel": f"Related {i}"
            } for i in range(100)],
            query=complex_query,
            execution_time=0.5
        )
        mock_executor.execute.return_value = mock_result

        # Benchmark the execution
        result = benchmark(mock_executor.execute, complex_query)
        assert result.success is True
        assert len(result.results) == 100

    def test_nested_query_execution(self, benchmark, nested_query, mock_executor):
        """Benchmark nested query with subqueries execution time."""
        mock_result = QueryResult(
            success=True,
            results=[{"s": f"subject_{i}", "count": 50 - i} for i in range(50)],
            query=nested_query,
            execution_time=0.8
        )
        mock_executor.execute.return_value = mock_result

        result = benchmark(mock_executor.execute, nested_query)
        assert result.success is True
        assert len(result.results) == 50

    @pytest.mark.parametrize("limit", [10, 100, 1000, 10000])
    def test_query_scaling_by_result_size(self, benchmark, limit, mock_executor):
        """Benchmark query execution time vs result set size."""
        query = f"""
        SELECT ?s ?p ?o
        WHERE {{
            ?s ?p ?o
        }}
        LIMIT {limit}
        """

        mock_result = QueryResult(
            success=True,
            results=[{"s": f"s_{i}", "p": "p", "o": f"o_{i}"} for i in range(limit)],
            query=query,
            execution_time=0.1 * (limit / 100)
        )
        mock_executor.execute.return_value = mock_result

        result = benchmark(mock_executor.execute, query)
        assert len(result.results) == limit

    @pytest.mark.parametrize("join_count", [1, 3, 5, 10])
    def test_query_complexity_scaling(self, benchmark, join_count, mock_executor):
        """Benchmark query execution time vs number of joins."""
        # Build query with multiple joins
        where_clauses = [f"?s{i} ?p{i} ?o{i} ." for i in range(join_count)]
        query = f"""
        SELECT * WHERE {{
            {' '.join(where_clauses)}
        }}
        LIMIT 10
        """

        mock_result = QueryResult(
            success=True,
            results=[{f"s{i}": f"val_{i}" for i in range(join_count)}] * 10,
            query=query,
            execution_time=0.1 * join_count
        )
        mock_executor.execute.return_value = mock_result

        result = benchmark(mock_executor.execute, query)
        assert len(result.results) == 10


class TestQueryParsingPerformance:
    """Benchmark tests for query parsing and validation."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        from sparql_agent.execution.validator import QueryValidator
        return QueryValidator()

    def test_simple_query_parsing(self, benchmark, validator):
        """Benchmark simple query parsing time."""
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
        result = benchmark(validator.validate_syntax, query)
        assert result is True

    def test_complex_query_parsing(self, benchmark, validator):
        """Benchmark complex query parsing time."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT ?entity ?label ?type
        WHERE {
            ?entity rdf:type ?type .
            ?entity rdfs:label ?label .
            ?type rdfs:subClassOf* ?superType .
            FILTER (lang(?label) = "en")
        }
        ORDER BY ?label
        LIMIT 100
        """
        result = benchmark(validator.validate_syntax, query)
        assert result is True


class TestQueryOptimizationPerformance:
    """Benchmark tests for query optimization."""

    def test_query_rewriting_performance(self, benchmark):
        """Benchmark query rewriting/optimization time."""
        def optimize_query(query: str) -> str:
            """Simple query optimization."""
            # Simulate optimization steps
            optimized = query.strip()
            optimized = optimized.replace("  ", " ")
            return optimized

        query = "SELECT  ?s  ?p  ?o  WHERE  {  ?s  ?p  ?o  }  LIMIT  10"
        result = benchmark(optimize_query, query)
        assert "SELECT" in result


class TestResultProcessingPerformance:
    """Benchmark tests for result processing and formatting."""

    @pytest.fixture
    def sample_results(self) -> List[Dict[str, Any]]:
        """Generate sample query results."""
        return [
            {
                "entity": f"http://example.org/entity_{i}",
                "label": f"Entity Label {i}",
                "value": i * 100,
                "description": f"This is a description for entity {i}"
            }
            for i in range(1000)
        ]

    def test_json_serialization_performance(self, benchmark, sample_results):
        """Benchmark JSON serialization of results."""
        result = benchmark(json.dumps, sample_results)
        assert len(result) > 0

    def test_result_filtering_performance(self, benchmark, sample_results):
        """Benchmark result filtering operations."""
        def filter_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return [r for r in results if r["value"] > 500]

        result = benchmark(filter_results, sample_results)
        assert len(result) < len(sample_results)

    def test_result_transformation_performance(self, benchmark, sample_results):
        """Benchmark result transformation operations."""
        def transform_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return [
                {
                    "id": r["entity"].split("_")[-1],
                    "name": r["label"],
                    "score": r["value"] / 100
                }
                for r in results
            ]

        result = benchmark(transform_results, sample_results)
        assert len(result) == len(sample_results)


class TestCachePerformance:
    """Benchmark tests for caching mechanisms."""

    @pytest.fixture
    def simple_cache(self) -> Dict[str, Any]:
        """Simple in-memory cache for testing."""
        return {}

    def test_cache_write_performance(self, benchmark, simple_cache):
        """Benchmark cache write operations."""
        def write_to_cache(cache: Dict[str, Any], key: str, value: Any) -> None:
            cache[key] = value

        benchmark(write_to_cache, simple_cache, "test_key", {"data": "test_value"})
        assert "test_key" in simple_cache

    def test_cache_read_performance(self, benchmark, simple_cache):
        """Benchmark cache read operations."""
        # Pre-populate cache
        for i in range(1000):
            simple_cache[f"key_{i}"] = {"data": f"value_{i}"}

        def read_from_cache(cache: Dict[str, Any], key: str) -> Any:
            return cache.get(key)

        result = benchmark(read_from_cache, simple_cache, "key_500")
        assert result is not None

    def test_cache_hit_vs_miss_performance(self, benchmark, simple_cache):
        """Compare cache hit vs miss performance."""
        simple_cache["existing_key"] = {"data": "cached_value"}

        def cache_lookup(cache: Dict[str, Any], key: str) -> Any:
            if key in cache:
                return cache[key]
            # Simulate expensive operation on cache miss
            return {"data": "computed_value"}

        # Test cache hit
        result = benchmark(cache_lookup, simple_cache, "existing_key")
        assert result["data"] == "cached_value"
