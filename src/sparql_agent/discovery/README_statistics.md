# SPARQL Dataset Statistics Module

Comprehensive dataset statistics and introspection for SPARQL endpoints.

## Features

- **Efficient Counting**: Optimized queries for large datasets
- **Class & Property Analysis**: Discover the most common classes and properties
- **Literal Analysis**: Datatype and language distribution
- **Namespace Detection**: Identify and count namespace usage
- **Pattern Detection**: Automatically detect OWL, SKOS, FOAF, and Dublin Core patterns
- **Graph Support**: Analyze named graphs
- **Caching**: Built-in query result caching for performance
- **Progress Reporting**: Real-time progress callbacks
- **Error Handling**: Automatic retry with exponential backoff

## Installation

```bash
pip install SPARQLWrapper
```

## Quick Start

### Basic Usage

```python
from sparql_agent.discovery import collect_statistics

# Collect statistics from a SPARQL endpoint
stats = collect_statistics(
    endpoint_url="https://dbpedia.org/sparql",
    timeout=30,
    class_limit=20,
    property_limit=20
)

# Print summary
print(stats.summary())

# Access specific statistics
print(f"Total triples: {stats.total_triples:,}")
print(f"Top class: {stats.top_classes[0]}")
```

### With Progress Reporting

```python
from sparql_agent.discovery import collect_statistics

def progress_callback(message, current=0, total=0):
    if total > 0:
        print(f"[{current}/{total}] {message}")
    else:
        print(f"[*] {message}")

stats = collect_statistics(
    endpoint_url="https://dbpedia.org/sparql",
    progress_callback=progress_callback
)
```

### Advanced Usage with StatisticsCollector

```python
from sparql_agent.discovery import StatisticsCollector

# Create collector with custom settings
collector = StatisticsCollector(
    endpoint_url="https://dbpedia.org/sparql",
    timeout=60,
    max_retries=3,
    cache_results=True
)

# Collect specific statistics
total_triples = collector.count_total_triples()
top_classes = collector.get_top_classes(limit=50)
top_properties = collector.get_top_properties(limit=50)

# Analyze literals
datatype_dist = collector.get_datatype_distribution()
language_dist = collector.get_language_distribution()

# Detect patterns
patterns = collector.detect_patterns()

# Full collection
stats = collector.collect_all_statistics(
    include_graphs=True,
    class_limit=100,
    property_limit=100
)
```

## API Reference

### `DatasetStatistics`

Container for dataset statistics with the following attributes:

#### Basic Counts
- `total_triples`: Total number of triples
- `distinct_subjects`: Number of distinct subjects
- `distinct_predicates`: Number of distinct predicates
- `distinct_objects`: Number of distinct objects

#### Class Statistics
- `total_classes`: Number of distinct classes
- `top_classes`: List of (class_uri, count) tuples

#### Property Statistics
- `total_properties`: Number of distinct properties
- `top_properties`: List of (property_uri, count) tuples

#### Type Statistics
- `typed_resources`: Resources with at least one rdf:type
- `untyped_resources`: Resources without rdf:type

#### Literal Statistics
- `total_literals`: Total number of literals
- `datatype_distribution`: Dict mapping datatype to count
- `language_distribution`: Dict mapping language tag to count

#### Graph Statistics
- `named_graphs`: List of named graph URIs
- `graph_sizes`: Dict mapping graph URI to triple count

#### Namespace Statistics
- `namespace_usage`: Dict mapping namespace to usage count

#### Pattern Detection
- `detected_patterns`: Dict of detected patterns and their characteristics

#### Methods

```python
# Convert to dictionary
stats_dict = stats.to_dict()

# Generate human-readable summary
summary_text = stats.summary()
```

### `StatisticsCollector`

Main class for collecting statistics.

#### Constructor

```python
collector = StatisticsCollector(
    endpoint_url: str,           # SPARQL endpoint URL
    timeout: int = 30,           # Query timeout in seconds
    max_retries: int = 3,        # Maximum number of retries
    cache_results: bool = True,  # Enable query result caching
    progress_callback: Optional[callable] = None  # Progress callback
)
```

#### Methods

##### Counting Methods

```python
# Count total triples
total = collector.count_total_triples()

# Count distinct subjects/predicates/objects
subjects = collector.count_distinct_subjects()
predicates = collector.count_distinct_predicates()
objects = collector.count_distinct_objects()

# Count typed/untyped resources
typed = collector.count_typed_resources()
untyped = collector.count_untyped_resources()

# Count literals
literals = collector.count_literals()
```

##### Analysis Methods

```python
# Get top classes
classes = collector.get_top_classes(limit=20)
# Returns: [(class_uri, instance_count), ...]

# Get top properties
properties = collector.get_top_properties(limit=20)
# Returns: [(property_uri, usage_count), ...]

# Get datatype distribution
datatypes = collector.get_datatype_distribution(limit=20)
# Returns: {datatype_uri: count, ...}

# Get language distribution
languages = collector.get_language_distribution(limit=20)
# Returns: {language_tag: count, ...}

# Analyze namespace usage
namespaces = collector.analyze_namespace_usage()
# Returns: {namespace: count, ...}

# Detect patterns
patterns = collector.detect_patterns()
# Returns: {pattern_name: value, ...}
```

##### Graph Methods

```python
# Get named graphs
graphs = collector.get_named_graphs()
# Returns: [graph_uri, ...]

# Get graph sizes
sizes = collector.get_graph_sizes(graphs)
# Returns: {graph_uri: triple_count, ...}
```

##### Collection Methods

```python
# Collect all statistics
stats = collector.collect_all_statistics(
    include_graphs=False,    # Include graph analysis
    class_limit=20,          # Max classes to collect
    property_limit=20        # Max properties to collect
)
# Returns: DatasetStatistics object
```

##### Utility Methods

```python
# Clear cache
collector.clear_cache()

# Get cache information
cache_info = collector.get_cache_info()
# Returns: {
#     'cache_size': int,
#     'cache_keys': [str],
#     'query_count': int,
#     'failed_queries': int
# }
```

### `collect_statistics()`

Convenience function for quick statistics collection.

```python
stats = collect_statistics(
    endpoint_url: str,
    timeout: int = 30,
    include_graphs: bool = False,
    class_limit: int = 20,
    property_limit: int = 20,
    progress_callback: Optional[callable] = None
)
```

## SPARQL Queries Used

### Basic Counts

```sparql
# Total triples
SELECT (COUNT(*) AS ?triples) WHERE { ?s ?p ?o }

# Distinct subjects
SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE { ?s ?p ?o }

# Distinct predicates
SELECT (COUNT(DISTINCT ?p) AS ?count) WHERE { ?s ?p ?o }

# Distinct objects
SELECT (COUNT(DISTINCT ?o) AS ?count) WHERE { ?s ?p ?o }
```

### Top Classes

```sparql
SELECT ?class (COUNT(?s) AS ?count)
WHERE {
    ?s a ?class
}
GROUP BY ?class
ORDER BY DESC(?count)
LIMIT 20
```

### Top Properties

```sparql
SELECT ?property (COUNT(*) AS ?count)
WHERE {
    ?s ?property ?o
}
GROUP BY ?property
ORDER BY DESC(?count)
LIMIT 20
```

### Datatype Distribution

```sparql
SELECT ?datatype (COUNT(*) AS ?count)
WHERE {
    ?s ?p ?o
    FILTER(isLiteral(?o))
    BIND(DATATYPE(?o) AS ?datatype)
}
GROUP BY ?datatype
ORDER BY DESC(?count)
LIMIT 20
```

### Language Distribution

```sparql
SELECT ?lang (COUNT(*) AS ?count)
WHERE {
    ?s ?p ?o
    FILTER(isLiteral(?o))
    BIND(LANG(?o) AS ?lang)
    FILTER(?lang != "")
}
GROUP BY ?lang
ORDER BY DESC(?count)
LIMIT 20
```

## Performance Considerations

### For Large Datasets

1. **Use appropriate timeouts**: Large datasets may require longer timeouts
   ```python
   collector = StatisticsCollector(endpoint_url=url, timeout=120)
   ```

2. **Limit result sizes**: Use reasonable limits for class/property lists
   ```python
   stats = collect_statistics(
       endpoint_url=url,
       class_limit=50,    # Don't go too high
       property_limit=50
   )
   ```

3. **Skip graph analysis**: Graph analysis can be slow
   ```python
   stats = collect_statistics(endpoint_url=url, include_graphs=False)
   ```

4. **Enable caching**: Reuse results across multiple queries
   ```python
   collector = StatisticsCollector(endpoint_url=url, cache_results=True)
   ```

### Incremental Collection

For very large datasets, collect statistics incrementally:

```python
collector = StatisticsCollector(endpoint_url=url, cache_results=True)

# Phase 1: Basic counts
basic = {
    'triples': collector.count_total_triples(),
    'subjects': collector.count_distinct_subjects(),
}

# Phase 2: Classes (separate step)
classes = collector.get_top_classes(limit=100)

# Phase 3: Properties (separate step)
properties = collector.get_top_properties(limit=100)

# Cache is preserved between calls
```

## Pattern Detection

The module automatically detects common RDF patterns:

### OWL Ontology Patterns
- Detects OWL classes, object properties, and datatype properties
- Sets `has_owl_ontology: true` if found
- Provides `owl_entity_count`

### SKOS Vocabulary Patterns
- Detects SKOS concepts and hierarchies
- Sets `has_skos_vocabulary: true` if found
- Provides `skos_usage_count`

### FOAF Patterns
- Detects FOAF Person and Organization entities
- Sets `has_foaf_data: true` if found
- Provides `foaf_entity_count`

### Dublin Core Metadata
- Detects DC Terms and DC Elements
- Sets `has_dublin_core_metadata: true` if found
- Provides `dc_usage_count`

## Export Options

### JSON Export

```python
import json

stats = collect_statistics(endpoint_url=url)

# Export to JSON
with open('statistics.json', 'w') as f:
    json.dump(stats.to_dict(), f, indent=2)
```

### Text Summary Export

```python
stats = collect_statistics(endpoint_url=url)

# Export summary
with open('summary.txt', 'w') as f:
    f.write(stats.summary())
```

## Examples

See `examples_statistics.py` for comprehensive examples:

1. **Basic Statistics**: Simple collection and display
2. **Detailed Collection**: Step-by-step with caching
3. **Literal Analysis**: Datatype and language analysis
4. **Namespace Analysis**: Namespace usage patterns
5. **Pattern Detection**: Automatic pattern detection
6. **Full Export**: Complete statistics with JSON export
7. **Endpoint Comparison**: Compare multiple endpoints
8. **Incremental Analysis**: Checkpoint-based collection

Run examples:

```bash
python examples_statistics.py 1  # Run example 1
python examples_statistics.py 2  # Run example 2
# etc.
```

## Error Handling

The module includes robust error handling:

- **Automatic Retry**: Failed queries are retried with exponential backoff
- **Timeout Handling**: Configurable timeouts for slow endpoints
- **Graceful Degradation**: Continues collection even if some queries fail
- **Error Logging**: Detailed logging of failures

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

collector = StatisticsCollector(
    endpoint_url=url,
    timeout=30,
    max_retries=3  # Retry up to 3 times
)
```

## Command-Line Usage

Run directly from command line:

```bash
# Basic usage
python -m sparql_agent.discovery.statistics https://dbpedia.org/sparql

# With full graph analysis
python -m sparql_agent.discovery.statistics https://dbpedia.org/sparql --include-graphs

# Output is printed and saved to dataset_statistics.json
```

## Limitations

- **COUNT Queries**: Some endpoints don't support COUNT(*) on very large datasets
- **DISTINCT Queries**: Can be slow on large datasets
- **Graph Analysis**: Enumerating all graphs can be very slow
- **Timeout Issues**: Some queries may timeout on large datasets

## Best Practices

1. **Start Small**: Begin with small limits and increase as needed
2. **Use Caching**: Enable caching for repeated queries
3. **Monitor Progress**: Use progress callbacks for long operations
4. **Handle Errors**: Check for failed queries in results
5. **Export Results**: Save statistics for later analysis
6. **Incremental Collection**: For large datasets, collect in phases

## License

Part of the sparql-agent project.
