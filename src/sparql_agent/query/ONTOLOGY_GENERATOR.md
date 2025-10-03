# Ontology-Guided SPARQL Query Generation

This module provides intelligent SPARQL query generation using OWL ontologies. It leverages class hierarchies, property domains/ranges, and reasoning capabilities to generate semantically enriched queries.

## Overview

The `OntologyGuidedGenerator` uses ontology structure to:
- **Expand queries** using class hierarchies (subclasses, superclasses, siblings)
- **Suggest property paths** between classes
- **Validate queries** against OWL axioms and constraints
- **Apply semantic reasoning** for implicit relationships
- **Integrate with EBI OLS4** for real-time ontology lookup
- **Cache ontology data** for performance

## Quick Start

```python
from sparql_agent.query import (
    create_ontology_generator,
    OntologyQueryContext,
    ExpansionStrategy,
)

# Create generator with an ontology
generator = create_ontology_generator(ontology_id="go")  # Gene Ontology

# Create query context
context = OntologyQueryContext(
    ontology_info=generator.ontology_info,
    expansion_strategy=ExpansionStrategy.CHILDREN,
    max_hops=3,
)

# Generate query
result = generator.generate_query(
    "Find all genes involved in cell division",
    context,
    include_explanation=True,
)

print(result.query)
print(result.explanation)
```

## Features

### 1. Class Hierarchy Traversal

The generator can expand queries using different traversal strategies:

```python
# Exact match - no expansion
ExpansionStrategy.EXACT

# Include direct children
ExpansionStrategy.CHILDREN

# Include all descendants (transitive)
ExpansionStrategy.DESCENDANTS

# Include all ancestors (parents)
ExpansionStrategy.ANCESTORS

# Include sibling classes (same parent)
ExpansionStrategy.SIBLINGS

# Include related classes via properties
ExpansionStrategy.RELATED
```

**Example:**

```python
from sparql_agent.query import ExpansionStrategy

# Query with class expansion
context = OntologyQueryContext(
    ontology_info=ontology,
    expansion_strategy=ExpansionStrategy.DESCENDANTS,
)

result = generator.generate_query("Find all organisms", context)
# Will include: Organism, Animal, Plant, Bacteria, etc.
```

### 2. Property Path Discovery

Automatically discover property paths connecting classes:

```python
context = OntologyQueryContext(
    ontology_info=ontology,
    max_hops=3,  # Maximum path length
)

result = generator.generate_query(
    "Which genes encode proteins that cause diseases?",
    context
)

# May generate paths like:
# Gene -> encodes -> Protein -> associatedWith -> Disease
```

**Property Path Types:**

- `DIRECT`: Direct property `<property>`
- `INVERSE`: Inverse property `^<property>`
- `SEQUENCE`: Sequence of properties `<p1>/<p2>/<p3>`
- `ALTERNATIVE`: Alternative paths `<p1>|<p2>`
- `ZERO_OR_MORE`: Zero or more repetitions `<p>*`
- `ONE_OR_MORE`: One or more repetitions `<p>+`
- `ZERO_OR_ONE`: Optional property `<p>?`

### 3. OWL Constraint Validation

Validate queries against ontology constraints:

```python
query = """
SELECT ?gene ?protein
WHERE {
    ?gene a <http://purl.obolibrary.org/obo/SO_0000704> .
    ?gene <http://example.org/encodes> ?protein .
}
"""

validation = generator.validate_query_against_ontology(query, ontology)

if not validation['is_valid']:
    print("Errors:", validation['errors'])
    print("Warnings:", validation['warnings'])
```

**Constraint Types:**

- **Domain constraints**: Property can only be used with specific subject classes
- **Range constraints**: Property can only have specific object classes/types
- **Cardinality constraints**: Min/max number of property values
- **Existential constraints**: Required property values
- **Value restrictions**: Specific required values

### 4. EBI OLS4 Integration

Real-time ontology lookup and expansion:

```python
# Expand terms using OLS
expanded = generator.expand_with_ols(
    term_label="gene",
    ontology_id="go",
    strategy=ExpansionStrategy.DESCENDANTS,
)

for term in expanded:
    print(f"{term['label']} - {term['description']}")
```

**Supported Ontologies:**

- GO (Gene Ontology)
- EFO (Experimental Factor Ontology)
- HP (Human Phenotype Ontology)
- MONDO (Monarch Disease Ontology)
- CHEBI (Chemical Entities of Biological Interest)
- PRO (Protein Ontology)
- UBERON (Uber Anatomy Ontology)
- CL (Cell Ontology)
- SO (Sequence Ontology)
- DOID (Human Disease Ontology)
- And many more...

### 5. Property Suggestions

Get property suggestions for connecting classes:

```python
suggestions = generator.suggest_properties_for_classes(
    class_uris=[
        "http://purl.obolibrary.org/obo/SO_0000704",  # Gene
        "http://purl.obolibrary.org/obo/PR_000000001",  # Protein
    ],
    ontology_id="so",
    max_suggestions=10,
)

for suggestion in suggestions:
    print(f"Property: {suggestion['label']}")
    print(f"  Score: {suggestion['score']}")
    print(f"  Domain: {suggestion['domain']}")
    print(f"  Range: {suggestion['range']}")
```

## Architecture

### Core Components

```
OntologyGuidedGenerator
├── Concept Extraction
│   ├── Class matching from natural language
│   ├── Property matching
│   └── Filter keyword extraction
│
├── Class Expansion
│   ├── Hierarchy traversal (BFS/DFS)
│   ├── Sibling discovery
│   └── Related class finding
│
├── Property Path Discovery
│   ├── BFS path finding
│   ├── Multi-hop paths
│   └── Path confidence scoring
│
├── Constraint Extraction
│   ├── Domain/Range validation
│   ├── Cardinality constraints
│   └── Restriction analysis
│
├── Query Building
│   ├── SPARQL generation
│   ├── Filter application
│   └── Optimization
│
└── OLS Integration
    ├── Real-time lookup
    ├── Term expansion
    └── Ontology caching
```

### Data Flow

```
Natural Language Query
    ↓
Concept Extraction (classes, properties, filters)
    ↓
Class Expansion (hierarchy traversal)
    ↓
Property Path Discovery (connecting classes)
    ↓
Constraint Extraction (OWL axioms)
    ↓
SPARQL Query Generation
    ↓
Validation & Confidence Scoring
    ↓
Generated Query + Explanation
```

## Advanced Usage

### Custom Ontology Loading

```python
from sparql_agent.ontology import OWLParser

# Load from file
parser = OWLParser("path/to/ontology.owl", enable_reasoning=True)
ontology_info = generator._convert_parser_to_ontology_info(parser)

# Use in query generation
context = OntologyQueryContext(ontology_info=ontology_info)
result = generator.generate_query("your query", context)
```

### Caching Ontologies

```python
from pathlib import Path

# Load and cache ontology
cache_dir = Path("./ontology_cache")
cache_dir.mkdir(exist_ok=True)

ontology = generator.load_ontology_from_ols(
    ontology_id="go",
    cache_path=cache_dir,
)

# Subsequent loads will use cached version
```

### Multi-Ontology Queries

```python
# Load multiple ontologies
go_generator = create_ontology_generator(ontology_id="go")
hp_generator = create_ontology_generator(ontology_id="hp")

# Generate queries with different ontologies
go_result = go_generator.generate_query("genes in cell cycle", go_context)
hp_result = hp_generator.generate_query("phenotypes of disease", hp_context)
```

### Custom Expansion Logic

```python
# Define custom expansion
def custom_expand(target_classes, ontology_info):
    expanded = {}
    for class_info in target_classes:
        uri = class_info["uri"]
        owl_class = ontology_info.classes[uri]

        # Custom logic: expand based on annotations
        if "important" in owl_class.comment[0]:
            # Add to expansion
            expanded[uri] = owl_class

    return expanded

# Use in generator
expanded = custom_expand(concepts["classes"], ontology_info)
```

## Configuration

### OntologyQueryContext Options

```python
context = OntologyQueryContext(
    ontology_info=ontology,

    # Target classes to include
    target_classes=["http://example.org/Gene"],

    # Required properties
    required_properties=["http://example.org/encodes"],

    # Expansion strategy
    expansion_strategy=ExpansionStrategy.DESCENDANTS,

    # Maximum property path hops
    max_hops=3,

    # Enable OWL reasoning
    use_reasoning=True,

    # Additional constraints
    constraints=[
        QueryConstraint(
            constraint_type="min_cardinality",
            property_uri="http://example.org/hasFunction",
            value=1,
        )
    ],

    # Metadata
    metadata={
        "timeout": 30,
        "limit": 100,
    },
)
```

### Generator Configuration

```python
generator = OntologyGuidedGenerator(
    ontology_info=ontology,
    ols_client=OLSClient(base_url="https://www.ebi.ac.uk/ols4/api/"),
    enable_caching=True,  # Enable caching for performance
)
```

## Performance Optimization

### Caching Strategies

```python
# 1. Class hierarchy cache
generator._class_hierarchy_cache  # Cached hierarchy lookups

# 2. Property path cache
generator._property_path_cache  # Cached path discoveries

# 3. Constraint cache
generator._constraint_cache  # Cached constraint extractions

# Clear cache if needed
generator._class_hierarchy_cache.clear()
```

### Limiting Expansion

```python
# Limit expansion depth
context = OntologyQueryContext(
    ontology_info=ontology,
    expansion_strategy=ExpansionStrategy.CHILDREN,  # Only direct children
    max_hops=2,  # Maximum 2 property hops
)

# Results in faster query generation
```

## Examples

### Example 1: Gene Ontology Query

```python
from sparql_agent.query import create_ontology_generator, OntologyQueryContext, ExpansionStrategy

# Create GO generator
generator = create_ontology_generator(ontology_id="go")

# Query with expansion
context = OntologyQueryContext(
    ontology_info=generator.ontology_info,
    expansion_strategy=ExpansionStrategy.DESCENDANTS,
    max_hops=2,
)

result = generator.generate_query(
    "Find all biological processes related to cell division",
    context,
    include_explanation=True,
)

print("Query:", result.query)
print("\nClasses used:", result.ontology_classes)
print("\nProperties used:", result.ontology_properties)
print("\nExplanation:", result.explanation)
```

### Example 2: Disease Ontology Query

```python
# Create MONDO generator (disease ontology)
generator = create_ontology_generator(ontology_id="mondo")

context = OntologyQueryContext(
    ontology_info=generator.ontology_info,
    expansion_strategy=ExpansionStrategy.CHILDREN,
)

result = generator.generate_query(
    "Find all genetic diseases",
    context,
)

print(result.query)
```

### Example 3: Property Validation

```python
query = """
SELECT ?gene ?name
WHERE {
    ?gene a <http://purl.obolibrary.org/obo/SO_0000704> .
    ?gene <http://example.org/hasName> ?name .
}
"""

validation = generator.validate_query_against_ontology(query, ontology)

if validation['is_valid']:
    print("Query is valid!")
else:
    print("Errors found:")
    for error in validation['errors']:
        print(f"  - {error}")

    print("\nSuggestions:")
    for suggestion in validation['suggestions']:
        print(f"  - {suggestion}")
```

## API Reference

### OntologyGuidedGenerator

Main class for ontology-guided query generation.

**Methods:**

- `generate_query(user_query, context, include_explanation=True)`: Generate SPARQL query
- `expand_with_ols(term_label, ontology_id, strategy)`: Expand terms using OLS
- `suggest_properties_for_classes(class_uris, ontology_id, max_suggestions)`: Get property suggestions
- `validate_query_against_ontology(query, ontology_info)`: Validate query
- `load_ontology_from_ols(ontology_id, cache_path)`: Load ontology from OLS

### OntologyQueryContext

Context for query generation.

**Attributes:**

- `ontology_info`: Loaded ontology
- `target_classes`: Target classes
- `required_properties`: Required properties
- `expansion_strategy`: Expansion strategy
- `max_hops`: Maximum path hops
- `use_reasoning`: Enable reasoning
- `constraints`: OWL constraints

### PropertyPath

Represents a property path in SPARQL.

**Attributes:**

- `properties`: List of property URIs
- `path_type`: Type of path
- `label`: Human-readable label
- `confidence`: Confidence score
- `hops`: Number of hops

**Methods:**

- `to_sparql()`: Convert to SPARQL syntax

### QueryConstraint

Represents an OWL constraint.

**Attributes:**

- `constraint_type`: Type of constraint
- `property_uri`: Property URI
- `class_uri`: Class URI
- `value`: Constraint value
- `is_required`: Whether required

**Methods:**

- `to_sparql_filter()`: Convert to SPARQL FILTER

## Testing

Run tests:

```bash
pytest src/sparql_agent/query/test_ontology_generator.py -v
```

Run with coverage:

```bash
pytest src/sparql_agent/query/test_ontology_generator.py --cov=sparql_agent.query.ontology_generator --cov-report=html
```

## Best Practices

1. **Cache ontologies**: Load and cache frequently-used ontologies
2. **Limit expansion**: Use appropriate expansion strategies to avoid over-expansion
3. **Set max hops**: Limit property path hops for performance
4. **Validate queries**: Always validate generated queries before execution
5. **Use OLS integration**: Leverage OLS for up-to-date ontology information
6. **Handle errors gracefully**: Check validation results and handle errors

## Troubleshooting

### Issue: Slow query generation

**Solution:** Enable caching and limit expansion depth

```python
generator = OntologyGuidedGenerator(enable_caching=True)
context = OntologyQueryContext(
    expansion_strategy=ExpansionStrategy.CHILDREN,  # Not DESCENDANTS
    max_hops=2,  # Not 5+
)
```

### Issue: OLS connection errors

**Solution:** Use cached ontologies or local files

```python
# Load from local file instead of OLS
generator = create_ontology_generator(
    ontology_source="path/to/ontology.owl",
    enable_ols=False,
)
```

### Issue: No property paths found

**Solution:** Increase max_hops or check ontology completeness

```python
context = OntologyQueryContext(
    max_hops=5,  # Increase from 3
)
```

## Contributing

Contributions are welcome! Please:

1. Add tests for new features
2. Update documentation
3. Follow code style guidelines
4. Submit pull requests

## License

MIT License - see LICENSE file for details

## References

- [SPARQL 1.1 Property Paths](https://www.w3.org/TR/sparql11-query/#propertypaths)
- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [EBI OLS4 API](https://www.ebi.ac.uk/ols4/docs/api)
- [Gene Ontology](http://geneontology.org/)
- [OBO Foundry](http://www.obofoundry.org/)
