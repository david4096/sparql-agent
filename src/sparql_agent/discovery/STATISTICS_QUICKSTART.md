# Statistics Module - Quick Start Guide

## 30-Second Overview

Collect comprehensive statistics about any SPARQL endpoint in 3 lines of code:

```python
from sparql_agent.discovery import collect_statistics

stats = collect_statistics("https://dbpedia.org/sparql")
print(stats.summary())
```

## Key Features

### 1. Basic Counts
- Total triples
- Distinct subjects, predicates, objects
- Execution time: ~5-10 seconds

### 2. Class Analysis
- Top N most common classes
- Instance counts per class
- Typed vs untyped resources

### 3. Property Analysis
- Top N most used properties
- Usage counts per property
- Property distribution

### 4. Literal Analysis
- Total literals
- Datatype distribution (xsd:string, xsd:integer, etc.)
- Language distribution (en, fr, de, etc.)

### 5. Namespace Detection
- Automatic namespace extraction
- Usage counts per namespace
- Identifies common vocabularies

### 6. Pattern Detection
- OWL ontologies
- SKOS vocabularies
- FOAF data
- Dublin Core metadata

### 7. Graph Support
- Named graph enumeration
- Triple counts per graph
- Optional (can be slow)

## Common Use Cases

### Use Case 1: Quick Endpoint Overview

```python
from sparql_agent.discovery import collect_statistics

stats = collect_statistics(
    endpoint_url="https://your-endpoint.org/sparql",
    timeout=30
)

print(f"Dataset size: {stats.total_triples:,} triples")
print(f"Top class: {stats.top_classes[0]}")
print(f"Collection time: {stats.collection_duration_seconds:.1f}s")
```

### Use Case 2: Detailed Class Analysis

```python
from sparql_agent.discovery import StatisticsCollector

collector = StatisticsCollector("https://your-endpoint.org/sparql")

# Get top 100 classes
classes = collector.get_top_classes(limit=100)

for cls, count in classes:
    print(f"{cls}: {count:,} instances")
```

### Use Case 3: Export to JSON

```python
import json
from sparql_agent.discovery import collect_statistics

stats = collect_statistics("https://your-endpoint.org/sparql")

with open('stats.json', 'w') as f:
    json.dump(stats.to_dict(), f, indent=2)
```

### Use Case 4: Compare Endpoints

```python
from sparql_agent.discovery import collect_statistics

endpoints = {
    'DBpedia': 'https://dbpedia.org/sparql',
    'Wikidata': 'https://query.wikidata.org/sparql',
}

for name, url in endpoints.items():
    stats = collect_statistics(url, timeout=30)
    print(f"{name}: {stats.total_triples:,} triples")
```

### Use Case 5: Progress Tracking

```python
from sparql_agent.discovery import collect_statistics

def show_progress(message, current=0, total=0):
    if total > 0:
        print(f"[{current}/{total}] {message}")
    else:
        print(f"[*] {message}")

stats = collect_statistics(
    endpoint_url="https://your-endpoint.org/sparql",
    progress_callback=show_progress
)
```

### Use Case 6: Incremental Collection

```python
from sparql_agent.discovery import StatisticsCollector

collector = StatisticsCollector(
    endpoint_url="https://your-endpoint.org/sparql",
    cache_results=True
)

# Step 1: Basic counts
print("Getting basic counts...")
triples = collector.count_total_triples()
subjects = collector.count_distinct_subjects()

# Step 2: Classes (cache is preserved)
print("Analyzing classes...")
classes = collector.get_top_classes(limit=50)

# Step 3: Properties
print("Analyzing properties...")
properties = collector.get_top_properties(limit=50)

# Cache info
print(f"Queries executed: {collector.get_cache_info()['query_count']}")
```

## Performance Tips

### For Large Datasets

1. **Increase timeout**: `timeout=120`
2. **Reduce limits**: `class_limit=20, property_limit=20`
3. **Skip graphs**: `include_graphs=False`
4. **Enable caching**: `cache_results=True`

### For Small Datasets

1. **Default settings work well**
2. **Can include graphs**: `include_graphs=True`
3. **Higher limits**: `class_limit=100, property_limit=100`

## Efficient Queries

The module uses optimized SPARQL queries:

```sparql
-- Total triples (efficient COUNT)
SELECT (COUNT(*) AS ?triples) WHERE { ?s ?p ?o }

-- Top classes (grouped and limited)
SELECT ?class (COUNT(?s) AS ?count)
WHERE { ?s a ?class }
GROUP BY ?class
ORDER BY DESC(?count)
LIMIT 20

-- Top properties (grouped and limited)
SELECT ?property (COUNT(*) AS ?count)
WHERE { ?s ?property ?o }
GROUP BY ?property
ORDER BY DESC(?count)
LIMIT 20
```

## Output Example

```
============================================================
SPARQL Dataset Statistics Summary
============================================================
Endpoint: https://dbpedia.org/sparql
Collected: 2024-10-02T20:00:00
Duration: 45.23s

Basic Counts:
  Total Triples: 1,234,567,890
  Distinct Subjects: 12,345,678
  Distinct Predicates: 1,234
  Distinct Objects: 23,456,789

Top 10 Classes:
  1. dbo:Person (1,234,567 instances)
  2. dbo:Place (987,654 instances)
  3. dbo:Work (765,432 instances)
  ...

Top 10 Properties:
  1. rdf:type (12,345,678 uses)
  2. rdfs:label (9,876,543 uses)
  3. dbo:abstract (7,654,321 uses)
  ...

Type Information:
  Typed Resources: 10,000,000
  Untyped Resources: 2,345,678

Literal Statistics:
  Total Literals: 50,000,000
  Datatype Distribution:
    string: 30,000,000
    integer: 10,000,000
    date: 5,000,000
  Language Distribution:
    en: 25,000,000
    de: 10,000,000
    fr: 8,000,000

Top Namespaces:
  http://dbpedia.org/ontology/: 15,000,000
  http://www.w3.org/1999/02/22-rdf-syntax-ns#: 12,000,000
  http://www.w3.org/2000/01/rdf-schema#: 10,000,000

Detected Patterns:
  has_owl_ontology: True
  owl_entity_count: 5,000
  has_foaf_data: True
  foaf_entity_count: 1,000,000

============================================================
```

## API Quick Reference

### Main Functions

```python
# Simple collection
collect_statistics(endpoint_url, timeout=30, include_graphs=False,
                   class_limit=20, property_limit=20, progress_callback=None)

# Create collector
collector = StatisticsCollector(endpoint_url, timeout=30, max_retries=3,
                                cache_results=True, progress_callback=None)
```

### Collector Methods

```python
# Counting
collector.count_total_triples()
collector.count_distinct_subjects()
collector.count_distinct_predicates()
collector.count_distinct_objects()
collector.count_typed_resources()
collector.count_untyped_resources()
collector.count_literals()

# Analysis
collector.get_top_classes(limit=20)
collector.get_top_properties(limit=20)
collector.get_datatype_distribution(limit=20)
collector.get_language_distribution(limit=20)
collector.analyze_namespace_usage()
collector.detect_patterns()

# Graphs
collector.get_named_graphs()
collector.get_graph_sizes(graphs)

# Full collection
collector.collect_all_statistics(include_graphs=False,
                                 class_limit=20,
                                 property_limit=20)

# Utilities
collector.clear_cache()
collector.get_cache_info()
```

### DatasetStatistics Attributes

```python
stats.total_triples
stats.distinct_subjects
stats.distinct_predicates
stats.distinct_objects
stats.top_classes          # [(uri, count), ...]
stats.top_properties       # [(uri, count), ...]
stats.typed_resources
stats.untyped_resources
stats.total_literals
stats.datatype_distribution   # {datatype: count}
stats.language_distribution   # {language: count}
stats.named_graphs
stats.graph_sizes          # {graph: count}
stats.namespace_usage      # {namespace: count}
stats.detected_patterns    # {pattern: value}
stats.endpoint_url
stats.collection_time
stats.collection_duration_seconds
```

### DatasetStatistics Methods

```python
stats.to_dict()    # Convert to dictionary
stats.summary()    # Generate text summary
```

## Error Handling

The module includes automatic retry and graceful degradation:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

collector = StatisticsCollector(
    endpoint_url=url,
    timeout=30,
    max_retries=3  # Retry failed queries up to 3 times
)

try:
    stats = collector.collect_all_statistics()
except Exception as e:
    print(f"Collection failed: {e}")
    # Partial results may still be in cache
    print(collector.get_cache_info())
```

## Command Line Usage

```bash
# Run directly
python -m sparql_agent.discovery.statistics https://dbpedia.org/sparql

# Run examples
cd src/sparql_agent/discovery/
python examples_statistics.py 1  # Basic statistics
python examples_statistics.py 2  # Detailed collection
python examples_statistics.py 3  # Literal analysis
# ... etc (see examples_statistics.py for all 8 examples)
```

## Files in This Module

- `statistics.py` - Main implementation (896 lines)
- `examples_statistics.py` - 8 usage examples (353 lines)
- `test_statistics.py` - Unit tests (359 lines)
- `README_statistics.md` - Comprehensive documentation
- `STATISTICS_QUICKSTART.md` - This quick start guide

## Next Steps

1. Try the examples: `python examples_statistics.py 1`
2. Read the full documentation: `README_statistics.md`
3. Run the tests: `python -m pytest test_statistics.py`
4. Collect statistics from your own endpoint

## Support

For issues or questions, see the main sparql-agent documentation.
