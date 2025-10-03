# SPARQL Dataset Metadata Inference

Automatic schema discovery and metadata inference from SPARQL queries and RDF data using ML-inspired pattern recognition.

## Overview

This module provides tools for working with VoID descriptions, which are RDF metadata about RDF datasets. VoID helps describe dataset statistics, structure, and relationships between datasets.

## Components

### 1. VoIDParser

Parses existing VoID descriptions from RDF data.

**Features:**
- Parse VoID Dataset descriptions
- Extract dataset metadata (title, description, homepage)
- Parse statistics (triples, entities, subjects, objects)
- Handle vocabulary usage
- Parse class and property partitions
- Support VoID Linksets (dataset relationships)
- Extract provenance information

**Usage:**

```python
from sparql_agent.schema import VoIDParser

# Parse from string
parser = VoIDParser()
datasets = parser.parse(rdf_data, format='turtle')

# Parse from file
datasets = parser.parse_from_file('void.ttl', format='turtle')

# Access dataset information
for dataset in datasets:
    print(f"Dataset: {dataset.title}")
    print(f"Triples: {dataset.triples:,}")
    print(f"Vocabularies: {dataset.vocabularies}")
```

### 2. VoIDExtractor

Queries SPARQL endpoints for VoID data or generates VoID descriptions from statistics.

**Features:**
- Query endpoints for existing VoID descriptions
- Generate VoID from endpoint statistics when missing
- Calculate dataset statistics (triple counts, distinct subjects/objects)
- Identify used vocabularies
- Generate class and property partitions
- Validate VoID consistency with actual data
- Export VoID to various RDF formats

**Usage:**

```python
from sparql_agent.schema import VoIDExtractor

# Initialize extractor
extractor = VoIDExtractor("https://example.org/sparql", timeout=30)

# Extract existing VoID or generate if missing
datasets = extractor.extract(generate_if_missing=True)

# Validate consistency
validation = extractor.validate_consistency(datasets[0])
print(f"Valid: {validation['valid']}")

# Export to RDF
turtle_output = extractor.export_to_rdf(datasets, format='turtle')
```

### 3. Data Classes

#### VoIDDataset

Represents a VoID dataset with comprehensive metadata:

```python
@dataclass
class VoIDDataset:
    uri: str
    title: Optional[str]
    description: Optional[str]
    homepage: Optional[str]
    sparql_endpoint: Optional[str]

    # Statistics
    triples: Optional[int]
    entities: Optional[int]
    distinct_subjects: Optional[int]
    distinct_objects: Optional[int]
    properties: Optional[int]
    classes: Optional[int]

    # Structure
    vocabularies: Set[str]
    class_partitions: Dict[str, int]
    property_partitions: Dict[str, int]

    # Relationships
    linksets: List[VoIDLinkset]

    # Provenance
    created: Optional[datetime]
    modified: Optional[datetime]
    creator: Optional[str]
    publisher: Optional[str]
    license: Optional[str]
```

#### VoIDLinkset

Represents connections between datasets:

```python
@dataclass
class VoIDLinkset:
    uri: str
    source_dataset: Optional[str]
    target_dataset: Optional[str]
    link_predicate: Optional[str]
    triples: Optional[int]
```

## SPARQL Queries

The extractor uses several optimized SPARQL queries:

### 1. Query for Existing VoID

```sparql
PREFIX void: <http://rdfs.org/ns/void#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT ?dataset ?property ?value WHERE {
    ?dataset a void:Dataset .
    ?dataset ?property ?value
}
```

### 2. Generate Statistics

```sparql
SELECT
    (COUNT(*) AS ?triples)
    (COUNT(DISTINCT ?s) AS ?subjects)
    (COUNT(DISTINCT ?o) AS ?objects)
WHERE {
    ?s ?p ?o
}
```

### 3. Class Partitions

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?class (COUNT(?s) AS ?count) WHERE {
    ?s rdf:type ?class
}
GROUP BY ?class
ORDER BY DESC(?count)
LIMIT 100
```

### 4. Property Partitions

```sparql
SELECT ?property (COUNT(*) AS ?count) WHERE {
    ?s ?property ?o
}
GROUP BY ?property
ORDER BY DESC(?count)
LIMIT 100
```

### 5. Vocabulary Discovery

```sparql
SELECT DISTINCT ?namespace WHERE {
    {
        ?s ?p ?o .
        BIND(REPLACE(STR(?p), "(.*[/#])[^/#]*$", "$1") AS ?namespace)
    }
    UNION
    {
        ?s a ?class .
        BIND(REPLACE(STR(?class), "(.*[/#])[^/#]*$", "$1") AS ?namespace)
    }
}
ORDER BY ?namespace
LIMIT 100
```

## Examples

### Example 1: Parse VoID from File

```python
from sparql_agent.schema import VoIDParser

void_data = """
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dcterms: <http://purl.org/dc/terms/> .

<http://example.org/dataset> a void:Dataset ;
    dcterms:title "Example Dataset" ;
    void:sparqlEndpoint <http://example.org/sparql> ;
    void:triples 1000000 ;
    void:vocabulary <http://xmlns.com/foaf/0.1/> .
"""

parser = VoIDParser()
datasets = parser.parse(void_data, format='turtle')

for dataset in datasets:
    print(f"Dataset: {dataset.title}")
    print(f"Endpoint: {dataset.sparql_endpoint}")
    print(f"Triples: {dataset.triples:,}")
```

### Example 2: Extract from Endpoint

```python
from sparql_agent.schema import VoIDExtractor

extractor = VoIDExtractor("https://dbpedia.org/sparql", timeout=30)
datasets = extractor.extract(generate_if_missing=True)

for dataset in datasets:
    print(f"Dataset: {dataset.uri}")
    print(f"Triples: {dataset.triples:,}")
    print(f"Classes: {dataset.classes}")
    print(f"Properties: {dataset.properties}")
```

### Example 3: Generate and Export VoID

```python
from sparql_agent.schema import VoIDExtractor

extractor = VoIDExtractor("https://query.wikidata.org/sparql", timeout=60)
datasets = extractor.extract(generate_if_missing=True)

# Export to Turtle
turtle_output = extractor.export_to_rdf(datasets, format='turtle')
print(turtle_output)

# Export to RDF/XML
xml_output = extractor.export_to_rdf(datasets, format='xml')
print(xml_output)
```

### Example 4: Validate Consistency

```python
from sparql_agent.schema import VoIDExtractor, VoIDParser

# Parse existing VoID
parser = VoIDParser()
datasets = parser.parse_from_file('dataset_void.ttl')

# Validate against actual endpoint
extractor = VoIDExtractor(datasets[0].sparql_endpoint)
validation = extractor.validate_consistency(datasets[0])

if validation['valid']:
    print("VoID description is consistent!")
else:
    print("Issues found:")
    for error in validation['errors']:
        print(f"  ERROR: {error}")
    for warning in validation['warnings']:
        print(f"  WARNING: {warning}")
```

### Example 5: Create VoID Programmatically

```python
from sparql_agent.schema import VoIDDataset, VoIDExtractor
from datetime import datetime

# Create dataset
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

# Export to RDF
extractor = VoIDExtractor("http://example.org/sparql")
rdf_output = extractor.export_to_rdf([dataset], format='turtle')
print(rdf_output)
```

## VoID Specification Coverage

This implementation covers the following VoID vocabulary terms:

### Core Classes
- `void:Dataset` - RDF dataset
- `void:Linkset` - Links between datasets

### Dataset Properties
- `void:sparqlEndpoint` - SPARQL endpoint URL
- `void:dataDump` - RDF dump download URL
- `void:exampleResource` - Example resource URI

### Statistics
- `void:triples` - Number of triples
- `void:entities` - Number of entities
- `void:distinctSubjects` - Distinct subject count
- `void:distinctObjects` - Distinct object count
- `void:properties` - Number of distinct properties
- `void:classes` - Number of distinct classes

### Partitions
- `void:classPartition` - Subset by class
- `void:propertyPartition` - Subset by property

### Vocabularies
- `void:vocabulary` - Used vocabulary namespace

### URI Patterns
- `void:uriSpace` - URI namespace
- `void:uriRegexPattern` - URI pattern regex

### Linksets
- `void:linkPredicate` - Linking predicate
- `void:subjectsTarget` - Source dataset
- `void:objectsTarget` - Target dataset

## Dependencies

- `rdflib` - RDF graph manipulation
- `SPARQLWrapper` - SPARQL endpoint interaction
- Standard library: `dataclasses`, `datetime`, `logging`, `urllib`

## Error Handling

The implementation includes comprehensive error handling:

- Query timeouts are configurable
- Failed queries log warnings and continue
- Invalid RDF data is caught and logged
- Network errors are handled gracefully
- Partial results are returned when possible

## Performance Considerations

For large endpoints:
- Statistics queries may timeout (adjust timeout parameter)
- Class/property partition queries limited to top 100 results
- Vocabulary discovery limited to 100 namespaces
- Consider querying VoID descriptions rather than generating

## References

- [VoID Specification](https://www.w3.org/TR/void/)
- [VoID Namespace](http://rdfs.org/ns/void#)
- [SPARQL 1.1 Query Language](https://www.w3.org/TR/sparql11-query/)
- [RDFLib Documentation](https://rdflib.readthedocs.io/)

## License

Part of the SPARQL Agent project.
