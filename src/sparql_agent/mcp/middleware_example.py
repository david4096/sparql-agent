"""
Example usage of MCP middleware components.

This module demonstrates how to use the error handling, logging, and validation
middleware with MCP handlers.
"""

import asyncio
import logging
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
from sparql_agent.core.exceptions import QueryExecutionError, ValidationError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ============================================================================
# Example 1: Individual Middleware Usage
# ============================================================================


async def example_individual_middleware():
    """Demonstrate using individual middleware components."""
    print("\n" + "=" * 60)
    print("Example 1: Individual Middleware Usage")
    print("=" * 60)

    # Configure error middleware
    error_config = ErrorMiddlewareConfig(
        debug=True,
        include_traceback=True,
        sanitize_errors=True,
    )
    error_middleware = ErrorMiddleware(config=error_config)

    # Create a handler that might fail
    @error_middleware.wrap_handler
    async def query_handler(query: str, endpoint_url: str) -> Dict[str, Any]:
        """Example query handler."""
        if not query:
            raise ValidationError("Query cannot be empty")
        if "DROP" in query.upper():
            raise QueryExecutionError("DROP operations not allowed")
        return {"status": "success", "query": query}

    # Test successful execution
    print("\n1. Testing successful execution:")
    result = await query_handler(
        query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        endpoint_url="https://example.org/sparql"
    )
    print(f"Result: {result}")

    # Test error handling
    print("\n2. Testing error handling:")
    error_result = await query_handler(query="", endpoint_url="https://example.org/sparql")
    print(f"Error result: {error_result}")

    # Get stats
    print("\n3. Error middleware stats:")
    print(error_middleware.get_stats())


# ============================================================================
# Example 2: Logging Middleware
# ============================================================================


async def example_logging_middleware():
    """Demonstrate logging middleware."""
    print("\n" + "=" * 60)
    print("Example 2: Logging Middleware")
    print("=" * 60)

    # Configure logging middleware
    logging_config = LoggingMiddlewareConfig(
        level=LogLevel.INFO,
        log_requests=True,
        log_responses=True,
        log_performance=True,
        include_arguments=True,
        performance_threshold_ms=100.0,
    )
    logging_middleware = LoggingMiddleware(config=logging_config)

    # Create a handler with logging
    @logging_middleware.wrap_handler
    async def discover_endpoint(endpoint_url: str, include_statistics: bool = True) -> Dict[str, Any]:
        """Example discovery handler."""
        # Simulate some work
        await asyncio.sleep(0.05)
        return {
            "endpoint_url": endpoint_url,
            "capabilities": ["SELECT", "CONSTRUCT"],
            "triple_count": 1000000,
        }

    # Execute handler multiple times
    print("\n1. Testing endpoint discovery:")
    for i in range(3):
        result = await discover_endpoint(
            endpoint_url=f"https://example{i}.org/sparql",
            include_statistics=True
        )
        print(f"Discovery {i+1} completed")

    # Get performance stats
    print("\n2. Logging middleware stats:")
    stats = logging_middleware.get_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Average duration: {stats['avg_duration_ms']:.2f}ms")
    print(f"Percentiles: {stats['percentiles']}")


# ============================================================================
# Example 3: Validation Middleware
# ============================================================================


async def example_validation_middleware():
    """Demonstrate validation middleware."""
    print("\n" + "=" * 60)
    print("Example 3: Validation Middleware")
    print("=" * 60)

    # Configure validation middleware
    validation_config = ValidationMiddlewareConfig(
        max_request_size=1024 * 100,  # 100KB
        max_query_length=10000,
        validate_urls=True,
        validate_sparql=True,
        sanitize_inputs=True,
    )
    validation_middleware = ValidationMiddleware(config=validation_config)

    # Create a handler with validation
    @validation_middleware.wrap_handler
    async def execute_query(query: str, endpoint_url: str, limit: int = 100) -> Dict[str, Any]:
        """Example query execution handler."""
        return {
            "status": "success",
            "query": query,
            "endpoint": endpoint_url,
            "limit": limit,
        }

    # Test valid input
    print("\n1. Testing valid input:")
    try:
        result = await execute_query(
            query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
            endpoint_url="https://example.org/sparql",
            limit=10
        )
        print(f"Success: {result['status']}")
    except ValidationError as e:
        print(f"Validation error: {e}")

    # Test invalid URL
    print("\n2. Testing invalid URL:")
    try:
        result = await execute_query(
            query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
            endpoint_url="javascript:alert('xss')",
            limit=10
        )
        print(f"Success: {result['status']}")
    except ValidationError as e:
        print(f"Validation error: {e}")

    # Test dangerous query
    print("\n3. Testing dangerous query:")
    try:
        result = await execute_query(
            query="DROP GRAPH <http://example.org/graph>",
            endpoint_url="https://example.org/sparql",
            limit=10
        )
        print(f"Success: {result['status']}")
    except ValidationError as e:
        print(f"Validation error: {e}")

    # Test invalid limit
    print("\n4. Testing invalid limit:")
    try:
        result = await execute_query(
            query="SELECT * WHERE { ?s ?p ?o }",
            endpoint_url="https://example.org/sparql",
            limit=999999
        )
        print(f"Success: {result['status']}")
    except ValidationError as e:
        print(f"Validation error: {e}")

    # Get stats
    print("\n5. Validation middleware stats:")
    print(validation_middleware.get_stats())


# ============================================================================
# Example 4: Middleware Chain
# ============================================================================


async def example_middleware_chain():
    """Demonstrate composing multiple middleware."""
    print("\n" + "=" * 60)
    print("Example 4: Middleware Chain")
    print("=" * 60)

    # Create middleware chain
    chain = MiddlewareChain()

    # Add validation first (validate before anything else)
    chain.add(ValidationMiddleware(config=ValidationMiddlewareConfig(
        validate_urls=True,
        validate_sparql=True,
    )))

    # Add logging second (log validated requests)
    chain.add(LoggingMiddleware(config=LoggingMiddlewareConfig(
        level=LogLevel.INFO,
        log_requests=True,
        log_responses=True,
    )))

    # Add error handling last (catch all errors)
    chain.add(ErrorMiddleware(config=ErrorMiddlewareConfig(
        debug=True,
        sanitize_errors=True,
    )))

    # Create a handler with the full chain
    @chain.wrap_handler
    async def full_handler(query: str, endpoint_url: str) -> Dict[str, Any]:
        """Handler with full middleware chain."""
        # Simulate some processing
        await asyncio.sleep(0.01)

        if "ERROR" in query:
            raise QueryExecutionError("Simulated query error")

        return {
            "status": "success",
            "query": query,
            "endpoint": endpoint_url,
            "results": [{"s": "http://example.org/1", "p": "rdf:type", "o": "owl:Class"}],
        }

    # Test successful execution
    print("\n1. Testing successful execution through full chain:")
    result = await full_handler(
        query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        endpoint_url="https://example.org/sparql"
    )
    print(f"Result status: {result.get('status', 'N/A')}")

    # Test error through full chain
    print("\n2. Testing error through full chain:")
    error_result = await full_handler(
        query="SELECT ERROR WHERE { ?s ?p ?o }",
        endpoint_url="https://example.org/sparql"
    )
    print(f"Error handled: {error_result.get('error_code', 'N/A')}")

    # Test validation failure through full chain
    print("\n3. Testing validation failure through full chain:")
    validation_result = await full_handler(
        query="DROP GRAPH <http://example.org/graph>",
        endpoint_url="https://example.org/sparql"
    )
    print(f"Validation error handled: {validation_result.get('error_code', 'N/A')}")

    # Get combined stats
    print("\n4. Combined middleware stats:")
    stats = chain.get_stats()
    for middleware_name, middleware_stats in stats.items():
        print(f"\n{middleware_name}:")
        for key, value in middleware_stats.items():
            print(f"  {key}: {value}")


# ============================================================================
# Example 5: Production Configuration
# ============================================================================


async def example_production_config():
    """Demonstrate production-ready middleware configuration."""
    print("\n" + "=" * 60)
    print("Example 5: Production Configuration")
    print("=" * 60)

    # Production error middleware
    error_middleware = ErrorMiddleware(config=ErrorMiddlewareConfig(
        debug=False,  # Disable debug in production
        include_traceback=False,  # Don't expose tracebacks
        sanitize_errors=True,  # Always sanitize
        max_error_length=500,  # Limit error message length
        log_errors=True,  # Log all errors
        log_level=LogLevel.ERROR,
    ))

    # Production logging middleware
    logging_middleware = LoggingMiddleware(config=LoggingMiddlewareConfig(
        level=LogLevel.INFO,
        log_requests=True,
        log_responses=True,
        log_performance=True,
        log_user_actions=True,
        include_arguments=False,  # Don't log sensitive args in production
        include_results=False,  # Results can be large
        max_log_length=1000,
        performance_threshold_ms=2000.0,  # Alert on slow operations
    ))

    # Production validation middleware
    validation_middleware = ValidationMiddleware(config=ValidationMiddlewareConfig(
        max_request_size=5 * 1024 * 1024,  # 5MB max
        max_query_length=50000,  # 50KB max query
        max_results_limit=5000,  # Reasonable limit
        validate_urls=True,
        validate_sparql=True,
        sanitize_inputs=True,
        rate_limit_enabled=True,
        rate_limit_per_minute=30,  # 30 requests per minute per handler
    ))

    # Create production chain
    production_chain = MiddlewareChain()
    production_chain.add(validation_middleware)
    production_chain.add(logging_middleware)
    production_chain.add(error_middleware)

    # Create production handler
    @production_chain.wrap_handler
    async def production_handler(query: str, endpoint_url: str, limit: int = 100) -> Dict[str, Any]:
        """Production-ready handler."""
        # Simulate query execution
        await asyncio.sleep(0.02)
        return {
            "status": "success",
            "row_count": 42,
            "execution_time": 0.02,
        }

    print("\n1. Testing production handler:")
    result = await production_handler(
        query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        endpoint_url="https://example.org/sparql",
        limit=10
    )
    print(f"Production result: {result}")

    print("\n2. Production middleware is now active with:")
    print("   - Sanitized error messages")
    print("   - Performance monitoring")
    print("   - Request validation")
    print("   - Rate limiting")
    print("   - Security controls")


# ============================================================================
# Main
# ============================================================================


async def main():
    """Run all examples."""
    await example_individual_middleware()
    await example_logging_middleware()
    await example_validation_middleware()
    await example_middleware_chain()
    await example_production_config()

    print("\n" + "=" * 60)
    print("All middleware examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
