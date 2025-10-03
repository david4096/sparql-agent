# SPARQL Discovery Module

This module provides comprehensive tools for discovering and analyzing SPARQL endpoint capabilities, including introspection queries, prefix extraction, and feature detection.

## Components

### 1. CapabilitiesDetector

The `CapabilitiesDetector` class discovers SPARQL endpoint features through introspection queries.

#### Features

- **SPARQL Version Detection**: Identifies whether the endpoint supports SPARQL 1.0 or 1.1
- **Named Graph Discovery**: Finds available named graphs in the endpoint
- **Namespace Discovery**: Extracts commonly used namespaces from endpoint data
- **Function Support**: Tests for availability of SPARQL functions (string, numeric, date/time, hash, aggregate)
- **Feature Detection**: Tests for SPARQL 1.1 features (BIND, EXISTS, MINUS, SERVICE, etc.)
- **Endpoint Statistics**: Gathers basic statistics about triple counts, subjects, and predicates

#### Usage Example

```python
from sparql_agent.discovery import CapabilitiesDetector

# Initialize detector
detector = CapabilitiesDetector(
    endpoint_url="https://query.wikidata.org/sparql",
    timeout=30
)

# Detect all capabilities at once
capabilities = detector.detect_all_capabilities()
print(f"SPARQL Version: {capabilities['sparql_version']}")
print(f"Named Graphs: {len(capabilities['named_graphs'])}")
print(f"Namespaces: {len(capabilities['namespaces'])}")

# Or detect specific capabilities
version = detector.detect_sparql_version()
graphs = detector.find_named_graphs(limit=10)
namespaces = detector.discover_namespaces(limit=100)
functions = detector.detect_supported_functions()
features = detector.detect_features()
stats = detector.get_endpoint_statistics()
```

#### Introspection Queries

The detector uses several introspection queries:

**Named Graph Discovery:**
```sparql
SELECT DISTINCT ?g
WHERE {
    GRAPH ?g { ?s ?p ?o }
}
LIMIT 100
```

**Namespace Discovery:**
```sparql
SELECT DISTINCT ?s ?p ?o
WHERE {
    ?s ?p ?o .
    FILTER(isIRI(?s) || isIRI(?p) || isIRI(?o))
}
LIMIT 1000
```

**Statistics:**
```sparql
SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o } LIMIT 1000000
SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE { ?s ?p ?o } LIMIT 1000000
SELECT (COUNT(DISTINCT ?p) AS ?count) WHERE { ?s ?p ?o } LIMIT 1000000
```

#### Detected Functions

The detector tests for the following SPARQL functions:

**String Functions:**
- STRLEN, SUBSTR, UCASE, LCASE
- STRSTARTS, STRENDS, CONTAINS
- CONCAT, REPLACE, REGEX

**Numeric Functions:**
- ABS, CEIL, FLOOR, ROUND, RAND

**Date/Time Functions:**
- NOW, YEAR, MONTH, DAY

**Hash Functions:**
- MD5, SHA1, SHA256

**Aggregate Functions:**
- COUNT, SUM, AVG, MIN, MAX, GROUP_CONCAT

**Other Functions:**
- BOUND, IF, COALESCE, UUID, STRUUID

### 2. PrefixExtractor

The `PrefixExtractor` class manages SPARQL prefix mappings and namespace handling.

#### Features

- **Common Prefix Library**: Includes 20+ well-known prefixes (rdf, rdfs, owl, foaf, schema, etc.)
- **Query Parsing**: Extracts PREFIX declarations from SPARQL queries
- **Automatic Generation**: Creates sensible prefix names from namespace URIs
- **URI Shortening**: Converts full URIs to prefixed form (e.g., `rdf:type`)
- **URI Expansion**: Expands prefixed URIs to full form
- **Conflict Resolution**: Handles prefix conflicts with multiple strategies
- **Declaration Generation**: Creates PREFIX declarations for SPARQL queries

#### Usage Example

```python
from sparql_agent.discovery import PrefixExtractor

# Initialize extractor
extractor = PrefixExtractor()

# Extract prefixes from a query
query = """
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>

SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }
"""
extracted = extractor.extract_from_query(query)

# Generate prefixes for discovered namespaces
namespaces = [
    "http://example.org/ontology/",
    "http://purl.org/vocab/bio/0.1/"
]
generated = extractor.extract_from_namespaces(namespaces)

# Shorten and expand URIs
shortened = extractor.shorten_uri("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
# Returns: "rdf:type"

expanded = extractor.expand_uri("rdf:type")
# Returns: "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

# Generate PREFIX declarations
declarations = extractor.get_prefix_declarations()
# Returns multi-line string with all PREFIX declarations

# Get summary
summary = extractor.get_mapping_summary()
```

#### Built-in Common Prefixes

```python
COMMON_PREFIXES = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'foaf': 'http://xmlns.com/foaf/0.1/',
    'schema': 'http://schema.org/',
    'dbo': 'http://dbpedia.org/ontology/',
    'dbr': 'http://dbpedia.org/resource/',
    'dbp': 'http://dbpedia.org/property/',
    'geo': 'http://www.w3.org/2003/01/geo/wgs84_pos#',
    'prov': 'http://www.w3.org/ns/prov#',
    'void': 'http://rdfs.org/ns/void#',
    'dcat': 'http://www.w3.org/ns/dcat#',
    'vcard': 'http://www.w3.org/2006/vcard/ns#',
    'time': 'http://www.w3.org/2006/time#',
    'org': 'http://www.w3.org/ns/org#',
    'qb': 'http://purl.org/linked-data/cube#',
}
```

#### Prefix Conflict Resolution

The `merge_mappings` method supports three strategies:

1. **keep_existing**: Keeps the current mapping, ignores new one
2. **overwrite**: Replaces existing mapping with new one
3. **rename**: Adds new mapping with numbered suffix (e.g., `prefix2`)

```python
other_mappings = {
    'ex': 'http://example.org/new/',
    'custom': 'http://custom.org/'
}

extractor.merge_mappings(other_mappings, strategy='rename')
```

## Combined Usage

Here's how to use both classes together to comprehensively analyze an endpoint:

```python
from sparql_agent.discovery import CapabilitiesDetector, PrefixExtractor

# Detect capabilities
detector = CapabilitiesDetector("https://query.wikidata.org/sparql")
capabilities = detector.detect_all_capabilities()

# Extract and generate prefixes
extractor = PrefixExtractor()
extractor.extract_from_namespaces(capabilities['namespaces'])

# Generate optimized query with discovered prefixes
declarations = extractor.get_prefix_declarations(
    namespaces=capabilities['namespaces'][:10]  # Top 10 most common
)

query = f"""
{declarations}

SELECT ?item ?label WHERE {{
    ?item wdt:P31 wd:Q5 .
    ?item rdfs:label ?label .
}}
LIMIT 10
"""
```

## Implementation Details

### Caching

`CapabilitiesDetector` caches results from `detect_all_capabilities()` to avoid redundant queries:

```python
# First call: runs all detection queries
capabilities = detector.detect_all_capabilities()

# Subsequent calls: returns cached results
capabilities = detector.detect_all_capabilities()  # No queries executed
```

### Error Handling

Both classes handle errors gracefully:

- Failed queries return empty results or fallback values
- Warnings are logged for failed operations
- Exceptions are caught and logged at debug level

### Logging

Both classes use Python's `logging` module:

```python
import logging

# Enable debug logging to see all operations
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger('sparql_agent.discovery')
logger.setLevel(logging.INFO)
```

## Dependencies

- `SPARQLWrapper`: For executing SPARQL queries
- `urllib.parse`: For URI parsing and validation
- `re`: For regular expression matching
- `logging`: For operation logging

## Performance Considerations

1. **Timeout Settings**: Adjust timeout based on endpoint responsiveness
2. **Limit Parameters**: Use appropriate limits for discovery queries
3. **Caching**: Take advantage of built-in caching for repeated operations
4. **Batch Operations**: Combine multiple detection operations when possible

## Testing

Run the example script to test the implementation:

```bash
cd /Users/david/git/sparql-agent
python examples/test_capabilities.py
```

This will test:
- Prefix extraction from queries
- Namespace-based prefix generation
- URI shortening and expansion
- Live endpoint capabilities detection (Wikidata, DBpedia)

## Future Enhancements

Potential improvements:

1. **Service Description**: Parse SPARQL Service Description documents
2. **VOID Analysis**: Extract metadata from VoID descriptions
3. **Property Paths**: Discover complex property path patterns
4. **Federated Queries**: Test SERVICE federation support
5. **Update Operations**: Detect SPARQL Update support
6. **Full-Text Search**: Test for full-text search extensions
7. **GeoSPARQL**: Detect geospatial query support
8. **Performance Profiling**: Measure query execution times

## License

MIT License
