# Python API Reference

Complete guide to using SPARQL Agent programmatically in Python.

## Installation

```bash
pip install sparql-agent
```

## Quick Start

```python
from sparql_agent import SPARQLAgent

# Initialize agent
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic"
)

# Execute natural language query
results = agent.query("Find all human proteins")

# Display results
for result in results:
    print(result)
```

## Core Classes

### SPARQLAgent

The main class for interacting with SPARQL endpoints.

```python
from sparql_agent import SPARQLAgent

agent = SPARQLAgent(
    endpoint: str,
    llm_provider: str = "anthropic",
    api_key: Optional[str] = None,
    timeout: int = 30,
    max_results: int = 1000,
    cache_enabled: bool = True
)
```

#### Parameters

- `endpoint`: SPARQL endpoint URL
- `llm_provider`: LLM provider ("anthropic", "openai", "local")
- `api_key`: API key for LLM provider (or set via environment variable)
- `timeout`: Query timeout in seconds
- `max_results`: Maximum number of results to return
- `cache_enabled`: Enable query result caching

#### Methods

##### query()

Execute a natural language query:

```python
results = agent.query(
    query: str,
    format: str = "json",
    ontology: Optional[str] = None,
    strategy: str = "auto"
) -> List[Dict[str, Any]]
```

**Example:**

```python
# Simple query
results = agent.query("Find all proteins")

# With ontology
results = agent.query(
    "Find genes with GO term DNA repair",
    ontology="go"
)

# With specific strategy
results = agent.query(
    "List all classes",
    strategy="template"
)
```

##### execute_sparql()

Execute a raw SPARQL query:

```python
results = agent.execute_sparql(
    sparql_query: str,
    format: str = "json"
) -> List[Dict[str, Any]]
```

**Example:**

```python
sparql = """
SELECT ?protein ?name
WHERE {
    ?protein a up:Protein ;
             rdfs:label ?name .
}
LIMIT 10
"""

results = agent.execute_sparql(sparql)
```

##### discover_schema()

Discover endpoint schema and capabilities:

```python
schema = agent.discover_schema(
    methods: List[str] = ["void", "introspection"],
    cache: bool = True
) -> Dict[str, Any]
```

**Example:**

```python
schema = agent.discover_schema()

print(f"Classes: {len(schema['classes'])}")
print(f"Properties: {len(schema['properties'])}")
print(f"Namespaces: {schema['namespaces']}")
```

##### validate_query()

Validate a SPARQL query:

```python
is_valid, errors = agent.validate_query(sparql_query: str)
```

**Example:**

```python
query = "SELECT ?s WHERE { ?s ?p ?o }"
is_valid, errors = agent.validate_query(query)

if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

## Ontology Support

### OLSClient

Query the EBI Ontology Lookup Service (OLS4):

```python
from sparql_agent.ontology import OLSClient

ols = OLSClient(base_url="https://www.ebi.ac.uk/ols4/api")
```

#### Methods

##### search()

Search for ontology terms:

```python
results = ols.search(
    query: str,
    ontology: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]
```

**Example:**

```python
# Search all ontologies
terms = ols.search("diabetes")

# Search specific ontology
terms = ols.search("diabetes", ontology="efo")

for term in terms:
    print(f"{term['label']}: {term['iri']}")
```

##### get_term()

Get detailed information about a term:

```python
term = ols.get_term(
    ontology: str,
    term_id: str
) -> Dict[str, Any]
```

**Example:**

```python
term = ols.get_term("efo", "EFO_0000400")

print(f"Label: {term['label']}")
print(f"Definition: {term['definition']}")
print(f"Synonyms: {term['synonyms']}")
```

##### get_ontology()

Get ontology metadata:

```python
ontology = ols.get_ontology(ontology_id: str) -> Dict[str, Any]
```

**Example:**

```python
ontology = ols.get_ontology("efo")

print(f"Title: {ontology['title']}")
print(f"Description: {ontology['description']}")
print(f"Version: {ontology['version']}")
```

### OWLParser

Parse and work with OWL ontologies:

```python
from sparql_agent.ontology import OWLParser

parser = OWLParser(ontology_path: str)
```

#### Methods

##### get_classes()

Get all classes from the ontology:

```python
classes = parser.get_classes() -> List[str]
```

**Example:**

```python
parser = OWLParser("http://purl.obolibrary.org/obo/go.owl")
classes = parser.get_classes()

for cls in classes[:10]:
    print(cls)
```

##### get_properties()

Get all properties:

```python
properties = parser.get_properties() -> List[str]
```

##### get_metadata()

Get ontology metadata:

```python
metadata = parser.get_metadata() -> Dict[str, Any]
```

**Example:**

```python
metadata = parser.get_metadata()
print(f"Ontology: {metadata['ontology_iri']}")
print(f"Version: {metadata['version']}")
```

## Schema Discovery

### ConnectivityChecker

Check endpoint connectivity and capabilities:

```python
from sparql_agent.discovery import ConnectivityChecker

checker = ConnectivityChecker(endpoint: str)
```

#### Methods

##### check_connectivity()

Test endpoint connectivity:

```python
is_connected = checker.check_connectivity() -> bool
```

##### get_statistics()

Get endpoint statistics:

```python
stats = checker.get_statistics() -> Dict[str, Any]
```

**Example:**

```python
checker = ConnectivityChecker("https://sparql.uniprot.org/sparql")

if checker.check_connectivity():
    stats = checker.get_statistics()
    print(f"Total triples: {stats['triple_count']}")
    print(f"Classes: {stats['class_count']}")
    print(f"Properties: {stats['property_count']}")
```

##### get_classes()

Get all classes from endpoint:

```python
classes = checker.get_classes(limit: int = 100) -> List[str]
```

##### get_properties()

Get all properties from endpoint:

```python
properties = checker.get_properties(limit: int = 100) -> List[str]
```

### SchemaInference

Infer schema from endpoint:

```python
from sparql_agent.schema import SchemaInference

inference = SchemaInference(endpoint: str)
schema = inference.infer_schema()
```

**Example:**

```python
inference = SchemaInference("https://sparql.uniprot.org/sparql")
schema = inference.infer_schema()

# Get class hierarchy
for cls, info in schema['classes'].items():
    print(f"Class: {cls}")
    print(f"  Instances: {info['instance_count']}")
    print(f"  Properties: {info['properties']}")
```

## Query Generation

### QueryGenerator

Generate SPARQL queries from natural language:

```python
from sparql_agent.query import QueryGenerator

generator = QueryGenerator(
    llm_provider: str = "anthropic",
    api_key: Optional[str] = None
)
```

#### Methods

##### generate()

Generate SPARQL query:

```python
sparql = generator.generate(
    natural_query: str,
    schema: Optional[Dict] = None,
    ontology: Optional[str] = None
) -> str
```

**Example:**

```python
generator = QueryGenerator(llm_provider="anthropic")

sparql = generator.generate(
    "Find all proteins from human",
    schema=schema_info
)

print(sparql)
```

### QueryValidator

Validate SPARQL queries:

```python
from sparql_agent.query import QueryValidator

validator = QueryValidator()
is_valid, errors = validator.validate(sparql_query: str)
```

**Example:**

```python
validator = QueryValidator()

query = "SELECT ?s WHERE { ?s ?p ?o }"
is_valid, errors = validator.validate(query)

if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

## Result Formatting

### ResultFormatter

Format query results in various formats:

```python
from sparql_agent.formatting import ResultFormatter

formatter = ResultFormatter()
```

#### Methods

##### to_table()

Format as ASCII table:

```python
table = formatter.to_table(
    results: List[Dict],
    max_width: int = 50
) -> str
```

**Example:**

```python
formatter = ResultFormatter()
table = formatter.to_table(results)
print(table)
```

##### to_csv()

Export to CSV:

```python
formatter.to_csv(
    results: List[Dict],
    filepath: str,
    delimiter: str = ","
)
```

##### to_json()

Export to JSON:

```python
json_str = formatter.to_json(
    results: List[Dict],
    indent: int = 2
) -> str
```

##### to_dataframe()

Convert to pandas DataFrame:

```python
import pandas as pd

df = formatter.to_dataframe(results: List[Dict]) -> pd.DataFrame
```

**Example:**

```python
df = formatter.to_dataframe(results)
print(df.head())

# Use pandas features
df.to_excel("results.xlsx")
df.plot()
```

## LLM Integration

### AnthropicClient

Use Anthropic Claude for query generation:

```python
from sparql_agent.llm import AnthropicClient

client = AnthropicClient(
    api_key: str,
    model: str = "claude-3-5-sonnet-20241022"
)
```

**Example:**

```python
client = AnthropicClient(api_key="sk-ant-...")

response = client.generate_query(
    natural_query="Find all proteins",
    context={"schema": schema_info}
)

print(response['sparql'])
```

### OpenAIClient

Use OpenAI GPT for query generation:

```python
from sparql_agent.llm import OpenAIClient

client = OpenAIClient(
    api_key: str,
    model: str = "gpt-4"
)
```

## Configuration

### Config

Manage configuration:

```python
from sparql_agent.config import Config

# Load from file
config = Config.from_file("config.yaml")

# Load from environment
config = Config.from_env()

# Create programmatically
config = Config(
    llm_provider="anthropic",
    default_endpoint="https://sparql.uniprot.org/sparql",
    timeout=60
)

# Use with agent
agent = SPARQLAgent(config=config)
```

## Error Handling

SPARQL Agent uses custom exceptions:

```python
from sparql_agent.core import (
    SPARQLAgentError,
    EndpointError,
    QueryGenerationError,
    ValidationError,
    TimeoutError
)

try:
    results = agent.query("Find proteins")
except EndpointError as e:
    print(f"Endpoint error: {e}")
except QueryGenerationError as e:
    print(f"Query generation error: {e}")
except ValidationError as e:
    print(f"Validation error: {e}")
except TimeoutError as e:
    print(f"Timeout: {e}")
except SPARQLAgentError as e:
    print(f"General error: {e}")
```

## Advanced Usage

### Custom Endpoint with Authentication

```python
from sparql_agent import SPARQLAgent
from sparql_agent.execution import SPARQLEndpoint

endpoint = SPARQLEndpoint(
    url="https://secure.example.com/sparql",
    auth=("username", "password"),
    headers={"User-Agent": "My-Agent"},
    verify_ssl=True
)

agent = SPARQLAgent(endpoint=endpoint)
```

### Federated Queries

```python
from sparql_agent import SPARQLAgent

agent = SPARQLAgent()

# Query multiple endpoints
query = """
SELECT ?protein ?disease
WHERE {
    SERVICE <https://sparql.uniprot.org/sparql> {
        ?protein a up:Protein .
    }
    SERVICE <https://sparql.omim.org/sparql> {
        ?protein :associatedWith ?disease .
    }
}
"""

results = agent.execute_sparql(query)
```

### Async Support

```python
import asyncio
from sparql_agent import AsyncSPARQLAgent

async def main():
    agent = AsyncSPARQLAgent(
        endpoint="https://sparql.uniprot.org/sparql"
    )

    results = await agent.query("Find proteins")
    return results

results = asyncio.run(main())
```

### Batch Processing

```python
from sparql_agent import SPARQLAgent

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")

queries = [
    "Find all proteins",
    "List all diseases",
    "Show all pathways"
]

# Process in parallel
results = agent.query_batch(queries, parallel=True)

for query, result in zip(queries, results):
    print(f"Query: {query}")
    print(f"Results: {len(result)}")
```

### Custom Query Templates

```python
from sparql_agent.query import TemplateGenerator

generator = TemplateGenerator()

# Add custom template
generator.add_template(
    "protein_by_name",
    """
    SELECT ?protein ?name
    WHERE {
        ?protein a up:Protein ;
                 rdfs:label ?name .
        FILTER(CONTAINS(LCASE(?name), LCASE("{{term}}")))
    }
    LIMIT {{limit}}
    """
)

# Use template
sparql = generator.generate(
    "protein_by_name",
    term="insulin",
    limit=10
)
```

### Caching

```python
from sparql_agent import SPARQLAgent
from sparql_agent.cache import RedisCache, FileCache

# Redis cache
cache = RedisCache(
    host="localhost",
    port=6379,
    ttl=3600
)

agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    cache=cache
)

# File cache
cache = FileCache(
    directory="~/.sparql-agent/cache",
    ttl=3600
)

agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    cache=cache
)
```

## Type Hints

SPARQL Agent is fully typed:

```python
from typing import List, Dict, Any, Optional
from sparql_agent import SPARQLAgent

def process_results(
    agent: SPARQLAgent,
    query: str
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = agent.query(query)
    return results
```

## Next Steps

- [CLI Reference](cli.md) - Command-line interface
- [Tutorials](tutorials/tutorial-basic.md) - Step-by-step guides
- [Examples](examples/code-samples.md) - Code examples
- [API Reference](api/core.md) - Detailed API documentation
