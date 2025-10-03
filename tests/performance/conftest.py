"""
Performance testing fixtures and utilities.

Provides common fixtures, utilities, and configuration for performance tests.
"""

import pytest
import psutil
import gc
import time
import json
import os
from typing import Dict, Any, List, Callable
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
from memory_profiler import profile


# Performance test configuration
PERFORMANCE_CONFIG = {
    "baseline_metrics": {
        "query_execution_ms": 100,
        "llm_generation_ms": 2000,
        "parsing_ms": 50,
        "memory_baseline_mb": 50,
    },
    "thresholds": {
        "max_query_time_ms": 500,
        "max_generation_time_ms": 5000,
        "max_parsing_time_ms": 200,
        "max_memory_mb": 200,
    },
    "load_test": {
        "users": 10,
        "spawn_rate": 1,
        "duration": "1m",
    }
}


@pytest.fixture(scope="session")
def performance_config() -> Dict[str, Any]:
    """Provide performance test configuration."""
    return PERFORMANCE_CONFIG


@pytest.fixture
def process():
    """Get current process for memory monitoring."""
    return psutil.Process()


@pytest.fixture
def memory_tracker(process):
    """Track memory usage during test execution."""
    class MemoryTracker:
        def __init__(self, proc):
            self.process = proc
            self.start_memory = None
            self.peak_memory = None
            self.measurements = []

        def start(self):
            """Start memory tracking."""
            gc.collect()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024
            self.peak_memory = self.start_memory
            self.measurements = [self.start_memory]

        def measure(self) -> float:
            """Take a memory measurement."""
            current = self.process.memory_info().rss / 1024 / 1024
            self.measurements.append(current)
            self.peak_memory = max(self.peak_memory, current)
            return current

        def stop(self) -> Dict[str, float]:
            """Stop tracking and return statistics."""
            gc.collect()
            end_memory = self.process.memory_info().rss / 1024 / 1024
            return {
                "start_mb": self.start_memory,
                "end_mb": end_memory,
                "peak_mb": self.peak_memory,
                "growth_mb": end_memory - self.start_memory,
                "measurements": self.measurements
            }

    tracker = MemoryTracker(process)
    tracker.start()
    yield tracker
    stats = tracker.stop()
    print(f"\nMemory Stats: Start={stats['start_mb']:.2f}MB, "
          f"End={stats['end_mb']:.2f}MB, Peak={stats['peak_mb']:.2f}MB, "
          f"Growth={stats['growth_mb']:.2f}MB")


@pytest.fixture
def timer():
    """Simple timer for performance measurements."""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed_time = None

        def start(self):
            """Start the timer."""
            self.start_time = time.perf_counter()

        def stop(self) -> float:
            """Stop timer and return elapsed time in seconds."""
            if self.start_time is None:
                raise RuntimeError("Timer not started")
            self.elapsed_time = time.perf_counter() - self.start_time
            return self.elapsed_time

        def elapsed_ms(self) -> float:
            """Get elapsed time in milliseconds."""
            return self.elapsed_time * 1000 if self.elapsed_time else 0

    return Timer()


@pytest.fixture
def performance_logger(tmp_path):
    """Logger for performance metrics."""
    class PerformanceLogger:
        def __init__(self, log_dir):
            self.log_dir = Path(log_dir)
            self.metrics = []

        def log_metric(self, test_name: str, metric_name: str,
                      value: float, unit: str = "ms"):
            """Log a performance metric."""
            self.metrics.append({
                "timestamp": time.time(),
                "test": test_name,
                "metric": metric_name,
                "value": value,
                "unit": unit
            })

        def save(self, filename: str = "performance_metrics.json"):
            """Save metrics to file."""
            output_file = self.log_dir / filename
            with open(output_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
            return output_file

        def to_dataframe(self) -> pd.DataFrame:
            """Convert metrics to pandas DataFrame."""
            return pd.DataFrame(self.metrics)

    return PerformanceLogger(tmp_path)


@pytest.fixture
def baseline_metrics(tmp_path):
    """Load or create baseline performance metrics."""
    baseline_file = Path("tests/performance/benchmarks/baseline.json")

    if baseline_file.exists():
        with open(baseline_file, 'r') as f:
            return json.load(f)
    else:
        # Create default baseline
        return PERFORMANCE_CONFIG["baseline_metrics"]


@pytest.fixture
def performance_threshold_checker(baseline_metrics):
    """Check if performance metrics are within acceptable thresholds."""
    class ThresholdChecker:
        def __init__(self, baselines):
            self.baselines = baselines

        def check(self, metric_name: str, value: float,
                 tolerance: float = 0.2) -> bool:
            """
            Check if metric is within tolerance of baseline.

            Args:
                metric_name: Name of the metric
                value: Current value
                tolerance: Acceptable deviation (default 20%)

            Returns:
                True if within threshold, False otherwise
            """
            if metric_name not in self.baselines:
                # No baseline, consider it passing
                return True

            baseline = self.baselines[metric_name]
            max_allowed = baseline * (1 + tolerance)
            return value <= max_allowed

        def assert_threshold(self, metric_name: str, value: float,
                           tolerance: float = 0.2):
            """Assert that metric is within threshold."""
            if not self.check(metric_name, value, tolerance):
                baseline = self.baselines.get(metric_name, 0)
                max_allowed = baseline * (1 + tolerance)
                raise AssertionError(
                    f"Performance regression detected for {metric_name}: "
                    f"{value} > {max_allowed} (baseline={baseline}, "
                    f"tolerance={tolerance*100}%)"
                )

    return ThresholdChecker(baseline_metrics)


@pytest.fixture
def mock_sparql_endpoint():
    """Create mock SPARQL endpoint for testing."""
    mock = Mock()
    mock.query = Mock(return_value={
        "results": {
            "bindings": [
                {"s": {"value": "subject"}, "p": {"value": "predicate"},
                 "o": {"value": "object"}}
            ]
        }
    })
    return mock


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider for testing."""
    from unittest.mock import AsyncMock

    mock = Mock()
    mock.generate_query = AsyncMock(return_value={
        "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
        "explanation": "Simple triple pattern query",
        "confidence": 0.95,
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    })
    return mock


@pytest.fixture
def sample_queries():
    """Provide sample queries for testing."""
    return {
        "simple": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
        "filtered": """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?entity ?label
            WHERE {
                ?entity rdf:type ?type .
                ?entity rdfs:label ?label .
                FILTER (lang(?label) = "en")
            }
            LIMIT 50
        """,
        "complex": """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT DISTINCT ?entity ?label ?type (COUNT(?related) as ?count)
            WHERE {
                ?entity rdf:type ?type .
                ?entity rdfs:label ?label .
                ?entity ?p ?related .
                FILTER (lang(?label) = "en")
            }
            GROUP BY ?entity ?label ?type
            HAVING (COUNT(?related) > 5)
            ORDER BY DESC(?count)
            LIMIT 50
        """
    }


@pytest.fixture
def sample_natural_language_questions():
    """Provide sample natural language questions."""
    return [
        "Find all people",
        "List organizations in California",
        "Show publications from 2023",
        "What proteins are associated with cancer?",
        "Find genes related to diabetes",
    ]


@pytest.fixture
def sample_schema():
    """Provide sample schema for testing."""
    return {
        "classes": [
            {"uri": "http://example.org/Person", "label": "Person"},
            {"uri": "http://example.org/Organization", "label": "Organization"},
            {"uri": "http://example.org/Publication", "label": "Publication"},
        ],
        "properties": [
            {"uri": "http://example.org/name", "label": "name"},
            {"uri": "http://example.org/worksFor", "label": "works for"},
            {"uri": "http://example.org/published", "label": "published"},
        ]
    }


@pytest.fixture
def benchmark_result_saver(tmp_path):
    """Save benchmark results for comparison."""
    class BenchmarkSaver:
        def __init__(self, output_dir):
            self.output_dir = Path(output_dir)
            self.results = {}

        def save_result(self, test_name: str, stats: Dict[str, Any]):
            """Save benchmark result."""
            self.results[test_name] = {
                "min": stats.get("min", 0),
                "max": stats.get("max", 0),
                "mean": stats.get("mean", 0),
                "median": stats.get("median", 0),
                "stddev": stats.get("stddev", 0),
                "rounds": stats.get("rounds", 0),
            }

        def save_all(self, filename: str = "benchmark_results.json"):
            """Save all results to file."""
            output_file = self.output_dir / filename
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            return output_file

    return BenchmarkSaver(tmp_path)


@pytest.fixture
def load_test_config():
    """Configuration for load tests."""
    return {
        "host": os.getenv("LOAD_TEST_HOST", "http://localhost:8000"),
        "users": int(os.getenv("LOAD_TEST_USERS", "10")),
        "spawn_rate": int(os.getenv("LOAD_TEST_SPAWN_RATE", "1")),
        "duration": os.getenv("LOAD_TEST_DURATION", "60s"),
    }


@pytest.fixture
def profiler_decorator():
    """Provide memory_profiler decorator for tests."""
    return profile


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "benchmark: mark test as benchmark test"
    )
    config.addinivalue_line(
        "markers", "load_test: mark test as load test"
    )
    config.addinivalue_line(
        "markers", "memory_test: mark test as memory profiling test"
    )
    config.addinivalue_line(
        "markers", "concurrency_test: mark test as concurrency test"
    )


def pytest_benchmark_update_json(config, benchmarks, output_json):
    """Customize benchmark JSON output."""
    # Add timestamp
    output_json["timestamp"] = time.time()

    # Add system information
    output_json["system"] = {
        "cpu_count": psutil.cpu_count(),
        "memory_total_mb": psutil.virtual_memory().total / 1024 / 1024,
        "python_version": os.sys.version,
    }


@pytest.fixture
def regression_detector(baseline_metrics):
    """Detect performance regressions."""
    class RegressionDetector:
        def __init__(self, baselines):
            self.baselines = baselines
            self.regressions = []

        def compare(self, metric_name: str, current_value: float,
                   threshold: float = 1.2) -> bool:
            """
            Compare current value with baseline.

            Returns True if regression detected (current > baseline * threshold).
            """
            if metric_name not in self.baselines:
                return False

            baseline = self.baselines[metric_name]
            is_regression = current_value > (baseline * threshold)

            if is_regression:
                self.regressions.append({
                    "metric": metric_name,
                    "baseline": baseline,
                    "current": current_value,
                    "increase_pct": ((current_value - baseline) / baseline) * 100
                })

            return is_regression

        def get_regressions(self) -> List[Dict[str, Any]]:
            """Get all detected regressions."""
            return self.regressions

        def print_report(self):
            """Print regression report."""
            if not self.regressions:
                print("\nNo performance regressions detected.")
                return

            print("\nPerformance Regressions Detected:")
            print("=" * 80)
            for reg in self.regressions:
                print(f"Metric: {reg['metric']}")
                print(f"  Baseline: {reg['baseline']:.2f}")
                print(f"  Current:  {reg['current']:.2f}")
                print(f"  Increase: {reg['increase_pct']:.1f}%")
                print("-" * 80)

    return RegressionDetector(baseline_metrics)


# Utility functions
def measure_execution_time(func: Callable, *args, **kwargs) -> tuple:
    """
    Measure execution time of a function.

    Returns: (result, elapsed_time_seconds)
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def measure_memory_usage(func: Callable, *args, **kwargs) -> tuple:
    """
    Measure memory usage of a function.

    Returns: (result, memory_used_mb)
    """
    process = psutil.Process()
    gc.collect()
    mem_before = process.memory_info().rss / 1024 / 1024

    result = func(*args, **kwargs)

    gc.collect()
    mem_after = process.memory_info().rss / 1024 / 1024
    mem_used = mem_after - mem_before

    return result, mem_used
