# MCP Middleware Documentation

Comprehensive middleware components for error handling, logging, and validation in the SPARQL Agent MCP server.

## Overview

The middleware system provides three core components that can be used individually or composed together:

1. **ErrorMiddleware** - Exception catching, formatting, and sanitization
2. **LoggingMiddleware** - Request/response logging and performance tracking
3. **ValidationMiddleware** - Input validation and security sanitization

## Quick Start

```python
from sparql_agent.mcp.middleware import (
    ErrorMiddleware,
    LoggingMiddleware,
    ValidationMiddleware,
    MiddlewareChain,
    LogLevel,
)

# Create middleware chain
chain = MiddlewareChain()
chain.add(ValidationMiddleware())
chain.add(LoggingMiddleware())
chain.add(ErrorMiddleware())

# Apply to handler
@chain.wrap_handler
async def my_handler(query: str, endpoint_url: str):
    # Your handler code
    return {"status": "success"}
```

## ErrorMiddleware

Catches and formats exceptions, converting them to MCP-compatible responses.

### Features

- Exception catching and formatting
- Error message sanitization (removes file paths, API keys, emails, IPs)
- Error code mapping for different exception types
- Debug mode with tracebacks
- Error statistics tracking

### Configuration

```python
from sparql_agent.mcp.middleware import ErrorMiddleware, ErrorMiddlewareConfig

config = ErrorMiddlewareConfig(
    debug=False,                # Enable debug mode (include extra details)
    include_traceback=False,    # Include Python tracebacks in errors
    sanitize_errors=True,       # Sanitize error messages
    max_error_length=1000,      # Maximum error message length
    log_errors=True,            # Log errors
    log_level=LogLevel.ERROR,   # Log level for errors
)

middleware = ErrorMiddleware(config=config)
```

### Usage

```python
# Wrap a handler
@middleware.wrap_handler
async def my_handler(arg: str):
    if not arg:
        raise ValueError("Argument required")
    return {"result": arg}

# Execute handler - errors are caught and formatted
result = await my_handler("")
# Returns: {"error": "Argument required", "error_type": "ValueError", ...}
```

### Error Codes

The middleware automatically maps exceptions to error codes:

| Exception Type | Error Code |
|---|---|
| `EndpointError` | `ENDPOINT_ERROR` |
| `QueryError` | `QUERY_ERROR` |
| `SchemaError` | `SCHEMA_ERROR` |
| `OntologyError` | `ONTOLOGY_ERROR` |
| `LLMError` | `LLM_ERROR` |
| `QueryGenerationError` | `GENERATION_ERROR` |
| `FormattingError` | `FORMATTING_ERROR` |
| `ConfigurationError` | `CONFIG_ERROR` |
| `ValidationError` | `VALIDATION_ERROR` |
| `ValueError` | `INVALID_INPUT` |
| `KeyError` | `MISSING_PARAMETER` |
| `TimeoutError` | `TIMEOUT` |
| Other | `INTERNAL_ERROR` |

### Error Response Format

```json
{
  "error": "Sanitized error message",
  "error_type": "QueryExecutionError",
  "error_code": "QUERY_ERROR",
  "handler": "query_sparql",
  "timestamp": "2025-10-02T22:30:00.000Z",
  "details": {
    "sanitized_key": "sanitized_value"
  }
}
```

### Sanitization

The middleware automatically removes sensitive information:

- File paths → `<file>`
- API keys and tokens → `<redacted>`
- Email addresses → `<email>`
- IP addresses → `<ip>`

### Statistics

```python
stats = middleware.get_stats()
# Returns:
# {
#   "total_errors": 10,
#   "recent_errors": [...]  # Last 10 errors
# }
```

## LoggingMiddleware

Logs requests, responses, and performance metrics.

### Features

- Request and response logging
- Performance metrics collection (percentiles, averages)
- User action tracking
- Slow operation detection
- Configurable log levels and detail
- Log truncation for large payloads

### Configuration

```python
from sparql_agent.mcp.middleware import LoggingMiddleware, LoggingMiddlewareConfig, LogLevel

config = LoggingMiddlewareConfig(
    level=LogLevel.INFO,                # Log level
    log_requests=True,                  # Log incoming requests
    log_responses=True,                 # Log responses
    log_performance=True,               # Track performance metrics
    log_user_actions=True,              # Log user actions
    include_arguments=True,             # Include request arguments in logs
    include_results=False,              # Include results (can be verbose)
    max_log_length=2000,               # Maximum log message length
    performance_threshold_ms=1000.0,   # Warn if operation exceeds this
)

middleware = LoggingMiddleware(config=config)
```

### Usage

```python
@middleware.wrap_handler
async def my_handler(query: str):
    # Your handler code
    return {"result": "success"}

# Logs:
# INFO: Request [my_handler_0] my_handler - Args: {"query": "SELECT..."}
# INFO: Response [my_handler_0] my_handler - 15.23ms
# INFO: UserAction: {"action": "my.handler", "success": true, "duration_ms": 15.23}
```

### Performance Tracking

The middleware tracks:
- Total requests
- Average duration
- Percentiles (p50, p95, p99)
- Slow operations (exceeding threshold)

```python
stats = middleware.get_stats()
# Returns:
# {
#   "total_requests": 100,
#   "total_duration_ms": 15234.5,
#   "avg_duration_ms": 152.3,
#   "percentiles": {
#     "p50": 120.5,
#     "p95": 450.2,
#     "p99": 890.1
#   },
#   "slow_operations": 5
# }
```

### Slow Operation Warning

When an operation exceeds `performance_threshold_ms`:

```
WARNING: Slow operation: my_handler took 2534.12ms (threshold: 1000ms)
```

## ValidationMiddleware

Validates and sanitizes input parameters.

### Features

- Request size limiting
- SPARQL query validation (syntax, dangerous operations)
- URL validation (format, allowed schemes)
- Parameter type checking
- Security sanitization (XSS, injection prevention)
- Rate limiting support

### Configuration

```python
from sparql_agent.mcp.middleware import ValidationMiddleware, ValidationMiddlewareConfig

config = ValidationMiddlewareConfig(
    max_request_size=10 * 1024 * 1024,  # 10MB max request size
    max_query_length=100000,             # 100KB max query length
    max_results_limit=10000,             # Maximum results per query
    allowed_tool_names=None,             # Set of allowed tool names (None = all)
    validate_urls=True,                  # Validate URL format
    validate_sparql=True,                # Validate SPARQL syntax
    sanitize_inputs=True,                # Sanitize inputs for XSS
    rate_limit_enabled=False,            # Enable rate limiting
    rate_limit_per_minute=60,           # Requests per minute
)

middleware = ValidationMiddleware(config=config)
```

### Usage

```python
@middleware.wrap_handler
async def my_handler(query: str, endpoint_url: str, limit: int):
    # Handler only executes if validation passes
    return {"result": "success"}

# Valid request
result = await my_handler(
    query="SELECT * WHERE { ?s ?p ?o }",
    endpoint_url="https://example.org/sparql",
    limit=100
)

# Invalid request - raises ValidationError
result = await my_handler(
    query="DROP GRAPH <http://example.org>",  # Dangerous operation
    endpoint_url="javascript:alert('xss')",    # Invalid URL scheme
    limit=999999                               # Exceeds max limit
)
```

### Validation Rules

#### SPARQL Queries

- Must be non-empty string
- Must contain SELECT, CONSTRUCT, ASK, or DESCRIBE
- Cannot exceed `max_query_length`
- Blocks dangerous operations:
  - `LOAD`
  - `DROP`
  - `CLEAR`
  - `CREATE`
  - `INSERT` (UPDATE context)
  - `DELETE` (UPDATE context)

#### URLs

- Must be valid HTTP/HTTPS URL
- Blocks dangerous schemes: `file://`, `ftp://`, `javascript:`, `data:`
- Validates format with regex

#### Limits

- Must be non-negative integer
- Cannot exceed `max_results_limit`

#### Request Size

- Total serialized request size cannot exceed `max_request_size`

### Input Sanitization

When `sanitize_inputs=True`, the middleware removes:

- Control characters (`\x00-\x1f`, `\x7f-\x9f`)
- `<script>` tags
- `javascript:` URIs
- Event handlers (`onclick=`, `onload=`, etc.)

### Rate Limiting

When `rate_limit_enabled=True`:

- Tracks requests per handler per minute
- Raises `ValidationError` if limit exceeded
- Sliding window algorithm (1 minute)

```python
config = ValidationMiddlewareConfig(
    rate_limit_enabled=True,
    rate_limit_per_minute=30,  # 30 requests/minute per handler
)
```

### Statistics

```python
stats = middleware.get_stats()
# Returns:
# {
#   "validation_failures": 5,
#   "rate_limit_cache_size": 3
# }
```

## MiddlewareChain

Compose multiple middleware components in a flexible order.

### Usage

```python
from sparql_agent.mcp.middleware import MiddlewareChain

# Create chain
chain = MiddlewareChain()

# Add middleware (order matters!)
chain.add(ValidationMiddleware())  # First: validate
chain.add(LoggingMiddleware())     # Second: log
chain.add(ErrorMiddleware())       # Third: catch errors

# Apply to handler
@chain.wrap_handler
async def my_handler(arg: str):
    return {"result": arg}
```

### Execution Order

Middleware is applied in **reverse order** (last added wraps first):

```python
chain.add(A)  # Third to execute
chain.add(B)  # Second to execute
chain.add(C)  # First to execute

# Execution flow:
# C.before → B.before → A.before → handler → A.after → B.after → C.after
```

**Recommended order:**
1. ValidationMiddleware (validate first)
2. LoggingMiddleware (log validated requests)
3. ErrorMiddleware (catch all errors last)

### Statistics

```python
stats = chain.get_stats()
# Returns combined stats from all middleware:
# {
#   "ValidationMiddleware_0": {...},
#   "LoggingMiddleware_1": {...},
#   "ErrorMiddleware_2": {...}
# }
```

## Production Configuration

Recommended production setup:

```python
from sparql_agent.mcp.middleware import (
    MiddlewareChain,
    ValidationMiddleware,
    ValidationMiddlewareConfig,
    LoggingMiddleware,
    LoggingMiddlewareConfig,
    ErrorMiddleware,
    ErrorMiddlewareConfig,
    LogLevel,
)

# Production validation
validation = ValidationMiddleware(config=ValidationMiddlewareConfig(
    max_request_size=5 * 1024 * 1024,  # 5MB
    max_query_length=50000,
    max_results_limit=5000,
    validate_urls=True,
    validate_sparql=True,
    sanitize_inputs=True,
    rate_limit_enabled=True,
    rate_limit_per_minute=30,
))

# Production logging
logging = LoggingMiddleware(config=LoggingMiddlewareConfig(
    level=LogLevel.INFO,
    log_requests=True,
    log_responses=True,
    log_performance=True,
    log_user_actions=True,
    include_arguments=False,        # Don't log sensitive args
    include_results=False,          # Results can be large
    performance_threshold_ms=2000,  # 2 second warning threshold
))

# Production error handling
error = ErrorMiddleware(config=ErrorMiddlewareConfig(
    debug=False,                    # No debug info in production
    include_traceback=False,        # Don't expose tracebacks
    sanitize_errors=True,           # Always sanitize
    max_error_length=500,
    log_errors=True,
    log_level=LogLevel.ERROR,
))

# Create production chain
production_chain = MiddlewareChain()
production_chain.add(validation)
production_chain.add(logging)
production_chain.add(error)

# Apply to all handlers
@production_chain.wrap_handler
async def my_handler(query: str, endpoint_url: str, limit: int = 100):
    # Production-ready handler with full middleware protection
    return await execute_query(query, endpoint_url, limit)
```

## Integration with MCP Server

Example of integrating middleware with the MCP server:

```python
from sparql_agent.mcp import MCPServer, MCPServerConfig
from sparql_agent.mcp.middleware import MiddlewareChain, ErrorMiddleware, LoggingMiddleware

class MiddlewareAwareMCPServer(MCPServer):
    """MCP Server with middleware support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Setup middleware
        self.middleware = MiddlewareChain()
        self.middleware.add(ValidationMiddleware())
        self.middleware.add(LoggingMiddleware())
        self.middleware.add(ErrorMiddleware())

    def _setup_handlers(self):
        """Setup MCP handlers with middleware."""
        # Wrap original handlers
        original_call_tool = self.handle_call_tool

        @self.middleware.wrap_handler
        async def wrapped_call_tool(*args, **kwargs):
            return await original_call_tool(*args, **kwargs)

        self.mcp.call_tool()(wrapped_call_tool)

        # Setup other handlers...
```

## Testing

Run the test suite:

```bash
pytest src/sparql_agent/mcp/test_middleware.py -v
```

Run examples:

```bash
python src/sparql_agent/mcp/middleware_example.py
```

## Best Practices

1. **Always use middleware in production** - Don't expose raw handlers
2. **Order matters** - Validate → Log → Handle Errors
3. **Configure for environment** - Different settings for dev/prod
4. **Monitor statistics** - Use `get_stats()` for observability
5. **Sanitize in production** - Always enable error sanitization
6. **Set reasonable limits** - Prevent resource exhaustion
7. **Log performance** - Track slow operations
8. **Rate limit** - Protect against abuse

## Performance Considerations

- **Minimal overhead**: Middleware adds ~1-2ms per request
- **Async-friendly**: All middleware is fully async
- **Memory efficient**: Limited history storage (last 100-1000 items)
- **No blocking**: All operations are non-blocking

## Security Features

- Error message sanitization (removes sensitive data)
- Input sanitization (XSS prevention)
- SPARQL injection prevention (blocks dangerous operations)
- URL validation (blocks dangerous schemes)
- Rate limiting
- Request size limiting

## Troubleshooting

### High Error Rate

Check error middleware stats:
```python
stats = error_middleware.get_stats()
print(stats["recent_errors"])
```

### Slow Operations

Check logging middleware stats:
```python
stats = logging_middleware.get_stats()
print(f"P95: {stats['percentiles']['p95']}ms")
print(f"Slow ops: {stats['slow_operations']}")
```

### Validation Failures

Check validation middleware stats:
```python
stats = validation_middleware.get_stats()
print(f"Failures: {stats['validation_failures']}")
```

## API Reference

See the inline documentation in `middleware.py` for complete API details:

```python
from sparql_agent.mcp.middleware import ErrorMiddleware
help(ErrorMiddleware)
```

## License

Copyright (c) 2025 SPARQL Agent contributors. See LICENSE for details.
