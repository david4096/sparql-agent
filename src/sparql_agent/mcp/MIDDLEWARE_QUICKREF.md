# MCP Middleware Quick Reference

## Installation

```python
from sparql_agent.mcp.middleware import (
    ErrorMiddleware,
    LoggingMiddleware,
    ValidationMiddleware,
    MiddlewareChain,
    LogLevel,
)
```

## Quick Start (3 lines)

```python
chain = MiddlewareChain()
chain.add(ValidationMiddleware()).add(LoggingMiddleware()).add(ErrorMiddleware())

@chain.wrap_handler
async def my_handler(query: str, endpoint_url: str):
    return {"status": "success"}
```

## Individual Middleware

### ErrorMiddleware

```python
# Basic
error_mw = ErrorMiddleware()

# Custom config
error_mw = ErrorMiddleware(config=ErrorMiddlewareConfig(
    debug=True,
    include_traceback=True,
    sanitize_errors=True,
))

@error_mw.wrap_handler
async def handler():
    # Your code
    pass
```

### LoggingMiddleware

```python
# Basic
log_mw = LoggingMiddleware()

# Custom config
log_mw = LoggingMiddleware(config=LoggingMiddlewareConfig(
    level=LogLevel.INFO,
    log_requests=True,
    log_performance=True,
))

@log_mw.wrap_handler
async def handler():
    # Your code
    pass
```

### ValidationMiddleware

```python
# Basic
val_mw = ValidationMiddleware()

# Custom config
val_mw = ValidationMiddleware(config=ValidationMiddlewareConfig(
    max_request_size=10*1024*1024,  # 10MB
    validate_urls=True,
    validate_sparql=True,
))

@val_mw.wrap_handler
async def handler(query: str, endpoint_url: str):
    # Your code
    pass
```

## Production Config

```python
# Production-ready setup
chain = MiddlewareChain()

chain.add(ValidationMiddleware(config=ValidationMiddlewareConfig(
    max_request_size=5*1024*1024,
    validate_urls=True,
    validate_sparql=True,
    sanitize_inputs=True,
    rate_limit_enabled=True,
    rate_limit_per_minute=30,
)))

chain.add(LoggingMiddleware(config=LoggingMiddlewareConfig(
    level=LogLevel.INFO,
    log_performance=True,
    include_arguments=False,  # Don't log sensitive data
    performance_threshold_ms=2000,
)))

chain.add(ErrorMiddleware(config=ErrorMiddlewareConfig(
    debug=False,
    include_traceback=False,
    sanitize_errors=True,
)))
```

## Statistics

```python
# Get stats from any middleware
stats = middleware.get_stats()

# Get combined stats from chain
all_stats = chain.get_stats()
```

## Error Codes

| Exception | Code |
|---|---|
| EndpointError | ENDPOINT_ERROR |
| QueryError | QUERY_ERROR |
| ValidationError | VALIDATION_ERROR |
| LLMError | LLM_ERROR |
| ValueError | INVALID_INPUT |
| KeyError | MISSING_PARAMETER |

## Validation Rules

### SPARQL Queries
- ✓ Must contain SELECT/CONSTRUCT/ASK/DESCRIBE
- ✗ Blocks: DROP, INSERT, DELETE, LOAD, CREATE, CLEAR

### URLs
- ✓ Allows: http://, https://
- ✗ Blocks: file://, javascript:, data:, ftp://

### Limits
- Max request size: 10MB (default)
- Max query length: 100KB (default)
- Max results limit: 10,000 (default)

## Sanitization

Automatically removes from errors:
- File paths → `<file>`
- API keys → `<redacted>`
- Emails → `<email>`
- IPs → `<ip>`

## Common Patterns

### Development
```python
chain = MiddlewareChain()
chain.add(ErrorMiddleware(config=ErrorMiddlewareConfig(
    debug=True,
    include_traceback=True,
)))
```

### Testing
```python
chain = MiddlewareChain()
chain.add(LoggingMiddleware(config=LoggingMiddlewareConfig(
    level=LogLevel.DEBUG,
    include_arguments=True,
    include_results=True,
)))
```

### Production
```python
chain = MiddlewareChain()
chain.add(ValidationMiddleware())
chain.add(LoggingMiddleware())
chain.add(ErrorMiddleware(config=ErrorMiddlewareConfig(
    debug=False,
    sanitize_errors=True,
)))
```

## Files

- `middleware.py` - Core implementation
- `middleware_example.py` - Usage examples
- `test_middleware.py` - Test suite (23 tests)
- `MIDDLEWARE.md` - Full documentation
- `MIDDLEWARE_SUMMARY.md` - Implementation summary
- `MIDDLEWARE_QUICKREF.md` - This file

## See Also

- Full documentation: `MIDDLEWARE.md`
- Examples: `middleware_example.py`
- Tests: `test_middleware.py`
