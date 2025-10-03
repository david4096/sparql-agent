"""
Comprehensive Performance and Stress Testing Suite.

This module provides exhaustive performance testing covering:
- Load testing (concurrent queries, LLM requests, endpoint connections)
- Scalability testing (varying complexity, result sizes, connection pools)
- Reliability testing (stability, error recovery, resource leaks)
- Response time analysis and benchmarking
- Resource usage monitoring (memory, CPU, network, I/O)
- Edge case performance testing
"""

import pytest
import asyncio
import time
import threading
import psutil
import gc
import statistics
from typing import Dict, Any, List, Tuple
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
import json


# ============================================================================
# Performance Test Configuration
# ============================================================================

@dataclass
class PerformanceMetrics:
    """Store performance metrics for analysis."""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    operations_count: int
    throughput_ops_per_sec: float
    memory_start_mb: float
    memory_end_mb: float
    memory_peak_mb: float
    memory_growth_mb: float
    cpu_percent_avg: float
    error_count: int
    success_count: int
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "test_name": self.test_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "operations_count": self.operations_count,
            "throughput_ops_per_sec": self.throughput_ops_per_sec,
            "memory_start_mb": self.memory_start_mb,
            "memory_end_mb": self.memory_end_mb,
            "memory_peak_mb": self.memory_peak_mb,
            "memory_growth_mb": self.memory_growth_mb,
            "cpu_percent_avg": self.cpu_percent_avg,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "metadata": self.metadata,
        }


class PerformanceTracker:
    """Track performance metrics during test execution."""

    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.end_time = None
        self.memory_start = None
        self.memory_peak = None
        self.cpu_samples = []
        self.latencies = []
        self.errors = 0
        self.successes = 0

    def start(self):
        """Start performance tracking."""
        gc.collect()
        self.start_time = datetime.now()
        self.memory_start = self.process.memory_info().rss / 1024 / 1024
        self.memory_peak = self.memory_start
        self.cpu_samples = []
        self.latencies = []
        self.errors = 0
        self.successes = 0

    def record_operation(self, duration_ms: float, success: bool = True):
        """Record an operation's performance."""
        self.latencies.append(duration_ms)
        if success:
            self.successes += 1
        else:
            self.errors += 1

    def sample_resources(self):
        """Take a resource usage sample."""
        current_mem = self.process.memory_info().rss / 1024 / 1024
        self.memory_peak = max(self.memory_peak, current_mem)
        self.cpu_samples.append(self.process.cpu_percent())

    def stop(self, test_name: str, operations_count: int) -> PerformanceMetrics:
        """Stop tracking and generate metrics."""
        gc.collect()
        self.end_time = datetime.now()
        memory_end = self.process.memory_info().rss / 1024 / 1024
        duration = (self.end_time - self.start_time).total_seconds()

        # Calculate percentiles
        sorted_latencies = sorted(self.latencies) if self.latencies else [0]

        return PerformanceMetrics(
            test_name=test_name,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_seconds=duration,
            operations_count=operations_count,
            throughput_ops_per_sec=operations_count / duration if duration > 0 else 0,
            memory_start_mb=self.memory_start,
            memory_end_mb=memory_end,
            memory_peak_mb=self.memory_peak,
            memory_growth_mb=memory_end - self.memory_start,
            cpu_percent_avg=statistics.mean(self.cpu_samples) if self.cpu_samples else 0,
            error_count=self.errors,
            success_count=self.successes,
            p50_latency_ms=statistics.median(sorted_latencies),
            p95_latency_ms=sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 20 else sorted_latencies[-1],
            p99_latency_ms=sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 100 else sorted_latencies[-1],
            min_latency_ms=min(sorted_latencies),
            max_latency_ms=max(sorted_latencies),
        )


# ============================================================================
# 1. LOAD TESTING
# ============================================================================

class TestLoadPerformance:
    """Load testing for concurrent operations."""

    @pytest.fixture
    def mock_executor(self):
        """Create mock SPARQL executor."""
        mock = Mock()
        mock.execute = Mock(return_value=Mock(
            is_success=True,
            bindings=[{"s": "subject", "p": "predicate", "o": "object"}],
            row_count=1,
            execution_time=0.01
        ))
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        mock = Mock()
        mock.generate = Mock(return_value=Mock(
            content="SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
            usage=Mock(total_tokens=100),
            metrics=Mock(latency_ms=50)
        ))
        return mock

    def test_concurrent_query_execution_load(self, mock_executor):
        """Test concurrent SPARQL query execution under load."""
        tracker = PerformanceTracker()
        tracker.start()

        num_concurrent = 50
        queries_per_thread = 20
        total_queries = num_concurrent * queries_per_thread

        def execute_queries(thread_id: int):
            """Execute multiple queries in a thread."""
            results = []
            for i in range(queries_per_thread):
                start = time.perf_counter()
                result = mock_executor.execute(f"SELECT ?s WHERE {{ ?s ?p ?o }} LIMIT {i}")
                duration_ms = (time.perf_counter() - start) * 1000
                tracker.record_operation(duration_ms, result.is_success)
                results.append(result)

                if i % 5 == 0:
                    tracker.sample_resources()
            return results

        # Execute queries concurrently
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(execute_queries, i) for i in range(num_concurrent)]
            results = [f.result() for f in as_completed(futures)]

        metrics = tracker.stop("concurrent_query_load", total_queries)

        # Assertions
        assert metrics.success_count == total_queries
        assert metrics.error_count == 0
        assert metrics.throughput_ops_per_sec > 100, f"Throughput too low: {metrics.throughput_ops_per_sec} ops/s"
        assert metrics.memory_growth_mb < 100, f"Memory growth too high: {metrics.memory_growth_mb} MB"
        assert metrics.p95_latency_ms < 100, f"P95 latency too high: {metrics.p95_latency_ms} ms"

        print(f"\nConcurrent Query Load Test Results:")
        print(f"  Total Queries: {total_queries}")
        print(f"  Duration: {metrics.duration_seconds:.2f}s")
        print(f"  Throughput: {metrics.throughput_ops_per_sec:.2f} ops/s")
        print(f"  P50 Latency: {metrics.p50_latency_ms:.2f}ms")
        print(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")
        print(f"  Memory Growth: {metrics.memory_growth_mb:.2f}MB")

    def test_concurrent_llm_requests_load(self, mock_llm):
        """Test concurrent LLM requests under load."""
        tracker = PerformanceTracker()
        tracker.start()

        num_concurrent = 20
        requests_per_thread = 10
        total_requests = num_concurrent * requests_per_thread

        def generate_queries(thread_id: int):
            """Generate multiple queries via LLM."""
            results = []
            for i in range(requests_per_thread):
                start = time.perf_counter()
                result = mock_llm.generate(f"Find entities of type {i}")
                duration_ms = (time.perf_counter() - start) * 1000
                tracker.record_operation(duration_ms, True)
                results.append(result)

                if i % 3 == 0:
                    tracker.sample_resources()
            return results

        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(generate_queries, i) for i in range(num_concurrent)]
            results = [f.result() for f in as_completed(futures)]

        metrics = tracker.stop("concurrent_llm_load", total_requests)

        assert metrics.success_count == total_requests
        assert metrics.throughput_ops_per_sec > 10, f"LLM throughput too low: {metrics.throughput_ops_per_sec} ops/s"
        assert metrics.memory_growth_mb < 200, f"LLM memory growth too high: {metrics.memory_growth_mb} MB"

        print(f"\nConcurrent LLM Load Test Results:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Duration: {metrics.duration_seconds:.2f}s")
        print(f"  Throughput: {metrics.throughput_ops_per_sec:.2f} ops/s")
        print(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")

    def test_sustained_load_over_time(self, mock_executor):
        """Test system stability under sustained load."""
        tracker = PerformanceTracker()
        tracker.start()

        duration_seconds = 30
        target_qps = 10  # queries per second
        end_time = time.time() + duration_seconds
        query_count = 0

        while time.time() < end_time:
            start = time.perf_counter()
            result = mock_executor.execute("SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10")
            duration_ms = (time.perf_counter() - start) * 1000
            tracker.record_operation(duration_ms, result.is_success)
            query_count += 1

            # Sample resources periodically
            if query_count % 10 == 0:
                tracker.sample_resources()

            # Rate limiting
            time.sleep(1.0 / target_qps)

        metrics = tracker.stop("sustained_load", query_count)

        assert metrics.success_count == query_count
        assert metrics.error_count == 0
        assert metrics.memory_growth_mb < 50, f"Memory leak detected: {metrics.memory_growth_mb} MB growth"
        assert metrics.throughput_ops_per_sec >= target_qps * 0.8, "Throughput degraded"

        print(f"\nSustained Load Test Results:")
        print(f"  Duration: {metrics.duration_seconds:.2f}s")
        print(f"  Total Queries: {query_count}")
        print(f"  Avg Throughput: {metrics.throughput_ops_per_sec:.2f} ops/s")
        print(f"  Memory Growth: {metrics.memory_growth_mb:.2f}MB")


# ============================================================================
# 2. SCALABILITY TESTING
# ============================================================================

class TestScalabilityPerformance:
    """Scalability testing with varying complexity and sizes."""

    @pytest.fixture
    def mock_executor(self):
        """Create mock executor with configurable delay."""
        def execute(query):
            # Simulate varying complexity
            complexity = len(query) / 100
            time.sleep(0.001 * complexity)  # Simulate processing time
            return Mock(
                is_success=True,
                bindings=[{"s": f"s{i}", "p": "p", "o": "o"} for i in range(int(complexity * 10))],
                row_count=int(complexity * 10),
                execution_time=0.001 * complexity
            )

        mock = Mock()
        mock.execute = Mock(side_effect=execute)
        return mock

    @pytest.mark.parametrize("query_complexity", ["simple", "medium", "complex"])
    def test_query_complexity_scaling(self, mock_executor, query_complexity):
        """Test performance scaling with query complexity."""
        queries = {
            "simple": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10",
            "medium": """
                SELECT ?s ?p ?o ?type WHERE {
                    ?s ?p ?o .
                    ?s a ?type .
                    FILTER(lang(?o) = "en")
                } LIMIT 100
            """,
            "complex": """
                SELECT ?entity ?label (COUNT(?rel) as ?count) WHERE {
                    ?entity a ?type .
                    ?entity rdfs:label ?label .
                    ?entity ?p ?rel .
                    FILTER(lang(?label) = "en")
                }
                GROUP BY ?entity ?label
                HAVING(COUNT(?rel) > 5)
                ORDER BY DESC(?count)
                LIMIT 100
            """
        }

        tracker = PerformanceTracker()
        tracker.start()

        query = queries[query_complexity]
        iterations = 100

        for i in range(iterations):
            start = time.perf_counter()
            result = mock_executor.execute(query)
            duration_ms = (time.perf_counter() - start) * 1000
            tracker.record_operation(duration_ms, result.is_success)

            if i % 10 == 0:
                tracker.sample_resources()

        metrics = tracker.stop(f"query_complexity_{query_complexity}", iterations)

        # Complexity-based thresholds
        latency_thresholds = {
            "simple": 10,
            "medium": 50,
            "complex": 200
        }

        assert metrics.p95_latency_ms < latency_thresholds[query_complexity], \
            f"{query_complexity} query P95 latency too high: {metrics.p95_latency_ms}ms"

        print(f"\nQuery Complexity Scaling ({query_complexity}):")
        print(f"  P50 Latency: {metrics.p50_latency_ms:.2f}ms")
        print(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")
        print(f"  Throughput: {metrics.throughput_ops_per_sec:.2f} ops/s")

    @pytest.mark.parametrize("result_size", [10, 100, 1000, 10000])
    def test_result_set_size_scaling(self, result_size):
        """Test performance with varying result set sizes."""
        tracker = PerformanceTracker()
        tracker.start()

        iterations = 50

        for i in range(iterations):
            start = time.perf_counter()

            # Generate result set
            results = [
                {
                    "entity": f"http://example.org/entity_{j}",
                    "label": f"Label {j}",
                    "value": j
                }
                for j in range(result_size)
            ]

            duration_ms = (time.perf_counter() - start) * 1000
            tracker.record_operation(duration_ms, True)

            # Clean up
            del results

            if i % 10 == 0:
                tracker.sample_resources()
                gc.collect()

        metrics = tracker.stop(f"result_size_{result_size}", iterations)

        # Memory should scale linearly with result size
        expected_memory_per_1k = 5  # MB
        max_expected_memory = (result_size / 1000) * expected_memory_per_1k * 2

        assert metrics.memory_peak_mb < max_expected_memory + 100, \
            f"Memory usage too high for {result_size} results: {metrics.memory_peak_mb}MB"

        print(f"\nResult Set Size Scaling ({result_size} results):")
        print(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")
        print(f"  Memory Peak: {metrics.memory_peak_mb:.2f}MB")
        print(f"  Memory Growth: {metrics.memory_growth_mb:.2f}MB")

    def test_connection_pool_scaling(self):
        """Test connection pool behavior under different loads."""
        class ConnectionPool:
            def __init__(self, size: int):
                self.size = size
                self.available = list(range(size))
                self.in_use = set()
                self.lock = threading.Lock()
                self.wait_time_total = 0
                self.wait_count = 0

            def acquire(self) -> int:
                start = time.time()
                while True:
                    with self.lock:
                        if self.available:
                            conn = self.available.pop()
                            self.in_use.add(conn)
                            wait_time = time.time() - start
                            self.wait_time_total += wait_time
                            self.wait_count += 1
                            return conn
                    time.sleep(0.001)

            def release(self, conn: int):
                with self.lock:
                    self.in_use.remove(conn)
                    self.available.append(conn)

            def avg_wait_time(self) -> float:
                return self.wait_time_total / max(self.wait_count, 1)

        pool_sizes = [5, 10, 20, 50]
        results = {}

        for pool_size in pool_sizes:
            pool = ConnectionPool(pool_size)
            tracker = PerformanceTracker()
            tracker.start()

            num_workers = 100
            operations_per_worker = 10

            def use_connection(worker_id: int):
                for i in range(operations_per_worker):
                    start = time.perf_counter()
                    conn = pool.acquire()
                    time.sleep(0.01)  # Simulate work
                    pool.release(conn)
                    duration_ms = (time.perf_counter() - start) * 1000
                    tracker.record_operation(duration_ms, True)

            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(use_connection, i) for i in range(num_workers)]
                for f in as_completed(futures):
                    f.result()

            metrics = tracker.stop(f"connection_pool_{pool_size}", num_workers * operations_per_worker)
            results[pool_size] = {
                "avg_wait_time": pool.avg_wait_time(),
                "p95_latency": metrics.p95_latency_ms,
                "throughput": metrics.throughput_ops_per_sec
            }

        print(f"\nConnection Pool Scaling:")
        for pool_size, result in results.items():
            print(f"  Pool Size {pool_size}:")
            print(f"    Avg Wait: {result['avg_wait_time']*1000:.2f}ms")
            print(f"    P95 Latency: {result['p95_latency']:.2f}ms")
            print(f"    Throughput: {result['throughput']:.2f} ops/s")


# ============================================================================
# 3. RELIABILITY TESTING
# ============================================================================

class TestReliabilityPerformance:
    """Reliability and stability testing."""

    def test_error_recovery_performance(self):
        """Test performance during error conditions and recovery."""
        error_rate = 0.1  # 10% error rate
        retry_count = 0

        def flaky_operation(op_id: int) -> bool:
            """Operation that fails randomly."""
            nonlocal retry_count
            if random.random() < error_rate:
                retry_count += 1
                raise Exception("Simulated failure")
            return True

        tracker = PerformanceTracker()
        tracker.start()

        operations = 1000
        max_retries = 3

        for i in range(operations):
            start = time.perf_counter()
            success = False

            for attempt in range(max_retries):
                try:
                    import random
                    flaky_operation(i)
                    success = True
                    break
                except Exception:
                    if attempt == max_retries - 1:
                        break
                    time.sleep(0.01 * (2 ** attempt))  # Exponential backoff

            duration_ms = (time.perf_counter() - start) * 1000
            tracker.record_operation(duration_ms, success)

            if i % 100 == 0:
                tracker.sample_resources()

        metrics = tracker.stop("error_recovery", operations)

        # Should handle errors gracefully without excessive performance impact
        assert metrics.success_count > operations * 0.85, "Too many failures"
        assert metrics.p95_latency_ms < 500, "Error recovery too slow"

        print(f"\nError Recovery Test Results:")
        print(f"  Success Rate: {metrics.success_count/operations*100:.1f}%")
        print(f"  Retry Count: {retry_count}")
        print(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")

    def test_resource_cleanup_after_errors(self):
        """Test that resources are properly cleaned up after errors."""
        process = psutil.Process()

        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        # Simulate operations that fail and should clean up
        error_count = 0
        for i in range(100):
            try:
                # Allocate resources
                data = [{"value": j} for j in range(1000)]

                # Simulate random failure
                import random
                if random.random() < 0.3:
                    raise Exception("Operation failed")

                # Process data
                result = sum(item["value"] for item in data)

            except Exception:
                error_count += 1
            finally:
                # Ensure cleanup
                if 'data' in locals():
                    del data
                gc.collect()

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_growth = mem_after - mem_before

        # Should not leak memory despite errors
        assert mem_growth < 20, f"Memory leak after errors: {mem_growth}MB"
        assert error_count > 0, "Test should have errors"

        print(f"\nResource Cleanup Test:")
        print(f"  Errors: {error_count}")
        print(f"  Memory Growth: {mem_growth:.2f}MB")

    def test_graceful_degradation_under_stress(self):
        """Test system degrades gracefully under extreme stress."""
        tracker = PerformanceTracker()
        tracker.start()

        # Gradually increase load
        phases = [
            ("normal", 10, 100),
            ("high", 50, 100),
            ("extreme", 100, 100),
            ("recovery", 10, 100),
        ]

        all_latencies = {phase: [] for phase, _, _ in phases}

        for phase_name, concurrency, operations in phases:
            def stress_operation(op_id: int):
                start = time.perf_counter()
                # Simulate work
                time.sleep(0.01)
                duration_ms = (time.perf_counter() - start) * 1000
                all_latencies[phase_name].append(duration_ms)
                return duration_ms

            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(stress_operation, i) for i in range(operations)]
                for f in as_completed(futures):
                    duration = f.result()
                    tracker.record_operation(duration, True)

        metrics = tracker.stop("graceful_degradation", sum(ops for _, _, ops in phases))

        # Check that system recovered
        normal_p95 = statistics.quantiles(all_latencies["normal"], n=20)[18]
        recovery_p95 = statistics.quantiles(all_latencies["recovery"], n=20)[18]

        assert recovery_p95 < normal_p95 * 2, "System did not recover properly"

        print(f"\nGraceful Degradation Test:")
        for phase_name, _, _ in phases:
            latencies = all_latencies[phase_name]
            print(f"  {phase_name.capitalize()} Phase:")
            print(f"    P95 Latency: {statistics.quantiles(latencies, n=20)[18]:.2f}ms")


# ============================================================================
# 4. RESPONSE TIME ANALYSIS
# ============================================================================

class TestResponseTimeAnalysis:
    """Detailed response time benchmarking."""

    def test_operation_benchmarks(self, benchmark):
        """Benchmark individual operations."""
        from sparql_agent.execution.executor import QueryExecutor
        from sparql_agent.core.types import EndpointInfo

        # Mock executor
        executor = Mock(spec=QueryExecutor)
        executor.execute = Mock(return_value=Mock(
            is_success=True,
            bindings=[],
            row_count=0
        ))

        # Benchmark query execution
        result = benchmark(executor.execute, "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10", Mock())

        # Benchmark should complete in reasonable time
        assert benchmark.stats['mean'] < 0.01, "Operation too slow"

    def test_percentile_analysis(self):
        """Detailed percentile analysis of operations."""
        tracker = PerformanceTracker()
        tracker.start()

        operations = 1000

        for i in range(operations):
            # Simulate varying latencies
            import random
            base_latency = 10  # ms
            variance = random.gauss(0, 2)
            # Occasional spike
            if random.random() < 0.05:
                variance += random.uniform(10, 50)

            latency = max(1, base_latency + variance)
            tracker.record_operation(latency, True)

        metrics = tracker.stop("percentile_analysis", operations)

        # Analyze distribution
        print(f"\nPercentile Analysis:")
        print(f"  Min: {metrics.min_latency_ms:.2f}ms")
        print(f"  P50: {metrics.p50_latency_ms:.2f}ms")
        print(f"  P95: {metrics.p95_latency_ms:.2f}ms")
        print(f"  P99: {metrics.p99_latency_ms:.2f}ms")
        print(f"  Max: {metrics.max_latency_ms:.2f}ms")

        # Check for reasonable distribution
        assert metrics.p50_latency_ms < 15, "Median latency too high"
        assert metrics.p95_latency_ms < 30, "P95 latency too high"


# ============================================================================
# 5. RESOURCE USAGE MONITORING
# ============================================================================

class TestResourceUsage:
    """Monitor CPU, memory, network, and I/O usage."""

    def test_cpu_usage_monitoring(self):
        """Monitor CPU usage during operations."""
        process = psutil.Process()
        cpu_samples = []

        # CPU-intensive operations
        def cpu_intensive_operation():
            result = 0
            for i in range(100000):
                result += i ** 2
            return result

        start_time = time.time()
        duration = 5  # seconds

        while time.time() - start_time < duration:
            cpu_intensive_operation()
            cpu_samples.append(process.cpu_percent())
            time.sleep(0.1)

        avg_cpu = statistics.mean(cpu_samples)
        max_cpu = max(cpu_samples)

        print(f"\nCPU Usage Monitoring:")
        print(f"  Average CPU: {avg_cpu:.1f}%")
        print(f"  Max CPU: {max_cpu:.1f}%")

        # Should use CPU but not peg it at 100%
        assert avg_cpu > 0, "CPU not being utilized"
        assert avg_cpu < 90, "CPU usage too high"

    def test_memory_usage_patterns(self):
        """Analyze memory usage patterns."""
        process = psutil.Process()

        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        memory_samples = []

        # Allocate and deallocate in phases
        for phase in range(5):
            # Allocation phase
            data = []
            for i in range(1000):
                data.append({"value": i, "data": "x" * 1000})
                if i % 100 == 0:
                    memory_samples.append(process.memory_info().rss / 1024 / 1024)

            # Deallocation phase
            del data
            gc.collect()
            memory_samples.append(process.memory_info().rss / 1024 / 1024)

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024

        print(f"\nMemory Usage Pattern:")
        print(f"  Start: {mem_before:.2f}MB")
        print(f"  End: {mem_after:.2f}MB")
        print(f"  Growth: {mem_after - mem_before:.2f}MB")
        print(f"  Peak: {max(memory_samples):.2f}MB")

        # Should return to baseline after GC
        assert mem_after - mem_before < 10, "Memory not released properly"


# ============================================================================
# 6. EDGE CASE PERFORMANCE
# ============================================================================

class TestEdgeCasePerformance:
    """Test performance under edge cases."""

    def test_very_large_query_performance(self):
        """Test performance with very large queries."""
        tracker = PerformanceTracker()
        tracker.start()

        # Generate very large query
        large_query = "SELECT ?s ?p ?o WHERE {\n"
        large_query += "  VALUES ?s {\n"
        for i in range(1000):
            large_query += f"    <http://example.org/entity_{i}>\n"
        large_query += "  }\n  ?s ?p ?o .\n}"

        # Mock executor
        mock = Mock()
        mock.execute = Mock(return_value=Mock(is_success=True, row_count=1000))

        iterations = 10
        for i in range(iterations):
            start = time.perf_counter()
            result = mock.execute(large_query)
            duration_ms = (time.perf_counter() - start) * 1000
            tracker.record_operation(duration_ms, result.is_success)

        metrics = tracker.stop("large_query", iterations)

        print(f"\nLarge Query Test:")
        print(f"  Query Size: {len(large_query)} chars")
        print(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")

        assert metrics.p95_latency_ms < 100, "Large query processing too slow"

    def test_empty_result_set_performance(self):
        """Test performance with empty result sets."""
        tracker = PerformanceTracker()
        tracker.start()

        mock = Mock()
        mock.execute = Mock(return_value=Mock(is_success=True, bindings=[], row_count=0))

        iterations = 1000
        for i in range(iterations):
            start = time.perf_counter()
            result = mock.execute("SELECT ?s WHERE { ?s ?p ?o } LIMIT 0")
            duration_ms = (time.perf_counter() - start) * 1000
            tracker.record_operation(duration_ms, result.is_success)

        metrics = tracker.stop("empty_results", iterations)

        assert metrics.p95_latency_ms < 5, "Empty result handling too slow"

        print(f"\nEmpty Result Test:")
        print(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")

    def test_network_instability_simulation(self):
        """Test performance under simulated network issues."""
        import random

        tracker = PerformanceTracker()
        tracker.start()

        def unstable_network_operation():
            """Simulate network with random delays and failures."""
            delay = random.choice([0.01, 0.05, 0.1, 0.5, 1.0])
            time.sleep(delay)

            if random.random() < 0.05:  # 5% failure rate
                raise Exception("Network timeout")

            return True

        operations = 200
        for i in range(operations):
            start = time.perf_counter()
            success = False

            try:
                unstable_network_operation()
                success = True
            except Exception:
                pass

            duration_ms = (time.perf_counter() - start) * 1000
            tracker.record_operation(duration_ms, success)

        metrics = tracker.stop("network_instability", operations)

        print(f"\nNetwork Instability Test:")
        print(f"  Success Rate: {metrics.success_count/operations*100:.1f}%")
        print(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")

        assert metrics.success_count > operations * 0.8, "Too many failures"


# ============================================================================
# Test Report Generation
# ============================================================================

@pytest.fixture(scope="session")
def performance_report(tmp_path_factory):
    """Generate comprehensive performance report."""
    report_dir = tmp_path_factory.mktemp("performance_reports")

    class PerformanceReport:
        def __init__(self, output_dir):
            self.output_dir = output_dir
            self.all_metrics = []

        def add_metrics(self, metrics: PerformanceMetrics):
            """Add metrics to report."""
            self.all_metrics.append(metrics)

        def generate_report(self):
            """Generate final performance report."""
            report_file = self.output_dir / "performance_report.json"

            report = {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.all_metrics),
                "summary": {
                    "total_operations": sum(m.operations_count for m in self.all_metrics),
                    "avg_throughput": statistics.mean([m.throughput_ops_per_sec for m in self.all_metrics]),
                    "total_errors": sum(m.error_count for m in self.all_metrics),
                },
                "tests": [m.to_dict() for m in self.all_metrics]
            }

            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            return report_file

    return PerformanceReport(report_dir)
