#!/usr/bin/env python3
"""
Comprehensive SPARQL Endpoint Stress Testing Suite

This script performs intensive stress testing of SPARQL endpoint connectivity
and query execution across multiple public endpoints.

Tests include:
1. Connectivity testing with various timeouts
2. Connection pooling under load
3. Retry mechanisms with temporary failures
4. Query execution (simple to complex)
5. Performance metrics collection
6. Error handling and recovery
7. Concurrent query execution
8. Timeout scenarios
"""

import asyncio
import sys
import time
import json
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    ConnectionConfig,
    EndpointStatus,
    EndpointHealth
)
from sparql_agent.execution.executor import (
    QueryExecutor,
    ResultFormat
)
from sparql_agent.core.types import EndpointInfo


# ============================================================================
# Test Configuration
# ============================================================================

@dataclass
class EndpointConfig:
    """Configuration for a test endpoint"""
    name: str
    url: str
    supports_update: bool = False
    requires_auth: bool = False
    notes: str = ""


@dataclass
class TestResult:
    """Result of a single test"""
    test_name: str
    endpoint_name: str
    success: bool
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StressTestReport:
    """Complete stress test report"""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    results: List[TestResult] = field(default_factory=list)
    endpoint_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    performance_summary: Dict[str, Any] = field(default_factory=dict)


# Major Public SPARQL Endpoints
TEST_ENDPOINTS = [
    EndpointConfig(
        name="Wikidata",
        url="https://query.wikidata.org/sparql",
        notes="Large knowledge graph with rate limiting"
    ),
    EndpointConfig(
        name="UniProt",
        url="https://sparql.uniprot.org/sparql",
        notes="Protein sequence and functional information"
    ),
    EndpointConfig(
        name="DBpedia",
        url="https://dbpedia.org/sparql",
        notes="Structured content from Wikipedia"
    ),
    EndpointConfig(
        name="EBI RDF",
        url="https://www.ebi.ac.uk/rdf/services/sparql",
        notes="European Bioinformatics Institute"
    ),
    EndpointConfig(
        name="ChEBI",
        url="https://www.ebi.ac.uk/rdf/services/chembl/sparql",
        notes="Chemical Entities of Biological Interest"
    ),
]


# Test Queries - From Simple to Complex
TEST_QUERIES = {
    "simple_ask": {
        "query": "ASK { ?s ?p ?o }",
        "description": "Simple ASK query",
        "expected_fast": True
    },
    "simple_select": {
        "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
        "description": "Simple SELECT with LIMIT",
        "expected_fast": True
    },
    "count_triples": {
        "query": "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o } LIMIT 1000",
        "description": "COUNT aggregate query",
        "expected_fast": False
    },
    "distinct_predicates": {
        "query": """
            SELECT DISTINCT ?p (COUNT(?s) as ?count)
            WHERE { ?s ?p ?o }
            GROUP BY ?p
            LIMIT 20
        """,
        "description": "GROUP BY with DISTINCT",
        "expected_fast": False
    },
    "construct": {
        "query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10",
        "description": "CONSTRUCT query",
        "expected_fast": True
    },
    "describe": {
        "query": "DESCRIBE ?s WHERE { ?s ?p ?o } LIMIT 1",
        "description": "DESCRIBE query",
        "expected_fast": True
    },
    "filter_regex": {
        "query": """
            SELECT ?s ?label
            WHERE {
                ?s ?p ?label .
                FILTER(isLiteral(?label))
                FILTER(REGEX(STR(?label), "protein", "i"))
            }
            LIMIT 20
        """,
        "description": "FILTER with REGEX",
        "expected_fast": False
    },
    "optional_join": {
        "query": """
            SELECT ?s ?p1 ?o1 ?p2 ?o2
            WHERE {
                ?s ?p1 ?o1 .
                OPTIONAL { ?s ?p2 ?o2 }
            }
            LIMIT 10
        """,
        "description": "OPTIONAL join",
        "expected_fast": True
    },
}

# Malformed queries for error testing
MALFORMED_QUERIES = {
    "syntax_error": "SELECT * WHERE { ?s ?p }",  # Missing closing brace
    "invalid_prefix": "SELECT * WHERE { ex:test ex:prop ?o }",  # Undefined prefix
    "invalid_function": "SELECT (INVALID_FUNC(?s) as ?result) WHERE { ?s ?p ?o }",
}


# ============================================================================
# Stress Test Class
# ============================================================================

class EndpointStressTester:
    """Comprehensive SPARQL endpoint stress tester"""

    def __init__(self, endpoints: List[EndpointConfig], verbose: bool = True):
        self.endpoints = endpoints
        self.verbose = verbose
        self.report = StressTestReport(start_time=datetime.now())

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] [{level}] {message}")

    def record_result(self, result: TestResult):
        """Record a test result"""
        self.report.results.append(result)
        self.report.total_tests += 1
        if result.success:
            self.report.passed_tests += 1
        else:
            self.report.failed_tests += 1

    # ========================================================================
    # Test 1: Connectivity Testing
    # ========================================================================

    async def test_connectivity(self):
        """Test basic connectivity with various timeout configurations"""
        self.log("=" * 80)
        self.log("TEST 1: Connectivity Testing")
        self.log("=" * 80)

        # Test different timeout configurations
        timeout_configs = [
            (5.0, "5s timeout"),
            (10.0, "10s timeout"),
            (30.0, "30s timeout"),
        ]

        for timeout, desc in timeout_configs:
            self.log(f"\nTesting with {desc}...")
            config = ConnectionConfig(
                timeout=timeout,
                retry_attempts=1,
                verify_ssl=True
            )

            async with EndpointPinger(config=config) as pinger:
                for endpoint in self.endpoints:
                    start_time = time.time()
                    try:
                        health = await pinger.ping_async(
                            endpoint.url,
                            check_query=False  # HEAD request only
                        )

                        elapsed_ms = (time.time() - start_time) * 1000

                        result = TestResult(
                            test_name=f"connectivity_{timeout}s",
                            endpoint_name=endpoint.name,
                            success=(health.status in [
                                EndpointStatus.HEALTHY,
                                EndpointStatus.DEGRADED
                            ]),
                            response_time_ms=health.response_time_ms or elapsed_ms,
                            error_message=health.error_message,
                            metadata={
                                "status": health.status.value,
                                "timeout": timeout,
                                "ssl_valid": health.ssl_valid,
                                "status_code": health.status_code
                            }
                        )

                        self.record_result(result)

                        status_icon = "✓" if result.success else "✗"
                        self.log(
                            f"{status_icon} {endpoint.name}: {health.status.value} "
                            f"({health.response_time_ms:.2f}ms)"
                        )

                    except Exception as e:
                        self.log(f"✗ {endpoint.name}: {str(e)}", "ERROR")
                        self.record_result(TestResult(
                            test_name=f"connectivity_{timeout}s",
                            endpoint_name=endpoint.name,
                            success=False,
                            error_message=str(e)
                        ))

    # ========================================================================
    # Test 2: Connection Pooling Under Load
    # ========================================================================

    async def test_connection_pooling(self):
        """Test connection pooling with concurrent requests"""
        self.log("\n" + "=" * 80)
        self.log("TEST 2: Connection Pooling Under Load")
        self.log("=" * 80)

        config = ConnectionConfig(timeout=15.0, retry_attempts=2)

        # Test with different pool sizes
        for pool_size in [5, 10, 20]:
            self.log(f"\nTesting with pool size: {pool_size}")

            async with EndpointPinger(config=config, pool_size=pool_size) as pinger:
                for endpoint in self.endpoints:
                    # Fire multiple concurrent requests
                    num_requests = pool_size * 2
                    self.log(f"  Sending {num_requests} concurrent requests to {endpoint.name}...")

                    start_time = time.time()
                    tasks = [
                        pinger.ping_async(endpoint.url, check_query=True)
                        for _ in range(num_requests)
                    ]

                    try:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        elapsed = time.time() - start_time

                        successes = sum(
                            1 for r in results
                            if isinstance(r, EndpointHealth) and
                            r.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]
                        )

                        avg_response_time = statistics.mean([
                            r.response_time_ms for r in results
                            if isinstance(r, EndpointHealth) and r.response_time_ms
                        ]) if results else 0

                        result = TestResult(
                            test_name=f"pool_load_{pool_size}",
                            endpoint_name=endpoint.name,
                            success=(successes >= num_requests * 0.8),  # 80% success rate
                            response_time_ms=elapsed * 1000,
                            metadata={
                                "pool_size": pool_size,
                                "num_requests": num_requests,
                                "successes": successes,
                                "success_rate": successes / num_requests,
                                "avg_response_time_ms": avg_response_time,
                                "total_time_s": elapsed
                            }
                        )

                        self.record_result(result)

                        status_icon = "✓" if result.success else "✗"
                        self.log(
                            f"{status_icon} {endpoint.name}: {successes}/{num_requests} "
                            f"succeeded in {elapsed:.2f}s (avg: {avg_response_time:.2f}ms)"
                        )

                    except Exception as e:
                        self.log(f"✗ {endpoint.name}: {str(e)}", "ERROR")
                        self.record_result(TestResult(
                            test_name=f"pool_load_{pool_size}",
                            endpoint_name=endpoint.name,
                            success=False,
                            error_message=str(e)
                        ))

    # ========================================================================
    # Test 3: Retry Mechanisms
    # ========================================================================

    async def test_retry_mechanisms(self):
        """Test retry logic with different configurations"""
        self.log("\n" + "=" * 80)
        self.log("TEST 3: Retry Mechanisms")
        self.log("=" * 80)

        retry_configs = [
            (1, 0.5, 1.0, "1 retry, 0.5s delay"),
            (3, 1.0, 2.0, "3 retries, exponential backoff"),
            (5, 0.5, 1.5, "5 retries, moderate backoff"),
        ]

        for retries, delay, backoff, desc in retry_configs:
            self.log(f"\nTesting: {desc}")
            config = ConnectionConfig(
                timeout=10.0,
                retry_attempts=retries,
                retry_delay=delay,
                retry_backoff=backoff
            )

            async with EndpointPinger(config=config) as pinger:
                for endpoint in self.endpoints:
                    start_time = time.time()
                    health = await pinger.ping_async(endpoint.url, check_query=True)
                    elapsed = time.time() - start_time

                    result = TestResult(
                        test_name=f"retry_{retries}",
                        endpoint_name=endpoint.name,
                        success=(health.status in [
                            EndpointStatus.HEALTHY,
                            EndpointStatus.DEGRADED
                        ]),
                        response_time_ms=elapsed * 1000,
                        error_message=health.error_message,
                        metadata={
                            "retry_attempts": retries,
                            "status": health.status.value
                        }
                    )

                    self.record_result(result)

                    status_icon = "✓" if result.success else "✗"
                    self.log(
                        f"{status_icon} {endpoint.name}: {health.status.value} "
                        f"({elapsed:.2f}s)"
                    )

    # ========================================================================
    # Test 4: Query Execution Tests
    # ========================================================================

    def test_query_execution(self):
        """Test various query types and complexity levels"""
        self.log("\n" + "=" * 80)
        self.log("TEST 4: Query Execution Tests")
        self.log("=" * 80)

        executor = QueryExecutor(
            timeout=60,
            max_retries=3,
            enable_metrics=True
        )

        for query_name, query_info in TEST_QUERIES.items():
            self.log(f"\n--- Testing: {query_info['description']} ---")

            for endpoint in self.endpoints:
                start_time = time.time()

                try:
                    result = executor.execute(
                        query=query_info['query'],
                        endpoint=EndpointInfo(url=endpoint.url)
                    )

                    elapsed = time.time() - start_time

                    test_result = TestResult(
                        test_name=f"query_{query_name}",
                        endpoint_name=endpoint.name,
                        success=result.is_success,
                        response_time_ms=elapsed * 1000,
                        error_message=result.error_message if not result.is_success else None,
                        metadata={
                            "query_type": query_name,
                            "row_count": result.row_count,
                            "variables": result.variables,
                            "expected_fast": query_info['expected_fast']
                        }
                    )

                    self.record_result(test_result)

                    if result.is_success:
                        self.log(
                            f"✓ {endpoint.name}: {result.row_count} results "
                            f"in {elapsed:.2f}s"
                        )
                    else:
                        self.log(
                            f"✗ {endpoint.name}: {result.error_message}",
                            "ERROR"
                        )

                except Exception as e:
                    elapsed = time.time() - start_time
                    self.log(f"✗ {endpoint.name}: {str(e)}", "ERROR")

                    self.record_result(TestResult(
                        test_name=f"query_{query_name}",
                        endpoint_name=endpoint.name,
                        success=False,
                        response_time_ms=elapsed * 1000,
                        error_message=str(e)
                    ))

                # Brief pause between endpoints
                time.sleep(0.5)

        executor.close()

    # ========================================================================
    # Test 5: Error Handling Tests
    # ========================================================================

    def test_error_handling(self):
        """Test error handling with malformed queries"""
        self.log("\n" + "=" * 80)
        self.log("TEST 5: Error Handling Tests")
        self.log("=" * 80)

        executor = QueryExecutor(timeout=30, max_retries=1)

        for error_type, malformed_query in MALFORMED_QUERIES.items():
            self.log(f"\n--- Testing: {error_type} ---")

            for endpoint in self.endpoints:
                start_time = time.time()

                try:
                    result = executor.execute(
                        query=malformed_query,
                        endpoint=EndpointInfo(url=endpoint.url)
                    )

                    elapsed = time.time() - start_time

                    # For malformed queries, we expect failure with graceful error handling
                    test_result = TestResult(
                        test_name=f"error_{error_type}",
                        endpoint_name=endpoint.name,
                        success=(not result.is_success),  # Success = graceful failure
                        response_time_ms=elapsed * 1000,
                        error_message=result.error_message,
                        metadata={
                            "error_type": error_type,
                            "graceful_failure": not result.is_success
                        }
                    )

                    self.record_result(test_result)

                    if not result.is_success:
                        self.log(f"✓ {endpoint.name}: Gracefully handled error")
                    else:
                        self.log(
                            f"⚠ {endpoint.name}: Unexpectedly succeeded",
                            "WARN"
                        )

                except Exception as e:
                    elapsed = time.time() - start_time
                    # Exception is actually good - it means error was caught
                    self.log(f"✓ {endpoint.name}: Error caught: {type(e).__name__}")

                    self.record_result(TestResult(
                        test_name=f"error_{error_type}",
                        endpoint_name=endpoint.name,
                        success=True,  # Catching the error is success
                        response_time_ms=elapsed * 1000,
                        error_message=str(e),
                        metadata={"error_type": error_type}
                    ))

                time.sleep(0.3)

        executor.close()

    # ========================================================================
    # Test 6: Timeout Scenarios
    # ========================================================================

    def test_timeout_scenarios(self):
        """Test various timeout configurations"""
        self.log("\n" + "=" * 80)
        self.log("TEST 6: Timeout Scenarios")
        self.log("=" * 80)

        # Test with very short timeouts to force timeout errors
        timeout_configs = [
            (1, "Very short (1s)"),
            (5, "Short (5s)"),
            (15, "Medium (15s)"),
            (30, "Long (30s)"),
        ]

        # Use a moderately complex query
        test_query = TEST_QUERIES['count_triples']['query']

        for timeout, desc in timeout_configs:
            self.log(f"\n--- Testing timeout: {desc} ---")

            executor = QueryExecutor(timeout=timeout, max_retries=1)

            for endpoint in self.endpoints:
                start_time = time.time()

                try:
                    result = executor.execute(
                        query=test_query,
                        endpoint=EndpointInfo(url=endpoint.url)
                    )

                    elapsed = time.time() - start_time

                    test_result = TestResult(
                        test_name=f"timeout_{timeout}s",
                        endpoint_name=endpoint.name,
                        success=result.is_success,
                        response_time_ms=elapsed * 1000,
                        error_message=result.error_message if not result.is_success else None,
                        metadata={
                            "timeout_config": timeout,
                            "timed_out": "timeout" in (result.error_message or "").lower(),
                            "elapsed_s": elapsed
                        }
                    )

                    self.record_result(test_result)

                    if result.is_success:
                        self.log(
                            f"✓ {endpoint.name}: Completed in {elapsed:.2f}s "
                            f"(within {timeout}s timeout)"
                        )
                    else:
                        self.log(
                            f"✗ {endpoint.name}: {result.error_message}",
                            "WARN"
                        )

                except Exception as e:
                    elapsed = time.time() - start_time
                    self.log(f"✗ {endpoint.name}: {str(e)}", "ERROR")

                    self.record_result(TestResult(
                        test_name=f"timeout_{timeout}s",
                        endpoint_name=endpoint.name,
                        success=False,
                        response_time_ms=elapsed * 1000,
                        error_message=str(e)
                    ))

            executor.close()

    # ========================================================================
    # Test 7: Concurrent Query Execution
    # ========================================================================

    def test_concurrent_execution(self):
        """Test concurrent query execution"""
        self.log("\n" + "=" * 80)
        self.log("TEST 7: Concurrent Query Execution")
        self.log("=" * 80)

        executor = QueryExecutor(
            timeout=30,
            pool_size=20,
            enable_metrics=True
        )

        # Test with increasing concurrency levels
        for num_concurrent in [5, 10, 20]:
            self.log(f"\n--- Testing {num_concurrent} concurrent queries ---")

            for endpoint in self.endpoints:
                start_time = time.time()

                with ThreadPoolExecutor(max_workers=num_concurrent) as pool:
                    futures = []

                    # Submit queries
                    for i in range(num_concurrent):
                        query = TEST_QUERIES['simple_select']['query']
                        future = pool.submit(
                            executor.execute,
                            query,
                            EndpointInfo(url=endpoint.url)
                        )
                        futures.append(future)

                    # Collect results
                    results = []
                    errors = []

                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            results.append(result)
                            if not result.is_success:
                                errors.append(result.error_message)
                        except Exception as e:
                            errors.append(str(e))

                    elapsed = time.time() - start_time
                    successes = sum(1 for r in results if r.is_success)

                    test_result = TestResult(
                        test_name=f"concurrent_{num_concurrent}",
                        endpoint_name=endpoint.name,
                        success=(successes >= num_concurrent * 0.7),  # 70% success rate
                        response_time_ms=elapsed * 1000,
                        metadata={
                            "concurrency": num_concurrent,
                            "successes": successes,
                            "failures": len(errors),
                            "success_rate": successes / num_concurrent,
                            "total_time_s": elapsed,
                            "queries_per_second": num_concurrent / elapsed
                        }
                    )

                    self.record_result(test_result)

                    status_icon = "✓" if test_result.success else "✗"
                    self.log(
                        f"{status_icon} {endpoint.name}: {successes}/{num_concurrent} "
                        f"succeeded in {elapsed:.2f}s "
                        f"({test_result.metadata['queries_per_second']:.2f} q/s)"
                    )

                    if errors:
                        self.log(f"  Errors: {errors[:3]}", "WARN")

        executor.close()

    # ========================================================================
    # Test 8: Performance Metrics
    # ========================================================================

    async def test_performance_metrics(self):
        """Collect detailed performance metrics"""
        self.log("\n" + "=" * 80)
        self.log("TEST 8: Performance Metrics Collection")
        self.log("=" * 80)

        config = ConnectionConfig(timeout=15.0, retry_attempts=2)

        async with EndpointPinger(config=config) as pinger:
            for endpoint in self.endpoints:
                self.log(f"\n--- Collecting metrics for {endpoint.name} ---")

                # Run multiple health checks
                num_checks = 10
                health_results = []

                for i in range(num_checks):
                    health = await pinger.ping_async(endpoint.url, check_query=True)
                    health_results.append(health)
                    pinger.record_health(health)
                    await asyncio.sleep(0.5)

                # Calculate statistics
                response_times = [
                    h.response_time_ms for h in health_results
                    if h.response_time_ms is not None
                ]

                if response_times:
                    stats = {
                        "min_ms": min(response_times),
                        "max_ms": max(response_times),
                        "mean_ms": statistics.mean(response_times),
                        "median_ms": statistics.median(response_times),
                        "stdev_ms": statistics.stdev(response_times) if len(response_times) > 1 else 0,
                        "uptime_pct": pinger.get_uptime_percentage(endpoint.url),
                        "avg_response_ms": pinger.get_average_response_time(endpoint.url),
                    }

                    # Store in report
                    self.report.endpoint_stats[endpoint.name] = stats

                    self.log(f"  Response times:")
                    self.log(f"    Min: {stats['min_ms']:.2f}ms")
                    self.log(f"    Max: {stats['max_ms']:.2f}ms")
                    self.log(f"    Mean: {stats['mean_ms']:.2f}ms")
                    self.log(f"    Median: {stats['median_ms']:.2f}ms")
                    self.log(f"    StdDev: {stats['stdev_ms']:.2f}ms")
                    self.log(f"    Uptime: {stats['uptime_pct']:.1f}%")

                    # Record result
                    self.record_result(TestResult(
                        test_name="performance_metrics",
                        endpoint_name=endpoint.name,
                        success=True,
                        response_time_ms=stats['mean_ms'],
                        metadata=stats
                    ))

    # ========================================================================
    # Report Generation
    # ========================================================================

    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        self.report.end_time = datetime.now()

        report_lines = []
        report_lines.append("\n" + "=" * 80)
        report_lines.append("SPARQL ENDPOINT STRESS TEST REPORT")
        report_lines.append("=" * 80)

        # Summary
        report_lines.append(f"\nTest Duration: {self.report.end_time - self.report.start_time}")
        report_lines.append(f"Total Tests: {self.report.total_tests}")
        report_lines.append(f"Passed: {self.report.passed_tests} ({self.report.passed_tests/self.report.total_tests*100:.1f}%)")
        report_lines.append(f"Failed: {self.report.failed_tests} ({self.report.failed_tests/self.report.total_tests*100:.1f}%)")

        # Per-endpoint summary
        report_lines.append("\n" + "-" * 80)
        report_lines.append("ENDPOINT SUMMARY")
        report_lines.append("-" * 80)

        endpoint_results = {}
        for result in self.report.results:
            if result.endpoint_name not in endpoint_results:
                endpoint_results[result.endpoint_name] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "response_times": []
                }

            endpoint_results[result.endpoint_name]["total"] += 1
            if result.success:
                endpoint_results[result.endpoint_name]["passed"] += 1
            else:
                endpoint_results[result.endpoint_name]["failed"] += 1

            if result.response_time_ms:
                endpoint_results[result.endpoint_name]["response_times"].append(
                    result.response_time_ms
                )

        for endpoint_name, stats in endpoint_results.items():
            report_lines.append(f"\n{endpoint_name}:")
            report_lines.append(f"  Tests: {stats['total']}")
            report_lines.append(f"  Passed: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
            report_lines.append(f"  Failed: {stats['failed']}")

            if stats['response_times']:
                avg_time = statistics.mean(stats['response_times'])
                report_lines.append(f"  Avg Response Time: {avg_time:.2f}ms")

        # Performance metrics
        if self.report.endpoint_stats:
            report_lines.append("\n" + "-" * 80)
            report_lines.append("PERFORMANCE METRICS")
            report_lines.append("-" * 80)

            for endpoint_name, metrics in self.report.endpoint_stats.items():
                report_lines.append(f"\n{endpoint_name}:")
                for key, value in metrics.items():
                    if isinstance(value, float):
                        report_lines.append(f"  {key}: {value:.2f}")
                    else:
                        report_lines.append(f"  {key}: {value}")

        # Test-specific results
        report_lines.append("\n" + "-" * 80)
        report_lines.append("TEST DETAILS")
        report_lines.append("-" * 80)

        # Group by test name
        test_groups = {}
        for result in self.report.results:
            if result.test_name not in test_groups:
                test_groups[result.test_name] = []
            test_groups[result.test_name].append(result)

        for test_name, results in sorted(test_groups.items()):
            passed = sum(1 for r in results if r.success)
            total = len(results)
            report_lines.append(f"\n{test_name}: {passed}/{total} passed")

        # Failed tests details
        failed_results = [r for r in self.report.results if not r.success]
        if failed_results:
            report_lines.append("\n" + "-" * 80)
            report_lines.append("FAILED TESTS DETAILS")
            report_lines.append("-" * 80)

            for result in failed_results[:20]:  # Limit to first 20
                report_lines.append(f"\n{result.test_name} - {result.endpoint_name}")
                if result.error_message:
                    error_msg = result.error_message[:200]
                    report_lines.append(f"  Error: {error_msg}")

        report_lines.append("\n" + "=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80 + "\n")

        return "\n".join(report_lines)

    def save_report(self, filename: str = None):
        """Save detailed report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stress_test_report_{timestamp}.json"

        report_data = {
            "start_time": self.report.start_time.isoformat(),
            "end_time": self.report.end_time.isoformat() if self.report.end_time else None,
            "total_tests": self.report.total_tests,
            "passed_tests": self.report.passed_tests,
            "failed_tests": self.report.failed_tests,
            "endpoint_stats": self.report.endpoint_stats,
            "results": [
                {
                    "test_name": r.test_name,
                    "endpoint_name": r.endpoint_name,
                    "success": r.success,
                    "response_time_ms": r.response_time_ms,
                    "error_message": r.error_message,
                    "metadata": r.metadata,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.report.results
            ]
        }

        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)

        self.log(f"\nDetailed report saved to: {filename}")
        return filename


# ============================================================================
# Main Execution
# ============================================================================

async def run_async_tests(tester: EndpointStressTester):
    """Run all async tests"""
    await tester.test_connectivity()
    await tester.test_connection_pooling()
    await tester.test_retry_mechanisms()
    await tester.test_performance_metrics()


def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("SPARQL ENDPOINT COMPREHENSIVE STRESS TEST")
    print("=" * 80)
    print(f"\nTesting {len(TEST_ENDPOINTS)} endpoints")
    print(f"Test queries: {len(TEST_QUERIES)}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 80)

    tester = EndpointStressTester(TEST_ENDPOINTS, verbose=True)

    try:
        # Run async tests
        tester.log("\nRunning asynchronous tests...")
        asyncio.run(run_async_tests(tester))

        # Run sync tests
        tester.log("\nRunning synchronous tests...")
        tester.test_query_execution()
        tester.test_error_handling()
        tester.test_timeout_scenarios()
        tester.test_concurrent_execution()

        # Generate and print report
        report = tester.generate_report()
        print(report)

        # Save detailed report
        report_file = tester.save_report()

        print(f"\n✓ Stress testing complete!")
        print(f"✓ Report saved to: {report_file}")

        return 0

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 130

    except Exception as e:
        print(f"\n\nFatal error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
