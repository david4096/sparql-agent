# SPARQL Query Executor - Quick Reference

## Installation

```bash
pip install rdflib SPARQLWrapper requests urllib3
```

## Basic Usage

### Simple Query Execution

```python
from sparql_agent.execution import execute_query

result = execute_query(
    query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
    endpoint="https://sparql.uniprot.org/sparql"
)

print(f"Results: {result.row_count}")
for binding in result.bindings:
    print(binding)
```

### Using QueryExecutor

```python
from sparql_agent.execution import QueryExecutor, EndpointInfo

# Create executor
executor = QueryExecutor(timeout=30)

# Define endpoint
endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql")

# Execute query
result = executor.execute(
    query="SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
    endpoint=endpoint
)

# Process results
for binding in result.bindings:
    print(binding)

executor.close()
```

### Context Manager (Recommended)

```python
with QueryExecutor() as executor:
    result = executor.execute(query, endpoint)
    process(result)
# Automatic cleanup
```

## Result Formats

```python
from sparql_agent.execution import ResultFormat

# JSON (default)
result = executor.execute(query, endpoint, format=ResultFormat.JSON)

# XML
result = executor.execute(query, endpoint, format=ResultFormat.XML)

# CSV
result = executor.execute(query, endpoint, format=ResultFormat.CSV)
```

## Streaming

```python
# Enable streaming for large results
executor = QueryExecutor(enable_streaming=True)

result = executor.execute(query, endpoint, stream=True)

# Process results lazily
for binding in result.bindings:
    process(binding)  # Doesn't load all into memory
```

## Federation

```python
from sparql_agent.execution import FederatedQuery, execute_federated_query

# Quick utility
endpoints = [
    "https://endpoint1.org/sparql",
    "https://endpoint2.org/sparql"
]

result = execute_federated_query(query, endpoints, parallel=True)

# Or with configuration
config = FederatedQuery(
    endpoints=[
        EndpointInfo(url="https://endpoint1.org/sparql"),
        EndpointInfo(url="https://endpoint2.org/sparql"),
    ],
    merge_strategy="union",  # union, intersection, sequential
    parallel=True,
    fail_on_error=False
)

result = executor.execute_federated(query, config)
```

## Performance Monitoring

```python
# Enable metrics
executor = QueryExecutor(enable_metrics=True)

result = executor.execute(query, endpoint)

# Access metrics
metrics = result.metadata["metrics"]
print(f"Execution time: {metrics['execution_time']}s")
print(f"Network time: {metrics['network_time']}s")
print(f"Parse time: {metrics['parse_time']}s")

# Overall statistics
stats = executor.get_statistics()
print(f"Total queries: {stats['total_queries']}")
print(f"Success rate: {stats['successful_queries'] / stats['total_queries']:.2%}")
print(f"Average time: {stats['average_execution_time']}s")
```

## Error Handling

```python
from sparql_agent.core.exceptions import (
    QueryExecutionError,
    QueryTimeoutError,
    EndpointConnectionError
)

try:
    result = executor.execute(query, endpoint)

    if result.is_success:
        process(result)
    else:
        handle_error(result.error_message)

except QueryTimeoutError as e:
    print(f"Query timed out: {e}")
except EndpointConnectionError as e:
    print(f"Connection failed: {e}")
except QueryExecutionError as e:
    print(f"Execution failed: {e}")
```

## Configuration

### Executor Configuration

```python
executor = QueryExecutor(
    timeout=60,              # Query timeout (seconds)
    max_retries=3,          # Retry attempts
    pool_size=10,           # Connection pool size
    enable_streaming=False, # Streaming by default
    enable_metrics=True,    # Metrics collection
    user_agent="Custom/1.0" # User agent string
)
```

### Endpoint Configuration

```python
endpoint = EndpointInfo(
    url="https://endpoint.com/sparql",
    name="My Endpoint",
    timeout=30,
    rate_limit=10,
    authentication_required=False,
    metadata={
        "credentials": {"username": "user", "password": "pass"}
    }
)
```

## Authentication

```python
# Basic authentication
credentials = {"username": "user", "password": "pass"}
result = executor.execute(query, endpoint, credentials=credentials)

# Or configure in endpoint
endpoint = EndpointInfo(
    url="https://secure.endpoint.com/sparql",
    authentication_required=True,
    metadata={"credentials": {"username": "user", "password": "pass"}}
)
```

## Custom Headers

```python
custom_headers = {
    "Accept-Language": "en",
    "X-API-Key": "your-api-key"
}

result = executor.execute(query, endpoint, custom_headers=custom_headers)
```

## Result Access

### QueryResult Object

```python
result.status            # QueryStatus.SUCCESS or FAILED
result.is_success        # Boolean
result.query             # Original query
result.bindings          # List of result bindings
result.row_count         # Number of results
result.variables         # Query variables
result.execution_time    # Execution time (seconds)
result.error_message     # Error if failed
result.metadata          # Additional metadata
```

### Processing Results

```python
# Iterate through results
for binding in result.bindings:
    subject = binding["s"]
    predicate = binding["p"]
    object = binding["o"]
    print(f"{subject} {predicate} {object}")

# Access specific variables
if result.row_count > 0:
    first = result.bindings[0]
    value = first["myVariable"]
```

## Common Patterns

### Batch Query Execution

```python
queries = [
    "SELECT * WHERE { ?s ?p ?o } LIMIT 10",
    "SELECT ?label WHERE { ?s rdfs:label ?label } LIMIT 10",
    "SELECT ?type WHERE { ?s a ?type } LIMIT 10"
]

with QueryExecutor() as executor:
    for query in queries:
        result = executor.execute(query, endpoint)
        process(result)
```

### Multi-Endpoint Query

```python
endpoints = [
    EndpointInfo(url="https://endpoint1.org/sparql", name="Endpoint 1"),
    EndpointInfo(url="https://endpoint2.org/sparql", name="Endpoint 2"),
    EndpointInfo(url="https://endpoint3.org/sparql", name="Endpoint 3"),
]

with QueryExecutor() as executor:
    for endpoint in endpoints:
        try:
            result = executor.execute(query, endpoint)
            print(f"{endpoint.name}: {result.row_count} results")
        except Exception as e:
            print(f"{endpoint.name}: Failed - {e}")
```

### Timeout Strategy

```python
# Different timeouts for different query types
simple_timeout = 10
complex_timeout = 300

with QueryExecutor() as executor:
    # Fast query
    result1 = executor.execute(simple_query, endpoint, timeout=simple_timeout)

    # Complex analytical query
    result2 = executor.execute(complex_query, endpoint, timeout=complex_timeout)
```

## Binding Types

```python
from sparql_agent.execution import Binding, BindingType

# Check binding type
if binding.is_uri():
    print(f"URI: {binding.value}")
elif binding.is_literal():
    print(f"Literal: {binding.value}")
    if binding.datatype:
        print(f"Datatype: {binding.datatype}")
    if binding.language:
        print(f"Language: {binding.language}")
elif binding.is_bnode():
    print(f"Blank Node: {binding.value}")
```

## Performance Tips

### 1. Reuse Executors

```python
# Good: Reuse executor for connection pooling
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

### 2. Use Streaming for Large Results

```python
# For queries that return many results
executor = QueryExecutor(enable_streaming=True)
result = executor.execute(large_query, endpoint, stream=True)
```

### 3. Optimize Connection Pool

```python
# For high concurrency
executor = QueryExecutor(pool_size=50)
```

### 4. Enable Metrics in Production

```python
executor = QueryExecutor(enable_metrics=True)
# Monitor statistics for optimization
```

## Merge Strategies

### Union (Combine All)

```python
config = FederatedQuery(
    endpoints=endpoints,
    merge_strategy="union"
)
# Returns all results from all endpoints
```

### Intersection (Common Only)

```python
config = FederatedQuery(
    endpoints=endpoints,
    merge_strategy="intersection"
)
# Returns only results present in all endpoints
```

### Sequential (First Success)

```python
config = FederatedQuery(
    endpoints=endpoints,
    merge_strategy="sequential"
)
# Returns results from first successful endpoint
```

## Monitoring

### Active Executions

```python
# Get currently running queries
active = executor.get_active_executions()

for query_hash, metrics in active.items():
    print(f"Query {query_hash}:")
    print(f"  Running for: {metrics['execution_time']:.2f}s")
    print(f"  Endpoint: {metrics['endpoint_url']}")
```

### Connection Pool Stats

```python
pool_stats = executor.pool.get_statistics()

print(f"Connections created: {pool_stats['connections_created']}")
print(f"Connections reused: {pool_stats['connections_reused']}")
print(f"Reuse ratio: {pool_stats['connections_reused'] / pool_stats['connections_created']:.2%}")
```

## Examples

Run the comprehensive examples:

```bash
python -m sparql_agent.execution.example_executor
```

Or run specific examples:

```python
from sparql_agent.execution.example_executor import (
    example_basic_execution,
    example_federated_query,
    example_performance_monitoring
)

example_basic_execution()
example_federated_query()
example_performance_monitoring()
```

## Testing

Run unit tests:

```bash
python -m pytest src/sparql_agent/execution/test_executor.py -v
```

Or run specific test:

```bash
python -m pytest src/sparql_agent/execution/test_executor.py::TestQueryExecutor -v
```

## Documentation

- **README.md**: Complete documentation with examples
- **EXECUTOR_SUMMARY.md**: Implementation overview
- **QUICK_REFERENCE.md**: This file

## Common Issues

### Timeout Errors

```python
# Increase timeout
result = executor.execute(query, endpoint, timeout=300)
```

### Connection Errors

```python
# Increase retries
executor = QueryExecutor(max_retries=5)
```

### Memory Issues

```python
# Enable streaming
executor = QueryExecutor(enable_streaming=True)
```

### Authentication Issues

```python
# Verify credentials
credentials = {"username": "user", "password": "pass"}
result = executor.execute(query, endpoint, credentials=credentials)
```

## API Summary

### Main Classes
- `QueryExecutor`: Main execution engine
- `ConnectionPool`: Connection management
- `ResultParser`: Result parsing
- `ExecutionMetrics`: Performance metrics
- `FederatedQuery`: Federation configuration
- `Binding`: Result binding

### Enums
- `ResultFormat`: JSON, XML, CSV, TSV, TURTLE, etc.
- `BindingType`: URI, LITERAL, BNODE, TYPED_LITERAL

### Utility Functions
- `execute_query()`: Quick single query execution
- `execute_federated_query()`: Quick federated execution

## Further Reading

- Full documentation: `README.md`
- Implementation details: `EXECUTOR_SUMMARY.md`
- Code examples: `example_executor.py`
- Unit tests: `test_executor.py`
