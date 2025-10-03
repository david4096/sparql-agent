# MCP Handlers Module - Implementation Summary

## Overview

This document provides a summary of the MCP request/response handling and routing implementation (AGENT 9B).

## What Was Built

### Core Components

1. **RequestRouter** - Central routing component with:
   - Request routing to appropriate handlers
   - Parameter validation and sanitization
   - Rate limiting per client (configurable)
   - Optional authentication/authorization
   - Request tracking and statistics
   - Request history logging

2. **Handler Classes** - Six specialized handlers:
   - **QueryHandler**: Execute SPARQL queries against endpoints
   - **DiscoveryHandler**: Endpoint introspection and capability detection
   - **GenerationHandler**: Natural language to SPARQL conversion
   - **ValidationHandler**: SPARQL query validation
   - **FormattingHandler**: Result formatting (JSON, CSV, text)
   - **OntologyHandler**: EBI OLS4 operations (NEW - as requested)

3. **Supporting Infrastructure**:
   - Request/Response wrapper classes
   - Rate limiting system with token bucket algorithm
   - Progress update mechanism for long-running operations
   - Standardized error responses
   - Statistics tracking and monitoring
   - Streaming support (prepared)

## File Structure

```
src/sparql_agent/mcp/
├── handlers.py              # Main handlers implementation (~1,350 lines)
├── example_handlers.py      # Comprehensive usage examples
├── HANDLERS.md              # Detailed documentation
└── README_HANDLERS.md       # This summary
```

## Key Features

### 1. Request Routing

The `RequestRouter` class provides:
- Async request handling
- Handler registration system
- Built-in rate limiting
- Authentication support
- Comprehensive statistics

### 2. Rate Limiting

Token bucket rate limiter with:
- Per-minute limits
- Per-hour limits
- Burst size control
- Per-client tracking
- Statistics and monitoring

### 3. Parameter Validation

All handlers include:
- Required parameter checking
- Optional parameter support
- Type validation
- Clear error messages
- Security validation

### 4. Response Formatting

Standardized responses with:
- Success/error status
- Data payload
- Error details (type, message, details)
- Metadata (timing, caching, etc.)
- Warnings array
- Streaming support flag

### 5. Error Handling

Comprehensive error handling:
- Specific error types
- Detailed error context
- Proper exception propagation
- User-friendly messages
- Security-conscious (no leaks)

## Handler Details

### QueryHandler

**Purpose**: Execute SPARQL queries

**Parameters**:
- `query` (required): SPARQL query string
- `endpoint` (required): Endpoint URL
- `timeout` (optional): Query timeout
- `format` (optional): Result format
- `limit` (optional): Result limit

**Returns**:
- Query results (bindings)
- Execution time
- Row count
- Variables
- Warnings

### DiscoveryHandler

**Purpose**: Discover endpoint capabilities and schema

**Parameters**:
- `endpoint` (required): Endpoint URL
- `discover_schema` (optional): Enable schema discovery
- `discover_capabilities` (optional): Enable capability detection
- `timeout` (optional): Discovery timeout

**Returns**:
- SPARQL version
- Named graphs
- Namespaces
- Classes and properties
- Statistics

### GenerationHandler

**Purpose**: Convert natural language to SPARQL

**Parameters**:
- `natural_language` (required): User query
- `endpoint` (optional): Target endpoint
- `schema` (optional): Schema information
- `ontology` (optional): Ontology information
- `strategy` (optional): Generation strategy
- `return_alternatives` (optional): Return alternatives

**Returns**:
- Generated SPARQL query
- Explanation
- Confidence score
- Validation errors
- Alternatives (if requested)

### ValidationHandler

**Purpose**: Validate SPARQL queries

**Parameters**:
- `query` (required): SPARQL query
- `strict` (optional): Strict validation mode

**Returns**:
- Validation status
- Errors
- Warnings
- Suggestions
- Summary

### FormattingHandler

**Purpose**: Format query results

**Parameters**:
- `result` (required): Query result
- `format` (required): Output format (json, csv, text)
- `pretty` (optional): Pretty printing
- `include_metadata` (optional): Include metadata

**Returns**:
- Formatted output
- Format type

### OntologyHandler (NEW)

**Purpose**: EBI OLS4 ontology operations

**Operations**:
1. **search**: Search for terms across ontologies
2. **get_term**: Get detailed term information
3. **get_ontology**: Get ontology metadata
4. **list_ontologies**: List available ontologies
5. **get_parents**: Get parent terms
6. **get_children**: Get child terms

**Parameters** (vary by operation):
- `operation` (required): Operation type
- `query` (for search): Search query
- `ontology` (for most ops): Ontology ID
- `term_id` (for term ops): Term identifier
- `limit` (optional): Result limit
- `exact` (optional): Exact match

**Returns** (vary by operation):
- Search results with terms
- Term details with hierarchy
- Ontology metadata
- Parent/child relationships

## Rate Limiting

### Configuration

```python
RateLimitConfig(
    requests_per_minute=60,     # 60 requests/minute
    requests_per_hour=1000,     # 1000 requests/hour
    burst_size=10,              # Allow burst of 10
    enable_per_client=True      # Track per client
)
```

### Algorithm

Token bucket with:
- Two buckets (minute and hour)
- Automatic cleanup of old entries
- Burst allowance
- Per-client tracking
- Statistics API

## Authentication

Optional authentication system:

```python
def validate_auth(token: str) -> bool:
    # Your validation logic
    return is_valid(token)

router = RequestRouter(
    enable_auth=True,
    auth_validator=validate_auth
)
```

Auth token passed in request metadata:
```python
request.metadata["auth_token"] = "your_token"
```

## Statistics

### Router Statistics

Tracks:
- Total requests
- Successful requests
- Failed requests
- Rate-limited requests
- Auth-failed requests
- Active requests
- Per-handler statistics

### Handler Statistics

Each handler tracks:
- Total requests
- Successful/failed counts
- Average duration
- Success rate

## Usage Examples

### Basic Query Execution

```python
from sparql_agent.mcp.handlers import create_router, handle_request

router = create_router()

response = await handle_request(router, {
    "type": "query",
    "params": {
        "query": "SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        "endpoint": "https://sparql.uniprot.org/sparql"
    }
})
```

### With Rate Limiting

```python
from sparql_agent.mcp.handlers import RequestRouter, RateLimitConfig

config = RateLimitConfig(requests_per_minute=30)
router = RequestRouter(rate_limit_config=config)
```

### Custom Handler

```python
from sparql_agent.mcp.handlers import BaseHandler

class CustomHandler(BaseHandler):
    async def handle(self, request):
        self.validate_params(request.params, required=["param1"])
        # Your logic here
        return MCPResponse.success(request.request_id, data=result)

router.register_handler(RequestType.CUSTOM, CustomHandler())
```

## Integration Points

The handlers integrate with:

1. **Execution Module**: `QueryExecutor` for query execution
2. **Validation Module**: `QueryValidator` for query validation
3. **Generation Module**: `SPARQLGenerator` for NL to SPARQL
4. **Discovery Module**: `CapabilitiesDetector`, `SchemaInference`
5. **Formatting Module**: `JSONFormatter`, `CSVFormatter`, `TextFormatter`
6. **Ontology Module**: `OLSClient` for EBI OLS4 access

## Error Handling

All errors follow this pattern:

```python
MCPResponse.error(
    request_id=request.request_id,
    error_type="ErrorClassName",
    error_message="Human-readable message",
    details={
        "additional": "context",
        "about": "error"
    }
)
```

Standard error types:
- `InputValidationError`: Invalid parameters
- `QueryExecutionError`: Query failed
- `QueryGenerationError`: Generation failed
- `EndpointError`: Endpoint issues
- `RateLimitError`: Rate limit exceeded
- `AuthenticationError`: Auth failed

## Testing

Comprehensive examples in `example_handlers.py`:

1. Query execution
2. Endpoint discovery
3. Query validation
4. Query generation (with/without LLM)
5. Ontology operations
6. Rate limiting demonstration
7. Statistics monitoring
8. Error handling patterns

Run: `python src/sparql_agent/mcp/example_handlers.py`

## Performance

Optimizations:
- Async operations throughout
- Connection pooling (QueryExecutor)
- Minimal overhead for statistics
- Efficient rate limiting (deque-based)
- No blocking operations

## Security

Security features:
- Input validation on all parameters
- Query sanitization
- Rate limiting (DoS protection)
- Optional authentication
- No sensitive data in errors
- Per-client isolation

## Documentation

Three documentation levels:

1. **HANDLERS.md**: Comprehensive guide with examples
2. **README_HANDLERS.md**: This implementation summary
3. **Inline docstrings**: Full API documentation

## Future Enhancements

Potential improvements:
- Response caching
- Request queueing
- Advanced authentication (OAuth, JWT)
- Webhook notifications
- Circuit breakers
- Distributed rate limiting (Redis)
- Request prioritization

## Completeness Checklist

✅ RequestRouter class with routing
✅ Parameter validation
✅ Authentication/authorization hooks
✅ Rate limiting per client
✅ QueryHandler for execution
✅ DiscoveryHandler for introspection
✅ GenerationHandler for NL to SPARQL
✅ ValidationHandler for query validation
✅ FormattingHandler for results
✅ OntologyHandler for EBI OLS4 (NEW)
✅ Standardized response formatting
✅ Error response formatting
✅ Progress update support
✅ Streaming support (prepared)
✅ Statistics tracking
✅ Request history
✅ Comprehensive examples
✅ Full documentation

## API Summary

### Main Classes

- `RequestRouter`: Central routing
- `BaseHandler`: Handler base class
- `QueryHandler`: Query execution
- `DiscoveryHandler`: Discovery
- `GenerationHandler`: Generation
- `ValidationHandler`: Validation
- `FormattingHandler`: Formatting
- `OntologyHandler`: Ontology ops

### Data Types

- `MCPRequest`: Request wrapper
- `MCPResponse`: Response wrapper
- `ProgressUpdate`: Progress notification
- `RequestType`: Request type enum
- `ResponseStatus`: Status enum
- `RateLimitConfig`: Rate limit config

### Utility Functions

- `create_router()`: Create router
- `handle_request()`: Handle request

## Implementation Statistics

- **Total Lines**: ~1,350 (handlers.py)
- **Handler Classes**: 6
- **Request Types**: 6
- **Error Types**: 7+
- **Examples**: 8 comprehensive examples
- **Documentation**: 3 files (~1,000 lines)

## Integration with MCP Server

The handlers are designed to integrate with the MCP server:

```python
# In server.py
from .handlers import RequestRouter, create_router

class MCPServer:
    def __init__(self):
        self.router = create_router()
        # Configure handlers...
```

## Summary

This implementation provides a robust, production-ready request handling and routing system for the MCP server with:

- Complete handler coverage (6 handlers)
- Advanced rate limiting
- Optional authentication
- Comprehensive error handling
- Full statistics tracking
- **NEW: EBI OLS4 ontology handler**
- Extensive documentation
- Working examples
- Clean, maintainable code

All requirements from AGENT 9B have been fulfilled, including the new OntologyHandler for EBI OLS4 operations.
