# Quick Start Guide

Get started with SPARQL Agent in 5 minutes.

## Installation

=== "UV (Recommended)"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv add sparql-agent
    ```

=== "pip"

    ```bash
    pip install sparql-agent
    ```

## Your First Query

### Using the CLI

Query UniProt for protein information:

```bash
uv run sparql-agent query \
  "Find all human proteins involved in DNA repair" \
  --endpoint https://sparql.uniprot.org/sparql \
  --format json
```

### Using Python API

```python
from sparql_agent import SPARQLAgent

# Initialize agent
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic",
    api_key="your-api-key"
)

# Natural language query
results = agent.query("Find all human proteins involved in DNA repair")

# Display results
for result in results:
    print(result)
```

### Using Interactive Shell

```bash
uv run python -m sparql_agent.cli.interactive
```

```
Welcome to SPARQL Agent Interactive Shell
Type 'help' for available commands

sparql> endpoint https://sparql.uniprot.org/sparql
Endpoint set to: https://sparql.uniprot.org/sparql

sparql> query Find all human proteins involved in DNA repair
Generating SPARQL query...
Executing query...

Results (10):
┌──────────────┬─────────────────────────────┬──────────────┐
│ Protein      │ Name                        │ Gene         │
├──────────────┼─────────────────────────────┼──────────────┤
│ P00533       │ BRCA1                       │ BRCA1        │
│ P38398       │ DNA repair protein RAD51    │ RAD51        │
│ ...          │ ...                         │ ...          │
└──────────────┴─────────────────────────────┴──────────────┘
```

## Common Use Cases

### 1. Query Biomedical Data

```python
from sparql_agent import SPARQLAgent

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")

# Find proteins by disease
proteins = agent.query(
    "What proteins are associated with Alzheimer's disease?"
)

# Get protein sequences
sequence = agent.query(
    "Get the amino acid sequence for protein P00533"
)

# Find protein-protein interactions
interactions = agent.query(
    "Show all proteins that interact with BRCA1"
)
```

### 2. Explore Wikidata

```python
agent = SPARQLAgent(endpoint="https://query.wikidata.org/sparql")

# Historical queries
winners = agent.query(
    "List all Nobel Prize winners in Physics after 2000"
)

# Geographic queries
cities = agent.query(
    "Find all cities in France with population over 100,000"
)

# Cultural queries
books = agent.query(
    "List books by Ernest Hemingway with publication dates"
)
```

### 3. Schema Discovery

Discover what's available in a SPARQL endpoint:

```python
from sparql_agent.discovery import ConnectivityChecker

checker = ConnectivityChecker("https://sparql.uniprot.org/sparql")

# Get endpoint statistics
stats = checker.get_statistics()
print(f"Total triples: {stats['triple_count']}")
print(f"Classes: {stats['class_count']}")
print(f"Properties: {stats['property_count']}")

# Find available classes
classes = checker.get_classes()
for cls in classes[:10]:
    print(f"- {cls}")

# Find properties
properties = checker.get_properties()
for prop in properties[:10]:
    print(f"- {prop}")
```

### 4. Work with Ontologies

```python
from sparql_agent.ontology import OLSClient, OWLParser

# Query OLS4 (Ontology Lookup Service)
ols = OLSClient()

# Search for terms
terms = ols.search("diabetes", ontology="efo")
for term in terms:
    print(f"{term['label']}: {term['iri']}")

# Load local OWL ontology
parser = OWLParser("http://purl.obolibrary.org/obo/go.owl")
classes = parser.get_classes()
properties = parser.get_properties()
```

### 5. Batch Processing

Process multiple queries from a file:

```bash
# Create queries file
cat > queries.txt <<EOF
Find all proteins related to cancer
What are the symptoms of diabetes?
List all enzymes in glycolysis pathway
EOF

# Run batch processing
uv run sparql-agent batch \
  --input queries.txt \
  --output results/ \
  --endpoint https://sparql.uniprot.org/sparql
```

```python
# Python API for batch processing
from sparql_agent.cli.batch import BatchProcessor

processor = BatchProcessor(
    endpoint="https://sparql.uniprot.org/sparql",
    output_dir="results"
)

queries = [
    "Find all proteins related to cancer",
    "What are the symptoms of diabetes?",
    "List all enzymes in glycolysis pathway"
]

results = processor.process_queries(queries)
```

## Configuration

### Set API Keys

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
export OPENAI_API_KEY=sk-your-key-here
```

### Create Configuration File

Create `~/.sparql-agent/config.yaml`:

```yaml
llm:
  provider: anthropic
  model: claude-3-5-sonnet-20241022

endpoints:
  default: https://sparql.uniprot.org/sparql

query:
  timeout: 30
  max_results: 1000
```

## Next Steps

### Learn More

- [CLI Reference](cli.md) - Complete CLI documentation
- [Python API](api.md) - Full API reference
- [Tutorials](tutorials/tutorial-basic.md) - Step-by-step guides
- [Examples](examples/notebooks.md) - Jupyter notebooks

### Common Tasks

- [Working with Ontologies](tutorials/tutorial-ontology.md)
- [Federated Queries](tutorials/tutorial-federation.md)
- [Natural Language Queries](tutorials/tutorial-llm.md)
- [Advanced Querying](tutorials/tutorial-advanced.md)

### Development

- [Architecture](architecture.md) - System design
- [Contributing](contributing.md) - Contribution guidelines
- [Testing](testing.md) - Testing guide

## Examples

### Example 1: Find Drug Targets

```python
from sparql_agent import SPARQLAgent

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")

# Find proteins that are drug targets
targets = agent.query("""
    Find all human proteins that are:
    - Membrane proteins
    - Involved in signal transduction
    - Have known drug interactions
""")

print(f"Found {len(targets)} potential drug targets")
```

### Example 2: Cross-Reference Databases

```python
# Query multiple endpoints
uniprot_agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
wikidata_agent = SPARQLAgent(endpoint="https://query.wikidata.org/sparql")

# Get protein from UniProt
protein = uniprot_agent.query("Get details for protein BRCA1")

# Find related information in Wikidata
wiki_info = wikidata_agent.query(
    f"Find all information about {protein['name']}"
)
```

### Example 3: Generate Reports

```python
from sparql_agent import SPARQLAgent
from sparql_agent.formatting import ResultFormatter

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
formatter = ResultFormatter()

# Query data
results = agent.query("Find all proteins in the p53 pathway")

# Format as table
print(formatter.to_table(results))

# Export to CSV
formatter.to_csv(results, "p53_proteins.csv")

# Create visualization
formatter.to_graph(results, "p53_network.png")
```

## Tips and Tricks

### 1. Use Verbose Mode for Debugging

```bash
uv run sparql-agent query "test query" \
  --endpoint https://sparql.uniprot.org/sparql \
  --verbose
```

### 2. Save Queries for Reuse

```python
agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")

# Save query
query = agent.generate_query("Find cancer-related proteins")
with open("cancer_proteins.sparql", "w") as f:
    f.write(query)

# Reuse later
with open("cancer_proteins.sparql") as f:
    results = agent.execute(f.read())
```

### 3. Handle Large Results

```python
# Use pagination
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    max_results=100
)

# Process in batches
for batch in agent.query_batched("Find all proteins", batch_size=100):
    process_batch(batch)
```

### 4. Cache Frequently Used Data

```python
from sparql_agent.cache import QueryCache

cache = QueryCache(ttl=3600)  # 1 hour cache

agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    cache=cache
)

# First call - executes query
results1 = agent.query("Find proteins")

# Second call - uses cache
results2 = agent.query("Find proteins")  # Fast!
```

## Troubleshooting

### Query Takes Too Long

```python
# Increase timeout
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    timeout=60  # 60 seconds
)
```

### Connection Errors

```python
# Add retry logic
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    retry_count=3,
    retry_delay=5
)
```

### Invalid SPARQL Syntax

```python
# Validate query before execution
from sparql_agent.query import QueryValidator

validator = QueryValidator()
is_valid, errors = validator.validate(query)

if not is_valid:
    print(f"Query errors: {errors}")
```

## Getting Help

- Documentation: [Full documentation](https://github.com/david4096/sparql-agent)
- Issues: [GitHub Issues](https://github.com/david4096/sparql-agent/issues)
- Examples: [Code samples](examples/code-samples.md)
