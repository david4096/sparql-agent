# SPARQL Query Execution Module

Comprehensive SPARQL query execution and result handling system with support for multiple endpoints, formats, streaming, federation, and performance monitoring.

## Features

### 1. Query Execution
- Execute SPARQL queries against any endpoint
- Support for SELECT, CONSTRUCT, ASK, and DESCRIBE queries
- Automatic retry logic with exponential backoff
- Timeout management and cancellation
- Custom authentication support
- Rate limiting and throttling

### 2. Result Format Support
- **JSON**: SPARQL JSON results format
- **XML**: SPARQL XML results format
- **CSV**: Comma-separated values
- **TSV**: Tab-separated values
- **Turtle**: RDF Turtle serialization
- **N-Triples**: RDF N-Triples format
- **RDF/XML**: RDF XML format

### 3. Result Processing
- Parse and normalize results from different formats
- Type-aware binding handling (URI, literal, blank node)
- Datatype and language tag preservation
- Lazy loading for memory efficiency
- Streaming support for large result sets

### 4. Connection Management
- Connection pooling for endpoint reuse
- HTTP session management with keep-alive
- Configurable pool size and timeouts
- Automatic connection cleanup
- Connection statistics and monitoring

### 5. Federation Support
- Execute queries across multiple endpoints
- Parallel or sequential execution
- Result merging strategies (union, intersection, sequential)
- Partial failure handling
- Per-endpoint timeout configuration

### 6. Performance Monitoring
- Detailed execution metrics
- Network and parse time tracking
- Result set statistics
- Query performance profiling
- Connection pool metrics
- Active execution monitoring

## Installation

The executor module requires the following dependencies:

```bash
pip install rdflib SPARQLWrapper requests urllib3
```

## Quick Start

### Basic Query Execution

```python
from sparql_agent.execution import QueryExecutor, EndpointInfo

# Create executor
executor = QueryExecutor(timeout=30)

# Define endpoint
endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql")

# Execute query
query = """
SELECT ?protein ?name
WHERE {
  ?protein a <http://purl.uniprot.org/core/Protein> ;
           <http://www.w3.org/2000/01/rdf-schema#label> ?name .
}
LIMIT 10
"""

result = executor.execute(query, endpoint)

# Process results
for binding in result.bindings:
    print(f"Protein: {binding['protein']}, Name: {binding['name']}")

executor.close()
```

### Using Context Manager

```python
from sparql_agent.execution import QueryExecutor

with QueryExecutor() as executor:
    result = executor.execute(query, endpoint)
    print(f"Found {result.row_count} results")
# Automatically closes connections
```

### Quick Utility Functions

```python
from sparql_agent.execution import execute_query

# One-liner execution
result = execute_query(
    query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
    endpoint="https://sparql.uniprot.org/sparql",
    timeout=30
)
```

## Advanced Usage

### Different Result Formats

```python
from sparql_agent.execution import ResultFormat

# JSON format (default)
result = executor.execute(query, endpoint, format=ResultFormat.JSON)

# XML format
result = executor.execute(query, endpoint, format=ResultFormat.XML)

# CSV format
result = executor.execute(query, endpoint, format=ResultFormat.CSV)
```

### Streaming Large Results

```python
# Enable streaming for large result sets
executor = QueryExecutor(enable_streaming=True)

result = executor.execute(query, endpoint, stream=True)

# Results are loaded lazily
for binding in result.bindings:
    process(binding)
```

### Federated Queries

```python
from sparql_agent.execution import FederatedQuery

# Define multiple endpoints
endpoints = [
    EndpointInfo(url="https://sparql.uniprot.org/sparql", name="UniProt"),
    EndpointInfo(url="https://www.ebi.ac.uk/rdf/services/reactome/sparql", name="Reactome"),
    EndpointInfo(url="https://query.wikidata.org/sparql", name="Wikidata"),
]

# Configure federation
config = FederatedQuery(
    endpoints=endpoints,
    merge_strategy="union",  # union, intersection, or sequential
    parallel=True,           # Execute in parallel
    fail_on_error=False,     # Continue if some endpoints fail
    timeout_per_endpoint=30
)

# Execute federated query
result = executor.execute_federated(query, config)

print(f"Results from {result.metadata['endpoints_count']} endpoints")
print(f"Total results: {result.row_count}")
```

### Authentication

```python
# Basic authentication
credentials = {
    "username": "user",
    "password": "pass"
}

result = executor.execute(query, endpoint, credentials=credentials)

# Or configure in endpoint
endpoint = EndpointInfo(
    url="https://secure.endpoint.com/sparql",
    authentication_required=True,
    metadata={"credentials": {"username": "user", "password": "pass"}}
)
```

### Custom Headers

```python
custom_headers = {
    "Accept-Language": "en",
    "X-Custom-Header": "value"
}

result = executor.execute(query, endpoint, custom_headers=custom_headers)
```

### Performance Monitoring

```python
# Enable metrics
executor = QueryExecutor(enable_metrics=True)

result = executor.execute(query, endpoint)

# Access metrics
metrics = result.metadata["metrics"]
print(f"Execution time: {metrics['execution_time']}s")
print(f"Network time: {metrics['network_time']}s")
print(f"Parse time: {metrics['parse_time']}s")
print(f"Results: {metrics['result_count']}")

# Get overall statistics
stats = executor.get_statistics()
print(f"Total queries: {stats['total_queries']}")
print(f"Average time: {stats['average_execution_time']}s")
print(f"Connection reuse: {stats['pool_stats']['connections_reused']}")
```

### Error Handling

```python
from sparql_agent.core.exceptions import (
    QueryExecutionError,
    QueryTimeoutError,
    EndpointConnectionError
)

try:
    result = executor.execute(query, endpoint)

    if result.is_success:
        print(f"Success: {result.row_count} results")
    else:
        print(f"Failed: {result.error_message}")

except QueryTimeoutError as e:
    print(f"Query timed out: {e}")
except EndpointConnectionError as e:
    print(f"Connection failed: {e}")
except QueryExecutionError as e:
    print(f"Execution failed: {e}")
```

## Architecture

### Component Overview

```
QueryExecutor
├── ConnectionPool          # HTTP connection management
│   ├── Session pooling
│   ├── Retry strategies
│   └── Statistics
├── ResultParser           # Result format parsing
│   ├── JSON parser
│   ├── XML parser
│   └── CSV parser
├── StreamingIterator      # Lazy result loading
└── Metrics               # Performance monitoring
```

### Execution Flow

1. **Query Submission**: Query and endpoint provided
2. **Connection Pooling**: Reuse or create connection
3. **Query Execution**: Send query to endpoint
4. **Result Streaming**: Receive results (streaming or bulk)
5. **Parsing**: Parse results based on format
6. **Standardization**: Convert to unified binding format
7. **Metrics Collection**: Track performance
8. **Result Return**: Return QueryResult object

### Federation Flow

1. **Configuration**: Define endpoints and merge strategy
2. **Query Distribution**: Send query to all endpoints
3. **Parallel/Sequential Execution**: Execute based on config
4. **Error Handling**: Handle partial failures
5. **Result Merging**: Merge results based on strategy
6. **Return**: Return unified QueryResult

## Result Structure

### QueryResult Object

```python
@dataclass
class QueryResult:
    status: QueryStatus              # SUCCESS, FAILED, TIMEOUT
    query: str                       # Original query
    bindings: List[Dict[str, Any]]  # Result bindings
    row_count: int                   # Number of results
    variables: List[str]             # Query variables
    execution_time: float            # Execution time (seconds)
    error_message: Optional[str]     # Error if failed
    metadata: Dict[str, Any]         # Additional metadata
```

### Binding Structure

Each result binding is a dictionary with variable names as keys:

```python
{
    "protein": "http://purl.uniprot.org/uniprot/P12345",
    "name": "Example Protein",
    "count": "42"
}
```

### Binding Objects

For detailed binding information, use the `Binding` class:

```python
@dataclass
class Binding:
    variable: str              # Variable name
    value: Any                 # Binding value
    binding_type: BindingType  # URI, LITERAL, BNODE
    datatype: Optional[str]    # Datatype URI
    language: Optional[str]    # Language tag
```

## Configuration

### Executor Configuration

```python
executor = QueryExecutor(
    timeout=60,              # Default query timeout (seconds)
    max_retries=3,          # Maximum retry attempts
    pool_size=10,           # Connection pool size
    enable_streaming=False, # Enable streaming by default
    enable_metrics=True,    # Enable metrics collection
    user_agent="Custom/1.0" # Custom user agent
)
```

### Endpoint Configuration

```python
endpoint = EndpointInfo(
    url="https://endpoint.com/sparql",
    name="My Endpoint",
    timeout=30,
    rate_limit=10,  # Requests per second
    authentication_required=False,
    metadata={
        "credentials": {"username": "user", "password": "pass"},
        "custom": "value"
    }
)
```

## Performance Tuning

### Connection Pool Optimization

```python
# Increase pool size for high concurrency
executor = QueryExecutor(pool_size=50)

# Adjust retry strategy
executor.pool.max_retries = 5
executor.pool.backoff_factor = 0.5
```

### Streaming for Large Results

```python
# Enable streaming for queries with many results
executor = QueryExecutor(enable_streaming=True)

# Or per-query
result = executor.execute(query, endpoint, stream=True)
```

### Timeout Management

```python
# Set different timeouts for different queries
fast_result = executor.execute(simple_query, endpoint, timeout=10)
slow_result = executor.execute(complex_query, endpoint, timeout=300)
```

### Federation Optimization

```python
# Parallel execution for speed
config = FederatedQuery(endpoints=endpoints, parallel=True)

# Sequential for resource constraints
config = FederatedQuery(endpoints=endpoints, parallel=False)
```

## Monitoring and Debugging

### Query Statistics

```python
stats = executor.get_statistics()

print(f"Total queries: {stats['total_queries']}")
print(f"Success rate: {stats['successful_queries'] / stats['total_queries']:.2%}")
print(f"Average time: {stats['average_execution_time']:.2f}s")

# Per-endpoint statistics
for endpoint_url, count in stats['queries_by_endpoint'].items():
    print(f"{endpoint_url}: {count} queries")

# Error analysis
for error_type, count in stats['errors_by_type'].items():
    print(f"{error_type}: {count} occurrences")
```

### Active Executions

```python
# Monitor currently running queries
active = executor.get_active_executions()

for query_hash, metrics in active.items():
    print(f"Query {query_hash}:")
    print(f"  Running for: {metrics['execution_time']:.2f}s")
    print(f"  Endpoint: {metrics['endpoint_url']}")
```

### Connection Pool Statistics

```python
pool_stats = executor.pool.get_statistics()

print(f"Connections created: {pool_stats['connections_created']}")
print(f"Connections reused: {pool_stats['connections_reused']}")
print(f"Reuse ratio: {pool_stats['connections_reused'] / pool_stats['connections_created']:.2%}")
```

## Best Practices

### 1. Use Context Managers

Always use context managers for automatic cleanup:

```python
with QueryExecutor() as executor:
    result = executor.execute(query, endpoint)
```

### 2. Enable Metrics for Production

Monitor performance in production:

```python
executor = QueryExecutor(enable_metrics=True)
```

### 3. Handle Errors Gracefully

Check result status and handle errors:

```python
result = executor.execute(query, endpoint)

if result.is_success:
    process_results(result.bindings)
else:
    log_error(result.error_message)
    handle_failure()
```

### 4. Use Streaming for Large Results

Enable streaming for queries that may return many results:

```python
executor = QueryExecutor(enable_streaming=True)
```

### 5. Optimize Timeouts

Set appropriate timeouts based on query complexity:

```python
# Simple queries
result = executor.execute(simple_query, endpoint, timeout=10)

# Complex analytical queries
result = executor.execute(complex_query, endpoint, timeout=300)
```

### 6. Reuse Executors

Reuse executor instances for connection pooling benefits:

```python
# Good: Reuse executor
executor = QueryExecutor()
for query in queries:
    result = executor.execute(query, endpoint)
executor.close()

# Bad: Create new executor each time
for query in queries:
    executor = QueryExecutor()
    result = executor.execute(query, endpoint)
    executor.close()
```

## Troubleshooting

### Timeout Issues

```python
# Increase timeout
result = executor.execute(query, endpoint, timeout=300)

# Check endpoint performance
metrics = result.metadata.get("metrics", {})
print(f"Network time: {metrics.get('network_time')}s")
```

### Connection Errors

```python
# Increase retry attempts
executor = QueryExecutor(max_retries=5)

# Check endpoint availability
try:
    result = executor.execute("ASK { ?s ?p ?o }", endpoint)
except EndpointConnectionError as e:
    print(f"Endpoint unavailable: {e}")
```

### Memory Issues with Large Results

```python
# Use streaming
executor = QueryExecutor(enable_streaming=True)

# Or add LIMIT to queries
query = query + " LIMIT 10000"
```

### Authentication Problems

```python
# Verify credentials
credentials = {"username": "user", "password": "pass"}
result = executor.execute(query, endpoint, credentials=credentials)

if not result.is_success:
    print(f"Auth failed: {result.error_message}")
```

## Examples

See `example_executor.py` for comprehensive examples covering:

1. Basic query execution
2. Different result formats
3. Streaming results
4. Federated queries
5. Performance monitoring
6. Error handling
7. Context manager usage
8. Quick utility functions

Run examples:

```bash
python -m sparql_agent.execution.example_executor
```

## API Reference

### Classes

- **QueryExecutor**: Main query execution class
- **ConnectionPool**: HTTP connection management
- **ResultParser**: Result format parsing
- **StreamingResultIterator**: Lazy result iteration
- **Binding**: Single variable binding
- **ExecutionMetrics**: Performance metrics
- **FederatedQuery**: Federation configuration
- **ResultFormat**: Result format enumeration
- **BindingType**: Binding type enumeration

### Functions

- **execute_query()**: Quick query execution utility
- **execute_federated_query()**: Quick federated execution utility

## Contributing

When adding new features to the executor:

1. Maintain backward compatibility
2. Add comprehensive error handling
3. Include performance metrics
4. Write tests for new functionality
5. Update documentation and examples

## License

See main project LICENSE file.
