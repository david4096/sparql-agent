# VoID Parser and Extractor Implementation

**Complete Implementation of VoID (Vocabulary of Interlinked Datasets) Support**

## Overview

This is a comprehensive implementation of VoID vocabulary parsing and extraction for SPARQL endpoints, providing both parsing of existing VoID descriptions and generation of VoID metadata from endpoint statistics.

## Files Created

### Core Implementation

1. **`void_parser.py`** (717 lines)
   - `VoIDParser` class - Parse VoID descriptions from RDF
   - `VoIDExtractor` class - Query and generate VoID from endpoints
   - `VoIDDataset` dataclass - Dataset representation
   - `VoIDLinkset` dataclass - Linkset representation
   - Complete SPARQL query templates
   - RDF export functionality

2. **`void_example.py`** (304 lines)
   - 6 comprehensive examples demonstrating all features
   - Examples for parsing, extracting, generating, validating
   - Production-ready code patterns
   - Proper error handling demonstrations

3. **`test_void_parser.py`** (341 lines)
   - Complete unit test suite
   - Tests for VoIDParser, VoIDDataset, VoIDLinkset, VoIDExtractor
   - Edge case coverage
   - pytest-compatible

4. **`README.md`** (381 lines)
   - Comprehensive documentation
   - API reference
   - SPARQL query examples
   - Usage patterns
   - VoID specification coverage

5. **`__init__.py`** (updated)
   - Package exports
   - Integration with other schema modules

## Features Implemented

### 1. VoIDParser Class

**Capabilities:**
- Parse VoID descriptions from RDF data (Turtle, RDF/XML, N3, etc.)
- Extract dataset metadata (title, description, homepage, endpoints)
- Parse comprehensive statistics:
  - Triple counts
  - Entity counts
  - Distinct subjects/objects
  - Property and class counts
- Handle vocabulary usage declarations
- Parse class and property partitions
- Support VoID Linksets (dataset interconnections)
- Extract provenance information (creator, publisher, license, dates)
- Parse URI patterns and example resources

**Key Methods:**
```python
parser = VoIDParser()
datasets = parser.parse(rdf_data, format='turtle')
datasets = parser.parse_from_file('void.ttl', format='turtle')
```

### 2. VoIDExtractor Class

**Capabilities:**
- Query SPARQL endpoints for existing VoID descriptions
- Generate VoID metadata from endpoint statistics
- Calculate comprehensive statistics:
  - Basic counts (triples, subjects, objects)
  - Property distribution
  - Class distribution
  - Top 100 classes by instance count
  - Top 100 properties by usage
  - Vocabulary namespace detection
- Validate VoID consistency with actual data
- Export VoID to multiple RDF formats (Turtle, RDF/XML, N3, etc.)

**SPARQL Queries Implemented:**
1. VoID Dataset Discovery
2. VoID Linkset Discovery
3. Basic Statistics (triples, subjects, objects)
4. Property Count
5. Class Count
6. Class Partitions (with counts)
7. Property Partitions (with counts)
8. Vocabulary Detection (namespace extraction)

**Key Methods:**
```python
extractor = VoIDExtractor(endpoint_url, timeout=30)
datasets = extractor.extract(generate_if_missing=True)
validation = extractor.validate_consistency(dataset)
rdf_output = extractor.export_to_rdf(datasets, format='turtle')
```

### 3. Data Classes

#### VoIDDataset
Comprehensive dataset representation with:
- Basic metadata (title, description, homepage, endpoint)
- Statistics (triples, entities, subjects, objects, properties, classes)
- Structure information (vocabularies, class/property partitions)
- Relationships (linksets)
- Technical details (URI patterns, examples, data dumps)
- Provenance (dates, creator, publisher, license)
- Conversion methods (to_dict)

#### VoIDLinkset
Linkset representation with:
- Source and target datasets
- Link predicates
- Triple counts
- Conversion methods (to_dict)

## VoID Specification Coverage

### ✓ Fully Implemented

**Core Classes:**
- `void:Dataset` - RDF dataset
- `void:Linkset` - Links between datasets

**Dataset Properties:**
- `void:sparqlEndpoint` - SPARQL endpoint URL
- `void:dataDump` - RDF dump download URL
- `void:exampleResource` - Example resource URI
- `void:rootResource` - Root resource URI

**Statistics:**
- `void:triples` - Number of triples
- `void:entities` - Number of entities
- `void:distinctSubjects` - Distinct subject count
- `void:distinctObjects` - Distinct object count
- `void:properties` - Number of distinct properties
- `void:classes` - Number of distinct classes

**Partitions:**
- `void:classPartition` - Subset by class
- `void:propertyPartition` - Subset by property

**Vocabularies:**
- `void:vocabulary` - Used vocabulary namespace

**URI Patterns:**
- `void:uriSpace` - URI namespace
- `void:uriRegexPattern` - URI pattern regex

**Linksets:**
- `void:linkPredicate` - Linking predicate
- `void:subjectsTarget` - Source dataset
- `void:objectsTarget` - Target dataset

**Metadata (via Dublin Core Terms):**
- `dcterms:title` - Dataset title
- `dcterms:description` - Dataset description
- `dcterms:creator` - Creator information
- `dcterms:publisher` - Publisher information
- `dcterms:created` - Creation date
- `dcterms:modified` - Modification date
- `dcterms:license` - License information

**Access (via FOAF):**
- `foaf:homepage` - Homepage URL

## Usage Examples

### Example 1: Parse Existing VoID

```python
from sparql_agent.schema import VoIDParser

parser = VoIDParser()
datasets = parser.parse_from_file('dataset_void.ttl')

for dataset in datasets:
    print(f"Dataset: {dataset.title}")
    print(f"Triples: {dataset.triples:,}")
    print(f"Vocabularies: {dataset.vocabularies}")
```

### Example 2: Extract from Endpoint

```python
from sparql_agent.schema import VoIDExtractor

extractor = VoIDExtractor("https://dbpedia.org/sparql", timeout=30)
datasets = extractor.extract(generate_if_missing=True)

for dataset in datasets:
    print(f"Dataset: {dataset.uri}")
    print(f"Triples: {dataset.triples:,}")
    print(f"Properties: {dataset.properties}")
    print(f"Classes: {dataset.classes}")
```

### Example 3: Generate and Export

```python
from sparql_agent.schema import VoIDExtractor

extractor = VoIDExtractor("https://example.org/sparql", timeout=60)
datasets = extractor.extract(generate_if_missing=True)

# Export to Turtle
turtle_output = extractor.export_to_rdf(datasets, format='turtle')
with open('void.ttl', 'w') as f:
    f.write(turtle_output)
```

### Example 4: Validate Consistency

```python
from sparql_agent.schema import VoIDExtractor, VoIDParser

# Parse existing VoID
parser = VoIDParser()
datasets = parser.parse_from_file('void.ttl')

# Validate against endpoint
extractor = VoIDExtractor(datasets[0].sparql_endpoint)
validation = extractor.validate_consistency(datasets[0])

print(f"Valid: {validation['valid']}")
for warning in validation['warnings']:
    print(f"WARNING: {warning}")
```

### Example 5: Create VoID Programmatically

```python
from sparql_agent.schema import VoIDDataset, VoIDExtractor
from datetime import datetime

dataset = VoIDDataset(
    uri="http://example.org/my-dataset",
    title="My Dataset",
    description="Custom RDF dataset",
    sparql_endpoint="http://example.org/sparql",
    triples=500000,
    entities=25000,
    distinct_subjects=25000,
    properties=75,
    classes=25,
    created=datetime.now(),
    license="http://creativecommons.org/licenses/by/4.0/"
)

dataset.vocabularies.add("http://xmlns.com/foaf/0.1/")
dataset.vocabularies.add("http://purl.org/dc/terms/")

extractor = VoIDExtractor("http://example.org/sparql")
rdf_output = extractor.export_to_rdf([dataset], format='turtle')
print(rdf_output)
```

### Example 6: Parse Linksets

```python
from sparql_agent.schema import VoIDParser

parser = VoIDParser()
datasets = parser.parse_from_file('linkset_void.ttl')

for dataset in datasets:
    print(f"Dataset: {dataset.title}")
    for linkset in dataset.linksets:
        print(f"  Linkset: {linkset.uri}")
        print(f"  Source: {linkset.source_dataset}")
        print(f"  Target: {linkset.target_dataset}")
        print(f"  Predicate: {linkset.link_predicate}")
        print(f"  Triples: {linkset.triples:,}")
```

## Testing

Comprehensive test suite with coverage for:
- Basic dataset parsing
- Statistics extraction
- Vocabulary handling
- Linkset parsing
- Provenance information
- Multiple datasets
- Data structure creation
- Dictionary conversion
- RDF export in multiple formats
- Namespace validation

**Run tests:**
```bash
cd src/sparql_agent/schema
python -m pytest test_void_parser.py -v
```

## Dependencies

Required packages:
- `rdflib` - RDF graph manipulation and parsing
- `SPARQLWrapper` - SPARQL endpoint interaction
- Python 3.8+ standard library

Install:
```bash
pip install rdflib SPARQLWrapper
```

## Performance Considerations

### For Large Endpoints

1. **Statistics Queries**: May timeout on very large endpoints (billions of triples)
   - Solution: Increase timeout parameter
   - Solution: Use LIMIT clauses in queries

2. **Partition Queries**: Limited to top 100 results by default
   - Rationale: Balance between completeness and performance
   - Customizable in query templates

3. **Vocabulary Detection**: Limited to 100 namespaces
   - Rationale: Most datasets use fewer than 100 vocabularies
   - Provides representative sample

### Optimization Tips

1. **Use Existing VoID**: Query for existing VoID first (`generate_if_missing=False`)
2. **Adjust Timeouts**: Set appropriate timeouts based on endpoint size
3. **Cache Results**: Save generated VoID to avoid regeneration
4. **Incremental Updates**: Generate VoID periodically, not on every query

## Error Handling

Robust error handling includes:
- Query timeout handling
- Network error recovery
- Invalid RDF data detection
- Missing data graceful degradation
- Partial result returns
- Comprehensive logging

## Integration

### With Other Modules

This implementation integrates with:
- `ontology_mapper.py` - Vocabulary detection and mapping
- `shex_parser.py` - Shape constraint validation
- `metadata_inference.py` - Automatic schema discovery

### Export to Package

```python
from sparql_agent.schema import (
    VoIDParser,
    VoIDExtractor,
    VoIDDataset,
    VoIDLinkset,
    VOID
)
```

## Production Readiness

This implementation is production-ready with:
- ✓ Comprehensive error handling
- ✓ Proper logging
- ✓ Type hints throughout
- ✓ Docstrings for all public APIs
- ✓ Unit test coverage
- ✓ Example code
- ✓ Documentation
- ✓ Performance optimizations
- ✓ Standard Python packaging

## Future Enhancements

Potential improvements:
1. Async query support for multiple endpoints
2. Incremental VoID updates
3. VoID diff/comparison tools
4. VoID visualization
5. VoID registry/catalog integration
6. More sophisticated vocabulary detection
7. Pattern-based URI space inference
8. Automatic linkset discovery

## References

- [W3C VoID Specification](https://www.w3.org/TR/void/)
- [VoID Namespace Documentation](http://rdfs.org/ns/void)
- [SPARQL 1.1 Query Language](https://www.w3.org/TR/sparql11-query/)
- [RDFLib Documentation](https://rdflib.readthedocs.io/)
- [Dublin Core Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)

## License

Part of the SPARQL Agent project.

## Author

Implementation completed as part of AGENT 3A task.

---

**Total Implementation:**
- 717 lines core implementation
- 304 lines examples
- 341 lines tests
- 381 lines documentation
- **1,743 lines total**
