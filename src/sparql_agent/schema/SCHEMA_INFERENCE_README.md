# Schema Inference Module

Intelligent ShEx schema generation from RDF data using statistical analysis and pattern recognition.

## Overview

The Schema Inference module automatically generates ShEx (Shape Expressions) schemas from RDF data by analyzing patterns, inferring constraints, and calculating quality metrics. It uses statistical methods to determine:

- Property cardinalities (required/optional, single/multi-valued)
- Value types and datatypes
- Numeric and string constraints
- Class hierarchies
- Data quality issues

## Features

### 1. **Intelligent Cardinality Inference**
   - Analyzes usage patterns to determine if properties are required or optional
   - Detects single-valued vs multi-valued properties
   - Provides confidence scores for each inference

### 2. **Statistical Property Analysis**
   - Tracks value types and datatypes
   - Calculates usage statistics
   - Identifies common patterns
   - Detects anomalies

### 3. **Smart Constraint Generation**
   - Infers numeric ranges (min/max)
   - Detects string patterns (email, URL, UUID, etc.)
   - Determines node kinds (IRI, Literal, etc.)
   - Generates value sets for enumerated types

### 4. **Shape Hierarchy Detection**
   - Identifies class inheritance relationships
   - Determines superclass/subclass relationships based on property overlap
   - Generates hierarchical shape definitions

### 5. **Quality Metrics**
   - Schema coverage (% of data covered)
   - Constraint confidence (reliability of inferences)
   - Completeness (% of properties captured)
   - Data consistency scores
   - Validation error detection

## Quick Start

### Basic Usage

```python
from sparql_agent.schema import SchemaInferencer

# Create inferencer
inferencer = SchemaInferencer()

# Add RDF triples
inferencer.add_triple(
    subject="http://example.org/protein1",
    predicate="http://example.org/name",
    obj="Hemoglobin",
    subject_type="http://example.org/Protein",
    datatype="http://www.w3.org/2001/XMLSchema#string"
)

# Generate schema
result = inferencer.generate_schema()

# Access the schema
print(result.schema)

# View quality metrics
print(f"Coverage: {result.quality_metrics.coverage:.1%}")
print(f"Confidence: {result.quality_metrics.constraint_confidence:.1%}")
```

### From SPARQL Endpoint

```python
from sparql_agent.schema import infer_schema_from_sparql

# Infer schema directly from endpoint
result = infer_schema_from_sparql(
    endpoint_url="https://sparql.uniprot.org/sparql",
    limit=1000,
    min_confidence=0.8
)

print(result.schema)
```

### With Custom Configuration

```python
inferencer = SchemaInferencer(
    min_confidence=0.8,           # Minimum confidence for constraints
    cardinality_threshold=0.9,    # Threshold for cardinality consistency
    optional_threshold=0.8,       # Threshold for required vs optional
    max_samples=1000              # Max sample values to collect
)
```

## API Reference

### SchemaInferencer

Main class for schema inference.

#### Constructor

```python
SchemaInferencer(
    min_confidence: float = 0.7,
    cardinality_threshold: float = 0.9,
    optional_threshold: float = 0.8,
    max_samples: int = 1000
)
```

**Parameters:**
- `min_confidence`: Minimum confidence threshold for including constraints
- `cardinality_threshold`: Threshold for inferring cardinality (% consistency)
- `optional_threshold`: Threshold for marking properties as optional
- `max_samples`: Maximum number of sample values to collect per property

#### Methods

##### add_triple()

Add a triple for analysis.

```python
add_triple(
    subject: str,
    predicate: str,
    obj: Any,
    subject_type: Optional[str] = None,
    object_type: Optional[str] = None,
    datatype: Optional[str] = None,
    language: Optional[str] = None
)
```

##### add_triples_from_query_result()

Add triples from SPARQL query result bindings.

```python
add_triples_from_query_result(bindings: List[Dict[str, Any]])
```

##### generate_schema()

Generate ShEx schema from collected data.

```python
generate_schema(
    base_uri: Optional[str] = None,
    include_examples: bool = True,
    generate_hierarchy: bool = True
) -> SchemaInferenceResult
```

**Returns:** `SchemaInferenceResult` containing:
- `schema`: Generated ShExSchema
- `property_stats`: Statistics for each property
- `class_stats`: Statistics for each class
- `constraints`: Inferred constraints with confidence
- `quality_metrics`: Quality assessment
- `warnings`: Any warnings during inference

### PropertyStats

Statistical information about a property.

**Attributes:**
- `uri`: Property URI
- `usage_count`: Total number of uses
- `subject_count`: Number of distinct subjects
- `object_count`: Number of distinct objects
- `value_types`: Counter of value types
- `datatypes`: Counter of datatypes
- `cardinality_info`: Cardinality statistics
- `sample_values`: Sample values

### ClassStats

Statistical information about a class.

**Attributes:**
- `uri`: Class URI
- `instance_count`: Number of instances
- `properties`: Set of properties used
- `required_properties`: Set of required properties
- `optional_properties`: Set of optional properties
- `property_usage`: Counter of property usage

### InferredConstraint

An inferred constraint with confidence metrics.

**Attributes:**
- `constraint_type`: Type of constraint
- `value`: Constraint value
- `confidence`: Confidence level (HIGH/MEDIUM/LOW/UNCERTAIN)
- `support`: Number of instances supporting constraint
- `counter_examples`: Number of violations
- `explanation`: Human-readable explanation

### QualityMetrics

Quality assessment of the inferred schema.

**Attributes:**
- `coverage`: % of data covered by schema
- `constraint_confidence`: Average constraint confidence
- `completeness`: % of properties captured
- `consistency`: % of data that validates
- `validation_errors`: List of quality issues

## Examples

### Example 1: Simple Protein Schema

```python
inferencer = SchemaInferencer()

# Add protein data
for i in range(3):
    protein_uri = f"http://example.org/protein{i}"

    inferencer.add_triple(protein_uri, "rdf:type", "http://example.org/Protein")
    inferencer.add_triple(
        protein_uri, "http://example.org/name", f"Protein {i}",
        subject_type="http://example.org/Protein"
    )

result = inferencer.generate_schema()
print(result.schema)
```

**Output:**
```
PREFIX example: <http://example.org/>

<ProteinShape> {
  example:name xsd:string,
}
```

### Example 2: Cardinality Inference

```python
inferencer = SchemaInferencer()

# Create data with different cardinalities
for i in range(10):
    protein_uri = f"http://example.org/protein{i}"

    # Required single value
    inferencer.add_triple(
        protein_uri, "http://example.org/name", f"Protein {i}",
        subject_type="http://example.org/Protein"
    )

    # Required multi-value
    for j in range(3):
        inferencer.add_triple(
            protein_uri, "http://example.org/synonym", f"Syn{j}",
            subject_type="http://example.org/Protein"
        )

    # Optional single value
    if i % 2 == 0:
        inferencer.add_triple(
            protein_uri, "http://example.org/description", f"Desc{i}",
            subject_type="http://example.org/Protein"
        )

result = inferencer.generate_schema()
```

**Output:**
```
<ProteinShape> {
  example:name xsd:string,           # EXACTLY_ONE
  example:synonym xsd:string+,       # ONE_OR_MORE
  example:description xsd:string?,   # ZERO_OR_ONE
}
```

### Example 3: Numeric Constraints

```python
inferencer = SchemaInferencer()

# Add numeric data with consistent range
for i in range(10):
    inferencer.add_triple(
        f"http://example.org/protein{i}",
        "http://example.org/mass",
        50000 + i * 1000,  # Range: 50000-59000
        subject_type="http://example.org/Protein",
        datatype="http://www.w3.org/2001/XMLSchema#integer"
    )

result = inferencer.generate_schema()

# Check inferred constraints
for constraint in result.constraints["http://example.org/Protein"]:
    if constraint.constraint_type == "min_inclusive":
        print(f"Min value: {constraint.value}")
        print(f"Confidence: {constraint.confidence.value}")
```

### Example 4: Quality Analysis

```python
inferencer = SchemaInferencer()

# Add data with varying completeness
for i in range(20):
    protein_uri = f"http://example.org/protein{i}"

    inferencer.add_triple(protein_uri, "rdf:type", "http://example.org/Protein")

    # 100% coverage
    inferencer.add_triple(
        protein_uri, "http://example.org/name", f"Protein {i}",
        subject_type="http://example.org/Protein"
    )

    # 80% coverage
    if i < 16:
        inferencer.add_triple(
            protein_uri, "http://example.org/organism", "http://example.org/org1",
            subject_type="http://example.org/Protein"
        )

    # 40% coverage
    if i < 8:
        inferencer.add_triple(
            protein_uri, "http://example.org/description", f"Desc {i}",
            subject_type="http://example.org/Protein"
        )

result = inferencer.generate_schema()

print(f"Coverage: {result.quality_metrics.coverage:.1%}")
print(f"Completeness: {result.quality_metrics.completeness:.1%}")
print(f"Constraint Confidence: {result.quality_metrics.constraint_confidence:.1%}")
```

### Example 5: Real-World UniProt Data

```python
from sparql_agent.schema import SchemaInferencer

inferencer = SchemaInferencer(min_confidence=0.8)

# Add realistic protein data
proteins = [
    {
        "uri": "http://purl.uniprot.org/uniprot/P69905",
        "name": "Hemoglobin subunit alpha",
        "organism": "http://purl.uniprot.org/taxonomy/9606",
        "mass": 15258,
        "sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF"
    },
    # ... more proteins
]

for protein in proteins:
    inferencer.add_triple(protein["uri"], "rdf:type",
                         "http://purl.uniprot.org/core/Protein")
    inferencer.add_triple(protein["uri"], "up:name", protein["name"],
                         subject_type="http://purl.uniprot.org/core/Protein")
    # ... more properties

result = inferencer.generate_schema(
    base_uri="http://purl.uniprot.org/shapes/"
)
```

## Cardinality Inference Logic

The module uses statistical analysis to infer cardinalities:

| Coverage | Avg Values/Subject | Inferred Cardinality |
|----------|-------------------|---------------------|
| ≥ 80%    | ≤ 1.2            | `1` (EXACTLY_ONE)   |
| ≥ 80%    | > 1.2            | `+` (ONE_OR_MORE)   |
| < 80%    | ≤ 1.2            | `?` (ZERO_OR_ONE)   |
| < 80%    | > 1.2            | `*` (ZERO_OR_MORE)  |

**Coverage** = (instances with property) / (total instances)

## Confidence Levels

Constraints are assigned confidence levels based on consistency:

- **HIGH** (>90%): Very consistent pattern
- **MEDIUM** (70-90%): Mostly consistent
- **LOW** (50-70%): Somewhat consistent
- **UNCERTAIN** (<50%): Inconsistent pattern

## Quality Metrics

The module calculates several quality metrics:

### Coverage
Percentage of instances that have a type assignment and are covered by the schema.

### Completeness
Percentage of discovered properties that are included in the generated shapes.

### Constraint Confidence
Average confidence level of all inferred constraints. Higher values indicate more reliable inferences.

### Consistency
Percentage of data that would validate against the generated schema.

## Advanced Features

### Pattern Detection

The module can detect common string patterns:

- Email addresses
- URLs
- UUIDs
- ISO dates
- Phone numbers
- Custom patterns

```python
# Automatically detects email pattern
for email in ["user1@example.com", "user2@example.com"]:
    inferencer.add_triple(
        f"http://example.org/person{i}",
        "http://example.org/email",
        email
    )
```

### Hierarchy Inference

Automatically detects class hierarchies based on property overlap:

```python
# Entity has properties: id
# Protein has properties: id, name, sequence

# Module infers: Protein is subclass of Entity
```

### Namespace Detection

Automatically extracts and suggests namespace prefixes:

```python
# Detects common namespaces
# http://www.w3.org/2001/XMLSchema# -> xsd
# http://purl.uniprot.org/core/ -> up
# http://xmlns.com/foaf/0.1/ -> foaf
```

## Integration with Existing Components

### With ShEx Parser

```python
from sparql_agent.schema import SchemaInferencer, ShExParser

# Generate schema
inferencer = SchemaInferencer()
# ... add data ...
result = inferencer.generate_schema()

# Parse and validate
parser = ShExParser()
parser.schema = result.schema

# Validate data
is_valid, errors = parser.validate_node(node_data, "<ProteinShape>")
```

### With Statistics Module

```python
from sparql_agent.discovery import StatisticsCollector
from sparql_agent.schema import SchemaInferencer

# Collect endpoint statistics
collector = StatisticsCollector("https://sparql.uniprot.org/sparql")
stats = collector.collect_all_statistics()

# Use for schema inference
inferencer = SchemaInferencer()
# ... use stats to guide inference ...
```

## Performance Considerations

- **Memory Usage**: Proportional to number of unique properties and sample values
- **Sample Limiting**: Use `max_samples` to limit memory for large datasets
- **Batch Processing**: Process data in batches for very large datasets
- **Caching**: Module caches namespace mappings and type inferences

## Limitations

1. **Sample Size**: Inferences improve with more data (recommended: 100+ instances per class)
2. **Heterogeneous Data**: Works best with structured, consistent data
3. **Complex Patterns**: May not detect very complex or domain-specific patterns
4. **Hierarchy Detection**: Heuristic-based, may not capture all relationships

## Best Practices

1. **Provide Type Information**: Include rdf:type triples for better inference
2. **Use Consistent Data**: More consistent data leads to higher confidence
3. **Set Appropriate Thresholds**: Adjust thresholds based on data quality
4. **Review Generated Schema**: Always review and refine generated schemas
5. **Validate Against Sample**: Test schema against sample data before deployment

## Troubleshooting

### Low Confidence Scores

**Problem**: Constraints have low confidence levels.

**Solutions:**
- Increase sample size
- Clean data to improve consistency
- Lower `min_confidence` threshold

### Missing Properties

**Problem**: Some properties not included in schema.

**Solutions:**
- Check `optional_threshold` setting
- Verify property has sufficient usage
- Review quality metrics

### Incorrect Cardinalities

**Problem**: Inferred cardinalities don't match expectations.

**Solutions:**
- Adjust `cardinality_threshold`
- Provide more representative sample data
- Check for data quality issues

## Contributing

Contributions welcome! Areas for improvement:

- Advanced pattern detection
- Machine learning integration
- Performance optimization
- Additional quality metrics
- Better hierarchy inference

## License

Part of the SPARQL Agent project. See main project license.

## See Also

- [ShEx Parser](./shex_parser.py) - ShEx parsing and validation
- [Statistics Module](../discovery/statistics.py) - Dataset statistics
- [Metadata Inference](./metadata_inference.py) - Metadata discovery
- [VoID Parser](./void_parser.py) - VoID vocabulary support
