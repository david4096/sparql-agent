# Tutorial: Working with Ontologies

Learn how to use OWL ontologies and the Ontology Lookup Service (OLS4) with SPARQL Agent.

## Introduction

Ontologies provide structured vocabularies for knowledge graphs. This tutorial covers:
- Searching OLS4 for ontology terms
- Loading OWL ontologies
- Using ontologies in queries
- Mapping natural language to ontology terms

## Prerequisites

```bash
uv add sparql-agent
export ANTHROPIC_API_KEY="your-key-here"
```

## Part 1: Searching OLS4

### Basic Search

```python
from sparql_agent.ontology import OLSClient

ols = OLSClient()

# Search across all ontologies
results = ols.search("diabetes")

for term in results[:5]:
    print(f"{term['label']} ({term['ontology']})")
    print(f"  IRI: {term['iri']}")
    print(f"  Definition: {term.get('definition', 'N/A')[:100]}...")
    print()
```

### Search Specific Ontology

```python
# Search in EFO (Experimental Factor Ontology)
results = ols.search("diabetes", ontology="efo")

# Search in MONDO (Monarch Disease Ontology)
results = ols.search("cancer", ontology="mondo")

# Search in HP (Human Phenotype Ontology)
results = ols.search("seizure", ontology="hp")
```

### Get Term Details

```python
# Get detailed information
term = ols.get_term("efo", "EFO_0000400")

print(f"Label: {term['label']}")
print(f"Definition: {term['definition']}")
print(f"Synonyms: {term.get('synonyms', [])}")
print(f"Parents: {term.get('parents', [])}")
print(f"Children: {term.get('children', [])}")
```

## Part 2: Loading OWL Ontologies

### Load from URL

```python
from sparql_agent.ontology import OWLParser

# Load Gene Ontology
parser = OWLParser("http://purl.obolibrary.org/obo/go.owl")

# Get classes
classes = parser.get_classes()
print(f"Found {len(classes)} classes")

# Get properties
properties = parser.get_properties()
print(f"Found {len(properties)} properties")

# Get metadata
metadata = parser.get_metadata()
print(f"Ontology: {metadata['ontology_iri']}")
print(f"Version: {metadata.get('version', 'N/A')}")
```

### Load from File

```python
# Download and load local file
parser = OWLParser("~/.sparql-agent/ontologies/go.owl")

# Explore hierarchy
for cls in parser.get_classes()[:10]:
    print(f"Class: {cls}")
    parents = parser.get_parents(cls)
    print(f"  Parents: {parents}")
```

## Part 3: Using Ontologies in Queries

### Map Terms to IRIs

```python
from sparql_agent import SPARQLAgent
from sparql_agent.ontology import OLSClient

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
ols = OLSClient()

# Search for GO term
go_terms = ols.search("DNA repair", ontology="go")
go_iri = go_terms[0]['iri']

# Use in query
results = agent.query(f"""
    Find proteins with GO annotation {go_iri}
""")

for result in results[:5]:
    print(result)
```

### Automatic Term Mapping

```python
# SPARQL Agent can automatically map terms
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic"
)

# Natural language query with ontology context
results = agent.query(
    "Find proteins with GO term DNA repair",
    ontology="go"
)
```

## Part 4: Biomedical Ontologies

### EFO (Experimental Factor Ontology)

```python
ols = OLSClient()

# Search for diseases
disease_terms = ols.search("alzheimer", ontology="efo")

for term in disease_terms:
    print(f"{term['label']}: {term['iri']}")

# Get disease hierarchy
term_details = ols.get_term("efo", "EFO_0000249")
print(f"Parents: {term_details.get('parents', [])}")
```

### MONDO (Monarch Disease Ontology)

```python
# Search MONDO
results = ols.search("breast cancer", ontology="mondo")

for term in results[:3]:
    print(f"\n{term['label']}")
    print(f"  IRI: {term['iri']}")

    # Get full details
    details = ols.get_term("mondo", term['short_form'])
    print(f"  Synonyms: {details.get('synonyms', [])[:3]}")
```

### HP (Human Phenotype Ontology)

```python
# Search phenotypes
results = ols.search("seizure", ontology="hp")

for term in results[:5]:
    print(f"{term['label']}: {term['short_form']}")
```

### GO (Gene Ontology)

```python
# Search GO terms
results = ols.search("cell division", ontology="go")

# Filter by category
for term in results:
    if 'biological_process' in term.get('obo_namespace', ''):
        print(f"Process: {term['label']}")
```

## Part 5: Complex Ontology Queries

### Query with Ontology Context

```python
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic"
)

# Query uses ontology for context
results = agent.query("""
    Find human proteins that:
    - Have GO term 'protein kinase activity'
    - Are located in the 'plasma membrane'
    - Are involved in 'signal transduction'
""", ontology="go")

for result in results[:5]:
    print(result)
```

### Hierarchical Queries

```python
from sparql_agent.ontology import OLSClient

ols = OLSClient()

# Get term and all descendants
term = ols.get_term("go", "GO_0006281")  # DNA repair
descendants = ols.get_descendants("go", "GO_0006281")

print(f"Found {len(descendants)} types of DNA repair")

# Query for all descendant terms
for desc in descendants[:5]:
    print(f"  - {desc['label']}")
```

## Part 6: Cross-Ontology Mapping

### Map Between Ontologies

```python
ols = OLSClient()

# Find equivalent terms
efo_term = ols.search("diabetes", ontology="efo")[0]
mondo_term = ols.search("diabetes", ontology="mondo")[0]

print(f"EFO: {efo_term['iri']}")
print(f"MONDO: {mondo_term['iri']}")

# Use mappings in queries
agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
results1 = agent.query(f"Find proteins associated with {efo_term['iri']}")
results2 = agent.query(f"Find proteins associated with {mondo_term['iri']}")
```

## Part 7: Custom Ontology Integration

### Build Ontology Cache

```python
from sparql_agent.ontology import OntologyCache

cache = OntologyCache(directory="~/.sparql-agent/ontologies")

# Download and cache ontologies
cache.download("go", "http://purl.obolibrary.org/obo/go.owl")
cache.download("mondo", "http://purl.obolibrary.org/obo/mondo.owl")

# Use cached ontologies
go = cache.load("go")
mondo = cache.load("mondo")
```

### Create Custom Mappings

```python
from sparql_agent.query import OntologyGenerator

generator = OntologyGenerator()

# Add custom term mappings
generator.add_mapping(
    term="cell growth",
    iri="http://purl.obolibrary.org/obo/GO_0016049",
    ontology="go"
)

# Use in queries
query = generator.generate_query(
    "Find proteins involved in cell growth",
    mappings=generator.get_mappings()
)
```

## Part 8: Practical Examples

### Example 1: Disease-Gene Associations

```python
from sparql_agent import SPARQLAgent
from sparql_agent.ontology import OLSClient

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
ols = OLSClient()

# Search for disease
disease = ols.search("Parkinson", ontology="mondo")[0]
print(f"Disease: {disease['label']}")

# Find associated genes/proteins
results = agent.query(f"""
    Find proteins associated with disease {disease['iri']}
    Include gene names and functions
""")

for result in results[:5]:
    print(f"  {result.get('gene')}: {result.get('function')}")
```

### Example 2: Pathway Analysis

```python
# Find all proteins in a pathway
go_pathway = ols.search("glycolysis", ontology="go")[0]

results = agent.query(f"""
    Find all enzymes in pathway {go_pathway['iri']}
    Include enzyme names and EC numbers
""")

print(f"Found {len(results)} enzymes in glycolysis")
```

### Example 3: Phenotype to Gene

```python
# Map phenotype to genes
phenotype = ols.search("intellectual disability", ontology="hp")[0]

results = agent.query(f"""
    Find genes associated with phenotype {phenotype['iri']}
""")

for result in results[:10]:
    print(f"{result['gene']}: {result['description']}")
```

## Best Practices

1. **Cache Ontologies**: Download and cache frequently used ontologies
2. **Use Specific Ontologies**: Specify ontology for better term matching
3. **Check Term Hierarchy**: Use parent/child relationships
4. **Validate Terms**: Verify terms exist before querying
5. **Handle Versioning**: Track ontology versions

## Exercises

1. Search EFO for "type 2 diabetes" and get all parent terms
2. Load Gene Ontology and find all terms under "DNA repair"
3. Map MONDO disease terms to UniProt proteins
4. Create a query using GO terms for "cell cycle" processes
5. Build a cache of biomedical ontologies

## Next Steps

- [Tutorial: Federation Queries](tutorial-federation.md)
- [Tutorial: LLM Integration](tutorial-llm.md)
- [Examples: Biomedical Use Cases](../examples/biomedical.md)

## Resources

- [OLS4 API](https://www.ebi.ac.uk/ols4/api)
- [Gene Ontology](http://geneontology.org/)
- [MONDO](https://mondo.monarchinitiative.org/)
- [EFO](https://www.ebi.ac.uk/efo/)
- [Human Phenotype Ontology](https://hpo.jax.org/)
