"""
Unit tests for MCP middleware components.

Tests error handling, logging, validation middleware and middleware chains.
"""

import asyncio
import json
import pytest
from typing import Any, Dict

from sparql_agent.mcp.middleware import (
    ErrorMiddleware,
    ErrorMiddlewareConfig,
    LoggingMiddleware,
    LoggingMiddlewareConfig,
    ValidationMiddleware,
    ValidationMiddlewareConfig,
    MiddlewareChain,
    LogLevel,
)
from sparql_agent.core.exceptions import (
    QueryExecutionError,
    ValidationError,
    EndpointConnectionError,
)


# ============================================================================
# Error Middleware Tests
# ============================================================================


class TestErrorMiddleware:
    """Tests for ErrorMiddleware."""

    @pytest.fixture
    def error_middleware(self):
        """Create error middleware instance."""
        config = ErrorMiddlewareConfig(
            debug=True,
            include_traceback=True,
            sanitize_errors=True,
        )
        return ErrorMiddleware(config=config)

    @pytest.mark.asyncio
    async def test_wrap_handler_success(self, error_middleware):
        """Test wrapping a successful handler."""
        @error_middleware.wrap_handler
        async def handler(x: int) -> int:
            return x * 2

        result = await handler(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_wrap_handler_error(self, error_middleware):
        """Test error handling in wrapped handler."""
        @error_middleware.wrap_handler
        async def handler() -> None:
            raise QueryExecutionError("Test error")

        result = await handler()
        assert "error" in result
        assert "error_type" in result
        assert result["error_type"] == "QueryExecutionError"
        assert result["error_code"] == "QUERY_ERROR"

    @pytest.mark.asyncio
    async def test_sanitize_error_message(self, error_middleware):
        """Test error message sanitization."""
        @error_middleware.wrap_handler
        async def handler() -> None:
            raise ValueError("Error with sk-1234567890abcdef and /path/to/file.py")

        result = await handler()
        assert "<redacted>" in result["error"]
        assert "<file>" in result["error"]
        assert "sk-1234567890abcdef" not in result["error"]
        assert "/path/to/file.py" not in result["error"]

    @pytest.mark.asyncio
    async def test_error_stats(self, error_middleware):
        """Test error statistics tracking."""
        @error_middleware.wrap_handler
        async def handler() -> None:
            raise ValueError("Test error")

        await handler()
        await handler()

        stats = error_middleware.get_stats()
        assert stats["total_errors"] == 2
        assert len(stats["recent_errors"]) == 2

    @pytest.mark.asyncio
    async def test_error_codes(self, error_middleware):
        """Test error code mapping."""
        errors_and_codes = [
            (QueryExecutionError("test"), "QUERY_ERROR"),
            (EndpointConnectionError("test"), "ENDPOINT_ERROR"),
            (ValidationError("test"), "VALIDATION_ERROR"),
            (ValueError("test"), "INVALID_INPUT"),
            (KeyError("test"), "MISSING_PARAMETER"),
        ]

        for error, expected_code in errors_and_codes:
            result = await error_middleware.handle_error(error, "test_handler", {})
            assert result["error_code"] == expected_code


# ============================================================================
# Logging Middleware Tests
# ============================================================================


class TestLoggingMiddleware:
    """Tests for LoggingMiddleware."""

    @pytest.fixture
    def logging_middleware(self):
        """Create logging middleware instance."""
        config = LoggingMiddlewareConfig(
            level=LogLevel.INFO,
            log_requests=True,
            log_responses=True,
            log_performance=True,
        )
        return LoggingMiddleware(config=config)

    @pytest.mark.asyncio
    async def test_wrap_handler(self, logging_middleware):
        """Test wrapping handler with logging."""
        @logging_middleware.wrap_handler
        async def handler(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        result = await handler(5)
        assert result == 10

        stats = logging_middleware.get_stats()
        assert stats["total_requests"] == 1
        assert stats["avg_duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_performance_tracking(self, logging_middleware):
        """Test performance tracking."""
        @logging_middleware.wrap_handler
        async def fast_handler() -> str:
            return "fast"

        @logging_middleware.wrap_handler
        async def slow_handler() -> str:
            await asyncio.sleep(0.05)
            return "slow"

        await fast_handler()
        await slow_handler()

        stats = logging_middleware.get_stats()
        assert stats["total_requests"] == 2
        assert "percentiles" in stats

    @pytest.mark.asyncio
    async def test_error_logging(self, logging_middleware):
        """Test error logging."""
        @logging_middleware.wrap_handler
        async def failing_handler() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_handler()

        stats = logging_middleware.get_stats()
        assert stats["total_requests"] == 1


# ============================================================================
# Validation Middleware Tests
# ============================================================================


class TestValidationMiddleware:
    """Tests for ValidationMiddleware."""

    @pytest.fixture
    def validation_middleware(self):
        """Create validation middleware instance."""
        config = ValidationMiddlewareConfig(
            max_request_size=1024,
            max_query_length=100,
            validate_urls=True,
            validate_sparql=True,
        )
        return ValidationMiddleware(config=config)

    @pytest.mark.asyncio
    async def test_valid_request(self, validation_middleware):
        """Test validation of valid request."""
        @validation_middleware.wrap_handler
        async def handler(query: str, endpoint_url: str) -> Dict[str, Any]:
            return {"status": "success"}

        result = await handler(
            query="SELECT * WHERE { ?s ?p ?o }",
            endpoint_url="https://example.org/sparql"
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_invalid_url(self, validation_middleware):
        """Test URL validation."""
        @validation_middleware.wrap_handler
        async def handler(endpoint_url: str) -> Dict[str, Any]:
            return {"status": "success"}

        with pytest.raises(ValidationError) as exc_info:
            await handler(endpoint_url="javascript:alert('xss')")

        assert "URL scheme not allowed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dangerous_query(self, validation_middleware):
        """Test SPARQL query validation for dangerous operations."""
        @validation_middleware.wrap_handler
        async def handler(query: str) -> Dict[str, Any]:
            return {"status": "success"}

        dangerous_queries = [
            "DROP GRAPH <http://example.org>",
            "INSERT DATA { <s> <p> <o> }",
            "DELETE DATA { <s> <p> <o> }",
            "LOAD <http://example.org/data>",
        ]

        for query in dangerous_queries:
            with pytest.raises(ValidationError):
                await handler(query=query)

    @pytest.mark.asyncio
    async def test_query_too_long(self, validation_middleware):
        """Test query length validation."""
        @validation_middleware.wrap_handler
        async def handler(query: str) -> Dict[str, Any]:
            return {"status": "success"}

        long_query = "SELECT * WHERE { ?s ?p ?o }" * 100

        with pytest.raises(ValidationError) as exc_info:
            await handler(query=long_query)

        assert "Query length" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_limit_validation(self, validation_middleware):
        """Test limit parameter validation."""
        @validation_middleware.wrap_handler
        async def handler(limit: int) -> Dict[str, Any]:
            return {"status": "success"}

        # Valid limit
        result = await handler(limit=100)
        assert result["status"] == "success"

        # Invalid limit (too large)
        with pytest.raises(ValidationError):
            await handler(limit=999999)

        # Invalid limit (negative)
        with pytest.raises(ValidationError):
            await handler(limit=-10)

    @pytest.mark.asyncio
    async def test_request_size_limit(self, validation_middleware):
        """Test request size validation."""
        @validation_middleware.wrap_handler
        async def handler(data: str) -> Dict[str, Any]:
            return {"status": "success"}

        # Large data that exceeds limit
        large_data = "x" * 10000

        with pytest.raises(ValidationError) as exc_info:
            await handler(data=large_data)

        assert "Request size" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_input_sanitization(self, validation_middleware):
        """Test input sanitization."""
        @validation_middleware.wrap_handler
        async def handler(**kwargs) -> Dict[str, Any]:
            return kwargs

        result = await handler(
            text="<script>alert('xss')</script>Hello",
            data="javascript:void(0)"
        )

        # Script tags should be removed
        assert "<script>" not in result["text"]
        assert "javascript:" not in result["data"]

    @pytest.mark.asyncio
    async def test_validation_stats(self, validation_middleware):
        """Test validation statistics."""
        @validation_middleware.wrap_handler
        async def handler(query: str) -> Dict[str, Any]:
            return {"status": "success"}

        # Valid request
        await handler(query="SELECT * WHERE { ?s ?p ?o }")

        # Invalid request
        try:
            await handler(query="DROP GRAPH <http://example.org>")
        except ValidationError:
            pass

        stats = validation_middleware.get_stats()
        assert stats["validation_failures"] == 1


# ============================================================================
# Middleware Chain Tests
# ============================================================================


class TestMiddlewareChain:
    """Tests for MiddlewareChain."""

    def test_create_chain(self):
        """Test creating middleware chain."""
        chain = MiddlewareChain()
        assert chain.middlewares == []

    def test_add_middleware(self):
        """Test adding middleware to chain."""
        chain = MiddlewareChain()
        error_middleware = ErrorMiddleware()
        logging_middleware = LoggingMiddleware()

        chain.add(error_middleware).add(logging_middleware)

        assert len(chain.middlewares) == 2

    @pytest.mark.asyncio
    async def test_chain_execution_order(self):
        """Test middleware execution order in chain."""
        execution_order = []

        class TestMiddleware:
            def __init__(self, name):
                self.name = name

            def wrap_handler(self, handler):
                async def wrapper(*args, **kwargs):
                    execution_order.append(f"{self.name}_before")
                    result = await handler(*args, **kwargs)
                    execution_order.append(f"{self.name}_after")
                    return result
                return wrapper

        chain = MiddlewareChain()
        chain.add(TestMiddleware("first"))
        chain.add(TestMiddleware("second"))
        chain.add(TestMiddleware("third"))

        @chain.wrap_handler
        async def handler():
            execution_order.append("handler")
            return "result"

        result = await handler()

        # Middleware should execute in reverse order (last added wraps first)
        # so: third wraps (second wraps (first wraps handler))
        # Execution: third_before -> second_before -> first_before -> handler -> first_after -> second_after -> third_after
        assert execution_order == [
            "third_before",
            "second_before",
            "first_before",
            "handler",
            "first_after",
            "second_after",
            "third_after",
        ]
        assert result == "result"

    @pytest.mark.asyncio
    async def test_full_chain(self):
        """Test full middleware chain with all components."""
        chain = MiddlewareChain()

        # Add all middleware
        chain.add(ValidationMiddleware(config=ValidationMiddlewareConfig(
            validate_urls=True,
            validate_sparql=True,
        )))
        chain.add(LoggingMiddleware(config=LoggingMiddlewareConfig(
            level=LogLevel.INFO,
        )))
        chain.add(ErrorMiddleware(config=ErrorMiddlewareConfig(
            debug=True,
        )))

        @chain.wrap_handler
        async def handler(query: str, endpoint_url: str) -> Dict[str, Any]:
            return {"status": "success", "query": query}

        # Test successful execution
        result = await handler(
            query="SELECT * WHERE { ?s ?p ?o }",
            endpoint_url="https://example.org/sparql"
        )
        assert result["status"] == "success"

        # Test validation error handling
        error_result = await handler(
            query="DROP GRAPH <http://example.org>",
            endpoint_url="https://example.org/sparql"
        )
        assert "error" in error_result
        assert error_result["error_code"] == "VALIDATION_ERROR"

    def test_chain_stats(self):
        """Test getting stats from middleware chain."""
        chain = MiddlewareChain()
        chain.add(ErrorMiddleware())
        chain.add(LoggingMiddleware())
        chain.add(ValidationMiddleware())

        stats = chain.get_stats()
        assert len(stats) == 3
        assert any("ErrorMiddleware" in key for key in stats.keys())
        assert any("LoggingMiddleware" in key for key in stats.keys())
        assert any("ValidationMiddleware" in key for key in stats.keys())


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for middleware components."""

    @pytest.mark.asyncio
    async def test_production_scenario(self):
        """Test realistic production scenario."""
        # Setup production-like middleware
        chain = MiddlewareChain()

        validation_config = ValidationMiddlewareConfig(
            max_request_size=1024 * 1024,
            validate_urls=True,
            validate_sparql=True,
            sanitize_inputs=True,
        )
        logging_config = LoggingMiddlewareConfig(
            level=LogLevel.INFO,
            log_requests=True,
            log_responses=True,
            log_performance=True,
        )
        error_config = ErrorMiddlewareConfig(
            debug=False,
            include_traceback=False,
            sanitize_errors=True,
        )

        chain.add(ValidationMiddleware(config=validation_config))
        chain.add(LoggingMiddleware(config=logging_config))
        chain.add(ErrorMiddleware(config=error_config))

        # Create handler
        @chain.wrap_handler
        async def query_handler(
            query: str,
            endpoint_url: str,
            limit: int = 100
        ) -> Dict[str, Any]:
            """Example query handler."""
            if "ERROR" in query:
                raise QueryExecutionError("Query failed")

            return {
                "status": "success",
                "query": query,
                "results": [{"s": "http://ex.org/1", "p": "rdf:type", "o": "owl:Class"}],
                "row_count": 1,
            }

        # Test successful query
        result = await query_handler(
            query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
            endpoint_url="https://example.org/sparql",
            limit=10
        )
        assert result["status"] == "success"
        assert result["row_count"] == 1

        # Test error handling
        error_result = await query_handler(
            query="SELECT ERROR WHERE { ?s ?p ?o }",
            endpoint_url="https://example.org/sparql",
            limit=10
        )
        assert "error" in error_result
        assert "error_code" in error_result

        # Verify stats
        stats = chain.get_stats()
        assert "LoggingMiddleware_1" in stats
        assert stats["LoggingMiddleware_1"]["total_requests"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
