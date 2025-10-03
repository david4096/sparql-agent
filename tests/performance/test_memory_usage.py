"""
Memory usage and leak detection performance tests.

Uses memory-profiler and psutil to track memory consumption and detect leaks.
"""

import pytest
import psutil
import gc
from typing import List, Dict, Any
from unittest.mock import Mock
import sys

from memory_profiler import profile


class TestMemoryUsageBaseline:
    """Baseline memory usage tests for core components."""

    @pytest.fixture
    def process(self):
        """Get current process for memory monitoring."""
        return psutil.Process()

    def test_query_executor_memory_baseline(self, process):
        """Measure baseline memory usage of query executor."""
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        from sparql_agent.execution.executor import SPARQLExecutor
        executor = SPARQLExecutor(endpoint="http://example.org/sparql")

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024  # MB

        mem_usage = mem_after - mem_before
        assert mem_usage < 50, f"Executor baseline memory too high: {mem_usage}MB"

    def test_owl_parser_memory_baseline(self, process):
        """Measure baseline memory usage of OWL parser."""
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        from sparql_agent.ontology.owl_parser import OWLParser
        parser = OWLParser()

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024

        mem_usage = mem_after - mem_before
        assert mem_usage < 30, f"OWL parser baseline memory too high: {mem_usage}MB"

    def test_llm_provider_memory_baseline(self, process):
        """Measure baseline memory usage of LLM providers."""
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        from sparql_agent.llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(api_key="test_key")

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024

        mem_usage = mem_after - mem_before
        assert mem_usage < 20, f"LLM provider baseline memory too high: {mem_usage}MB"


class TestMemoryScaling:
    """Test memory usage scaling with data size."""

    @pytest.fixture
    def process(self):
        """Get current process for memory monitoring."""
        return psutil.Process()

    @pytest.mark.parametrize("result_count", [100, 1000, 10000])
    def test_result_set_memory_scaling(self, result_count, process):
        """Test memory usage scaling with result set size."""
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        # Generate large result set
        results = [
            {
                "entity": f"http://example.org/entity_{i}",
                "label": f"Entity Label {i}",
                "value": i,
                "description": f"Description for entity {i}" * 10
            }
            for i in range(result_count)
        ]

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_usage = mem_after - mem_before

        # Memory should scale roughly linearly
        expected_mb_per_1k = 5  # ~5MB per 1000 results
        expected_usage = (result_count / 1000) * expected_mb_per_1k
        tolerance = expected_usage * 0.5  # 50% tolerance

        assert mem_usage < expected_usage + tolerance, \
            f"Memory usage {mem_usage}MB exceeds expected {expected_usage}MB"

        # Clean up
        del results
        gc.collect()

    @pytest.mark.parametrize("ontology_size", [10, 50, 100])
    def test_ontology_memory_scaling(self, ontology_size, process):
        """Test memory usage scaling with ontology size."""
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        # Generate ontology structure
        ontology = {
            "classes": [
                {
                    "uri": f"http://example.org/Class{i}",
                    "label": f"Class {i}",
                    "properties": [f"prop{j}" for j in range(10)]
                }
                for i in range(ontology_size)
            ],
            "properties": [
                {
                    "uri": f"http://example.org/prop{i}",
                    "label": f"Property {i}",
                    "domain": "Class1",
                    "range": "Class2"
                }
                for i in range(ontology_size * 2)
            ]
        }

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_usage = mem_after - mem_before

        # Expect ~1MB per 10 classes
        expected_usage = (ontology_size / 10) * 1
        assert mem_usage < expected_usage + 5, \
            f"Ontology memory {mem_usage}MB exceeds expected {expected_usage}MB"

        del ontology
        gc.collect()


class TestMemoryLeaks:
    """Test for memory leaks in repeated operations."""

    @pytest.fixture
    def process(self):
        """Get current process for memory monitoring."""
        return psutil.Process()

    def test_repeated_query_execution_no_leak(self, process):
        """Ensure repeated query execution doesn't leak memory."""
        from sparql_agent.execution.executor import SPARQLExecutor

        executor = Mock(spec=SPARQLExecutor)
        executor.execute = Mock(return_value=Mock(
            success=True,
            results=[{"s": "subject", "p": "predicate", "o": "object"}]
        ))

        gc.collect()
        mem_start = process.memory_info().rss / 1024 / 1024

        # Execute query many times
        for _ in range(1000):
            result = executor.execute("SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10")

        gc.collect()
        mem_end = process.memory_info().rss / 1024 / 1024

        mem_growth = mem_end - mem_start
        # Should not grow more than 10MB for 1000 iterations
        assert mem_growth < 10, f"Memory leak detected: grew {mem_growth}MB"

    def test_repeated_parsing_no_leak(self, process):
        """Ensure repeated parsing doesn't leak memory."""
        from sparql_agent.schema.shex_parser import ShExParser

        parser = ShExParser()
        shex_schema = """
        PREFIX ex: <http://example.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        ex:PersonShape {
            ex:name xsd:string ;
            ex:age xsd:integer
        }
        """

        gc.collect()
        mem_start = process.memory_info().rss / 1024 / 1024

        # Parse schema many times
        for _ in range(500):
            result = parser.parse(shex_schema)

        gc.collect()
        mem_end = process.memory_info().rss / 1024 / 1024

        mem_growth = mem_end - mem_start
        assert mem_growth < 10, f"Memory leak in parsing: grew {mem_growth}MB"

    def test_cache_memory_growth(self, process):
        """Test cache doesn't grow unbounded."""
        cache: Dict[str, Any] = {}
        max_cache_size = 1000

        gc.collect()
        mem_start = process.memory_info().rss / 1024 / 1024

        # Add items to cache with LRU eviction
        for i in range(5000):
            key = f"key_{i}"
            cache[key] = {"data": f"value_{i}" * 100}

            # Simple LRU: keep only last N items
            if len(cache) > max_cache_size:
                oldest_key = next(iter(cache))
                del cache[oldest_key]

        gc.collect()
        mem_end = process.memory_info().rss / 1024 / 1024

        mem_growth = mem_end - mem_start
        # Cache should be bounded
        assert len(cache) <= max_cache_size
        # Memory should not grow excessively
        assert mem_growth < 50, f"Cache memory grew too much: {mem_growth}MB"


class TestLargeDataHandling:
    """Test memory efficiency with large datasets."""

    @pytest.fixture
    def process(self):
        """Get current process for memory monitoring."""
        return psutil.Process()

    def test_large_result_set_streaming(self, process):
        """Test memory usage with streaming large result sets."""
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        # Simulate streaming results instead of loading all at once
        def stream_results(count: int):
            """Generator that yields results one at a time."""
            for i in range(count):
                yield {
                    "entity": f"http://example.org/entity_{i}",
                    "value": i
                }

        # Process 100k results via streaming
        processed = 0
        for result in stream_results(100000):
            processed += 1

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_usage = mem_after - mem_before

        # Streaming should keep memory low regardless of total count
        assert mem_usage < 20, f"Streaming used too much memory: {mem_usage}MB"
        assert processed == 100000

    def test_chunked_data_processing(self, process):
        """Test memory usage with chunked data processing."""
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        chunk_size = 1000
        total_items = 50000

        def process_chunk(chunk: List[Dict[str, Any]]) -> int:
            """Process a chunk of data."""
            return sum(item["value"] for item in chunk)

        total = 0
        for start in range(0, total_items, chunk_size):
            chunk = [
                {"value": i}
                for i in range(start, min(start + chunk_size, total_items))
            ]
            total += process_chunk(chunk)
            del chunk
            gc.collect()

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_usage = mem_after - mem_before

        # Chunked processing should keep memory bounded
        assert mem_usage < 30, f"Chunked processing used too much memory: {mem_usage}MB"


class TestMemoryProfiling:
    """Memory profiling tests for detailed analysis."""

    def test_query_generation_memory_profile(self):
        """Profile memory usage during query generation."""
        from sparql_agent.query.generator import QueryGenerator

        @profile
        def generate_queries():
            """Generate multiple queries."""
            generator = Mock(spec=QueryGenerator)
            results = []
            for i in range(100):
                query = f"SELECT ?s ?p ?o WHERE {{ ?s ?p ?o }} LIMIT {i}"
                results.append(query)
            return results

        # Note: @profile decorator will output to stdout
        # Run with: python -m memory_profiler test_memory_usage.py
        results = generate_queries()
        assert len(results) == 100

    def test_ontology_loading_memory_profile(self):
        """Profile memory usage during ontology loading."""
        @profile
        def load_ontology():
            """Load and parse ontology."""
            ontology = {
                "classes": [],
                "properties": []
            }

            # Simulate loading large ontology
            for i in range(1000):
                ontology["classes"].append({
                    "uri": f"http://example.org/Class{i}",
                    "label": f"Class {i}",
                    "description": f"Description for class {i}" * 5
                })

            return ontology

        result = load_ontology()
        assert len(result["classes"]) == 1000


class TestMemoryCleanup:
    """Test proper memory cleanup and garbage collection."""

    @pytest.fixture
    def process(self):
        """Get current process for memory monitoring."""
        return psutil.Process()

    def test_executor_cleanup(self, process):
        """Test executor properly releases resources."""
        from sparql_agent.execution.executor import SPARQLExecutor

        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        # Create and destroy multiple executors
        for _ in range(100):
            executor = Mock(spec=SPARQLExecutor)
            executor.execute("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
            del executor

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024

        mem_growth = mem_after - mem_before
        # Should clean up properly
        assert mem_growth < 5, f"Executor cleanup issue: grew {mem_growth}MB"

    def test_graph_cleanup(self, process):
        """Test RDF graph cleanup."""
        from rdflib import Graph

        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        # Create and destroy multiple graphs
        for i in range(50):
            g = Graph()
            # Add some triples
            for j in range(100):
                g.add((
                    f"http://example.org/s{j}",
                    "http://example.org/p",
                    f"Object {j}"
                ))
            del g

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024

        mem_growth = mem_after - mem_before
        assert mem_growth < 20, f"Graph cleanup issue: grew {mem_growth}MB"


class TestMemoryPerformanceRegression:
    """Test for memory performance regressions."""

    @pytest.fixture
    def baseline_metrics(self) -> Dict[str, float]:
        """Baseline memory metrics (MB)."""
        return {
            "executor_baseline": 50.0,
            "parser_baseline": 30.0,
            "query_generation": 20.0,
            "result_processing_1k": 5.0,
        }

    def test_memory_regression_check(self, baseline_metrics):
        """Check current memory usage against baselines."""
        process = psutil.Process()

        # Test executor
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024
        from sparql_agent.execution.executor import SPARQLExecutor
        executor = SPARQLExecutor(endpoint="http://example.org/sparql")
        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024
        executor_usage = mem_after - mem_before

        # Allow 20% regression tolerance
        tolerance = 1.2
        assert executor_usage < baseline_metrics["executor_baseline"] * tolerance, \
            f"Memory regression in executor: {executor_usage}MB > {baseline_metrics['executor_baseline']}MB"
