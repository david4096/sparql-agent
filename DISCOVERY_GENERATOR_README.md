# Discovery-Based SPARQL Query Generator

A comprehensive, production-ready system for generating accurate SPARQL queries using endpoint discovery results. This system combines rule-based vocabulary matching, incremental query building, and optional LLM integration to create queries that actually work with real endpoints.

## Key Features

### 1. Discovery-Driven Approach
- **Uses Real Endpoint Data**: Leverages actual capabilities discovered from endpoint introspection
- **Vocabulary Extraction**: Automatically extracts and indexes classes, properties, and namespaces
- **Pattern Recognition**: Identifies common query patterns specific to each endpoint
- **Feature Detection**: Validates query components against supported SPARQL features

### 2. Incremental Query Building
- **Step-by-Step Construction**: Builds queries component by component with validation at each step
- **Component Validation**: Ensures each piece uses correct vocabulary and syntax
- **Error Recovery**: Provides detailed error messages for invalid components
- **Query State Tracking**: Maintains complete state of query construction process

### 3. Rule-Based + LLM Hybrid
- **Rules for SPARQL Construction**: Uses deterministic rules for generating syntactically correct SPARQL
- **LLM for Understanding**: Optionally uses LLM only for natural language intent parsing
- **Fast and Reliable**: Rule-based construction ensures consistent, fast generation
- **No Hallucination**: Uses only discovered vocabulary, not LLM knowledge

### 4. Multi-Endpoint Support
- **Endpoint-Specific Patterns**: Recognizes and uses patterns for Wikidata, UniProt, DBpedia, etc.
- **Namespace Management**: Handles prefix declarations automatically
- **Feature Compatibility**: Adapts queries to endpoint capabilities

## Architecture

### Core Components

```
DiscoveryBasedQueryGenerator
├── DiscoveryKnowledge         # Knowledge base from endpoint discovery
│   ├── Namespaces             # Discovered namespace URIs
│   ├── Prefixes               # Prefix mappings
│   ├── Classes                # Available RDF classes
│   ├── Properties             # Available properties
│   ├── Features               # Supported SPARQL features
│   └── Patterns               # Common query patterns
│
├── VocabularyMatcher          # Matches NL terms to vocabulary
│   ├── Class Index            # Searchable class index
│   ├── Property Index         # Searchable property index
│   └── URI Shortening         # Converts URIs to prefixed form
│
├── QueryValidator             # Validates query components
│   ├── Prefix Validation      # Checks prefix declarations
│   ├── Class Validation       # Verifies class URIs
│   ├── Property Validation    # Verifies property URIs
│   ├── Feature Validation     # Checks SPARQL feature support
│   └── Syntax Validation      # Basic SPARQL syntax checks
│
└── QueryBuildState            # Tracks incremental building
    ├── Prefixes               # Accumulated PREFIX declarations
    ├── SELECT Variables       # Variables in SELECT clause
    ├── WHERE Clauses          # Triple patterns
    ├── Filters                # FILTER expressions
    ├── Optional Clauses       # OPTIONAL patterns
    └── Modifiers              # LIMIT, ORDER BY, etc.
```

## Usage Examples

### Basic Usage

```python
from discovery_query_generator import DiscoveryBasedQueryGenerator

# Create generator
generator = DiscoveryBasedQueryGenerator(fast_mode=True)

# Generate query (automatic endpoint discovery)
sparql, metadata = generator.generate(
    "Find 10 people born in Paris",
    "https://query.wikidata.org/sparql"
)

print(sparql)
# Outputs:
# PREFIX wd: <http://www.wikidata.org/entity/>
# PREFIX wdt: <http://www.wikidata.org/prop/direct/>
#
# SELECT *
# WHERE {
#   ?person wdt:P31 wd:Q5 .
#   ?person wdt:P19 wd:Q90 .
# }
# LIMIT 10
```

### With Pre-Cached Discovery Data

```python
from discovery_query_generator import (
    DiscoveryBasedQueryGenerator,
    DiscoveryKnowledge
)

# Create knowledge base from previous discovery
knowledge = DiscoveryKnowledge(
    endpoint_url="https://query.wikidata.org/sparql",
    namespaces=[
        "http://www.wikidata.org/entity/",
        "http://www.wikidata.org/prop/direct/",
    ],
    prefixes={
        "wd": "http://www.wikidata.org/entity/",
        "wdt": "http://www.wikidata.org/prop/direct/",
    },
    patterns={
        'human': '?person wdt:P31 wd:Q5',
    }
)

generator = DiscoveryBasedQueryGenerator()
generator.knowledge_cache[knowledge.endpoint_url] = knowledge

# Generate query using cached knowledge
sparql, metadata = generator.generate(
    "Find 5 humans",
    knowledge.endpoint_url
)
```

### Incremental Query Building

```python
from discovery_query_generator import QueryBuildState

# Build query step by step
state = QueryBuildState()

# Add prefixes
state.add_prefix("wd", "http://www.wikidata.org/entity/")
state.add_prefix("wdt", "http://www.wikidata.org/prop/direct/")

# Set variables
state.select_vars = ['?person', '?name']

# Add patterns
state.add_where_clause("?person wdt:P31 wd:Q5 .")
state.add_where_clause("?person rdfs:label ?name .")

# Add filters
state.add_filter('LANG(?name) = "en"')

# Set limit
state.limit = 10

# Build final query
query = state.build_query()
```

### Vocabulary Matching

```python
from discovery_query_generator import VocabularyMatcher, DiscoveryKnowledge

knowledge = DiscoveryKnowledge(
    endpoint_url="https://example.com/sparql",
    classes=[
        "http://xmlns.com/foaf/0.1/Person",
        "http://schema.org/Organization",
    ],
    properties=[
        "http://xmlns.com/foaf/0.1/name",
        "http://schema.org/birthDate",
    ]
)

matcher = VocabularyMatcher(knowledge)

# Find matching classes
classes = matcher.find_classes(["person", "human"], limit=3)
for class_uri, score in classes:
    print(f"{class_uri}: {score}")

# Find matching properties
properties = matcher.find_properties(["name", "label"], limit=3)
for prop_uri, score in properties:
    print(f"{prop_uri}: {score}")
```

### Query Validation

```python
from discovery_query_generator import QueryValidator, DiscoveryKnowledge

knowledge = DiscoveryKnowledge(
    endpoint_url="https://example.com/sparql",
    features={
        'BIND': True,
        'PROPERTY_PATHS': False,
    }
)

validator = QueryValidator(knowledge)

# Validate complete query
query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
is_valid, errors = validator.validate_query(query)

if not is_valid:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")

# Validate features
is_valid, error = validator.validate_feature('PROPERTY_PATHS')
if not is_valid:
    print(f"Feature not supported: {error}")
```

## Integration with Existing Systems

### With LLM Providers

```python
from sparql_agent.llm import create_anthropic_provider
from discovery_query_generator import DiscoveryBasedQueryGenerator

# Create LLM client
llm_client = create_anthropic_provider(api_key="your-key")

# Create generator with LLM for better intent parsing
generator = DiscoveryBasedQueryGenerator(
    llm_client=llm_client,
    fast_mode=False
)

# LLM will be used for parsing natural language intent
sparql, metadata = generator.generate(
    "Find all proteins from human that are involved in DNA repair",
    "https://sparql.uniprot.org/sparql"
)
```

### With Endpoint Discovery

```python
from sparql_agent.discovery.capabilities import CapabilitiesDetector
from discovery_query_generator import DiscoveryKnowledge

# Run full discovery
detector = CapabilitiesDetector(
    "https://query.wikidata.org/sparql",
    timeout=30,
    fast_mode=False
)

capabilities = detector.detect_all_capabilities()

# Convert to knowledge base
knowledge = DiscoveryKnowledge(
    endpoint_url=capabilities['endpoint_url'],
    namespaces=capabilities['namespaces'],
    features=capabilities['features'],
    functions=capabilities['supported_functions'],
    statistics=capabilities['statistics']
)

# Use for query generation
generator = DiscoveryBasedQueryGenerator()
generator.knowledge_cache[knowledge.endpoint_url] = knowledge
```

## Query Generation Metadata

Each generated query includes comprehensive metadata:

```python
sparql, metadata = generator.generate("Find 10 humans", endpoint_url)

# Metadata structure:
{
    'endpoint_url': str,              # Target endpoint
    'intent': {                       # Parsed intent
        'action': str,                # 'select', 'count', etc.
        'keywords': List[str],        # Extracted keywords
        'filters': List[str],         # Filter expressions
        'limit': int,                 # Result limit
        'order_by': Optional[str],    # Ordering
    },
    'validation_errors': List[str],   # Any validation issues
    'prefixes_used': int,             # Number of prefixes
    'where_clauses': int,             # Number of WHERE patterns
    'is_valid': bool,                 # Overall validity
}
```

## Endpoint-Specific Patterns

### Wikidata

```python
# Automatically recognizes Wikidata patterns
patterns = {
    'human': '?person wdt:P31 wd:Q5',
    'entity_type': '?entity wdt:P31 ?type',
    'label': '?entity rdfs:label ?label . FILTER(LANG(?label) = "en")',
    'label_service': 'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }',
}
```

### UniProt

```python
patterns = {
    'protein': '?protein a up:Protein',
    'human_protein': '?protein a up:Protein ; up:organism taxon:9606',
    'protein_name': '?protein up:recommendedName/up:fullName ?name',
    'reviewed': '?protein up:reviewed true',
}
```

### DBpedia

```python
patterns = {
    'resource': '?resource a dbo:Thing',
    'label': '?resource rdfs:label ?label . FILTER(LANG(?label) = "en")',
    'abstract': '?resource dbo:abstract ?abstract . FILTER(LANG(?abstract) = "en")',
}
```

## Performance

### Fast Mode

```python
# Fast mode: skips expensive discovery queries
generator = DiscoveryBasedQueryGenerator(fast_mode=True)

# Typical generation time: < 100ms (with cached discovery)
# Typical generation time: < 5s (with full discovery in fast mode)
```

### Full Mode

```python
# Full mode: complete endpoint analysis
generator = DiscoveryBasedQueryGenerator(fast_mode=False)

# Typical generation time: < 100ms (with cached discovery)
# Typical generation time: < 30s (with full discovery)
```

### Caching

```python
# Discovery results are cached automatically
generator = DiscoveryBasedQueryGenerator()

# First query: performs discovery (~5-30s)
sparql1, _ = generator.generate("Find 10 items", endpoint_url)

# Second query: uses cached discovery (~100ms)
sparql2, _ = generator.generate("Find 5 items", endpoint_url)
```

## Testing

Run the comprehensive test suite:

```bash
python3 test_discovery_generator.py
```

Test coverage includes:
- Vocabulary matching and indexing
- Query validation (syntax, features, vocabulary)
- Incremental query building
- Endpoint-specific pattern recognition
- Multiple endpoint support (Wikidata, UniProt)
- Metadata generation

## Advantages Over Pure LLM Generation

1. **No Hallucination**: Uses only actual endpoint vocabulary
2. **Consistent Syntax**: Rule-based construction ensures valid SPARQL
3. **Fast**: No LLM call needed for SPARQL construction
4. **Reliable**: Always produces syntactically correct queries
5. **Validated**: Each component checked against endpoint capabilities
6. **Predictable**: Same input always produces same query structure
7. **Debuggable**: Clear error messages for validation failures
8. **Scalable**: Can cache discovery data across queries

## Limitations and Future Work

### Current Limitations

1. **Simple Intent Parsing**: Without LLM, intent parsing is basic pattern matching
2. **No Complex Reasoning**: Cannot handle highly complex natural language
3. **Pattern-Based**: Relies on predefined patterns for complex queries
4. **Limited Class/Property Discovery**: Classes and properties must be provided or discovered

### Future Enhancements

1. **Automated Class/Property Discovery**: Infer classes/properties from sample data
2. **Query Template Learning**: Learn common patterns from query logs
3. **Multi-Step Query Planning**: Break complex queries into sub-queries
4. **Result Validation**: Execute queries and validate results
5. **Query Optimization**: Rewrite queries for better performance
6. **Federated Query Support**: Generate queries across multiple endpoints

## File Structure

```
/Users/david/git/sparql-agent/
├── discovery_query_generator.py      # Main implementation
├── test_discovery_generator.py       # Comprehensive test suite
├── DISCOVERY_GENERATOR_README.md     # This documentation
└── src/sparql_agent/
    ├── discovery/
    │   ├── capabilities.py           # Endpoint discovery
    │   └── connectivity.py           # Connection management
    └── llm/
        └── client.py                 # LLM integration
```

## API Reference

### DiscoveryBasedQueryGenerator

Main class for query generation.

**Methods:**
- `discover_endpoint(endpoint_url, force_refresh=False)` - Discover endpoint capabilities
- `parse_intent(natural_language, knowledge)` - Parse NL query intent
- `build_query_incremental(intent, knowledge)` - Build query step-by-step
- `generate(natural_language, endpoint_url, force_discovery=False)` - Generate complete query

### DiscoveryKnowledge

Knowledge base from endpoint discovery.

**Attributes:**
- `endpoint_url` - SPARQL endpoint URL
- `namespaces` - List of namespace URIs
- `prefixes` - Dict of prefix mappings
- `classes` - List of available classes
- `properties` - List of available properties
- `features` - Dict of supported SPARQL features
- `functions` - Dict of supported SPARQL functions
- `statistics` - Dict of dataset statistics
- `patterns` - Dict of common query patterns

### VocabularyMatcher

Matches natural language terms to endpoint vocabulary.

**Methods:**
- `find_classes(keywords, limit=5)` - Find matching classes
- `find_properties(keywords, limit=5)` - Find matching properties
- `shorten_uri(uri)` - Convert URI to prefixed form

### QueryValidator

Validates query components against discovery knowledge.

**Methods:**
- `validate_prefix(prefix, namespace)` - Validate prefix declaration
- `validate_class(class_uri)` - Validate class URI
- `validate_property(prop_uri)` - Validate property URI
- `validate_feature(feature)` - Validate SPARQL feature
- `validate_function(function)` - Validate SPARQL function
- `validate_query(query)` - Validate complete query

### QueryBuildState

State tracking during incremental query building.

**Methods:**
- `add_prefix(prefix, namespace)` - Add PREFIX declaration
- `add_where_clause(clause)` - Add WHERE pattern
- `add_filter(filter_expr)` - Add FILTER expression
- `add_optional(optional_pattern)` - Add OPTIONAL pattern
- `build_query()` - Build complete SPARQL query

## License

Part of the sparql-agent project.

## Contributing

Contributions welcome! Please ensure:
1. All tests pass: `python3 test_discovery_generator.py`
2. Code follows existing style
3. New features include tests
4. Documentation is updated

## Support

For issues, questions, or contributions, please refer to the main sparql-agent repository.
