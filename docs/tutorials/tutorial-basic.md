# Tutorial: Basic SPARQL Queries

Learn the fundamentals of querying SPARQL endpoints with SPARQL Agent.

## Prerequisites

- SPARQL Agent installed (`uv add sparql-agent`)
- Basic understanding of RDF and knowledge graphs
- API key for LLM provider (optional for this tutorial)

## Step 1: Your First Query

Let's start by querying UniProt for protein information.

### Using CLI

```bash
uv run sparql-agent query \
  "Find 10 proteins from human" \
  --endpoint https://sparql.uniprot.org/sparql \
  --format table
```

### Using Python API

```python
from sparql_agent import SPARQLAgent

# Initialize agent
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql"
)

# Execute query
results = agent.query("Find 10 proteins from human")

# Display results
for result in results:
    print(f"Protein: {result.get('protein')}")
    print(f"Name: {result.get('name')}")
    print("---")
```

**Expected Output:**

```
Protein: http://purl.uniprot.org/uniprot/P00533
Name: Epidermal growth factor receptor
---
Protein: http://purl.uniprot.org/uniprot/P04637
Name: Cellular tumor antigen p53
---
...
```

## Step 2: Understanding the Generated SPARQL

See what SPARQL query was generated:

```bash
uv run sparql-agent query \
  "Find 10 proteins from human" \
  --endpoint https://sparql.uniprot.org/sparql \
  --show-sparql \
  --no-execute
```

**Generated SPARQL:**

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX taxon: <http://purl.uniprot.org/taxonomy/>

SELECT ?protein ?name
WHERE {
    ?protein a up:Protein ;
             up:organism taxon:9606 ;
             rdfs:label ?name .
}
LIMIT 10
```

## Step 3: Executing Raw SPARQL

Execute SPARQL directly:

```python
from sparql_agent import SPARQLAgent

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")

# Write your own SPARQL
sparql = """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?protein ?name ?organism
WHERE {
    ?protein a up:Protein ;
             rdfs:label ?name ;
             up:organism ?organism .
}
LIMIT 10
"""

results = agent.execute_sparql(sparql)
print(f"Found {len(results)} results")
```

## Step 4: Filtering Results

Add filters to your queries:

```python
agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")

# Find proteins with specific characteristics
results = agent.query("""
    Find human proteins that:
    - Have the word 'kinase' in their name
    - Are reviewed (Swiss-Prot)
""")

for result in results[:5]:
    print(f"{result['name']}: {result['protein']}")
```

## Step 5: Working with Different Endpoints

### Wikidata

```python
# Query Wikidata
agent = SPARQLAgent(endpoint="https://query.wikidata.org/sparql")

results = agent.query("List Nobel Prize winners in Physics after 2000")

for result in results:
    print(f"{result.get('name')}: {result.get('year')}")
```

### DBpedia

```python
# Query DBpedia
agent = SPARQLAgent(endpoint="https://dbpedia.org/sparql")

results = agent.query("Find European countries with population over 10 million")

for result in results:
    print(f"{result.get('country')}: {result.get('population')}")
```

## Step 6: Formatting Results

### Table Format

```python
from sparql_agent.formatting import ResultFormatter

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
formatter = ResultFormatter()

results = agent.query("Find 10 human proteins")

# Format as table
table = formatter.to_table(results)
print(table)
```

**Output:**

```
┌──────────────────────────────┬─────────────────────────────────┐
│ Protein                      │ Name                            │
├──────────────────────────────┼─────────────────────────────────┤
│ ...uniprot/P00533            │ Epidermal growth factor receptor│
│ ...uniprot/P04637            │ Cellular tumor antigen p53      │
└──────────────────────────────┴─────────────────────────────────┘
```

### CSV Export

```python
# Export to CSV
formatter.to_csv(results, "proteins.csv")
print("Results saved to proteins.csv")
```

### JSON Export

```python
# Export to JSON
json_output = formatter.to_json(results, indent=2)
print(json_output)
```

### DataFrame

```python
# Convert to pandas DataFrame
df = formatter.to_dataframe(results)
print(df.head())

# Use pandas features
df.to_excel("proteins.xlsx")
df.plot.bar(x='name', y='count')
```

## Step 7: Handling Errors

Proper error handling:

```python
from sparql_agent import SPARQLAgent
from sparql_agent.core import (
    EndpointError,
    QueryGenerationError,
    TimeoutError
)

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")

try:
    results = agent.query("Find all proteins")
except EndpointError as e:
    print(f"Endpoint error: {e}")
    print("Check if endpoint is available")
except QueryGenerationError as e:
    print(f"Query generation error: {e}")
    print("Try rephrasing your query")
except TimeoutError as e:
    print(f"Query timeout: {e}")
    print("Query took too long, try reducing scope")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Step 8: Query Validation

Validate queries before execution:

```python
from sparql_agent.query import QueryValidator

validator = QueryValidator()

sparql = """
SELECT ?protein ?name
WHERE {
    ?protein a up:Protein ;
             rdfs:label ?name
}
LIMIT 10
"""

is_valid, errors = validator.validate(sparql)

if is_valid:
    results = agent.execute_sparql(sparql)
else:
    print("Query has errors:")
    for error in errors:
        print(f"  - {error}")
```

## Step 9: Performance Optimization

### Use Limits

```python
# Limit results for faster queries
results = agent.query(
    "Find proteins",
    limit=100  # Only get first 100 results
)
```

### Set Timeouts

```python
# Set query timeout
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    timeout=60  # 60 seconds
)
```

### Enable Caching

```python
# Enable result caching
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    cache_enabled=True
)

# First call - executes query
results1 = agent.query("Find proteins")  # Slow

# Second call - uses cache
results2 = agent.query("Find proteins")  # Fast!
```

## Step 10: Batch Processing

Process multiple queries efficiently:

```python
agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")

queries = [
    "Find proteins involved in DNA repair",
    "Find proteins in the cell membrane",
    "Find enzymes in glycolysis"
]

# Process in parallel
results = agent.query_batch(queries, parallel=True)

for query, result in zip(queries, results):
    print(f"\nQuery: {query}")
    print(f"Results: {len(result)}")
```

## Common Patterns

### 1. Count Queries

```python
# Count results
results = agent.query("How many proteins are in UniProt?")
print(f"Total proteins: {results[0]['count']}")
```

### 2. Aggregation

```python
# Group and aggregate
results = agent.query("""
    Count proteins by organism
    Show top 10 organisms
""")

for result in results:
    print(f"{result['organism']}: {result['count']} proteins")
```

### 3. Property Paths

```python
# Use property paths for complex relationships
results = agent.query("""
    Find proteins that interact with proteins
    that interact with p53
""")
```

### 4. OPTIONAL Clauses

```python
# Get optional information
sparql = """
SELECT ?protein ?name ?description
WHERE {
    ?protein a up:Protein ;
             rdfs:label ?name .
    OPTIONAL { ?protein up:annotation ?description }
}
LIMIT 10
"""

results = agent.execute_sparql(sparql)
```

## Exercises

Try these exercises to practice:

1. **Exercise 1**: Find all proteins from mouse (taxon:10090)
2. **Exercise 2**: Query Wikidata for countries and their capitals
3. **Exercise 3**: Find proteins with more than 1000 amino acids
4. **Exercise 4**: Export results to both CSV and JSON
5. **Exercise 5**: Write a query with error handling and retry logic

## Solutions

<details>
<summary>Exercise 1 Solution</summary>

```python
agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
results = agent.query("Find proteins from mouse")

for result in results[:10]:
    print(result['name'])
```
</details>

<details>
<summary>Exercise 2 Solution</summary>

```python
agent = SPARQLAgent(endpoint="https://query.wikidata.org/sparql")
results = agent.query("Find countries and their capitals")

for result in results[:10]:
    print(f"{result['country']}: {result['capital']}")
```
</details>

## Next Steps

- [Tutorial: Working with Ontologies](tutorial-ontology.md)
- [Tutorial: Federation Queries](tutorial-federation.md)
- [Tutorial: Natural Language Queries](tutorial-llm.md)
- [Examples: Biomedical Use Cases](../examples/biomedical.md)

## Further Reading

- [SPARQL Specification](https://www.w3.org/TR/sparql11-query/)
- [UniProt SPARQL](https://www.uniprot.org/help/sparql)
- [Wikidata Query Service](https://query.wikidata.org/)
