"""
Performance and load testing framework for sparql-agent.

This package contains comprehensive performance testing including:
- Benchmark tests for query execution, generation, and parsing
- Memory profiling and leak detection
- Concurrency and stress testing
- Load testing for all major components
- Performance regression detection
- Profiling and reporting utilities
"""

__all__ = [
    "conftest",
    "test_query_performance",
    "test_generation_performance",
    "test_parsing_performance",
    "test_memory_usage",
    "test_concurrency",
]
