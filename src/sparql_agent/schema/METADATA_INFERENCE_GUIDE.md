# Metadata Inference - Complete Implementation Guide

## Overview

The `metadata_inference.py` module provides **automatic schema discovery and metadata inference** from SPARQL queries and RDF data using ML-inspired pattern recognition techniques. This implementation enables SPARQL agents to learn about dataset structures, relationships, and quality issues without requiring manual schema documentation.

## Key Features

### 1. **Schema Discovery**
- Automatic class detection from RDF types and URI patterns
- Property analysis with domain/range inference
- Implicit relationship discovery through property chains
- Class hierarchy detection from property patterns

### 2. **ML-Inspired Pattern Recognition**
- URI template extraction (numeric IDs, UUIDs, codes)
- Data type inference (URIs, literals, numerics, dates)
- Value pattern analysis
- Statistical learning from frequencies

### 3. **Constraint Detection**
- Cardinality inference (1:1, 1:N, N:1, N:N)
- Functional property detection
- Inverse functional property identification
- Domain/range constraint mining

### 4. **Query Pattern Learning**
- SPARQL query structure analysis
- Type inference from query patterns
- Relationship discovery from joins
- Usage statistics tracking

### 5. **Data Quality Analysis**
- Incomplete data detection
- Type inconsistency identification
- Outlier detection for numeric properties
- Coverage analysis

### 6. **Statistical Analysis**
- Min/max/average for numeric properties
- Value distribution analysis
- Property and class usage metrics
- Quality scoring

## Core Classes

### MetadataInferencer

Main inference engine that coordinates all analysis processes.

**Constructor:**
```python
MetadataInferencer(min_confidence=0.7, max_samples=1000)
```

**Key Methods:**

- `analyze_triple(subject, predicate, object, subject_type=None, object_type=None)` - Analyze single triple
- `analyze_query(query, results=None)` - Learn from SPARQL queries
- `analyze_sample_data(triples, type_map=None)` - Analyze dataset sample
- `get_metadata()` - Get complete inferred metadata
- `get_property_info(uri)` - Get property metadata
- `get_class_info(uri)` - Get class metadata
- `get_relationships_for_class(uri)` - Get class relationships
- `generate_summary_report()` - Generate human-readable report

### Data Structures

#### InferredMetadata
Complete metadata container with:
- `classes: Dict[str, ClassMetadata]` - Discovered classes
- `properties: Dict[str, PropertyMetadata]` - Discovered properties
- `uri_patterns: List[URIPattern]` - URI templates
- `relationships: List[Relationship]` - Implicit relationships
- `namespaces: Dict[str, str]` - Namespace mappings
- `quality_issues: List[DataQualityIssue]` - Quality problems
- `statistics: Dict[str, Any]` - Overall statistics

#### PropertyMetadata
Property-specific metadata:
- `uri: str` - Property URI
- `usage_count: int` - Number of uses
- `domains: Counter` - Subject types
- `ranges: Counter` - Object types
- `data_types: Counter` - Value data types
- `cardinality: CardinalityType` - Relationship cardinality
- `is_functional: bool` - Single value per subject
- `is_inverse_functional: bool` - Unique identifier property
- `sample_values: List` - Example values
- `value_patterns: Set[str]` - URI patterns
- `min_value, max_value, avg_value` - Numeric statistics

#### ClassMetadata
Class-specific metadata:
- `uri: str` - Class URI
- `instance_count: int` - Number of instances
- `properties: Set[str]` - Used properties
- `super_classes, sub_classes: Set[str]` - Hierarchy
- `sample_instances: List[str]` - Example instances
- `uri_patterns: Set[str]` - Instance URI patterns

#### URIPattern
Discovered URI template:
- `pattern: str` - Template with placeholders
- `regex: str` - Regular expression
- `examples: List[str]` - Example URIs
- `frequency: int` - Occurrence count
- `associated_types: Set[str]` - Related classes

#### Relationship
Implicit relationship:
- `subject_type: str` - Source class
- `predicate: str` - Connecting property
- `object_type: str` - Target class
- `confidence: float` - Confidence score
- `examples: List[Tuple]` - Example triples

#### DataQualityIssue
Quality problem description:
- `issue_type: str` - Type of issue
- `severity: str` - "low", "medium", "high"
- `description: str` - Human-readable description
- `affected_properties: List[str]` - Problem properties
- `sample_cases: List[str]` - Examples
- `recommendation: str` - Fix suggestion

## Usage Examples

### Example 1: Basic Triple Analysis

```python
from metadata_inference import MetadataInferencer

inferencer = MetadataInferencer()

triples = [
    ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/name", "Alice"),
    ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/age", "30"),
    ("http://example.org/person/2", "http://xmlns.com/foaf/0.1/name", "Bob"),
    ("http://example.org/person/2", "http://xmlns.com/foaf/0.1/age", "25"),
]

inferencer.analyze_sample_data(triples)

# Access metadata
for prop_uri, prop_meta in inferencer.metadata.properties.items():
    print(f"{prop_uri}: {prop_meta.usage_count} uses")
    print(f"  Data Types: {list(prop_meta.data_types.keys())}")
```

### Example 2: Query Pattern Learning

```python
query = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT ?name ?email WHERE {
    ?person a foaf:Person .
    ?person foaf:name ?name .
    ?person foaf:email ?email .
}
"""

results = [
    {"name": "Alice", "email": "alice@example.org"},
    {"name": "Bob", "email": "bob@example.org"},
]

inferencer.analyze_query(query, results)

# Check discovered relationships
for rel in inferencer.metadata.relationships:
    print(f"{rel.subject_type} --[{rel.predicate}]--> {rel.object_type}")
    print(f"  Confidence: {rel.confidence:.2f}")
```

### Example 3: URI Pattern Discovery

```python
triples = [
    ("http://example.org/person/001", "foaf:name", "Alice"),
    ("http://example.org/person/002", "foaf:name", "Bob"),
    ("http://example.org/item/550e8400-e29b-41d4-a716-446655440000", "dc:title", "Item A"),
]

inferencer.analyze_sample_data(triples)

# View discovered patterns
for pattern in inferencer.metadata.uri_patterns:
    print(f"Pattern: {pattern.pattern}")
    print(f"  Regex: {pattern.regex}")
    print(f"  Frequency: {pattern.frequency}")
```

### Example 4: Comprehensive Analysis with Report

```python
# Include type information
type_map = {
    "http://example.org/person/1": ["http://xmlns.com/foaf/0.1/Person"],
    "http://example.org/person/2": ["http://xmlns.com/foaf/0.1/Person"],
}

inferencer.analyze_sample_data(triples, type_map)

# Generate full report
report = inferencer.generate_summary_report()
print(report)
```

### Example 5: Property Analysis

```python
# Get detailed property info
prop_meta = inferencer.get_property_info("http://xmlns.com/foaf/0.1/name")

print(f"Property: {prop_meta.uri}")
print(f"  Usage: {prop_meta.usage_count}")
print(f"  Domains: {list(prop_meta.domains.keys())}")
print(f"  Ranges: {list(prop_meta.ranges.keys())}")
print(f"  Cardinality: {prop_meta.cardinality.value if prop_meta.cardinality else 'unknown'}")
print(f"  Functional: {prop_meta.is_functional}")
```

### Example 6: Data Quality Checking

```python
inferencer.analyze_sample_data(triples, type_map)

# Check quality issues
for issue in inferencer.metadata.quality_issues:
    print(f"[{issue.severity.upper()}] {issue.issue_type}")
    print(f"  {issue.description}")
    print(f"  Recommendation: {issue.recommendation}")
```

## Implementation Details

### Pattern Detection Algorithms

#### URI Pattern Extraction
```python
# Replaces specific components with placeholders
# http://example.org/person/123 -> http://example.org/person/{id}
pattern = re.sub(r'/\d+', '/{id}', uri)
pattern = re.sub(uuid_pattern, '{uuid}', pattern)
pattern = re.sub(r'/[a-zA-Z0-9]{7,}', '/{code}', pattern)
```

#### Data Type Inference
Uses cascading checks:
1. URI detection (scheme + netloc)
2. Integer parsing
3. Float parsing
4. Boolean keywords
5. Date/datetime regex patterns
6. Language-tagged strings
7. Default to string

#### Cardinality Inference
```python
# Compute averages
avg_objects_per_subject = mean([len(objs) for objs in objects_per_subject])
avg_subjects_per_object = mean([len(subjs) for subjs in subjects_per_object])

# Classify
if avg_objects ≤ 1.1 and avg_subjects ≤ 1.1: ONE_TO_ONE
elif avg_objects > 1.1 and avg_subjects ≤ 1.1: ONE_TO_MANY
elif avg_objects ≤ 1.1 and avg_subjects > 1.1: MANY_TO_ONE
else: MANY_TO_MANY
```

#### Functional Property Detection
```python
# Functional if >90% of subjects have exactly one value
functional_ratio = count(subject_counts == 1) / total_subjects
is_functional = functional_ratio > 0.9
```

#### Implicit Relationship Discovery
Finds transitive relationships through property chains:
```python
# If prop1's range overlaps with prop2's domain
range_domain_overlap = prop1.ranges ∩ prop2.domains
if overlap:
    create_relationship(class -> prop1 -> overlap -> prop2 -> target)
```

### Quality Issue Detection

#### Incomplete Data
```python
coverage = property_usage_count / class_instance_count
if coverage < 0.5:
    report_incomplete_data_issue()
```

#### Type Inconsistency
```python
if len(property.data_types) > 2:
    report_inconsistent_types_issue()
```

#### Outlier Detection
```python
# Using 3-sigma rule
outliers = [v for v in values if abs(v - mean) > 3 * std_dev]
if outliers:
    report_outlier_issue()
```

## ML-Inspired Techniques

### 1. Statistical Learning
- Frequency-based pattern detection
- Distribution analysis for anomalies
- Confidence scoring from occurrence counts

### 2. Pattern Recognition
- Regular expression generation from examples
- Template extraction through substitution
- Type inference from value patterns

### 3. Clustering
- Grouping similar URI patterns
- Identifying value distributions
- Class hierarchy inference

### 4. Feature Extraction
- Property co-occurrence analysis
- Path-based relationship discovery
- Domain/range constraint mining

## Performance Characteristics

- **Memory**: O(n) where n = number of unique properties/classes
- **Time**: O(m) where m = number of triples analyzed
- **Sampling**: Configurable max_samples limit (default: 1000)
- **Caching**: Type inferences and URI patterns cached
- **Incremental**: Supports incremental analysis

## Integration Points

### SPARQL Agents
```python
# Learn from queries
agent.on_query(query, results):
    inferencer.analyze_query(query, results)

# Use metadata for optimization
metadata = inferencer.get_metadata()
optimize_query_plan(query, metadata)
```

### Data Catalogs
```python
# Generate dataset documentation
datasets = extract_datasets()
for dataset in datasets:
    inferencer.analyze_sample_data(dataset.sample_triples)
    catalog.add_metadata(dataset.id, inferencer.get_metadata())
```

### ETL Pipelines
```python
# Validate transformations
source_metadata = infer_metadata(source_data)
target_metadata = infer_metadata(target_data)
validation = compare_metadata(source_metadata, target_metadata)
```

## Future Enhancements

1. **SHACL/ShEx Generation**: Export discovered constraints
2. **Graph Embeddings**: Use for type inference
3. **Active Learning**: Interactive schema refinement
4. **Federated Optimization**: Multi-endpoint query planning
5. **Streaming Analysis**: Real-time metadata updates
6. **Visualization**: Schema diagram generation
7. **Export Formats**: OWL, RDFS, Schema.org

## Testing

Run the test suite:
```bash
python test_metadata_inference.py
```

Run examples:
```bash
python metadata_examples.py
```

## References

- **VoID Vocabulary**: Dataset descriptions
- **SPARQL 1.1**: Query pattern analysis
- **OWL 2**: Property characteristics
- **SHACL**: Constraint validation
- **Schema.org**: Common vocabularies

## License

Part of the SPARQL Agent project. MIT License.
