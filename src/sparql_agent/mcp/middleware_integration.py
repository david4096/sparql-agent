"""
Example integration of middleware with MCP server handlers.

This module demonstrates how to integrate the middleware components
with the actual MCP server implementation.
"""

import asyncio
from typing import Any, Dict, Optional

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


# ============================================================================
# Example 1: Wrapping Individual MCP Tool Handlers
# ============================================================================


def create_tool_handler_middleware() -> MiddlewareChain:
    """
    Create middleware chain for MCP tool handlers.

    Returns:
        Configured middleware chain
    """
    chain = MiddlewareChain()

    # Add validation
    chain.add(ValidationMiddleware(config=ValidationMiddlewareConfig(
        max_request_size=5 * 1024 * 1024,  # 5MB
        max_query_length=50000,
        validate_urls=True,
        validate_sparql=True,
        sanitize_inputs=True,
    )))

    # Add logging
    chain.add(LoggingMiddleware(config=LoggingMiddlewareConfig(
        level=LogLevel.INFO,
        log_requests=True,
        log_responses=True,
        log_performance=True,
        performance_threshold_ms=2000,
    )))

    # Add error handling
    chain.add(ErrorMiddleware(config=ErrorMiddlewareConfig(
        debug=False,
        include_traceback=False,
        sanitize_errors=True,
    )))

    return chain


# Create middleware instance
tool_middleware = create_tool_handler_middleware()


# Example tool handlers with middleware
@tool_middleware.wrap_handler
async def handle_query_sparql(
    query: str,
    endpoint_url: str,
    timeout: Optional[int] = None,
    limit: Optional[int] = None,
    format: str = "json",
    **kwargs
) -> Dict[str, Any]:
    """
    Execute SPARQL query with full middleware protection.

    Args:
        query: SPARQL query string
        endpoint_url: SPARQL endpoint URL
        timeout: Query timeout in seconds
        limit: Maximum number of results
        format: Output format (json, csv, text)
        **kwargs: Additional arguments

    Returns:
        Query results or error response
    """
    # Your actual query execution logic here
    # The middleware will:
    # 1. Validate the query and URL
    # 2. Log the request
    # 3. Track performance
    # 4. Catch and format any errors

    # Simulated execution
    await asyncio.sleep(0.1)

    return {
        "status": "success",
        "query": query,
        "endpoint": endpoint_url,
        "bindings": [
            {"s": "http://example.org/1", "p": "rdf:type", "o": "owl:Class"}
        ],
        "row_count": 1,
        "execution_time": 0.1,
    }


@tool_middleware.wrap_handler
async def handle_discover_endpoint(
    endpoint_url: str,
    include_statistics: bool = True,
    include_schema: bool = True,
    sample_size: int = 1000,
    **kwargs
) -> Dict[str, Any]:
    """
    Discover endpoint capabilities with middleware protection.

    Args:
        endpoint_url: SPARQL endpoint URL
        include_statistics: Include detailed statistics
        include_schema: Discover schema information
        sample_size: Number of triples to sample
        **kwargs: Additional arguments

    Returns:
        Endpoint capabilities or error response
    """
    # Your actual discovery logic here
    await asyncio.sleep(0.2)

    return {
        "endpoint_url": endpoint_url,
        "capabilities": ["SELECT", "CONSTRUCT", "ASK", "DESCRIBE"],
        "supports_service": True,
        "triple_count": 1000000,
    }


@tool_middleware.wrap_handler
async def handle_generate_query(
    natural_language: str,
    endpoint_url: Optional[str] = None,
    schema_context: Optional[str] = None,
    strategy: str = "auto",
    **kwargs
) -> Dict[str, Any]:
    """
    Generate SPARQL query from natural language with middleware protection.

    Args:
        natural_language: Natural language question
        endpoint_url: Optional endpoint URL for context
        schema_context: Optional schema information
        strategy: Generation strategy
        **kwargs: Additional arguments

    Returns:
        Generated query or error response
    """
    # Your actual generation logic here
    await asyncio.sleep(0.3)

    return {
        "query": "SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        "natural_language": natural_language,
        "explanation": "Query retrieves all triples with a limit of 10",
        "confidence": 0.95,
    }


# ============================================================================
# Example 2: Environment-Specific Middleware Configurations
# ============================================================================


def create_development_middleware() -> MiddlewareChain:
    """Create middleware for development environment."""
    chain = MiddlewareChain()

    # Relaxed validation
    chain.add(ValidationMiddleware(config=ValidationMiddlewareConfig(
        max_request_size=100 * 1024 * 1024,  # 100MB
        validate_urls=False,  # Allow any URL in dev
        validate_sparql=True,
    )))

    # Verbose logging
    chain.add(LoggingMiddleware(config=LoggingMiddlewareConfig(
        level=LogLevel.DEBUG,
        log_requests=True,
        log_responses=True,
        include_arguments=True,
        include_results=True,
        performance_threshold_ms=500,
    )))

    # Detailed errors
    chain.add(ErrorMiddleware(config=ErrorMiddlewareConfig(
        debug=True,
        include_traceback=True,
        sanitize_errors=False,  # Don't sanitize in dev
    )))

    return chain


def create_staging_middleware() -> MiddlewareChain:
    """Create middleware for staging environment."""
    chain = MiddlewareChain()

    # Standard validation
    chain.add(ValidationMiddleware(config=ValidationMiddlewareConfig(
        max_request_size=10 * 1024 * 1024,
        validate_urls=True,
        validate_sparql=True,
        rate_limit_enabled=True,
        rate_limit_per_minute=100,
    )))

    # Standard logging
    chain.add(LoggingMiddleware(config=LoggingMiddlewareConfig(
        level=LogLevel.INFO,
        log_requests=True,
        log_responses=True,
        include_arguments=True,
        include_results=False,
        performance_threshold_ms=1000,
    )))

    # Moderate error detail
    chain.add(ErrorMiddleware(config=ErrorMiddlewareConfig(
        debug=True,
        include_traceback=False,
        sanitize_errors=True,
    )))

    return chain


def create_production_middleware() -> MiddlewareChain:
    """Create middleware for production environment."""
    chain = MiddlewareChain()

    # Strict validation
    chain.add(ValidationMiddleware(config=ValidationMiddlewareConfig(
        max_request_size=5 * 1024 * 1024,
        max_query_length=50000,
        max_results_limit=5000,
        validate_urls=True,
        validate_sparql=True,
        sanitize_inputs=True,
        rate_limit_enabled=True,
        rate_limit_per_minute=30,
    )))

    # Production logging
    chain.add(LoggingMiddleware(config=LoggingMiddlewareConfig(
        level=LogLevel.INFO,
        log_requests=True,
        log_responses=True,
        log_performance=True,
        log_user_actions=True,
        include_arguments=False,  # Don't log sensitive args
        include_results=False,
        performance_threshold_ms=2000,
    )))

    # Minimal error detail
    chain.add(ErrorMiddleware(config=ErrorMiddlewareConfig(
        debug=False,
        include_traceback=False,
        sanitize_errors=True,
        max_error_length=500,
    )))

    return chain


# ============================================================================
# Example 3: Middleware Factory with Environment Detection
# ============================================================================


import os


def create_middleware_for_environment() -> MiddlewareChain:
    """
    Create middleware based on environment variable.

    Reads ENVIRONMENT variable to determine configuration.
    Falls back to production if not set.

    Returns:
        Configured middleware chain
    """
    env = os.environ.get("ENVIRONMENT", "production").lower()

    if env == "development":
        return create_development_middleware()
    elif env == "staging":
        return create_staging_middleware()
    else:
        return create_production_middleware()


# ============================================================================
# Example 4: Selective Middleware Application
# ============================================================================


# Different middleware for different operations
query_middleware = MiddlewareChain()
query_middleware.add(ValidationMiddleware(config=ValidationMiddlewareConfig(
    validate_sparql=True,
    max_query_length=50000,
)))
query_middleware.add(LoggingMiddleware())
query_middleware.add(ErrorMiddleware())

# Lighter middleware for read-only operations
readonly_middleware = MiddlewareChain()
readonly_middleware.add(LoggingMiddleware())
readonly_middleware.add(ErrorMiddleware())

# Apply appropriate middleware
@query_middleware.wrap_handler
async def execute_query(query: str, **kwargs):
    """Execute query with full validation."""
    return {"status": "success"}


@readonly_middleware.wrap_handler
async def list_resources(**kwargs):
    """List resources with lighter middleware."""
    return {"resources": []}


# ============================================================================
# Example 5: Monitoring and Metrics
# ============================================================================


class MiddlewareMonitor:
    """Monitor middleware statistics."""

    def __init__(self, middleware_chain: MiddlewareChain):
        """Initialize monitor."""
        self.chain = middleware_chain

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status from middleware stats."""
        stats = self.chain.get_stats()

        # Extract key metrics
        health = {
            "status": "healthy",
            "checks": {},
        }

        # Check error rate
        for middleware_name, middleware_stats in stats.items():
            if "ErrorMiddleware" in middleware_name:
                error_count = middleware_stats.get("total_errors", 0)
                health["checks"]["error_rate"] = {
                    "status": "ok" if error_count < 10 else "warning",
                    "total_errors": error_count,
                }

            # Check performance
            if "LoggingMiddleware" in middleware_name:
                percentiles = middleware_stats.get("percentiles", {})
                p95 = percentiles.get("p95", 0)

                health["checks"]["performance"] = {
                    "status": "ok" if p95 < 2000 else "warning",
                    "p95_ms": p95,
                }

            # Check validation
            if "ValidationMiddleware" in middleware_name:
                failures = middleware_stats.get("validation_failures", 0)
                health["checks"]["validation"] = {
                    "status": "ok" if failures < 10 else "warning",
                    "failures": failures,
                }

        # Overall status
        if any(
            check["status"] == "warning"
            for check in health["checks"].values()
        ):
            health["status"] = "degraded"

        return health


# ============================================================================
# Example 6: Usage
# ============================================================================


async def main():
    """Demonstrate middleware integration."""
    print("=" * 60)
    print("MCP Middleware Integration Examples")
    print("=" * 60)

    # Test tool handlers
    print("\n1. Testing query handler with middleware:")
    result = await handle_query_sparql(
        query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        endpoint_url="https://example.org/sparql",
        limit=10
    )
    print(f"   Status: {result.get('status', 'N/A')}")

    print("\n2. Testing endpoint discovery with middleware:")
    result = await handle_discover_endpoint(
        endpoint_url="https://example.org/sparql"
    )
    print(f"   Capabilities: {len(result.get('capabilities', []))} found")

    print("\n3. Testing query generation with middleware:")
    result = await handle_generate_query(
        natural_language="Find all proteins that bind to DNA"
    )
    print(f"   Confidence: {result.get('confidence', 0)}")

    # Test environment-specific middleware
    print("\n4. Environment-specific middleware:")
    for env_name, creator in [
        ("Development", create_development_middleware),
        ("Staging", create_staging_middleware),
        ("Production", create_production_middleware),
    ]:
        chain = creator()
        print(f"   {env_name}: {len(chain.middlewares)} middleware components")

    # Monitor health
    print("\n5. Middleware health status:")
    monitor = MiddlewareMonitor(tool_middleware)
    health = monitor.get_health_status()
    print(f"   Overall status: {health['status']}")
    for check_name, check_data in health['checks'].items():
        print(f"   - {check_name}: {check_data['status']}")

    print("\n" + "=" * 60)
    print("All integration examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
