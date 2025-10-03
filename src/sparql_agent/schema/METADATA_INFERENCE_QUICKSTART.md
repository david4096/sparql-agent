# Metadata Inference - Quick Start

## Installation
```python
from sparql_agent.schema import MetadataInferencer
```

## Basic Usage

### 1. Analyze Triples
```python
inferencer = MetadataInferencer()

triples = [
    ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/name", "Alice"),
    ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/age", "30"),
]

inferencer.analyze_sample_data(triples)
```

### 2. Get Property Info
```python
prop = inferencer.get_property_info("http://xmlns.com/foaf/0.1/name")
print(f"Usage: {prop.usage_count}")
print(f"Data Types: {list(prop.data_types.keys())}")
print(f"Functional: {prop.is_functional}")
```

### 3. Generate Report
```python
print(inferencer.generate_summary_report())
```

## Advanced Features

### Analyze Queries
```python
query = """
SELECT ?name WHERE {
    ?person foaf:name ?name .
}
"""
inferencer.analyze_query(query)
```

### With Type Information
```python
type_map = {
    "http://example.org/person/1": ["http://xmlns.com/foaf/0.1/Person"]
}
inferencer.analyze_sample_data(triples, type_map)
```

### Check Quality Issues
```python
for issue in inferencer.metadata.quality_issues:
    print(f"[{issue.severity}] {issue.description}")
    print(f"  Fix: {issue.recommendation}")
```

### Get Statistics
```python
stats = inferencer.metadata.statistics
print(f"Classes: {stats['total_classes']}")
print(f"Properties: {stats['total_properties']}")
print(f"Quality Issues: {stats['total_quality_issues']}")
```

## Key Classes

### MetadataInferencer
Main inference engine
- `analyze_triple()` - Single triple
- `analyze_query()` - SPARQL query
- `analyze_sample_data()` - Batch analysis
- `get_metadata()` - Get all metadata
- `generate_summary_report()` - Human-readable report

### InferredMetadata
Complete metadata container
- `properties` - Property metadata dict
- `classes` - Class metadata dict
- `uri_patterns` - URI templates
- `relationships` - Implicit relationships
- `quality_issues` - Quality problems
- `statistics` - Overall stats

### PropertyMetadata
Property information
- `usage_count` - Number of uses
- `domains` - Subject types
- `ranges` - Object types
- `data_types` - Value types
- `cardinality` - Relationship type
- `is_functional` - Single value?
- `min_value, max_value, avg_value` - Numeric stats

## Pattern Detection

### URI Patterns
```python
# Input:  http://example.org/person/123
# Output: http://example.org/person/{id}

for pattern in inferencer.metadata.uri_patterns:
    print(f"{pattern.pattern} (x{pattern.frequency})")
```

### Data Types
Automatically detected:
- URIs
- Integers, Floats
- Booleans
- Dates, DateTimes
- Language-tagged strings
- Plain strings

### Cardinality
- `1:1` - One-to-one
- `1:N` - One-to-many
- `N:1` - Many-to-one
- `N:N` - Many-to-many

## Configuration

```python
inferencer = MetadataInferencer(
    min_confidence=0.7,    # Minimum confidence for inferences
    max_samples=1000       # Max sample values per property
)
```

## Examples

### Example 1: Basic Analysis
```python
from sparql_agent.schema import MetadataInferencer

inferencer = MetadataInferencer()
triples = [("s", "p", "o")]
inferencer.analyze_sample_data(triples)
print(inferencer.generate_summary_report())
```

### Example 2: Property Details
```python
prop = inferencer.get_property_info("http://xmlns.com/foaf/0.1/age")
if prop.min_value:
    print(f"Age range: {prop.min_value} - {prop.max_value}")
    print(f"Average: {prop.avg_value:.1f}")
```

### Example 3: Class Analysis
```python
cls = inferencer.get_class_info("http://xmlns.com/foaf/0.1/Person")
print(f"Instances: {cls.instance_count}")
print(f"Properties: {len(cls.properties)}")
```

### Example 4: Relationships
```python
rels = inferencer.get_relationships_for_class("http://xmlns.com/foaf/0.1/Person")
for rel in rels:
    print(f"{rel.subject_type} --[{rel.predicate}]--> {rel.object_type}")
```

## Common Patterns

### Pattern 1: Dataset Documentation
```python
inferencer = MetadataInferencer()
inferencer.analyze_sample_data(sample_triples)
with open('dataset_metadata.txt', 'w') as f:
    f.write(inferencer.generate_summary_report())
```

### Pattern 2: Quality Monitoring
```python
inferencer.analyze_sample_data(new_data)
if inferencer.metadata.quality_issues:
    send_alert(inferencer.metadata.quality_issues)
```

### Pattern 3: Query Optimization
```python
# Learn from historical queries
for query in query_history:
    inferencer.analyze_query(query)

# Use metadata for optimization
metadata = inferencer.get_metadata()
optimize_query(new_query, metadata)
```

## Files

- `metadata_inference.py` - Core implementation
- `test_metadata_inference.py` - Test suite
- `metadata_examples.py` - Usage examples
- `METADATA_INFERENCE_GUIDE.md` - Full guide

## Performance

- Memory: O(properties + classes)
- Time: O(triples analyzed)
- Configurable sampling limit
- Incremental analysis support

## Quick Tips

1. **Start small**: Analyze a sample before full dataset
2. **Include types**: Provide type_map for better inference
3. **Check quality**: Review quality_issues regularly
4. **Incremental**: Analyze queries as they come
5. **Monitor**: Track statistics over time

## Next Steps

- Read `METADATA_INFERENCE_GUIDE.md` for details
- Run `metadata_examples.py` for demonstrations
- Check `test_metadata_inference.py` for test cases
- Integrate with your SPARQL agent
