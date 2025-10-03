# SPARQL Error Handler and Query Optimizer

Comprehensive error handling and query optimization system for SPARQL queries with intelligent error recovery, user-friendly messages, and automatic optimization suggestions.

## Features

### 1. Error Categorization
- **12 error categories** covering all common SPARQL failure modes
- Automatic detection and classification of errors
- Severity assessment (1-10 scale)
- Recovery strategy recommendations

### 2. User-Friendly Error Messages
- Clear, actionable error descriptions
- Context-aware suggestions
- Technical details preserved for debugging
- Formatted error reports

### 3. Query Optimization
- Performance issue detection
- Automatic query optimization
- Multiple optimization levels
- Estimated performance improvements

### 4. Error Recovery
- Retry strategies (immediate, exponential backoff, linear backoff)
- Fallback to alternative endpoints
- Automatic query optimization on failure
- Partial result handling

### 5. Common Patterns
- Timeout → suggest pagination with LIMIT/OFFSET
- Memory → suggest limiting result sets
- Syntax → specific corrections with examples
- Network → retry with backoff

## Error Categories

| Category | Description | Recoverable | Strategy |
|----------|-------------|-------------|----------|
| SYNTAX | Query syntax errors | Yes | None (fix query) |
| TIMEOUT | Query execution timeout | Yes | Exponential backoff |
| MEMORY | Out of memory/too many results | Yes | None (optimize query) |
| NETWORK | Connection/network failures | Yes | Exponential backoff |
| AUTHENTICATION | Auth failures | No | None (provide credentials) |
| RATE_LIMIT | Rate limiting | Yes | Linear backoff |
| ENDPOINT_UNAVAILABLE | Service down | Yes | Exponential backoff |
| QUERY_TOO_COMPLEX | Query complexity exceeded | Yes | None (simplify query) |
| RESOURCE_NOT_FOUND | Endpoint not found (404) | No | None (check URL) |
| PERMISSION_DENIED | Access forbidden (403) | No | None (request access) |
| MALFORMED_RESPONSE | Invalid response format | Yes | Immediate retry |
| UNKNOWN | Uncategorized errors | Yes | Immediate retry |

## Usage Examples

### Basic Error Handling

```python
from sparql_agent.execution import ErrorHandler, handle_query_error
from sparql_agent.core.exceptions import QueryTimeoutError

# Quick error handling
error = QueryTimeoutError("Query timed out after 30s")
query = "SELECT * WHERE { ?s ?p ?o }"

context = handle_query_error(error, query)
print(f"Category: {context.category.value}")
print(f"Message: {context.message}")
for suggestion in context.suggestions:
    print(f"  - {suggestion}")
```

### Error Categorization

```python
from sparql_agent.execution import ErrorHandler
from sparql_agent.core.types import EndpointInfo

handler = ErrorHandler()

# Categorize with full context
error = QueryTimeoutError("Timeout after 30s")
query = "SELECT * WHERE { ?s ?p ?o }"
endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql", timeout=30)

context = handler.categorize_error(error, query, endpoint)

print(f"Category: {context.category.value}")
print(f"Severity: {context.severity}/10")
print(f"Recoverable: {context.is_recoverable}")
print(f"Retry Strategy: {context.retry_strategy.value}")
print(f"\nSuggestions:")
for i, suggestion in enumerate(context.suggestions, 1):
    print(f"{i}. {suggestion}")
```

### Query Optimization

```python
from sparql_agent.execution import ErrorHandler, OptimizationLevel

handler = ErrorHandler()

# Inefficient query
query = """
SELECT DISTINCT *
WHERE {
    ?s ?p ?o .
    OPTIONAL { ?s ?p1 ?o1 }
    OPTIONAL { ?s ?p2 ?o2 }
    OPTIONAL { ?s ?p3 ?o3 }
    OPTIONAL { ?s ?p4 ?o4 }
    OPTIONAL { ?s ?p5 ?o5 }
}
ORDER BY ?s
"""

# Analyze for optimization opportunities
optimizations = handler.suggest_optimizations(query)
print(f"Found {len(optimizations)} optimization opportunities:")
for opt in optimizations:
    print(f"\n{opt.issue}")
    print(f"  Impact: {opt.impact}")
    print(f"  Suggestion: {opt.suggestion}")
    if opt.estimated_improvement:
        print(f"  Estimated improvement: {opt.estimated_improvement}%")

# Auto-optimize
optimized = handler.optimize_query(query, OptimizationLevel.MEDIUM)
print(f"\nOptimized query:")
print(optimized)
```

### Error Recovery with Retry

```python
from sparql_agent.execution import ErrorHandler
from sparql_agent.core.types import EndpointInfo

handler = ErrorHandler(
    max_retries=3,
    retry_delay=1.0,
    enable_fallback=True,
    enable_optimization_suggestions=True
)

query = "SELECT * WHERE { ?s ?p ?o }"
endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql")
alternative_endpoints = [
    EndpointInfo(url="https://alternative1.org/sparql"),
    EndpointInfo(url="https://alternative2.org/sparql"),
]

def execute_query(query, endpoint):
    # Your query execution logic
    pass

# Attempt recovery
error = QueryTimeoutError("Timeout")
result = handler.recover_from_error(
    error=error,
    query=query,
    endpoint=endpoint,
    execute_func=execute_query,
    alternative_endpoints=alternative_endpoints
)

if result.success:
    print(f"Recovery succeeded after {result.attempts} attempts")
    print(f"Strategy used: {result.strategy_used.value}")
    if result.fallback_used:
        print(f"Used fallback endpoint: {result.metadata['fallback_endpoint']}")
else:
    print(f"Recovery failed after {result.attempts} attempts")
    for error_ctx in result.errors_encountered:
        print(f"  - {error_ctx.message}")
```

### Formatted Error Reports

```python
from sparql_agent.execution import ErrorHandler

handler = ErrorHandler()

error = QueryTimeoutError("Query execution exceeded timeout")
query = "SELECT * WHERE { ?s ?p ?o }"

context = handler.categorize_error(error, query)
report = handler.format_error_report(context)

print(report)
# Output:
# ======================================================================
# ERROR: Query execution timed out
# ======================================================================
#
# Category: timeout
# Severity: 6/10
# Recoverable: Yes
#
# SUGGESTIONS:
#   1. Add or reduce LIMIT clause to fetch fewer results
#   2. Use pagination with LIMIT and OFFSET for large result sets
#   3. Add more specific FILTER conditions to narrow results
#   ...
```

### Convenience Functions

```python
from sparql_agent.execution import (
    handle_query_error,
    get_error_suggestions,
    optimize_query
)

# Quick error handling
error = QueryTimeoutError("Timeout")
context = handle_query_error(error, "SELECT * WHERE { ?s ?p ?o }")

# Get just suggestions
suggestions = get_error_suggestions(error, "SELECT * WHERE { ?s ?p ?o }")

# Quick optimization
optimized_query, optimizations = optimize_query("SELECT * WHERE { ?s ?p ?o }")
```

## Query Optimization Patterns

### 1. Missing LIMIT
**Problem:** Query without LIMIT can fetch millions of results

```sparql
# Bad
SELECT * WHERE { ?s ?p ?o }

# Good
SELECT * WHERE { ?s ?p ?o } LIMIT 1000
```

**Detection:** High impact, automatic fix available

### 2. Excessive OPTIONAL Clauses
**Problem:** Too many OPTIONALs slow query execution

```sparql
# Bad - 6 OPTIONAL clauses
SELECT * WHERE {
    ?s ?p ?o .
    OPTIONAL { ?s rdfs:label ?l1 }
    OPTIONAL { ?s rdfs:comment ?c1 }
    OPTIONAL { ?s rdfs:seeAlso ?s1 }
    OPTIONAL { ?o rdfs:label ?l2 }
    OPTIONAL { ?o rdfs:comment ?c2 }
    OPTIONAL { ?o rdfs:seeAlso ?s2 }
}

# Good - Only essential OPTIONALs
SELECT * WHERE {
    ?s ?p ?o .
    OPTIONAL { ?s rdfs:label ?l1 }
    OPTIONAL { ?o rdfs:label ?l2 }
} LIMIT 1000
```

### 3. DISTINCT Without LIMIT
**Problem:** DISTINCT requires buffering all results in memory

```sparql
# Bad
SELECT DISTINCT ?s WHERE { ?s ?p ?o }

# Good
SELECT DISTINCT ?s WHERE { ?s ?p ?o } LIMIT 10000
```

### 4. ORDER BY Without LIMIT
**Problem:** Must sort entire result set before returning

```sparql
# Bad
SELECT ?s WHERE { ?s ?p ?o } ORDER BY ?s

# Good
SELECT ?s WHERE { ?s ?p ?o } ORDER BY ?s LIMIT 1000
```

### 5. Triple Wildcard
**Problem:** Fully unbound triple pattern is very expensive

```sparql
# Bad
SELECT * WHERE { ?s ?p ?o } LIMIT 10

# Good
SELECT * WHERE {
    ?s a :SpecificClass .
    ?s ?p ?o
} LIMIT 10
```

### 6. Late FILTER Placement
**Problem:** FILTER applied after fetching all intermediate results

```sparql
# Bad
SELECT ?s ?p ?o WHERE {
    ?s ?p ?o .
    ?s rdfs:label ?label .
    ?o rdfs:label ?oLabel .
    FILTER(regex(str(?s), "pattern"))
}

# Good
SELECT ?s ?p ?o WHERE {
    ?s ?p ?o .
    FILTER(regex(str(?s), "pattern"))
    ?s rdfs:label ?label .
    ?o rdfs:label ?oLabel .
}
```

## Optimization Levels

### NONE
No optimization applied. Query returned as-is.

### LOW
Basic safety optimizations:
- Add LIMIT if missing (default: 10000)

### MEDIUM (Recommended)
Low optimizations plus:
- Moderate LIMIT adjustments
- Basic pattern reordering

### HIGH
Medium optimizations plus:
- Aggressive LIMIT reduction
- Complex pattern optimization

### AGGRESSIVE
All optimizations plus:
- Endpoint-specific optimizations
- Query rewriting for performance

## Retry Strategies

### IMMEDIATE
Single immediate retry attempt.
**Use for:** Transient errors, malformed responses

### EXPONENTIAL_BACKOFF
Retry with exponentially increasing delays (1s, 2s, 4s, ...).
**Use for:** Network errors, endpoint unavailable, timeouts

### LINEAR_BACKOFF
Retry with linearly increasing delays (1s, 2s, 3s, ...).
**Use for:** Rate limiting (respects cooldown periods)

### ALTERNATIVE_ENDPOINT
Try alternative endpoints if primary fails.
**Use for:** Endpoint unavailable, persistent failures

## Error Recovery Workflow

```
1. Error Occurs
   ↓
2. Categorize Error
   ↓
3. Check if Recoverable
   ↓
4. Select Retry Strategy
   ↓
5. Apply Strategy
   - Immediate retry
   - Exponential backoff
   - Linear backoff
   ↓
6. Try Alternative Endpoints (if enabled)
   ↓
7. Try Optimized Query (if enabled)
   ↓
8. Return Result
```

## Statistics

Track error handling performance:

```python
handler = ErrorHandler()

# ... handle multiple errors ...

stats = handler.get_statistics()
print(f"Total errors: {stats['total_errors']}")
print(f"Recovery rate: {stats['recovery_rate']}")
print(f"Successful recoveries: {stats['successful_recoveries']}")
print(f"Failed recoveries: {stats['failed_recoveries']}")
print(f"Errors by category: {stats['errors_by_category']}")
print(f"Retry counts: {stats['retry_counts']}")
```

## Integration with QueryExecutor

```python
from sparql_agent.execution import QueryExecutor, ErrorHandler
from sparql_agent.core.types import EndpointInfo

executor = QueryExecutor(timeout=60)
handler = ErrorHandler(max_retries=3, enable_fallback=True)

endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql")
query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

try:
    result = executor.execute(query, endpoint)
except Exception as error:
    # Handle error
    context = handler.categorize_error(error, query, endpoint)

    print(f"Error occurred: {context.message}")
    print("\nSuggestions:")
    for suggestion in context.suggestions:
        print(f"  - {suggestion}")

    # Attempt recovery
    if context.is_recoverable:
        recovery_result = handler.recover_from_error(
            error=error,
            query=query,
            endpoint=endpoint,
            execute_func=executor.execute
        )

        if recovery_result.success:
            result = recovery_result.result
            print(f"Successfully recovered!")
        else:
            print(f"Recovery failed")
```

## Best Practices

1. **Always enable optimization suggestions** for production systems
2. **Use appropriate retry strategies** based on error type
3. **Configure fallback endpoints** for high availability
4. **Monitor statistics** to identify recurring issues
5. **Set reasonable retry limits** to avoid excessive delays
6. **Add LIMIT clauses** to all SELECT queries
7. **Use specific patterns** instead of triple wildcards
8. **Place FILTER clauses early** in query patterns
9. **Minimize OPTIONAL clauses** for better performance
10. **Cache optimization suggestions** for repeated queries

## Performance Impact

### Error Categorization
- **Overhead:** ~0.1-0.5ms per error
- **Memory:** ~1KB per error context

### Query Optimization Analysis
- **Overhead:** ~1-5ms per query
- **Memory:** ~2-10KB per analysis

### Error Recovery
- **Overhead:** Depends on retry strategy
  - Immediate: ~10-50ms
  - Exponential backoff: ~1-30s
  - Alternative endpoints: ~100-500ms per endpoint

### Recommended Configuration

```python
# For production systems
handler = ErrorHandler(
    max_retries=3,              # Balance between recovery and latency
    retry_delay=1.0,            # 1 second initial delay
    enable_fallback=True,       # High availability
    enable_optimization_suggestions=True  # Performance monitoring
)

# For development/testing
handler = ErrorHandler(
    max_retries=1,              # Fail fast
    retry_delay=0.1,            # Quick retry
    enable_fallback=False,      # Test primary endpoint
    enable_optimization_suggestions=True  # Learn query patterns
)
```

## Error Message Examples

### Timeout Error
```
======================================================================
ERROR: Query execution timed out
======================================================================

Category: timeout
Severity: 6/10
Recoverable: Yes

SUGGESTIONS:
  1. Add LIMIT clause (e.g., LIMIT 1000) to prevent fetching all results
  2. Add or reduce LIMIT clause to fetch fewer results
  3. Use pagination with LIMIT and OFFSET for large result sets
  4. Add more specific FILTER conditions to narrow results
  5. Consider breaking complex query into smaller queries

Recommended Action: exponential_backoff

Technical Details:
  QueryTimeoutError: Query execution exceeded timeout of 30 seconds

======================================================================
```

### Memory Error
```
======================================================================
ERROR: Query result set is too large or memory limit exceeded
======================================================================

Category: memory
Severity: 7/10
Recoverable: Yes

SUGGESTIONS:
  1. CRITICAL: Add LIMIT clause immediately (e.g., LIMIT 1000)
  2. Add LIMIT clause to fetch results in smaller batches
  3. Use OFFSET with LIMIT for pagination through large results
  4. Add more selective FILTER conditions
  5. Remove DISTINCT if not necessary (it requires buffering all results)

Recommended Action: none

Technical Details:
  Exception: Result set too large: out of memory

======================================================================
```

## API Reference

### ErrorHandler

```python
ErrorHandler(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    enable_fallback: bool = True,
    enable_optimization_suggestions: bool = True
)
```

**Methods:**
- `categorize_error(error, query, endpoint)` → ErrorContext
- `suggest_optimizations(query)` → List[QueryOptimization]
- `optimize_query(query, level)` → str
- `recover_from_error(error, query, endpoint, execute_func, alternative_endpoints)` → RecoveryResult
- `format_error_report(context)` → str
- `get_statistics()` → Dict[str, Any]

### Convenience Functions

- `handle_query_error(error, query, endpoint)` → ErrorContext
- `get_error_suggestions(error, query)` → List[str]
- `optimize_query(query)` → Tuple[str, List[QueryOptimization]]

## License

Part of the SPARQL Agent project.
