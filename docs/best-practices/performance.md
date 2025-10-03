# Performance Best Practices

Optimize SPARQL Agent performance for production use.

## Query Optimization

### 1. Use Appropriate Limits

```python
# Always specify limits
results = agent.query("Find proteins", limit=100)

# Or in SPARQL
sparql = """
SELECT ?protein
WHERE { ?protein a up:Protein }
LIMIT 100
"""
```

### 2. Filter Early

```sparql
# Bad: Filter after selecting all
SELECT ?protein ?name
WHERE {
    ?protein a up:Protein ;
             rdfs:label ?name .
}
LIMIT 10

# Good: Filter early
SELECT ?protein ?name
WHERE {
    ?protein a up:Protein ;
             up:organism taxon:9606 ;  # Human only
             rdfs:label ?name .
}
LIMIT 10
```

### 3. Use Selective Predicates

```sparql
# Bad: Very generic
SELECT * WHERE { ?s ?p ?o } LIMIT 10

# Good: Specific predicates
SELECT ?protein ?name
WHERE {
    ?protein a up:Protein ;
             rdfs:label ?name .
}
LIMIT 10
```

## Caching Strategies

### Enable Query Caching

```python
from sparql_agent.cache import RedisCache, FileCache

# Redis cache (production)
cache = RedisCache(
    host="localhost",
    port=6379,
    ttl=3600  # 1 hour
)

agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    cache=cache
)
```

### Multi-Level Caching

```python
class MultiLevelCache:
    def __init__(self):
        self.l1 = MemoryCache(max_size=100)  # Fast, small
        self.l2 = RedisCache()               # Medium, shared
        self.l3 = FileCache()                # Slow, persistent

    def get(self, key):
        return (
            self.l1.get(key) or
            self.l2.get(key) or
            self.l3.get(key)
        )
```

## Connection Management

### Connection Pooling

```python
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    pool_size=10,
    pool_max_overflow=20
)
```

### Reuse Connections

```python
# Bad: Creating new agent for each query
for query in queries:
    agent = SPARQLAgent(endpoint=endpoint)
    results = agent.query(query)

# Good: Reuse agent
agent = SPARQLAgent(endpoint=endpoint)
for query in queries:
    results = agent.query(query)
```

## Parallel Processing

### Query Batch in Parallel

```python
from concurrent.futures import ThreadPoolExecutor

agent = SPARQLAgent(endpoint=endpoint)

queries = ["query1", "query2", "query3"]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(agent.query, queries))
```

### Async Support

```python
import asyncio
from sparql_agent import AsyncSPARQLAgent

async def main():
    agent = AsyncSPARQLAgent(endpoint=endpoint)

    # Execute in parallel
    tasks = [
        agent.query("query1"),
        agent.query("query2"),
        agent.query("query3")
    ]

    results = await asyncio.gather(*tasks)
    return results

results = asyncio.run(main())
```

## Memory Management

### Limit Result Sets

```python
# Process in batches
def process_large_query(agent, query):
    offset = 0
    batch_size = 1000

    while True:
        sparql = f"{query} LIMIT {batch_size} OFFSET {offset}"
        batch = agent.execute_sparql(sparql)

        if not batch:
            break

        process_batch(batch)
        offset += batch_size
```

### Stream Results

```python
for batch in agent.query_batched(query, batch_size=100):
    process_batch(batch)
    # Previous batches are garbage collected
```

## LLM Optimization

### Cache LLM Responses

```python
# Cache generated queries
agent = SPARQLAgent(
    llm_provider="anthropic",
    cache_enabled=True,
    cache_ttl=86400  # 24 hours
)

# First call - uses LLM
results1 = agent.query("Find proteins")  # Slow, costs $

# Second call - uses cache
results2 = agent.query("Find proteins")  # Fast, free!
```

### Use Templates When Possible

```python
# For simple queries, use templates (no LLM cost)
results = agent.query("Find proteins", strategy="template")

# For complex queries, use LLM
results = agent.query(
    "Find proteins with multiple conditions...",
    strategy="llm"
)
```

## Monitoring & Profiling

### Track Performance

```python
import time

start = time.time()
results = agent.query("Find proteins")
duration = time.time() - start

print(f"Query took {duration:.2f}s")
```

### Use Profiling

```python
import cProfile

cProfile.run('agent.query("Find proteins")')
```

## Production Configuration

```yaml
# config/production.yaml
query:
  timeout: 60
  max_results: 1000

cache:
  enabled: true
  backend: redis
  ttl: 3600

web:
  workers: 4
  pool_size: 10

performance:
  max_workers: 4
  max_memory_mb: 2048
```

## Best Practices Summary

1. **Always use LIMIT** in queries
2. **Filter early** in WHERE clauses
3. **Enable caching** for frequently accessed data
4. **Reuse connections** and agent instances
5. **Process in parallel** when possible
6. **Monitor performance** and optimize bottlenecks
7. **Use appropriate timeouts**
8. **Batch large operations**
9. **Cache LLM responses**
10. **Profile before optimizing**
