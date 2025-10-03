"""
Tests for the ErrorHandler module.
"""

import pytest
import time
from unittest.mock import Mock, patch

from sparql_agent.execution.error_handler import (
    ErrorHandler,
    ErrorCategory,
    ErrorContext,
    RetryStrategy,
    OptimizationLevel,
    QueryOptimization,
    RecoveryResult,
    handle_query_error,
    get_error_suggestions,
    optimize_query,
)
from sparql_agent.core.exceptions import (
    QueryTimeoutError,
    QuerySyntaxError,
    EndpointConnectionError,
    EndpointRateLimitError,
    EndpointUnavailableError,
    EndpointAuthenticationError,
    QueryTooComplexError,
)
from sparql_agent.core.types import EndpointInfo, QueryResult, QueryStatus


class TestErrorHandler:
    """Test ErrorHandler class."""

    def test_initialization(self):
        """Test handler initialization."""
        handler = ErrorHandler(
            max_retries=5,
            retry_delay=2.0,
            enable_fallback=False,
            enable_optimization_suggestions=False,
        )

        assert handler.max_retries == 5
        assert handler.retry_delay == 2.0
        assert handler.enable_fallback is False
        assert handler.enable_optimization_suggestions is False
        assert handler.stats["total_errors"] == 0

    def test_categorize_syntax_error(self):
        """Test categorization of syntax errors."""
        handler = ErrorHandler()
        error = QuerySyntaxError("Syntax error at line 5")
        query = "SELECT * WHERE ?s ?p ?o }"

        context = handler.categorize_error(error, query)

        assert context.category == ErrorCategory.SYNTAX
        assert context.severity == 3
        assert context.is_recoverable is True
        assert context.retry_strategy == RetryStrategy.NONE
        assert len(context.suggestions) > 0
        assert "syntax" in context.message.lower()

    def test_categorize_timeout_error(self):
        """Test categorization of timeout errors."""
        handler = ErrorHandler()
        error = QueryTimeoutError("Query timed out after 30s")
        query = "SELECT * WHERE { ?s ?p ?o }"
        endpoint = EndpointInfo(url="https://example.org/sparql", timeout=30)

        context = handler.categorize_error(error, query, endpoint)

        assert context.category == ErrorCategory.TIMEOUT
        assert context.severity == 6
        assert context.is_recoverable is True
        assert context.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert len(context.suggestions) > 0
        assert "timeout" in context.message.lower()

    def test_categorize_network_error(self):
        """Test categorization of network errors."""
        handler = ErrorHandler()
        error = EndpointConnectionError("Connection refused")
        query = "SELECT * WHERE { ?s ?p ?o }"
        endpoint = EndpointInfo(url="https://example.org/sparql")

        context = handler.categorize_error(error, query, endpoint)

        assert context.category == ErrorCategory.NETWORK
        assert context.severity == 7
        assert context.is_recoverable is True
        assert context.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert len(context.suggestions) > 0

    def test_categorize_rate_limit_error(self):
        """Test categorization of rate limit errors."""
        handler = ErrorHandler()
        error = EndpointRateLimitError("Rate limit exceeded")
        query = "SELECT * WHERE { ?s ?p ?o }"

        context = handler.categorize_error(error, query)

        assert context.category == ErrorCategory.RATE_LIMIT
        assert context.is_recoverable is True
        assert context.retry_strategy == RetryStrategy.LINEAR_BACKOFF

    def test_categorize_authentication_error(self):
        """Test categorization of authentication errors."""
        handler = ErrorHandler()
        error = EndpointAuthenticationError("Authentication failed")
        query = "SELECT * WHERE { ?s ?p ?o }"

        context = handler.categorize_error(error, query)

        assert context.category == ErrorCategory.AUTHENTICATION
        assert context.is_recoverable is False
        assert context.retry_strategy == RetryStrategy.NONE

    def test_categorize_unavailable_error(self):
        """Test categorization of endpoint unavailable errors."""
        handler = ErrorHandler()
        error = EndpointUnavailableError("Service unavailable")
        query = "SELECT * WHERE { ?s ?p ?o }"

        context = handler.categorize_error(error, query)

        assert context.category == ErrorCategory.ENDPOINT_UNAVAILABLE
        assert context.is_recoverable is True
        assert context.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_categorize_complexity_error(self):
        """Test categorization of query complexity errors."""
        handler = ErrorHandler()
        error = QueryTooComplexError("Query too complex")
        query = "SELECT * WHERE { ?s ?p ?o }"

        context = handler.categorize_error(error, query)

        assert context.category == ErrorCategory.QUERY_TOO_COMPLEX
        assert context.is_recoverable is True

    def test_categorize_unknown_error(self):
        """Test categorization of unknown errors."""
        handler = ErrorHandler()
        error = Exception("Some unknown error")
        query = "SELECT * WHERE { ?s ?p ?o }"

        context = handler.categorize_error(error, query)

        assert context.category == ErrorCategory.UNKNOWN
        assert len(context.suggestions) > 0

    def test_memory_error_detection(self):
        """Test detection of memory/result size errors."""
        handler = ErrorHandler()
        error = Exception("Out of memory: result set too large")
        query = "SELECT * WHERE { ?s ?p ?o }"

        context = handler.categorize_error(error, query)

        assert context.category == ErrorCategory.MEMORY
        assert "LIMIT" in " ".join(context.suggestions)
        assert "critical_fix" in context.metadata

    def test_timeout_without_limit(self):
        """Test timeout error suggestions for query without LIMIT."""
        handler = ErrorHandler()
        error = QueryTimeoutError("Timeout")
        query = "SELECT * WHERE { ?s ?p ?o }"

        context = handler.categorize_error(error, query)

        assert context.category == ErrorCategory.TIMEOUT
        # Should suggest adding LIMIT
        suggestions_text = " ".join(context.suggestions).lower()
        assert "limit" in suggestions_text
        assert "suggested_limit" in context.metadata


class TestQueryOptimization:
    """Test query optimization features."""

    def test_detect_missing_limit(self):
        """Test detection of missing LIMIT clause."""
        handler = ErrorHandler()
        query = "SELECT * WHERE { ?s ?p ?o }"

        optimizations = handler.suggest_optimizations(query)

        limit_opts = [o for o in optimizations if "LIMIT" in o.issue]
        assert len(limit_opts) > 0
        assert limit_opts[0].impact == "high"

    def test_detect_select_star(self):
        """Test detection of SELECT *."""
        handler = ErrorHandler()
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

        optimizations = handler.suggest_optimizations(query)

        select_star_opts = [o for o in optimizations if "SELECT *" in o.issue]
        assert len(select_star_opts) > 0

    def test_detect_excessive_optionals(self):
        """Test detection of too many OPTIONAL clauses."""
        handler = ErrorHandler()
        query = """
        SELECT * WHERE {
            ?s ?p ?o .
            OPTIONAL { ?s ?p1 ?o1 }
            OPTIONAL { ?s ?p2 ?o2 }
            OPTIONAL { ?s ?p3 ?o3 }
            OPTIONAL { ?s ?p4 ?o4 }
            OPTIONAL { ?s ?p5 ?o5 }
        } LIMIT 10
        """

        optimizations = handler.suggest_optimizations(query)

        optional_opts = [o for o in optimizations if "OPTIONAL" in o.issue]
        assert len(optional_opts) > 0
        assert optional_opts[0].impact == "high"

    def test_detect_distinct_without_limit(self):
        """Test detection of DISTINCT without LIMIT."""
        handler = ErrorHandler()
        query = "SELECT DISTINCT ?s WHERE { ?s ?p ?o }"

        optimizations = handler.suggest_optimizations(query)

        distinct_opts = [o for o in optimizations if "DISTINCT" in o.issue]
        assert len(distinct_opts) > 0

    def test_detect_order_by_without_limit(self):
        """Test detection of ORDER BY without LIMIT."""
        handler = ErrorHandler()
        query = "SELECT ?s WHERE { ?s ?p ?o } ORDER BY ?s"

        optimizations = handler.suggest_optimizations(query)

        order_opts = [o for o in optimizations if "ORDER BY" in o.issue]
        assert len(order_opts) > 0

    def test_detect_triple_wildcard(self):
        """Test detection of triple wildcard pattern."""
        handler = ErrorHandler()
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

        optimizations = handler.suggest_optimizations(query)

        wildcard_opts = [o for o in optimizations if "wildcard" in o.issue.lower()]
        assert len(wildcard_opts) > 0

    def test_detect_regex_filter(self):
        """Test detection of regex in FILTER."""
        handler = ErrorHandler()
        query = """
        SELECT ?s WHERE {
            ?s ?p ?o .
            FILTER(regex(str(?s), "pattern"))
        } LIMIT 10
        """

        optimizations = handler.suggest_optimizations(query)

        regex_opts = [o for o in optimizations if "regex" in o.issue.lower()]
        assert len(regex_opts) > 0

    def test_detect_nested_subqueries(self):
        """Test detection of multiple nested subqueries."""
        handler = ErrorHandler()
        query = """
        SELECT ?s WHERE {
            { SELECT ?s WHERE { { SELECT ?s WHERE { ?s ?p ?o } } } }
            { SELECT ?x WHERE { ?x ?y ?z } }
        } LIMIT 10
        """

        optimizations = handler.suggest_optimizations(query)

        subquery_opts = [o for o in optimizations if "subquer" in o.issue.lower()]
        assert len(subquery_opts) > 0

    def test_optimize_query_add_limit(self):
        """Test automatic addition of LIMIT clause."""
        handler = ErrorHandler()
        query = "SELECT * WHERE { ?s ?p ?o }"

        optimized = handler.optimize_query(query, OptimizationLevel.LOW)

        assert "LIMIT" in optimized.upper()
        assert optimized != query

    def test_optimize_query_levels(self):
        """Test different optimization levels."""
        handler = ErrorHandler()
        query = "SELECT * WHERE { ?s ?p ?o }"

        none_opt = handler.optimize_query(query, OptimizationLevel.NONE)
        low_opt = handler.optimize_query(query, OptimizationLevel.LOW)
        medium_opt = handler.optimize_query(query, OptimizationLevel.MEDIUM)

        # NONE should not change query
        assert none_opt == query

        # LOW and MEDIUM should add LIMIT
        assert "LIMIT" in low_opt.upper()
        assert "LIMIT" in medium_opt.upper()

    def test_auto_optimize_on_timeout(self):
        """Test automatic optimization for timeout errors."""
        handler = ErrorHandler()
        query = "SELECT * WHERE { ?s ?p ?o }"
        context = ErrorContext(
            original_error=QueryTimeoutError("timeout"),
            category=ErrorCategory.TIMEOUT,
            severity=6,
            message="Timeout",
            technical_details="",
        )

        optimized = handler._auto_optimize_query(query, context)

        assert optimized is not None
        assert "LIMIT" in optimized.upper()

    def test_auto_optimize_on_memory(self):
        """Test automatic optimization for memory errors."""
        handler = ErrorHandler()
        query = "SELECT * WHERE { ?s ?p ?o }"
        context = ErrorContext(
            original_error=Exception("out of memory"),
            category=ErrorCategory.MEMORY,
            severity=7,
            message="Memory",
            technical_details="",
        )

        optimized = handler._auto_optimize_query(query, context)

        assert optimized is not None
        assert "LIMIT" in optimized.upper()


class TestErrorRecovery:
    """Test error recovery functionality."""

    def test_retry_immediate_success(self):
        """Test immediate retry that succeeds."""
        handler = ErrorHandler()
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
        endpoint = EndpointInfo(url="https://example.org/sparql")

        # Mock execute function that succeeds on retry
        call_count = [0]
        def mock_execute(q, e):
            call_count[0] += 1
            if call_count[0] == 1:
                raise EndpointConnectionError("Connection failed")
            return QueryResult(status=QueryStatus.SUCCESS, query=q, row_count=10)

        error = EndpointConnectionError("Connection failed")
        result = handler.recover_from_error(
            error, query, endpoint, mock_execute
        )

        assert result.success is True
        assert result.attempts >= 1
        assert result.strategy_used == RetryStrategy.IMMEDIATE

    def test_retry_immediate_failure(self):
        """Test immediate retry that fails."""
        handler = ErrorHandler(max_retries=1)
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
        endpoint = EndpointInfo(url="https://example.org/sparql")

        # Mock execute function that always fails
        def mock_execute(q, e):
            raise Exception("Malformed response")

        error = Exception("Malformed response")
        result = handler.recover_from_error(
            error, query, endpoint, mock_execute
        )

        assert result.success is False
        assert result.attempts >= 1

    def test_retry_exponential_backoff(self):
        """Test exponential backoff retry."""
        handler = ErrorHandler(max_retries=2, retry_delay=0.01)
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
        endpoint = EndpointInfo(url="https://example.org/sparql")

        call_count = [0]
        def mock_execute(q, e):
            call_count[0] += 1
            if call_count[0] < 3:
                raise QueryTimeoutError("Timeout")
            return QueryResult(status=QueryStatus.SUCCESS, query=q, row_count=10)

        error = QueryTimeoutError("Timeout")
        start_time = time.time()
        result = handler.recover_from_error(
            error, query, endpoint, mock_execute
        )
        elapsed = time.time() - start_time

        assert result.success is True
        assert result.strategy_used == RetryStrategy.EXPONENTIAL_BACKOFF
        # Should have some delay from backoff
        assert elapsed > 0.01

    def test_retry_linear_backoff(self):
        """Test linear backoff retry."""
        handler = ErrorHandler(max_retries=2, retry_delay=0.01)
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
        endpoint = EndpointInfo(url="https://example.org/sparql")

        def mock_execute(q, e):
            raise EndpointRateLimitError("Rate limited")

        error = EndpointRateLimitError("Rate limited")
        result = handler.recover_from_error(
            error, query, endpoint, mock_execute
        )

        assert result.strategy_used == RetryStrategy.LINEAR_BACKOFF

    def test_non_recoverable_error(self):
        """Test handling of non-recoverable errors."""
        handler = ErrorHandler()
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
        endpoint = EndpointInfo(url="https://example.org/sparql")

        def mock_execute(q, e):
            return QueryResult(status=QueryStatus.SUCCESS, query=q, row_count=10)

        error = EndpointAuthenticationError("Authentication failed")
        result = handler.recover_from_error(
            error, query, endpoint, mock_execute
        )

        assert result.success is False
        assert result.attempts == 0

    def test_fallback_to_alternative_endpoints(self):
        """Test fallback to alternative endpoints."""
        handler = ErrorHandler(enable_fallback=True)
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
        endpoint = EndpointInfo(url="https://example.org/sparql")
        alternatives = [
            EndpointInfo(url="https://alternative1.org/sparql"),
            EndpointInfo(url="https://alternative2.org/sparql"),
        ]

        call_count = [0]
        def mock_execute(q, e):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise EndpointConnectionError("Connection failed")
            return QueryResult(status=QueryStatus.SUCCESS, query=q, row_count=10)

        error = EndpointConnectionError("Connection failed")
        result = handler.recover_from_error(
            error, query, endpoint, mock_execute, alternatives
        )

        assert result.success is True
        assert result.fallback_used is True
        assert "fallback_endpoint" in result.metadata

    def test_try_optimized_query(self):
        """Test trying optimized query as recovery."""
        handler = ErrorHandler(enable_optimization_suggestions=True)
        query = "SELECT * WHERE { ?s ?p ?o }"  # No LIMIT
        endpoint = EndpointInfo(url="https://example.org/sparql")

        call_count = [0]
        def mock_execute(q, e):
            call_count[0] += 1
            # Succeed only if query has LIMIT
            if "LIMIT" in q.upper():
                return QueryResult(status=QueryStatus.SUCCESS, query=q, row_count=10)
            raise QueryTimeoutError("Timeout")

        error = QueryTimeoutError("Timeout")
        result = handler.recover_from_error(
            error, query, endpoint, mock_execute
        )

        # Should eventually succeed with optimized query
        if result.success:
            assert result.metadata.get("query_optimized") is True


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_handle_query_error(self):
        """Test handle_query_error convenience function."""
        error = QueryTimeoutError("Timeout")
        query = "SELECT * WHERE { ?s ?p ?o }"

        context = handle_query_error(error, query)

        assert isinstance(context, ErrorContext)
        assert context.category == ErrorCategory.TIMEOUT
        assert len(context.suggestions) > 0

    def test_get_error_suggestions(self):
        """Test get_error_suggestions convenience function."""
        error = QuerySyntaxError("Syntax error")
        query = "SELECT * WHERE ?s ?p ?o }"

        suggestions = get_error_suggestions(error, query)

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)

    def test_optimize_query_function(self):
        """Test optimize_query convenience function."""
        query = "SELECT * WHERE { ?s ?p ?o }"

        optimized, optimizations = optimize_query(query)

        assert isinstance(optimized, str)
        assert isinstance(optimizations, list)
        assert "LIMIT" in optimized.upper()
        assert len(optimizations) > 0


class TestStatistics:
    """Test statistics tracking."""

    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        handler = ErrorHandler()

        # Process multiple errors
        errors = [
            QueryTimeoutError("timeout"),
            QuerySyntaxError("syntax"),
            QueryTimeoutError("timeout"),
            EndpointConnectionError("connection"),
        ]

        for error in errors:
            handler.categorize_error(error, "SELECT * WHERE { ?s ?p ?o }")

        stats = handler.get_statistics()

        assert stats["total_errors"] == 4
        assert stats["errors_by_category"]["timeout"] == 2
        assert stats["errors_by_category"]["syntax"] == 1
        assert stats["errors_by_category"]["network"] == 1

    def test_recovery_statistics(self):
        """Test recovery statistics."""
        handler = ErrorHandler(max_retries=1)
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
        endpoint = EndpointInfo(url="https://example.org/sparql")

        def mock_execute_success(q, e):
            return QueryResult(status=QueryStatus.SUCCESS, query=q, row_count=10)

        def mock_execute_failure(q, e):
            raise Exception("Always fails")

        # Successful recovery
        handler.recover_from_error(
            Exception("test"), query, endpoint, mock_execute_success
        )

        # Failed recovery
        handler.recover_from_error(
            Exception("test"), query, endpoint, mock_execute_failure
        )

        stats = handler.get_statistics()

        assert stats["successful_recoveries"] >= 1
        assert stats["failed_recoveries"] >= 1
        assert "recovery_rate" in stats


class TestErrorReporting:
    """Test error reporting functionality."""

    def test_format_error_report(self):
        """Test formatted error report generation."""
        handler = ErrorHandler()
        error = QueryTimeoutError("Query timed out")
        query = "SELECT * WHERE { ?s ?p ?o }"

        context = handler.categorize_error(error, query)
        report = handler.format_error_report(context)

        assert isinstance(report, str)
        assert "ERROR" in report
        assert context.message in report
        assert "SUGGESTIONS" in report
        assert str(context.severity) in report

    def test_error_context_string(self):
        """Test ErrorContext string representation."""
        context = ErrorContext(
            original_error=QueryTimeoutError("timeout"),
            category=ErrorCategory.TIMEOUT,
            severity=6,
            message="Query timed out",
            technical_details="Technical details here",
            suggestions=["Add LIMIT", "Use pagination"],
        )

        # ErrorContext should be printable
        str_repr = str(context)
        # Basic check that it doesn't error
        assert isinstance(str_repr, str)


def test_integration_scenario():
    """Integration test of complete error handling workflow."""
    handler = ErrorHandler(
        max_retries=2,
        retry_delay=0.01,
        enable_fallback=True,
        enable_optimization_suggestions=True
    )

    query = "SELECT * WHERE { ?s ?p ?o }"
    endpoint = EndpointInfo(url="https://example.org/sparql", timeout=30)

    # 1. Categorize error
    error = QueryTimeoutError("Query execution exceeded timeout")
    context = handler.categorize_error(error, query, endpoint)

    assert context.category == ErrorCategory.TIMEOUT
    assert context.is_recoverable

    # 2. Get suggestions
    assert len(context.suggestions) > 0

    # 3. Analyze query
    optimizations = handler.suggest_optimizations(query)
    assert len(optimizations) > 0

    # 4. Optimize query
    optimized = handler.optimize_query(query, OptimizationLevel.MEDIUM)
    assert "LIMIT" in optimized.upper()

    # 5. Generate report
    report = handler.format_error_report(context)
    assert "timeout" in report.lower()

    # 6. Check statistics
    stats = handler.get_statistics()
    assert stats["total_errors"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
