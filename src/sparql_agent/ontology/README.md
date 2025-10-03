# Ontology Module

Comprehensive OWL ontology parsing with EBI OLS4 integration for life science knowledge graphs.

## Features

### OLS4 Integration (`ols_client.py`)

- **Search**: Search terms across 250+ ontologies
- **Browse**: Navigate term hierarchies (parents, children, ancestors, descendants)
- **Download**: Download OWL/OBO files from standard repositories
- **Metadata**: Access ontology metadata (versions, descriptions, statistics)
- **Common Ontologies**: Pre-configured support for GO, ChEBI, PRO, HPO, MONDO, and more

### OWL Parsing (`owl_parser.py`)

- **Load**: Parse OWL files using owlready2
- **Classes**: Extract class definitions with labels, comments, and restrictions
- **Properties**: Parse object, data, and annotation properties
- **Hierarchies**: Build and traverse class hierarchies
- **Restrictions**: Handle cardinality, value, and quantifier restrictions
- **Reasoning**: Optional Pellet reasoner integration
- **Search**: Find classes and properties by label or URI

## Installation

The ontology module requires additional dependencies:

```bash
pip install owlready2 pronto requests
```

These are included in the `sparql-agent` package by default.

## Quick Start

### Search Ontologies with OLS4

```python
from sparql_agent.ontology import OLSClient

# Initialize client
client = OLSClient()

# Search for terms
results = client.search("diabetes", ontology="mondo", limit=10)
for term in results:
    print(f"{term['label']} ({term['id']})")
    print(f"  {term['description']}")

# Get ontology information
go_info = client.get_ontology("go")
print(f"Gene Ontology has {go_info['num_terms']:,} terms")

# Browse hierarchy
parents = client.get_term_parents("go", "GO_0008150")
children = client.get_term_children("go", "GO_0008150")
```

### Download and Parse OWL Files

```python
from sparql_agent.ontology import OLSClient, OWLParser

# Download ontology
client = OLSClient()
owl_file = client.download_ontology("hp")  # Human Phenotype Ontology

# Parse with owlready2
parser = OWLParser(enable_reasoning=False)
ontology = parser.load_ontology(owl_file)

print(f"Loaded: {ontology.title}")
print(f"Classes: {len(ontology.classes)}")
print(f"Properties: {len(ontology.properties)}")

# Search for classes
matches = parser.search_classes("heart")
for owl_class in matches:
    print(f"  {owl_class.get_primary_label()}: {owl_class.uri}")
```

### Common Life Science Ontologies

```python
from sparql_agent.ontology import get_ontology_config, list_common_ontologies

# List all configured ontologies
for onto in list_common_ontologies():
    print(f"{onto['name']}: {onto['description']}")

# Get specific configuration
go_config = get_ontology_config("GO")
print(f"Download URL: {go_config['url']}")
print(f"Namespace: {go_config['namespace']}")
```

## Common Ontologies

Pre-configured life science ontologies:

| Key | Name | Description | Size |
|-----|------|-------------|------|
| GO | Gene Ontology | Gene function classification | ~500MB |
| CHEBI | Chemical Entities | Molecular entities of biological interest | ~100MB |
| PRO | Protein Ontology | Protein entities | ~30MB |
| HPO | Human Phenotype Ontology | Human phenotypic abnormalities | ~14MB |
| MONDO | Monarch Disease Ontology | Integrated disease ontology | ~25MB |
| UBERON | Uber Anatomy Ontology | Cross-species anatomy | ~40MB |
| CL | Cell Ontology | Cell types | ~12MB |
| SO | Sequence Ontology | Genomic features | ~8MB |
| EFO | Experimental Factor Ontology | Experimental variables | ~45MB |
| DOID | Disease Ontology | Human diseases | ~15MB |

## API Reference

### OLSClient

#### Methods

- `search(query, ontology=None, exact=False, limit=10)` - Search for terms
- `get_term(ontology, term_id)` - Get term details
- `get_ontology(ontology_id)` - Get ontology metadata
- `list_ontologies(limit=100)` - List available ontologies
- `get_term_parents(ontology, term_id)` - Get parent terms
- `get_term_children(ontology, term_id)` - Get child terms
- `get_term_ancestors(ontology, term_id)` - Get all ancestors
- `get_term_descendants(ontology, term_id)` - Get all descendants
- `download_ontology(ontology_id, output_path=None)` - Download OWL file
- `suggest_ontology(query, limit=5)` - Suggest relevant ontologies

### OWLParser

#### Methods

- `load_ontology(path, iri=None)` - Load OWL file
- `load_from_iri(iri)` - Load from URL
- `search_classes(query, case_sensitive=False)` - Search classes
- `get_class_hierarchy(class_uri, max_depth=-1)` - Get hierarchy
- `get_class_instances(class_uri)` - Get instances
- `close()` - Clean up resources

#### Properties

- `enable_reasoning` - Enable/disable Pellet reasoner
- `ontology` - Loaded owlready2 ontology object
- `world` - Owlready2 world instance

## Examples

See `example_usage.py` for comprehensive examples:

1. **OLS Search** - Search for terms using OLS4
2. **OLS Ontology Info** - Get ontology metadata
3. **OLS Hierarchy** - Browse term hierarchies
4. **Common Ontologies** - List pre-configured ontologies
5. **Download Ontology** - Download OWL files
6. **Parse OWL** - Parse ontologies with owlready2
7. **Search Classes** - Find classes in parsed ontologies
8. **Class Hierarchy** - Traverse class relationships
9. **Complete Integration** - Full workflow example

Run examples:

```bash
python -m sparql_agent.ontology.example_usage
```

## Architecture

### OLS4 Integration

The `OLSClient` provides a Pythonic interface to the EBI OLS4 REST API:

```
OLSClient
├── HTTP Session Management
├── Response Formatting
├── Error Handling
├── Download Management
└── Common Ontology Configs
```

### OWL Parsing

The `OWLParser` uses owlready2 for robust OWL parsing:

```
OWLParser
├── File Loading (local/remote)
├── Class Extraction
│   ├── Labels & Comments
│   ├── Hierarchy (subclass_of)
│   ├── Equivalence & Disjointness
│   └── Restrictions
├── Property Extraction
│   ├── Object Properties
│   ├── Data Properties
│   ├── Annotation Properties
│   └── Property Characteristics
├── Reasoning (Pellet)
└── Search & Query
```

## Integration with SPARQL Agent

The ontology module integrates with other SPARQL Agent components:

### Schema Discovery

```python
from sparql_agent.discovery import discover_schema
from sparql_agent.ontology import OLSClient, OWLParser

# Discover endpoint schema
schema = discover_schema(endpoint_url)

# Enrich with ontology information
client = OLSClient()
for class_uri in schema.classes:
    # Search for matching ontology terms
    results = client.search(class_uri.split("/")[-1])
    # Add ontology annotations to schema
```

### Query Generation

```python
from sparql_agent.ontology import get_ontology_config, OWLParser

# Load domain ontology
go_config = get_ontology_config("GO")
parser = OWLParser()
ontology = parser.load_from_iri(go_config['url'])

# Use ontology classes in query generation
for class_uri, owl_class in ontology.classes.items():
    # Generate SPARQL patterns using ontology structure
    label = owl_class.get_primary_label()
    parents = owl_class.subclass_of
```

## Performance Considerations

### Caching

- OLS responses are cached by the HTTP session
- Downloaded ontologies can be stored locally
- Parsed ontologies should be reused when possible

### Large Ontologies

Some ontologies are very large:

- **GO**: ~500MB, 50k+ terms, 10+ seconds to parse
- **ChEBI**: ~100MB, 100k+ terms, 5+ seconds to parse
- **MONDO**: ~25MB, 25k+ terms, 2+ seconds to parse

For large ontologies:

1. Download once and cache locally
2. Consider using OLS API instead of parsing
3. Disable reasoning for faster loading
4. Use specific term lookups rather than full parsing

### Memory Usage

- Full ontology parsing keeps entire model in memory
- Large ontologies can use 500MB+ RAM
- Close parser when done to free resources

```python
# Use context manager for automatic cleanup
with OWLParser() as parser:
    ontology = parser.load_ontology("large_ontology.owl")
    # Do work
# Automatically cleaned up
```

## Error Handling

The module defines specific exceptions:

```python
from sparql_agent.core.exceptions import (
    OntologyLoadError,      # Failed to load ontology
    OntologyParseError,     # Failed to parse ontology
    OntologyInconsistentError,  # Ontology is inconsistent
    OntologyNotFoundError,  # Ontology not found
)

try:
    parser = OWLParser(enable_reasoning=True)
    ontology = parser.load_ontology("myonto.owl")
except OntologyLoadError as e:
    print(f"Load failed: {e}")
except OntologyInconsistentError as e:
    print(f"Ontology is inconsistent: {e}")
```

## Testing

Run tests:

```bash
pytest src/sparql_agent/ontology/test_ontology.py -v
```

Tests include:

- OLS client methods
- Common ontology configurations
- OWL parser initialization
- Error handling
- Integration tests (network-dependent, skipped by default)

## Limitations

1. **OLS4 API**: Rate limits may apply for heavy usage
2. **Reasoning**: Pellet reasoner may fail on complex ontologies
3. **Large Files**: Some ontologies are very large and slow to parse
4. **Network**: Downloads require internet connection
5. **Dependencies**: Requires owlready2 and Java (for reasoning)

## Future Enhancements

- [ ] SPARQL query generation from ontology patterns
- [ ] Ontology-based query validation
- [ ] Automatic ontology selection for endpoints
- [ ] Incremental ontology loading
- [ ] Alternative reasoners (HermiT, ELK)
- [ ] OBO format parser
- [ ] Ontology diff and versioning
- [ ] Term recommendation for query building

## Resources

- [EBI OLS4 API](https://www.ebi.ac.uk/ols4/api/)
- [OBO Foundry](http://obofoundry.org/)
- [owlready2 Documentation](https://owlready2.readthedocs.io/)
- [OWL 2 Specification](https://www.w3.org/TR/owl2-overview/)
- [Gene Ontology](http://geneontology.org/)
- [ChEBI](https://www.ebi.ac.uk/chebi/)

## Contributing

Contributions welcome! Please ensure:

1. Tests pass: `pytest test_ontology.py`
2. Code formatted: `black *.py`
3. Type hints included
4. Documentation updated

## License

MIT License - see LICENSE file for details
