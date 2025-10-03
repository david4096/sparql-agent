# MCP Request/Response Handlers and Routing

Comprehensive request handling and routing system for the MCP server.

## Overview

The handlers module provides a complete request/response handling framework with:

- **RequestRouter**: Routes MCP requests to appropriate handlers
- **Handler Classes**: Specialized handlers for different operations
- **Parameter Validation**: Automatic validation and sanitization
- **Rate Limiting**: Per-client rate limiting with configurable limits
- **Authentication**: Optional authentication and authorization
- **Response Formatting**: Standardized response structure
- **Error Handling**: Comprehensive error handling and recovery
- **Progress Updates**: Support for long-running operations
- **Statistics**: Request and handler statistics tracking

## Architecture

```
┌──────────────┐
│ MCP Request  │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────┐
│      RequestRouter                  │
│  ┌───────────────────────────────┐  │
│  │ • Authentication              │  │
│  │ • Rate Limiting               │  │
│  │ • Request Validation          │  │
│  │ • Handler Routing             │  │
│  └───────────────────────────────┘  │
└────────┬────────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌────────┐  ┌────────┐
│Handler │  │Handler │  │Handler │
│   1    │  │   2    │  │   3    │
└────────┘  └────────┘  └────────┘
    │         │          │
    └─────────┴──────────┘
              ▼
    ┌──────────────┐
    │ MCP Response │
    └──────────────┘
```

## Handler Classes

### 1. QueryHandler

Executes SPARQL queries against endpoints.

**Operations:**
- Query execution
- Timeout management
- Result processing
- Format conversion

**Example:**
```python
from sparql_agent.mcp.handlers import QueryHandler

handler = QueryHandler()
request = MCPRequest(
    request_id="req_123",
    request_type=RequestType.QUERY,
    params={
        "query": "SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        "endpoint": "https://sparql.uniprot.org/sparql",
        "timeout": 30
    }
)

response = await handler.handle(request)
print(response.data['bindings'])
```

### 2. DiscoveryHandler

Performs endpoint introspection and discovery.

**Operations:**
- Capability detection
- Schema discovery
- Namespace extraction
- Statistics gathering

**Example:**
```python
from sparql_agent.mcp.handlers import DiscoveryHandler

handler = DiscoveryHandler()
request = MCPRequest(
    request_id="req_124",
    request_type=RequestType.DISCOVER,
    params={
        "endpoint": "https://sparql.uniprot.org/sparql",
        "discover_schema": True,
        "discover_capabilities": True
    }
)

response = await handler.handle(request)
print(response.data['capabilities'])
print(response.data['schema'])
```

### 3. GenerationHandler

Converts natural language to SPARQL queries.

**Operations:**
- NL parsing
- Query generation
- Template matching
- LLM-based generation
- Alternative generation

**Example:**
```python
from sparql_agent.mcp.handlers import GenerationHandler
from sparql_agent.query.generator import SPARQLGenerator

generator = SPARQLGenerator(llm_client=llm_client)
handler = GenerationHandler(generator=generator)

request = MCPRequest(
    request_id="req_125",
    request_type=RequestType.GENERATE,
    params={
        "natural_language": "Find all proteins from human",
        "return_alternatives": True
    }
)

response = await handler.handle(request)
print(response.data['query'])
print(response.data['confidence'])
```

### 4. ValidationHandler

Validates SPARQL query syntax and semantics.

**Operations:**
- Syntax validation
- Semantic checks
- Best practice suggestions
- Error reporting

**Example:**
```python
from sparql_agent.mcp.handlers import ValidationHandler

handler = ValidationHandler()
request = MCPRequest(
    request_id="req_126",
    request_type=RequestType.VALIDATE,
    params={
        "query": "SELECT * WHERE { ?s ?p ?o }",
        "strict": False
    }
)

response = await handler.handle(request)
print(response.data['is_valid'])
print(response.data['errors'])
print(response.data['warnings'])
```

### 5. FormattingHandler

Formats query results into various output formats.

**Operations:**
- JSON formatting
- CSV/TSV export
- Text formatting
- Metadata inclusion

**Example:**
```python
from sparql_agent.mcp.handlers import FormattingHandler

handler = FormattingHandler()
request = MCPRequest(
    request_id="req_127",
    request_type=RequestType.FORMAT,
    params={
        "result": query_result,
        "format": "json",
        "pretty": True,
        "include_metadata": True
    }
)

response = await handler.handle(request)
print(response.data['formatted'])
```

### 6. OntologyHandler

Interfaces with EBI OLS4 for ontology operations.

**Operations:**
- Term search
- Ontology lookup
- Hierarchy traversal
- Cross-references

**Example:**
```python
from sparql_agent.mcp.handlers import OntologyHandler

handler = OntologyHandler()

# Search for terms
request = MCPRequest(
    request_id="req_128",
    request_type=RequestType.ONTOLOGY,
    params={
        "operation": "search",
        "query": "protein",
        "ontology": "go",
        "limit": 10
    }
)

response = await handler.handle(request)
print(response.data['results'])
```

## RequestRouter

Central routing component with validation, rate limiting, and authentication.

### Basic Usage

```python
from sparql_agent.mcp.handlers import RequestRouter, MCPRequest, RequestType

# Create router
router = RequestRouter()

# Route a request
request = MCPRequest(
    request_id="req_129",
    request_type=RequestType.QUERY,
    params={
        "query": "SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        "endpoint": "https://sparql.uniprot.org/sparql"
    },
    client_id="client_1"
)

response = await router.route(request)
```

### With Rate Limiting

```python
from sparql_agent.mcp.handlers import RequestRouter, RateLimitConfig

# Configure rate limits
rate_config = RateLimitConfig(
    requests_per_minute=60,
    requests_per_hour=1000,
    burst_size=10,
    enable_per_client=True
)

router = RequestRouter(rate_limit_config=rate_config)
```

### With Authentication

```python
def validate_token(token: str) -> bool:
    """Custom authentication validator."""
    # Your authentication logic here
    return token in valid_tokens

router = RequestRouter(
    enable_auth=True,
    auth_validator=validate_token
)

# Request with auth token
request = MCPRequest(
    request_id="req_130",
    request_type=RequestType.QUERY,
    params={"query": "...", "endpoint": "..."},
    metadata={"auth_token": "your_token_here"}
)

response = await router.route(request)
```

### Custom Handlers

```python
from sparql_agent.mcp.handlers import BaseHandler, MCPRequest, MCPResponse

class CustomHandler(BaseHandler):
    def __init__(self):
        super().__init__("CustomHandler")

    async def handle(self, request: MCPRequest) -> MCPResponse:
        # Validate parameters
        self.validate_params(
            request.params,
            required=["param1", "param2"],
            optional=["param3"]
        )

        # Your custom logic here
        result = do_something(request.params)

        return MCPResponse.success(
            request_id=request.request_id,
            data=result
        )

# Register custom handler
router = RequestRouter()
router.register_handler(RequestType.CUSTOM, CustomHandler())
```

## Rate Limiting

### Configuration

```python
from sparql_agent.mcp.handlers import RateLimitConfig

config = RateLimitConfig(
    requests_per_minute=60,    # Max 60 requests per minute
    requests_per_hour=1000,    # Max 1000 requests per hour
    burst_size=10,             # Allow burst of 10 requests
    enable_per_client=True     # Track per client
)
```

### Monitoring

```python
# Get rate limit statistics for a client
stats = router.rate_limiter.get_client_stats("client_id")
print(f"Requests last minute: {stats['requests_last_minute']}")
print(f"Requests last hour: {stats['requests_last_hour']}")
print(f"Burst available: {stats['burst_size']}")
```

## Response Format

### Success Response

```json
{
    "request_id": "req_123",
    "status": "success",
    "data": {
        // Response-specific data
    },
    "metadata": {
        "duration": 0.123,
        "timestamp": "2025-10-02T12:00:00Z"
    },
    "warnings": []
}
```

### Error Response

```json
{
    "request_id": "req_123",
    "status": "error",
    "error": {
        "type": "QueryExecutionError",
        "message": "Query execution failed",
        "details": {
            "endpoint": "...",
            "reason": "..."
        }
    },
    "metadata": {
        "duration": 0.123
    }
}
```

## Statistics and Monitoring

### Router Statistics

```python
stats = router.get_stats()

# Overall statistics
print(f"Total requests: {stats['total_requests']}")
print(f"Successful: {stats['successful_requests']}")
print(f"Failed: {stats['failed_requests']}")
print(f"Rate limited: {stats['rate_limited_requests']}")
print(f"Auth failed: {stats['auth_failed_requests']}")
print(f"Active: {stats['active_requests']}")

# Per-handler statistics
for handler_name, handler_stats in stats['handler_stats'].items():
    print(f"\n{handler_name}:")
    print(f"  Total: {handler_stats['total_requests']}")
    print(f"  Success rate: {handler_stats['successful_requests'] / handler_stats['total_requests']:.2%}")
    print(f"  Average duration: {handler_stats['average_duration']:.3f}s")
```

### Request History

```python
# Get recent request history
history = router.get_request_history(limit=100)

for entry in history:
    print(f"{entry['timestamp']}: {entry['type']} - {entry['status']}")
```

## Progress Updates

For long-running operations:

```python
from sparql_agent.mcp.handlers import ProgressUpdate

# Create progress update
update = ProgressUpdate(
    request_id="req_123",
    progress=45.5,
    message="Processing query results",
    current_step="Formatting",
    total_steps=3
)

# Convert to dict for sending
update_dict = update.to_dict()
```

## Error Handling

### Standard Error Types

- `InputValidationError`: Invalid request parameters
- `QueryExecutionError`: Query execution failed
- `QueryGenerationError`: Query generation failed
- `EndpointError`: Endpoint connection/availability issues
- `RateLimitError`: Rate limit exceeded
- `AuthenticationError`: Authentication failed

### Error Response Pattern

```python
try:
    response = await router.route(request)
    if response.status == ResponseStatus.ERROR:
        error = response.error
        print(f"Error type: {error['type']}")
        print(f"Message: {error['message']}")
        print(f"Details: {error.get('details', {})}")
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
```

## Best Practices

### 1. Parameter Validation

Always validate parameters in handlers:

```python
def handle(self, request: MCPRequest) -> MCPResponse:
    self.validate_params(
        request.params,
        required=["param1", "param2"],
        optional=["param3"]
    )
    # ... rest of handler logic
```

### 2. Error Context

Provide detailed error context:

```python
return MCPResponse.error(
    request_id=request.request_id,
    error_type="QueryExecutionError",
    error_message="Query execution failed",
    details={
        "endpoint": endpoint_url,
        "query_hash": query_hash,
        "reason": str(e)
    }
)
```

### 3. Statistics Tracking

Update statistics in handlers:

```python
start_time = time.time()
try:
    # ... handler logic
    duration = time.time() - start_time
    self.update_stats(success=True, duration=duration)
except Exception as e:
    duration = time.time() - start_time
    self.update_stats(success=False, duration=duration)
    raise
```

### 4. Client Identification

Always include client ID for rate limiting:

```python
request = MCPRequest(
    request_id="req_123",
    request_type=RequestType.QUERY,
    params={...},
    client_id="my_app_v1"  # Important for rate limiting
)
```

### 5. Timeouts

Set appropriate timeouts:

```python
params = {
    "query": "...",
    "endpoint": "...",
    "timeout": 30  # Adjust based on query complexity
}
```

## Testing

### Unit Tests

```python
import pytest
from sparql_agent.mcp.handlers import QueryHandler, MCPRequest, RequestType

@pytest.mark.asyncio
async def test_query_handler():
    handler = QueryHandler()
    request = MCPRequest(
        request_id="test_123",
        request_type=RequestType.QUERY,
        params={
            "query": "SELECT * WHERE { ?s ?p ?o } LIMIT 1",
            "endpoint": "http://test-endpoint/sparql"
        }
    )

    response = await handler.handle(request)
    assert response.status == ResponseStatus.SUCCESS
    assert "bindings" in response.data
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_routing():
    router = create_router(enable_rate_limiting=False)

    request_data = {
        "type": "validate",
        "params": {
            "query": "SELECT * WHERE { ?s ?p ?o }"
        }
    }

    response = await handle_request(router, request_data)
    assert response["status"] == "success"
    assert response["data"]["is_valid"] == True
```

## Examples

See `example_handlers.py` for comprehensive usage examples including:

1. Query execution
2. Endpoint discovery
3. Query validation
4. Query generation
5. Ontology operations
6. Rate limiting
7. Statistics monitoring
8. Error handling

Run examples:

```bash
python src/sparql_agent/mcp/example_handlers.py
```

## API Reference

### Classes

- `RequestRouter`: Main routing class
- `BaseHandler`: Abstract base for handlers
- `QueryHandler`: SPARQL query execution
- `DiscoveryHandler`: Endpoint discovery
- `GenerationHandler`: Query generation
- `ValidationHandler`: Query validation
- `FormattingHandler`: Result formatting
- `OntologyHandler`: Ontology operations

### Data Types

- `MCPRequest`: Request wrapper
- `MCPResponse`: Response wrapper
- `ProgressUpdate`: Progress notification
- `RequestType`: Request type enum
- `ResponseStatus`: Response status enum
- `RateLimitConfig`: Rate limit configuration

### Utility Functions

- `create_router()`: Create configured router
- `handle_request()`: Convenience function for handling requests

## Performance Considerations

1. **Connection Pooling**: QueryHandler uses connection pooling for efficiency
2. **Caching**: Consider adding response caching for frequently accessed data
3. **Async Operations**: All handlers are async for better concurrency
4. **Rate Limiting**: Protects against abuse and resource exhaustion
5. **Statistics**: Minimal overhead, tracked asynchronously

## Security

1. **Input Validation**: All parameters validated before processing
2. **Query Sanitization**: SPARQL queries checked for injection attempts
3. **Rate Limiting**: Prevents DoS attacks
4. **Authentication**: Optional but recommended for production
5. **Error Messages**: No sensitive information leaked in errors

## Future Enhancements

- [ ] Response caching
- [ ] Request queueing for fairness
- [ ] Advanced authentication (OAuth, JWT)
- [ ] Webhook support for progress updates
- [ ] Request retry policies
- [ ] Circuit breakers for failing endpoints
- [ ] Request prioritization
- [ ] Distributed rate limiting (Redis)
