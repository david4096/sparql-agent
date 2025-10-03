"""
Pytest configuration and fixtures for integration tests.

This module provides shared fixtures and configuration for all integration tests,
including endpoint availability checking, response caching, retry logic, and
test data management.
"""

import os
import time
from typing import Any, Dict, Optional
from unittest.mock import Mock

import pytest
import requests
from SPARQLWrapper import SPARQLWrapper, JSON, POST, GET


# ============================================================================
# MARKERS
# ============================================================================

def pytest_configure(config: Any) -> None:
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring real endpoints"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring internet connectivity"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (execution time > 5 seconds)"
    )
    config.addinivalue_line(
        "markers", "endpoint: mark test as endpoint-specific"
    )
    config.addinivalue_line(
        "markers", "smoke: mark test as smoke test (basic connectivity)"
    )
    config.addinivalue_line(
        "markers", "functional: mark test as functional test (complete feature)"
    )
    config.addinivalue_line(
        "markers", "regression: mark test as regression test (known good queries)"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test (response time monitoring)"
    )


# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def skip_network_tests() -> bool:
    """Check if network tests should be skipped."""
    return os.environ.get("SKIP_NETWORK_TESTS", "false").lower() == "true"


@pytest.fixture(scope="session")
def skip_slow_tests() -> bool:
    """Check if slow tests should be skipped."""
    return os.environ.get("SKIP_SLOW_TESTS", "false").lower() == "true"


@pytest.fixture(scope="session")
def test_timeout() -> int:
    """Get timeout for test queries."""
    return int(os.environ.get("TEST_TIMEOUT", "30"))


@pytest.fixture(scope="session")
def max_retries() -> int:
    """Get maximum number of retries for failed queries."""
    return int(os.environ.get("MAX_RETRIES", "3"))


# ============================================================================
# ENDPOINT AVAILABILITY
# ============================================================================

class EndpointChecker:
    """Check endpoint availability and cache results."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._cache: Dict[str, tuple[bool, float]] = {}
        self._cache_ttl = 300  # 5 minutes

    def is_available(self, endpoint_url: str, force: bool = False) -> bool:
        """
        Check if an endpoint is available.

        Args:
            endpoint_url: SPARQL endpoint URL
            force: Force check even if cached

        Returns:
            True if endpoint is available, False otherwise
        """
        # Check cache
        if not force and endpoint_url in self._cache:
            available, timestamp = self._cache[endpoint_url]
            if time.time() - timestamp < self._cache_ttl:
                return available

        # Perform check
        try:
            # Try a simple ASK query
            sparql = SPARQLWrapper(endpoint_url)
            sparql.setQuery("ASK { ?s ?p ?o }")
            sparql.setReturnFormat(JSON)
            sparql.setTimeout(self.timeout)
            sparql.setMethod(GET)

            result = sparql.query().convert()
            available = result.get("boolean", False)

        except Exception as e:
            print(f"Endpoint {endpoint_url} not available: {e}")
            available = False

        # Cache result
        self._cache[endpoint_url] = (available, time.time())
        return available


@pytest.fixture(scope="session")
def endpoint_checker(test_timeout: int) -> EndpointChecker:
    """Create endpoint checker with session scope."""
    return EndpointChecker(timeout=test_timeout)


@pytest.fixture
def check_endpoint_available(endpoint_checker: EndpointChecker):
    """Factory fixture to check if an endpoint is available."""
    def _check(endpoint_url: str) -> None:
        if not endpoint_checker.is_available(endpoint_url):
            pytest.skip(f"Endpoint {endpoint_url} is not available")
    return _check


# ============================================================================
# SPARQL WRAPPER FIXTURES
# ============================================================================

@pytest.fixture
def sparql_wrapper_factory(test_timeout: int):
    """Factory for creating configured SPARQLWrapper instances."""
    def _create_wrapper(endpoint_url: str, query_method: str = "GET") -> SPARQLWrapper:
        sparql = SPARQLWrapper(endpoint_url)
        sparql.setReturnFormat(JSON)
        sparql.setTimeout(test_timeout)
        sparql.setMethod(GET if query_method == "GET" else POST)
        sparql.addCustomHttpHeader("User-Agent", "SPARQL-Agent-Tests/1.0")
        return sparql
    return _create_wrapper


@pytest.fixture
def sparql_query_executor(sparql_wrapper_factory, max_retries: int):
    """Execute SPARQL queries with retry logic."""
    def _execute(endpoint_url: str, query: str, retries: int = None) -> Dict[str, Any]:
        """
        Execute SPARQL query with retry logic.

        Args:
            endpoint_url: SPARQL endpoint URL
            query: SPARQL query string
            retries: Number of retries (default: max_retries)

        Returns:
            Query results as dictionary

        Raises:
            Exception: If query fails after all retries
        """
        if retries is None:
            retries = max_retries

        last_error = None
        for attempt in range(retries):
            try:
                sparql = sparql_wrapper_factory(endpoint_url)
                sparql.setQuery(query)
                result = sparql.query().convert()
                return result
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue

        raise last_error or Exception("Query failed after retries")

    return _execute


# ============================================================================
# RESPONSE CACHING
# ============================================================================

class ResponseCache:
    """Cache query responses to avoid rate limiting."""

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self._cache: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get cached response if not expired."""
        if key in self._cache:
            response, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return response
            else:
                del self._cache[key]
        return None

    def set(self, key: str, response: Any) -> None:
        """Cache response with current timestamp."""
        self._cache[key] = (response, time.time())

    def clear(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()


@pytest.fixture(scope="session")
def response_cache() -> ResponseCache:
    """Create response cache with session scope."""
    return ResponseCache(ttl=3600)


@pytest.fixture
def cached_query_executor(sparql_query_executor, response_cache: ResponseCache):
    """Execute SPARQL queries with response caching."""
    def _execute(endpoint_url: str, query: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Execute SPARQL query with caching.

        Args:
            endpoint_url: SPARQL endpoint URL
            query: SPARQL query string
            use_cache: Whether to use cached responses

        Returns:
            Query results as dictionary
        """
        cache_key = f"{endpoint_url}:{hash(query)}"

        if use_cache:
            cached = response_cache.get(cache_key)
            if cached is not None:
                return cached

        result = sparql_query_executor(endpoint_url, query)

        if use_cache:
            response_cache.set(cache_key, result)

        return result

    return _execute


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

class PerformanceMonitor:
    """Monitor query performance and track baselines."""

    def __init__(self):
        self.measurements: Dict[str, list[float]] = {}

    def measure(self, query_name: str, duration: float) -> None:
        """Record a performance measurement."""
        if query_name not in self.measurements:
            self.measurements[query_name] = []
        self.measurements[query_name].append(duration)

    def get_stats(self, query_name: str) -> Optional[Dict[str, float]]:
        """Get statistics for a query."""
        if query_name not in self.measurements:
            return None

        measurements = self.measurements[query_name]
        return {
            "count": len(measurements),
            "mean": sum(measurements) / len(measurements),
            "min": min(measurements),
            "max": max(measurements),
        }


@pytest.fixture(scope="session")
def performance_monitor() -> PerformanceMonitor:
    """Create performance monitor with session scope."""
    return PerformanceMonitor()


@pytest.fixture
def timed_query_executor(sparql_query_executor, performance_monitor: PerformanceMonitor):
    """Execute SPARQL queries with timing."""
    def _execute(
        endpoint_url: str,
        query: str,
        query_name: Optional[str] = None
    ) -> tuple[Dict[str, Any], float]:
        """
        Execute SPARQL query and measure execution time.

        Args:
            endpoint_url: SPARQL endpoint URL
            query: SPARQL query string
            query_name: Optional name for tracking performance

        Returns:
            Tuple of (results, duration_seconds)
        """
        start_time = time.time()
        result = sparql_query_executor(endpoint_url, query)
        duration = time.time() - start_time

        if query_name:
            performance_monitor.measure(query_name, duration)

        return result, duration

    return _execute


# ============================================================================
# TEST DATA
# ============================================================================

@pytest.fixture
def sample_protein_ids() -> list[str]:
    """Sample UniProt protein IDs for testing."""
    return [
        "P12345",  # Example protein
        "P04637",  # TP53 (Tumor protein p53)
        "P68871",  # HBB (Hemoglobin subunit beta)
        "P01308",  # INS (Insulin)
        "P00533",  # EGFR (Epidermal growth factor receptor)
    ]


@pytest.fixture
def sample_go_terms() -> list[str]:
    """Sample Gene Ontology terms for testing."""
    return [
        "GO:0005515",  # protein binding
        "GO:0003677",  # DNA binding
        "GO:0005634",  # nucleus
        "GO:0005737",  # cytoplasm
        "GO:0016301",  # kinase activity
    ]


@pytest.fixture
def sample_taxonomy_ids() -> list[str]:
    """Sample NCBI taxonomy IDs for testing."""
    return [
        "9606",   # Homo sapiens
        "10090",  # Mus musculus
        "7227",   # Drosophila melanogaster
        "6239",   # Caenorhabditis elegans
        "559292", # Saccharomyces cerevisiae S288C
    ]


@pytest.fixture
def expected_protein_properties() -> set[str]:
    """Expected properties for protein queries."""
    return {
        "protein",
        "mnemonic",
        "name",
        "organism",
        "sequence",
        "length",
        "mass",
    }


# ============================================================================
# CLEANUP
# ============================================================================

@pytest.fixture(autouse=True, scope="session")
def cleanup_session(request, performance_monitor: PerformanceMonitor):
    """Cleanup after test session."""
    yield

    # Print performance summary
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)

    for query_name in sorted(performance_monitor.measurements.keys()):
        stats = performance_monitor.get_stats(query_name)
        if stats:
            print(f"\n{query_name}:")
            print(f"  Count: {stats['count']}")
            print(f"  Mean:  {stats['mean']:.3f}s")
            print(f"  Min:   {stats['min']:.3f}s")
            print(f"  Max:   {stats['max']:.3f}s")

    print("\n" + "=" * 70)
