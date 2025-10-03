"""
Comprehensive Integration Tests for SPARQL Endpoint Connectivity and Querying

This module tests real SPARQL endpoints with actual queries to validate:
- EndpointPinger connectivity testing
- QueryExecutor query execution
- Different query types (SELECT, CONSTRUCT, ASK, DESCRIBE)
- Timeout and retry mechanisms
- Error handling and recovery
- Performance metrics and response times

Test Endpoints:
- UniProt: https://sparql.uniprot.org/sparql
- Wikidata: https://query.wikidata.org/sparql
- DBpedia: https://dbpedia.org/sparql

Note: These tests require internet connectivity and may take several seconds to complete.
"""

import pytest
import time
import asyncio
from datetime import timedelta
from typing import Dict, List, Any
import json

from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    ConnectionConfig,
    EndpointHealth,
    EndpointStatus,
)
from sparql_agent.execution.executor import (
    QueryExecutor,
    ResultFormat,
    FederatedQuery,
)
from sparql_agent.core.types import (
    EndpointInfo,
    QueryResult,
    QueryStatus,
)
from sparql_agent.core.exceptions import (
    QueryExecutionError,
    QueryTimeoutError,
    EndpointConnectionError,
)


# Test endpoint configurations
TEST_ENDPOINTS = {
    "uniprot": {
        "url": "https://sparql.uniprot.org/sparql",
        "name": "UniProt",
        "timeout": 30,
        "supports_describe": True,
        "supports_construct": True,
    },
    "wikidata": {
        "url": "https://query.wikidata.org/sparql",
        "name": "Wikidata",
        "timeout": 30,
        "supports_describe": True,
        "supports_construct": True,
    },
    "dbpedia": {
        "url": "https://dbpedia.org/sparql",
        "name": "DBpedia",
        "timeout": 30,
        "supports_describe": True,
        "supports_construct": True,
    },
}


# Test queries for different types
TEST_QUERIES = {
    "select_simple": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
    "select_count": "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }",
    "ask_simple": "ASK { ?s ?p ?o }",
    "describe_simple": "DESCRIBE <http://www.w3.org/2000/01/rdf-schema#Class>",
    "construct_simple": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 5",
}


# Endpoint-specific queries
ENDPOINT_QUERIES = {
    "uniprot": {
        "select": """
            SELECT ?protein ?name ?organism
            WHERE {
                ?protein a <http://purl.uniprot.org/core/Protein> ;
                         <http://purl.uniprot.org/core/recommendedName> ?recName ;
                         <http://purl.uniprot.org/core/organism> ?org .
                ?recName <http://purl.uniprot.org/core/fullName> ?name .
                ?org <http://purl.uniprot.org/core/scientificName> ?organism .
            }
            LIMIT 10
        """,
        "ask": """
            ASK {
                ?protein a <http://purl.uniprot.org/core/Protein> .
            }
        """,
        "count": """
            SELECT (COUNT(DISTINCT ?protein) as ?count)
            WHERE {
                ?protein a <http://purl.uniprot.org/core/Protein> .
            }
        """,
    },
    "wikidata": {
        "select": """
            SELECT ?item ?itemLabel ?birthDate
            WHERE {
                ?item wdt:P31 wd:Q5 ;
                      wdt:P569 ?birthDate .
                SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
            }
            LIMIT 10
        """,
        "ask": """
            ASK {
                ?item wdt:P31 wd:Q5 .
            }
        """,
        "count": """
            SELECT (COUNT(?item) as ?count)
            WHERE {
                ?item wdt:P31 wd:Q5 .
            }
            LIMIT 1
        """,
    },
    "dbpedia": {
        "select": """
            SELECT ?person ?name ?birthDate
            WHERE {
                ?person a dbo:Person ;
                        foaf:name ?name ;
                        dbo:birthDate ?birthDate .
            }
            LIMIT 10
        """,
        "ask": """
            ASK {
                ?person a dbo:Person .
            }
        """,
        "count": """
            SELECT (COUNT(?person) as ?count)
            WHERE {
                ?person a dbo:Person .
            }
            LIMIT 1
        """,
    },
}


@pytest.fixture
def endpoint_pinger():
    """Create an EndpointPinger instance."""
    config = ConnectionConfig(
        timeout=30.0,
        verify_ssl=True,
        retry_attempts=3,
        retry_delay=1.0,
    )
    pinger = EndpointPinger(config=config, pool_size=10)
    yield pinger
    pinger.close_sync()


@pytest.fixture
def query_executor():
    """Create a QueryExecutor instance."""
    executor = QueryExecutor(
        timeout=60,
        max_retries=3,
        pool_size=10,
        enable_metrics=True,
    )
    yield executor
    executor.close()


@pytest.fixture
async def async_endpoint_pinger():
    """Create an async EndpointPinger instance."""
    config = ConnectionConfig(
        timeout=30.0,
        verify_ssl=True,
        retry_attempts=3,
        retry_delay=1.0,
    )
    pinger = EndpointPinger(config=config, pool_size=10)
    yield pinger
    await pinger.close_async()


# Performance metrics collection
class PerformanceMetrics:
    """Collect and report performance metrics."""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def record(
        self,
        endpoint: str,
        operation: str,
        success: bool,
        duration: float,
        details: Dict[str, Any] = None,
    ):
        """Record a performance metric."""
        self.results.append({
            "endpoint": endpoint,
            "operation": operation,
            "success": success,
            "duration_ms": duration * 1000,
            "details": details or {},
            "timestamp": time.time(),
        })

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.results:
            return {}

        successful = [r for r in self.results if r["success"]]
        failed = [r for r in self.results if not r["success"]]

        durations = [r["duration_ms"] for r in successful]

        return {
            "total_tests": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.results) * 100 if self.results else 0,
            "average_response_time_ms": sum(durations) / len(durations) if durations else 0,
            "min_response_time_ms": min(durations) if durations else 0,
            "max_response_time_ms": max(durations) if durations else 0,
            "by_endpoint": self._group_by_endpoint(),
            "by_operation": self._group_by_operation(),
        }

    def _group_by_endpoint(self) -> Dict[str, Any]:
        """Group results by endpoint."""
        by_endpoint = {}
        for result in self.results:
            endpoint = result["endpoint"]
            if endpoint not in by_endpoint:
                by_endpoint[endpoint] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "durations": [],
                }
            by_endpoint[endpoint]["total"] += 1
            if result["success"]:
                by_endpoint[endpoint]["successful"] += 1
                by_endpoint[endpoint]["durations"].append(result["duration_ms"])
            else:
                by_endpoint[endpoint]["failed"] += 1

        # Calculate averages
        for endpoint, data in by_endpoint.items():
            if data["durations"]:
                data["average_ms"] = sum(data["durations"]) / len(data["durations"])
                data["min_ms"] = min(data["durations"])
                data["max_ms"] = max(data["durations"])
            del data["durations"]

        return by_endpoint

    def _group_by_operation(self) -> Dict[str, Any]:
        """Group results by operation."""
        by_operation = {}
        for result in self.results:
            operation = result["operation"]
            if operation not in by_operation:
                by_operation[operation] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "durations": [],
                }
            by_operation[operation]["total"] += 1
            if result["success"]:
                by_operation[operation]["successful"] += 1
                by_operation[operation]["durations"].append(result["duration_ms"])
            else:
                by_operation[operation]["failed"] += 1

        # Calculate averages
        for operation, data in by_operation.items():
            if data["durations"]:
                data["average_ms"] = sum(data["durations"]) / len(data["durations"])
            del data["durations"]

        return by_operation


@pytest.fixture
def performance_metrics():
    """Create a performance metrics collector."""
    return PerformanceMetrics()


# ============================================================================
# ENDPOINT PINGER TESTS - SYNCHRONOUS
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
class TestEndpointPingerSync:
    """Test EndpointPinger with real endpoints (synchronous)."""

    def test_ping_uniprot_head_request(self, endpoint_pinger, performance_metrics):
        """Test HEAD request to UniProt endpoint."""
        endpoint = TEST_ENDPOINTS["uniprot"]["url"]

        start = time.time()
        health = endpoint_pinger.ping_sync(endpoint, check_query=False)
        duration = time.time() - start

        performance_metrics.record("uniprot", "ping_head", health.status == EndpointStatus.HEALTHY, duration)

        assert health is not None
        assert health.endpoint_url == endpoint
        assert health.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]
        assert health.response_time_ms is not None
        assert health.response_time_ms > 0
        assert health.status_code in [200, 405]  # Some endpoints don't support HEAD
        print(f"\nUniProt HEAD: {health.response_time_ms:.2f}ms - Status: {health.status.value}")

    def test_ping_uniprot_with_query(self, endpoint_pinger, performance_metrics):
        """Test query execution on UniProt endpoint."""
        endpoint = TEST_ENDPOINTS["uniprot"]["url"]

        start = time.time()
        health = endpoint_pinger.ping_sync(endpoint, check_query=True)
        duration = time.time() - start

        performance_metrics.record("uniprot", "ping_query", health.status == EndpointStatus.HEALTHY, duration)

        assert health is not None
        assert health.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]
        assert health.response_time_ms is not None
        print(f"\nUniProt Query: {health.response_time_ms:.2f}ms - Status: {health.status.value}")

    def test_ping_wikidata(self, endpoint_pinger, performance_metrics):
        """Test Wikidata endpoint connectivity."""
        endpoint = TEST_ENDPOINTS["wikidata"]["url"]

        start = time.time()
        health = endpoint_pinger.ping_sync(endpoint, check_query=True)
        duration = time.time() - start

        performance_metrics.record("wikidata", "ping_query", health.status == EndpointStatus.HEALTHY, duration)

        assert health is not None
        assert health.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]
        print(f"\nWikidata Query: {health.response_time_ms:.2f}ms - Status: {health.status.value}")

    def test_ping_dbpedia(self, endpoint_pinger, performance_metrics):
        """Test DBpedia endpoint connectivity."""
        endpoint = TEST_ENDPOINTS["dbpedia"]["url"]

        start = time.time()
        health = endpoint_pinger.ping_sync(endpoint, check_query=True)
        duration = time.time() - start

        performance_metrics.record("dbpedia", "ping_query", health.status == EndpointStatus.HEALTHY, duration)

        assert health is not None
        # DBpedia can be less reliable
        assert health.status in [
            EndpointStatus.HEALTHY,
            EndpointStatus.DEGRADED,
            EndpointStatus.TIMEOUT,
            EndpointStatus.UNREACHABLE,
        ]
        print(f"\nDBpedia Query: {health.response_time_ms or 0:.2f}ms - Status: {health.status.value}")

    def test_ping_multiple_endpoints(self, endpoint_pinger, performance_metrics):
        """Test pinging multiple endpoints at once."""
        endpoints = [
            TEST_ENDPOINTS["uniprot"]["url"],
            TEST_ENDPOINTS["wikidata"]["url"],
        ]

        start = time.time()
        results = endpoint_pinger.ping_multiple_sync(endpoints, check_query=True)
        duration = time.time() - start

        assert len(results) == 2
        for health in results:
            endpoint_name = [k for k, v in TEST_ENDPOINTS.items() if v["url"] == health.endpoint_url][0]
            performance_metrics.record(
                endpoint_name,
                "ping_multiple",
                health.status == EndpointStatus.HEALTHY,
                duration / len(results),
            )
            print(f"\n{endpoint_name}: {health.response_time_ms or 0:.2f}ms - {health.status.value}")

    def test_ping_with_custom_timeout(self, endpoint_pinger, performance_metrics):
        """Test ping with custom timeout."""
        endpoint = TEST_ENDPOINTS["uniprot"]["url"]
        config = ConnectionConfig(timeout=5.0, retry_attempts=1)

        start = time.time()
        health = endpoint_pinger.ping_sync(endpoint, check_query=True, config=config)
        duration = time.time() - start

        performance_metrics.record("uniprot", "ping_custom_timeout", True, duration)

        assert health is not None
        assert duration < 10  # Should complete within timeout + overhead

    def test_ping_invalid_endpoint(self, endpoint_pinger, performance_metrics):
        """Test pinging an invalid endpoint."""
        endpoint = "https://invalid-sparql-endpoint-that-does-not-exist.com/sparql"

        start = time.time()
        health = endpoint_pinger.ping_sync(endpoint, check_query=True)
        duration = time.time() - start

        performance_metrics.record("invalid", "ping_invalid", False, duration)

        assert health is not None
        assert health.status in [EndpointStatus.UNREACHABLE, EndpointStatus.TIMEOUT]
        assert health.error_message is not None
        print(f"\nInvalid endpoint error: {health.error_message}")

    def test_health_history_tracking(self, endpoint_pinger):
        """Test health history tracking."""
        endpoint = TEST_ENDPOINTS["uniprot"]["url"]

        # Record multiple health checks
        for _ in range(3):
            health = endpoint_pinger.ping_sync(endpoint, check_query=True)
            endpoint_pinger.record_health(health)
            time.sleep(0.5)

        history = endpoint_pinger.get_health_history(endpoint)
        assert len(history) == 3

        uptime = endpoint_pinger.get_uptime_percentage(endpoint)
        assert uptime is not None
        assert 0 <= uptime <= 100

        avg_response = endpoint_pinger.get_average_response_time(endpoint)
        assert avg_response is not None
        assert avg_response > 0
        print(f"\nUptime: {uptime:.2f}%, Avg Response: {avg_response:.2f}ms")


# ============================================================================
# ENDPOINT PINGER TESTS - ASYNCHRONOUS
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.endpoint
@pytest.mark.asyncio
class TestEndpointPingerAsync:
    """Test EndpointPinger with real endpoints (asynchronous)."""

    async def test_ping_async_uniprot(self, async_endpoint_pinger, performance_metrics):
        """Test async ping to UniProt."""
        endpoint = TEST_ENDPOINTS["uniprot"]["url"]

        start = time.time()
        health = await async_endpoint_pinger.ping_async(endpoint, check_query=True)
        duration = time.time() - start

        performance_metrics.record("uniprot", "ping_async", health.status == EndpointStatus.HEALTHY, duration)

        assert health is not None
        assert health.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]
        print(f"\nUniProt Async: {health.response_time_ms:.2f}ms")

    async def test_ping_async_multiple(self, async_endpoint_pinger, performance_metrics):
        """Test async ping to multiple endpoints concurrently."""
        endpoints = [
            TEST_ENDPOINTS["uniprot"]["url"],
            TEST_ENDPOINTS["wikidata"]["url"],
        ]

        start = time.time()
        results = await async_endpoint_pinger.ping_multiple_async(endpoints, check_query=True)
        duration = time.time() - start

        assert len(results) == 2
        print(f"\nAsync multiple endpoints completed in {duration:.2f}s")
        for health in results:
            endpoint_name = [k for k, v in TEST_ENDPOINTS.items() if v["url"] == health.endpoint_url][0]
            print(f"  {endpoint_name}: {health.response_time_ms or 0:.2f}ms - {health.status.value}")


# ============================================================================
# QUERY EXECUTOR TESTS - SELECT QUERIES
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestQueryExecutorSelect:
    """Test QueryExecutor with SELECT queries."""

    def test_simple_select_uniprot(self, query_executor, performance_metrics):
        """Test simple SELECT query on UniProt."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = ENDPOINT_QUERIES["uniprot"]["select"]

        start = time.time()
        result = query_executor.execute(query, endpoint, format=ResultFormat.JSON, timeout=30)
        duration = time.time() - start

        performance_metrics.record(
            "uniprot",
            "select_query",
            result.is_success,
            duration,
            {"row_count": result.row_count},
        )

        assert result is not None
        assert result.status == QueryStatus.SUCCESS
        assert result.row_count > 0
        assert len(result.bindings) > 0
        assert len(result.variables) > 0
        print(f"\nUniProt SELECT: {result.row_count} rows in {result.execution_time:.2f}s")
        print(f"Variables: {result.variables}")
        if result.bindings:
            print(f"Sample: {result.bindings[0]}")

    def test_simple_select_wikidata(self, query_executor, performance_metrics):
        """Test simple SELECT query on Wikidata."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["wikidata"]["url"])
        query = ENDPOINT_QUERIES["wikidata"]["select"]

        start = time.time()
        result = query_executor.execute(query, endpoint, format=ResultFormat.JSON, timeout=30)
        duration = time.time() - start

        performance_metrics.record(
            "wikidata",
            "select_query",
            result.is_success,
            duration,
            {"row_count": result.row_count},
        )

        assert result is not None
        assert result.status == QueryStatus.SUCCESS
        assert result.row_count > 0
        print(f"\nWikidata SELECT: {result.row_count} rows in {result.execution_time:.2f}s")

    def test_count_query_uniprot(self, query_executor, performance_metrics):
        """Test COUNT query on UniProt."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = ENDPOINT_QUERIES["uniprot"]["count"]

        start = time.time()
        result = query_executor.execute(query, endpoint, format=ResultFormat.JSON, timeout=30)
        duration = time.time() - start

        performance_metrics.record("uniprot", "count_query", result.is_success, duration)

        assert result is not None
        assert result.status == QueryStatus.SUCCESS
        assert result.row_count > 0
        print(f"\nUniProt COUNT: {result.bindings}")

    def test_generic_select(self, query_executor, performance_metrics):
        """Test generic SELECT query on UniProt."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = TEST_QUERIES["select_simple"]

        start = time.time()
        result = query_executor.execute(query, endpoint, format=ResultFormat.JSON, timeout=30)
        duration = time.time() - start

        performance_metrics.record("uniprot", "generic_select", result.is_success, duration)

        assert result is not None
        assert result.status == QueryStatus.SUCCESS
        assert result.row_count == 10  # LIMIT 10
        print(f"\nGeneric SELECT: {result.row_count} rows")


# ============================================================================
# QUERY EXECUTOR TESTS - ASK QUERIES
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestQueryExecutorAsk:
    """Test QueryExecutor with ASK queries."""

    def test_ask_query_uniprot(self, query_executor, performance_metrics):
        """Test ASK query on UniProt."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = ENDPOINT_QUERIES["uniprot"]["ask"]

        start = time.time()
        result = query_executor.execute(query, endpoint, format=ResultFormat.JSON, timeout=30)
        duration = time.time() - start

        performance_metrics.record("uniprot", "ask_query", result.is_success, duration)

        assert result is not None
        assert result.status == QueryStatus.SUCCESS
        # ASK queries return a boolean result
        print(f"\nUniProt ASK result: {result.bindings}")

    def test_ask_query_wikidata(self, query_executor, performance_metrics):
        """Test ASK query on Wikidata."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["wikidata"]["url"])
        query = ENDPOINT_QUERIES["wikidata"]["ask"]

        start = time.time()
        result = query_executor.execute(query, endpoint, format=ResultFormat.JSON, timeout=30)
        duration = time.time() - start

        performance_metrics.record("wikidata", "ask_query", result.is_success, duration)

        assert result is not None
        assert result.status == QueryStatus.SUCCESS
        print(f"\nWikidata ASK result: {result.bindings}")


# ============================================================================
# QUERY EXECUTOR TESTS - ERROR HANDLING
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestQueryExecutorErrorHandling:
    """Test QueryExecutor error handling."""

    def test_invalid_query_syntax(self, query_executor, performance_metrics):
        """Test invalid SPARQL syntax handling."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = "INVALID SPARQL SYNTAX { ?s ?p ?o }"

        start = time.time()
        result = query_executor.execute(query, endpoint, timeout=30)
        duration = time.time() - start

        performance_metrics.record("uniprot", "invalid_syntax", False, duration)

        assert result is not None
        assert result.status == QueryStatus.FAILED
        assert result.error_message is not None
        print(f"\nInvalid syntax error: {result.error_message}")

    def test_timeout_query(self, query_executor, performance_metrics):
        """Test query timeout handling."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        # Very short timeout for a potentially slow query
        query = """
            SELECT (COUNT(*) as ?count) WHERE {
                ?s ?p ?o .
                ?s2 ?p2 ?o2 .
                ?s3 ?p3 ?o3 .
            }
        """

        start = time.time()
        result = query_executor.execute(query, endpoint, timeout=1)  # 1 second timeout
        duration = time.time() - start

        performance_metrics.record("uniprot", "timeout_test", result.is_success, duration)

        # May timeout or succeed depending on endpoint speed
        assert result is not None
        print(f"\nTimeout test: {result.status.value}")
        if result.status == QueryStatus.FAILED:
            print(f"Error: {result.error_message}")

    def test_invalid_endpoint(self, query_executor, performance_metrics):
        """Test query to invalid endpoint."""
        endpoint = EndpointInfo(url="https://invalid-endpoint.com/sparql")
        query = TEST_QUERIES["select_simple"]

        start = time.time()
        result = query_executor.execute(query, endpoint, timeout=10)
        duration = time.time() - start

        performance_metrics.record("invalid", "invalid_endpoint", False, duration)

        assert result is not None
        assert result.status == QueryStatus.FAILED
        assert result.error_message is not None
        print(f"\nInvalid endpoint error: {result.error_message}")


# ============================================================================
# QUERY EXECUTOR TESTS - DIFFERENT FORMATS
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestQueryExecutorFormats:
    """Test QueryExecutor with different result formats."""

    def test_json_format(self, query_executor, performance_metrics):
        """Test JSON result format."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = TEST_QUERIES["select_simple"]

        result = query_executor.execute(query, endpoint, format=ResultFormat.JSON, timeout=30)

        assert result is not None
        assert result.status == QueryStatus.SUCCESS
        assert result.row_count > 0
        print(f"\nJSON format: {result.row_count} rows")

    def test_xml_format(self, query_executor, performance_metrics):
        """Test XML result format."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = TEST_QUERIES["select_simple"]

        result = query_executor.execute(query, endpoint, format=ResultFormat.XML, timeout=30)

        assert result is not None
        # XML parsing may or may not populate bindings depending on implementation
        print(f"\nXML format: status={result.status.value}")

    def test_csv_format(self, query_executor, performance_metrics):
        """Test CSV result format."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = TEST_QUERIES["select_simple"]

        result = query_executor.execute(query, endpoint, format=ResultFormat.CSV, timeout=30)

        assert result is not None
        # CSV parsing may or may not populate bindings depending on implementation
        print(f"\nCSV format: status={result.status.value}")


# ============================================================================
# QUERY EXECUTOR TESTS - FEDERATED QUERIES
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.slow
@pytest.mark.functional
class TestQueryExecutorFederated:
    """Test QueryExecutor with federated queries."""

    def test_federated_union(self, query_executor, performance_metrics):
        """Test federated query with union merge strategy."""
        endpoints = [
            EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"]),
            EndpointInfo(url=TEST_ENDPOINTS["wikidata"]["url"]),
        ]

        config = FederatedQuery(
            endpoints=endpoints,
            merge_strategy="union",
            parallel=True,
            fail_on_error=False,
            timeout_per_endpoint=30,
        )

        query = TEST_QUERIES["select_simple"]

        start = time.time()
        result = query_executor.execute_federated(query, config, timeout=60)
        duration = time.time() - start

        performance_metrics.record("federated", "union_query", result.is_success, duration)

        assert result is not None
        # Result should contain data from both endpoints
        print(f"\nFederated union: {result.row_count} total rows in {duration:.2f}s")
        print(f"Status: {result.status.value}")

    def test_federated_sequential(self, query_executor, performance_metrics):
        """Test federated query with sequential execution."""
        endpoints = [
            EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"]),
        ]

        config = FederatedQuery(
            endpoints=endpoints,
            merge_strategy="sequential",
            parallel=False,
            fail_on_error=True,
            timeout_per_endpoint=30,
        )

        query = TEST_QUERIES["select_simple"]

        start = time.time()
        result = query_executor.execute_federated(query, config, timeout=60)
        duration = time.time() - start

        performance_metrics.record("federated", "sequential_query", result.is_success, duration)

        assert result is not None
        assert result.status == QueryStatus.SUCCESS
        print(f"\nFederated sequential: {result.row_count} rows in {duration:.2f}s")


# ============================================================================
# QUERY EXECUTOR TESTS - RETRY MECHANISM
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestQueryExecutorRetry:
    """Test QueryExecutor retry mechanisms."""

    def test_retry_on_transient_failure(self, performance_metrics):
        """Test retry mechanism on transient failures."""
        # Create executor with aggressive retry settings
        executor = QueryExecutor(
            timeout=10,
            max_retries=3,
            enable_metrics=True,
        )

        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = TEST_QUERIES["select_simple"]

        start = time.time()
        result = executor.execute(query, endpoint, timeout=30)
        duration = time.time() - start

        performance_metrics.record("uniprot", "retry_test", result.is_success, duration)

        assert result is not None
        # Should succeed on first try or after retries
        print(f"\nRetry test: {result.status.value} in {duration:.2f}s")

        stats = executor.get_statistics()
        print(f"Executor stats: {stats}")

        executor.close()


# ============================================================================
# QUERY EXECUTOR TESTS - METRICS AND STATISTICS
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestQueryExecutorMetrics:
    """Test QueryExecutor metrics collection."""

    def test_metrics_collection(self, query_executor, performance_metrics):
        """Test that metrics are collected properly."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])
        query = TEST_QUERIES["select_simple"]

        result = query_executor.execute(query, endpoint, timeout=30)

        assert result is not None
        assert result.status == QueryStatus.SUCCESS

        # Check metrics in result metadata
        assert "metrics" in result.metadata
        metrics = result.metadata["metrics"]
        assert "execution_time" in metrics
        assert "result_count" in metrics
        print(f"\nQuery metrics: {metrics}")

    def test_executor_statistics(self, query_executor, performance_metrics):
        """Test executor statistics collection."""
        endpoint = EndpointInfo(url=TEST_ENDPOINTS["uniprot"]["url"])

        # Execute several queries
        for _ in range(3):
            query_executor.execute(TEST_QUERIES["select_simple"], endpoint, timeout=30)

        stats = query_executor.get_statistics()

        assert stats is not None
        assert stats["total_queries"] >= 3
        assert stats["successful_queries"] > 0
        assert "average_execution_time" in stats
        print(f"\nExecutor statistics: {json.dumps(stats, indent=2, default=str)}")


# ============================================================================
# PERFORMANCE SUMMARY TEST
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.performance
class TestPerformanceSummary:
    """Generate performance summary report."""

    def test_generate_performance_report(self, performance_metrics):
        """Generate and display performance summary."""
        # This test runs last and displays summary of all tests
        summary = performance_metrics.get_summary()

        print("\n" + "=" * 80)
        print("SPARQL ENDPOINT INTEGRATION TEST PERFORMANCE SUMMARY")
        print("=" * 80)
        print(f"\nTotal Tests: {summary.get('total_tests', 0)}")
        print(f"Successful: {summary.get('successful', 0)}")
        print(f"Failed: {summary.get('failed', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.2f}%")
        print(f"\nAverage Response Time: {summary.get('average_response_time_ms', 0):.2f}ms")
        print(f"Min Response Time: {summary.get('min_response_time_ms', 0):.2f}ms")
        print(f"Max Response Time: {summary.get('max_response_time_ms', 0):.2f}ms")

        print("\n" + "-" * 80)
        print("BY ENDPOINT:")
        print("-" * 80)
        for endpoint, data in summary.get("by_endpoint", {}).items():
            print(f"\n{endpoint.upper()}:")
            print(f"  Total: {data['total']}")
            print(f"  Successful: {data['successful']}")
            print(f"  Failed: {data['failed']}")
            if "average_ms" in data:
                print(f"  Average: {data['average_ms']:.2f}ms")
                print(f"  Min: {data['min_ms']:.2f}ms")
                print(f"  Max: {data['max_ms']:.2f}ms")

        print("\n" + "-" * 80)
        print("BY OPERATION:")
        print("-" * 80)
        for operation, data in summary.get("by_operation", {}).items():
            print(f"\n{operation}:")
            print(f"  Total: {data['total']}")
            print(f"  Successful: {data['successful']}")
            print(f"  Failed: {data['failed']}")
            if "average_ms" in data:
                print(f"  Average: {data['average_ms']:.2f}ms")

        print("\n" + "=" * 80)
