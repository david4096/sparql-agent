# Schema Inference Quick Start Guide

## 30-Second Overview

Automatically generate ShEx schemas from RDF data with statistical analysis and confidence scoring.

## Installation

```python
from sparql_agent.schema import SchemaInferencer, infer_schema_from_sparql
```

## Basic Usage (3 lines)

```python
inferencer = SchemaInferencer()
inferencer.add_triple(subject, predicate, obj, subject_type=type_uri)
result = inferencer.generate_schema()
```

## Common Patterns

### Pattern 1: From Manual Data

```python
from sparql_agent.schema import SchemaInferencer

# Create inferencer
inferencer = SchemaInferencer()

# Add data
inferencer.add_triple(
    subject="http://example.org/protein1",
    predicate="http://example.org/name",
    obj="Hemoglobin",
    subject_type="http://example.org/Protein"
)

# Generate
result = inferencer.generate_schema()
print(result.schema)
```

### Pattern 2: From SPARQL Endpoint

```python
from sparql_agent.schema import infer_schema_from_sparql

result = infer_schema_from_sparql(
    endpoint_url="https://sparql.uniprot.org/sparql",
    limit=1000
)
print(result.schema)
```

### Pattern 3: From Query Results

```python
from sparql_agent.schema import SchemaInferencer
from SPARQLWrapper import SPARQLWrapper, JSON

# Query endpoint
sparql = SPARQLWrapper("https://sparql.uniprot.org/sparql")
sparql.setQuery("""
    SELECT ?s ?type ?p ?o
    WHERE {
        ?s a ?type .
        ?s ?p ?o .
    }
    LIMIT 1000
""")
sparql.setReturnFormat(JSON)
results = sparql.query().convert()

# Generate schema
inferencer = SchemaInferencer()
inferencer.add_triples_from_query_result(results['results']['bindings'])
result = inferencer.generate_schema()
```

### Pattern 4: With Custom Settings

```python
inferencer = SchemaInferencer(
    min_confidence=0.8,          # Higher confidence threshold
    cardinality_threshold=0.95,  # Stricter cardinality inference
    optional_threshold=0.85,     # More properties required
    max_samples=500              # Limit memory usage
)
```

## What You Get

### Generated Schema
```python
result.schema  # ShExSchema object
str(result.schema)  # ShEx text format
```

### Statistics
```python
result.property_stats  # Dict[str, PropertyStats]
result.class_stats     # Dict[str, ClassStats]
```

### Quality Metrics
```python
result.quality_metrics.coverage              # % of data covered
result.quality_metrics.constraint_confidence # Average confidence
result.quality_metrics.completeness          # % of properties
result.quality_metrics.validation_errors     # List of issues
```

### Constraints with Confidence
```python
result.constraints  # Dict[str, List[InferredConstraint]]

for class_uri, constraints in result.constraints.items():
    for c in constraints:
        print(f"{c.constraint_type}: {c.value} (confidence: {c.confidence.value})")
```

## Cardinality Cheat Sheet

| Symbol | Meaning | When Used |
|--------|---------|-----------|
| (none) | Exactly one | 100% coverage, single value |
| `?` | Zero or one | <80% coverage, single value |
| `+` | One or more | 100% coverage, multiple values |
| `*` | Zero or more | <80% coverage, multiple values |

## Datatype Cheat Sheet

Auto-detected datatypes:
- `xsd:string` - String literals
- `xsd:integer` - Integers
- `xsd:float` - Floating point
- `xsd:boolean` - Boolean values
- `xsd:date` - Date values
- `xsd:dateTime` - Datetime values
- `IRI` - URI references
- `LITERAL` - Generic literals

## Common Use Cases

### Use Case 1: Quick Schema Prototype
```python
# Generate schema from sample data
inferencer = SchemaInferencer()
# ... add sample data ...
schema = inferencer.generate_schema().schema
print(schema)  # Use as starting point
```

### Use Case 2: Data Quality Check
```python
result = inferencer.generate_schema()
metrics = result.quality_metrics

if metrics.coverage < 0.9:
    print("Warning: Low coverage - missing types?")
if metrics.constraint_confidence < 0.7:
    print("Warning: Low confidence - inconsistent data?")
```

### Use Case 3: Documentation Generation
```python
result = inferencer.generate_schema()

# Generate documentation
for class_uri, stats in result.class_stats.items():
    print(f"Class: {class_uri}")
    print(f"  Instances: {stats.instance_count}")
    print(f"  Required properties: {len(stats.required_properties)}")
    print(f"  Optional properties: {len(stats.optional_properties)}")
```

## Tips & Tricks

### Tip 1: Better Results with More Data
```python
# ✗ Avoid: Too little data
inferencer.add_triple(...)  # Just 1 triple

# ✓ Better: Multiple instances
for i in range(100):  # At least 10-20 per class
    inferencer.add_triple(...)
```

### Tip 2: Include Type Information
```python
# ✗ Avoid: No types
inferencer.add_triple(subject, predicate, obj)

# ✓ Better: With types
inferencer.add_triple(subject, predicate, obj, subject_type=class_uri)
```

### Tip 3: Adjust Thresholds for Data Quality
```python
# Low quality data: relaxed thresholds
inferencer = SchemaInferencer(
    optional_threshold=0.6,  # More properties optional
    cardinality_threshold=0.7  # More lenient
)

# High quality data: strict thresholds
inferencer = SchemaInferencer(
    optional_threshold=0.9,  # More properties required
    cardinality_threshold=0.95  # Very strict
)
```

### Tip 4: Review Confidence Scores
```python
for class_uri, constraints in result.constraints.items():
    low_conf = [c for c in constraints
                if c.confidence.value in ['low', 'uncertain']]
    if low_conf:
        print(f"Review these constraints: {low_conf}")
```

## Troubleshooting

### Problem: Empty Schema
```python
# Cause: No type information
# Fix: Add rdf:type triples
inferencer.add_triple(subject, 'rdf:type', class_uri)
```

### Problem: All Properties Optional
```python
# Cause: Low coverage or threshold too high
# Fix: Lower optional_threshold
inferencer = SchemaInferencer(optional_threshold=0.6)
```

### Problem: Low Confidence Scores
```python
# Cause: Inconsistent data
# Fix: Clean data or accept lower confidence
inferencer = SchemaInferencer(min_confidence=0.5)
```

## Next Steps

- Read full [README](./SCHEMA_INFERENCE_README.md) for detailed API
- See [Examples](./schema_inference_examples.py) for complete scenarios
- Check [Implementation](./SCHEMA_INFERENCE_IMPLEMENTATION.md) for technical details
- Run [Tests](./test_schema_inference.py) to verify functionality

## Complete Example

```python
from sparql_agent.schema import SchemaInferencer

# Create inferencer with custom settings
inferencer = SchemaInferencer(
    min_confidence=0.8,
    optional_threshold=0.85
)

# Add data (typically from a loop over query results)
proteins = [
    ("http://ex.org/p1", "Hemoglobin", 64500),
    ("http://ex.org/p2", "Insulin", 5808),
    ("http://ex.org/p3", "Catalase", 240000),
]

for uri, name, mass in proteins:
    # Type
    inferencer.add_triple(uri, "rdf:type", "http://ex.org/Protein")

    # Properties
    inferencer.add_triple(
        uri, "http://ex.org/name", name,
        subject_type="http://ex.org/Protein",
        datatype="http://www.w3.org/2001/XMLSchema#string"
    )
    inferencer.add_triple(
        uri, "http://ex.org/mass", mass,
        subject_type="http://ex.org/Protein",
        datatype="http://www.w3.org/2001/XMLSchema#integer"
    )

# Generate schema
result = inferencer.generate_schema()

# Output
print("Generated Schema:")
print("=" * 60)
print(result.schema)

print("\nQuality Metrics:")
print(f"  Coverage: {result.quality_metrics.coverage:.1%}")
print(f"  Confidence: {result.quality_metrics.constraint_confidence:.1%}")
print(f"  Completeness: {result.quality_metrics.completeness:.1%}")

print("\nProperty Statistics:")
for prop_uri, stats in result.property_stats.items():
    print(f"  {prop_uri.split('/')[-1]}: {stats.usage_count} uses")
```

**Output:**
```
Generated Schema:
============================================================
PREFIX ex: <http://ex.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

<ProteinShape> {
  ex:name xsd:string,
  ex:mass xsd:integer
}

Quality Metrics:
  Coverage: 100.0%
  Confidence: 95.0%
  Completeness: 100.0%

Property Statistics:
  name: 3 uses
  mass: 3 uses
```
