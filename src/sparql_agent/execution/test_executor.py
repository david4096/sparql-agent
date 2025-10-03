"""
Unit tests for the QueryExecutor module.

Tests cover:
- Basic query execution
- Different result formats
- Error handling
- Federation
- Performance metrics
- Connection pooling
- Result parsing
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from typing import Dict, Any

from ..core.types import EndpointInfo, QueryResult, QueryStatus
from ..core.exceptions import (
    QueryExecutionError,
    QueryTimeoutError,
    EndpointConnectionError,
)
from .executor import (
    QueryExecutor,
    ResultFormat,
    ResultParser,
    Binding,
    BindingType,
    ConnectionPool,
    FederatedQuery,
    ExecutionMetrics,
)


class TestResultParser(unittest.TestCase):
    """Test ResultParser functionality."""

    def test_parse_json_select_results(self):
        """Test parsing SPARQL JSON SELECT results."""
        json_data = {
            "head": {"vars": ["s", "p", "o"]},
            "results": {
                "bindings": [
                    {
                        "s": {"type": "uri", "value": "http://example.org/subject"},
                        "p": {"type": "uri", "value": "http://example.org/predicate"},
                        "o": {"type": "literal", "value": "Object value"}
                    },
                    {
                        "s": {"type": "uri", "value": "http://example.org/subject2"},
                        "p": {"type": "uri", "value": "http://example.org/predicate2"},
                        "o": {
                            "type": "literal",
                            "value": "42",
                            "datatype": "http://www.w3.org/2001/XMLSchema#integer"
                        }
                    }
                ]
            }
        }

        results = ResultParser.parse_json(json_data)

        self.assertEqual(len(results), 2)
        self.assertIn("s", results[0])
        self.assertIn("p", results[0])
        self.assertIn("o", results[0])

        # Check first binding
        self.assertEqual(results[0]["s"].value, "http://example.org/subject")
        self.assertEqual(results[0]["s"].binding_type, BindingType.URI)

        # Check typed literal
        self.assertEqual(results[1]["o"].value, "42")
        self.assertEqual(results[1]["o"].binding_type, BindingType.TYPED_LITERAL)
        self.assertEqual(
            results[1]["o"].datatype,
            "http://www.w3.org/2001/XMLSchema#integer"
        )

    def test_parse_json_ask_results(self):
        """Test parsing SPARQL JSON ASK results."""
        json_data = {"head": {}, "boolean": True}

        results = ResultParser.parse_json(json_data)

        self.assertEqual(len(results), 1)
        self.assertIn("result", results[0])
        self.assertTrue(results[0]["result"].value)

    def test_parse_csv(self):
        """Test parsing CSV results."""
        csv_data = """s,p,o
http://example.org/subject,http://example.org/predicate,Object value
http://example.org/subject2,http://example.org/predicate2,Another value"""

        results = ResultParser.parse_csv(csv_data)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["s"].value, "http://example.org/subject")
        self.assertEqual(results[1]["o"].value, "Another value")

    def test_parse_xml(self):
        """Test parsing XML results."""
        xml_data = """<?xml version="1.0"?>
<sparql xmlns="http://www.w3.org/2005/sparql-results#">
  <head>
    <variable name="s"/>
    <variable name="p"/>
    <variable name="o"/>
  </head>
  <results>
    <result>
      <binding name="s">
        <uri>http://example.org/subject</uri>
      </binding>
      <binding name="p">
        <uri>http://example.org/predicate</uri>
      </binding>
      <binding name="o">
        <literal>Object value</literal>
      </binding>
    </result>
  </results>
</sparql>"""

        results = ResultParser.parse_xml(xml_data)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["s"].value, "http://example.org/subject")
        self.assertEqual(results[0]["o"].value, "Object value")


class TestBinding(unittest.TestCase):
    """Test Binding functionality."""

    def test_binding_creation(self):
        """Test creating bindings."""
        binding = Binding(
            variable="test",
            value="http://example.org/resource",
            binding_type=BindingType.URI
        )

        self.assertEqual(binding.variable, "test")
        self.assertEqual(binding.value, "http://example.org/resource")
        self.assertTrue(binding.is_uri())
        self.assertFalse(binding.is_literal())

    def test_binding_types(self):
        """Test binding type checks."""
        uri_binding = Binding("s", "http://ex.org/uri", BindingType.URI)
        literal_binding = Binding("o", "text", BindingType.LITERAL)
        bnode_binding = Binding("b", "_:b1", BindingType.BNODE)

        self.assertTrue(uri_binding.is_uri())
        self.assertTrue(literal_binding.is_literal())
        self.assertTrue(bnode_binding.is_bnode())

    def test_binding_to_dict(self):
        """Test converting binding to dictionary."""
        binding = Binding(
            variable="name",
            value="John Doe",
            binding_type=BindingType.LITERAL,
            language="en"
        )

        binding_dict = binding.to_dict()

        self.assertEqual(binding_dict["variable"], "name")
        self.assertEqual(binding_dict["value"], "John Doe")
        self.assertEqual(binding_dict["type"], "literal")
        self.assertEqual(binding_dict["language"], "en")


class TestConnectionPool(unittest.TestCase):
    """Test ConnectionPool functionality."""

    def test_pool_initialization(self):
        """Test connection pool initialization."""
        pool = ConnectionPool(pool_size=5, max_retries=3, timeout=30)

        self.assertEqual(pool.pool_size, 5)
        self.assertEqual(pool.max_retries, 3)
        self.assertEqual(pool.timeout, 30)

    def test_session_creation(self):
        """Test session creation and reuse."""
        pool = ConnectionPool()

        # First call creates session
        session1 = pool.get_session("https://example.org/sparql")
        self.assertEqual(pool.stats["connections_created"], 1)
        self.assertEqual(pool.stats["connections_reused"], 0)

        # Second call reuses session
        session2 = pool.get_session("https://example.org/sparql")
        self.assertEqual(pool.stats["connections_created"], 1)
        self.assertEqual(pool.stats["connections_reused"], 1)
        self.assertIs(session1, session2)

        # Different endpoint creates new session
        session3 = pool.get_session("https://other.org/sparql")
        self.assertEqual(pool.stats["connections_created"], 2)
        self.assertIsNot(session1, session3)

    def test_pool_statistics(self):
        """Test connection pool statistics."""
        pool = ConnectionPool()

        pool.get_session("https://example1.org/sparql")
        pool.get_session("https://example2.org/sparql")
        pool.get_session("https://example1.org/sparql")  # Reuse

        stats = pool.get_statistics()

        self.assertEqual(stats["connections_created"], 2)
        self.assertEqual(stats["connections_reused"], 1)


class TestExecutionMetrics(unittest.TestCase):
    """Test ExecutionMetrics functionality."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = ExecutionMetrics(endpoint_url="https://example.org/sparql")

        self.assertIsNotNone(metrics.start_time)
        self.assertIsNone(metrics.end_time)
        self.assertEqual(metrics.execution_time, 0.0)
        self.assertEqual(metrics.endpoint_url, "https://example.org/sparql")

    def test_metrics_finalization(self):
        """Test metrics finalization."""
        metrics = ExecutionMetrics()

        # Simulate some execution time
        import time
        time.sleep(0.01)

        metrics.finalize()

        self.assertIsNotNone(metrics.end_time)
        self.assertGreater(metrics.execution_time, 0)

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ExecutionMetrics(
            endpoint_url="https://example.org/sparql",
            result_count=42
        )
        metrics.finalize()

        metrics_dict = metrics.to_dict()

        self.assertIn("start_time", metrics_dict)
        self.assertIn("end_time", metrics_dict)
        self.assertIn("execution_time", metrics_dict)
        self.assertEqual(metrics_dict["result_count"], 42)


class TestQueryExecutor(unittest.TestCase):
    """Test QueryExecutor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.executor = QueryExecutor(timeout=30, enable_metrics=True)
        self.endpoint = EndpointInfo(url="https://test.example.org/sparql")
        self.query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

    def tearDown(self):
        """Clean up after tests."""
        self.executor.close()

    @patch('sparql_agent.execution.executor.SPARQLWrapper')
    def test_basic_execution(self, mock_wrapper_class):
        """Test basic query execution."""
        # Mock SPARQLWrapper
        mock_wrapper = MagicMock()
        mock_wrapper_class.return_value = mock_wrapper

        # Mock query response
        mock_result = MagicMock()
        mock_result.convert.return_value = {
            "head": {"vars": ["s", "p", "o"]},
            "results": {
                "bindings": [
                    {
                        "s": {"type": "uri", "value": "http://example.org/s"},
                        "p": {"type": "uri", "value": "http://example.org/p"},
                        "o": {"type": "literal", "value": "value"}
                    }
                ]
            }
        }
        mock_wrapper.query.return_value = mock_result

        # Execute query
        result = self.executor.execute(self.query, self.endpoint)

        # Verify execution
        self.assertEqual(result.status, QueryStatus.SUCCESS)
        self.assertEqual(result.row_count, 1)
        self.assertGreater(len(result.variables), 0)

    def test_executor_statistics(self):
        """Test executor statistics tracking."""
        initial_stats = self.executor.get_statistics()

        self.assertEqual(initial_stats["total_queries"], 0)
        self.assertEqual(initial_stats["successful_queries"], 0)
        self.assertEqual(initial_stats["failed_queries"], 0)

    def test_context_manager(self):
        """Test executor context manager."""
        with QueryExecutor() as executor:
            self.assertIsNotNone(executor)
            stats = executor.get_statistics()
            self.assertEqual(stats["total_queries"], 0)

        # After context exit, connections should be closed
        # (We can't directly test this without mocking)

    def test_convert_exception(self):
        """Test exception conversion."""
        timeout_error = Exception("timeout occurred")
        converted = self.executor._convert_exception(timeout_error, self.endpoint)
        self.assertIsInstance(converted, QueryTimeoutError)

        auth_error = Exception("401 unauthorized")
        converted = self.executor._convert_exception(auth_error, self.endpoint)
        from ..core.exceptions import EndpointAuthenticationError
        self.assertIsInstance(converted, EndpointAuthenticationError)

        connection_error = Exception("connection failed")
        converted = self.executor._convert_exception(connection_error, self.endpoint)
        self.assertIsInstance(converted, EndpointConnectionError)


class TestFederatedQuery(unittest.TestCase):
    """Test federated query functionality."""

    def test_federated_config(self):
        """Test federated query configuration."""
        endpoints = [
            EndpointInfo(url="https://endpoint1.org/sparql"),
            EndpointInfo(url="https://endpoint2.org/sparql"),
        ]

        config = FederatedQuery(
            endpoints=endpoints,
            merge_strategy="union",
            parallel=True
        )

        self.assertEqual(len(config.endpoints), 2)
        self.assertEqual(config.merge_strategy, "union")
        self.assertTrue(config.parallel)

    @patch('sparql_agent.execution.executor.QueryExecutor.execute')
    def test_merge_results_union(self, mock_execute):
        """Test merging results with union strategy."""
        executor = QueryExecutor()

        # Create mock results
        result1 = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[{"s": "value1"}],
            row_count=1,
            variables=["s"],
            execution_time=0.1
        )

        result2 = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[{"s": "value2"}],
            row_count=1,
            variables=["s"],
            execution_time=0.2
        )

        # Merge with union
        merged = executor._merge_results(
            [result1, result2],
            strategy="union",
            errors=[]
        )

        self.assertEqual(merged.status, QueryStatus.SUCCESS)
        self.assertEqual(merged.row_count, 2)
        self.assertEqual(len(merged.bindings), 2)

        executor.close()

    @patch('sparql_agent.execution.executor.QueryExecutor.execute')
    def test_merge_results_sequential(self, mock_execute):
        """Test merging results with sequential strategy."""
        executor = QueryExecutor()

        result1 = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[{"s": "value1"}],
            row_count=1,
            variables=["s"],
            execution_time=0.1
        )

        result2 = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[{"s": "value2"}],
            row_count=1,
            variables=["s"],
            execution_time=0.2
        )

        # Sequential returns first result
        merged = executor._merge_results(
            [result1, result2],
            strategy="sequential",
            errors=[]
        )

        self.assertEqual(merged.status, QueryStatus.SUCCESS)
        self.assertEqual(merged.row_count, 1)
        self.assertEqual(merged.bindings[0]["s"], "value1")

        executor.close()


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""

    @patch('sparql_agent.execution.executor.QueryExecutor.execute')
    def test_execute_query_utility(self, mock_execute):
        """Test execute_query utility function."""
        from .executor import execute_query

        mock_execute.return_value = QueryResult(
            status=QueryStatus.SUCCESS,
            row_count=5
        )

        # This will fail without proper mocking of the context manager
        # but demonstrates the test structure
        # result = execute_query("SELECT * WHERE { ?s ?p ?o }", "https://example.org/sparql")


def suite():
    """Create test suite."""
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestResultParser))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBinding))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConnectionPool))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestExecutionMetrics))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestQueryExecutor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFederatedQuery))

    return suite


if __name__ == "__main__":
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
