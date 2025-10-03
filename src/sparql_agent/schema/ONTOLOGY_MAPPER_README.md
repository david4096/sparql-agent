# Ontology Mapper and Vocabulary Detector

Comprehensive ontology mapping and vocabulary detection system for SPARQL Agent.

## Overview

This module provides sophisticated ontology mapping capabilities including:

- **Vocabulary Mapping**: Map between different vocabularies (FOAF, Dublin Core, Schema.org, etc.)
- **owl:sameAs Handling**: Track and resolve owl:sameAs relationships between URIs
- **URI Resolution**: Normalize and resolve URI variations to canonical forms
- **Vocabulary Detection**: Identify ontologies used in RDF data and SPARQL queries
- **Life Science Support**: Specialized support for UniProt, Gene Ontology, OBO Foundry, and FAIR vocabularies
- **LOV Integration**: Cross-reference with Linked Open Vocabularies
- **Statistics & Analytics**: Extract vocabulary usage statistics and detect misuse

## Architecture

### Core Classes

#### 1. OntologyMapper

The main class for vocabulary mapping and URI resolution.

**Key Features:**
- Pre-loaded with 30+ standard vocabularies
- Support for web vocabularies (FOAF, Schema.org, Dublin Core)
- Life science ontologies (UniProt, GO, CHEBI, HP, MONDO, etc.)
- FAIR vocabulary support
- owl:sameAs relationship graph
- URI normalization and resolution
- LOV URL lookup

**Methods:**
```python
# Vocabulary lookup
get_vocabulary_by_prefix(prefix: str) -> Optional[VocabularyInfo]
get_vocabulary_by_namespace(namespace: str) -> Optional[VocabularyInfo]
get_vocabulary_for_uri(uri: str) -> Optional[VocabularyInfo]

# URI operations
extract_prefix_from_uri(uri: str) -> Optional[Tuple[str, str]]
normalize_uri(uri: str) -> str
resolve_uri(uri: str, prefer_namespace: Optional[str] = None) -> str

# Mapping operations
add_same_as_mapping(uri1: str, uri2: str)
get_equivalent_uris(uri: str) -> Set[str]
add_mapping(mapping: OntologyMapping)

# Search and discovery
search_vocabularies(query: str) -> List[VocabularyInfo]
list_vocabularies_by_domain(domain: OntologyDomain) -> List[VocabularyInfo]
get_lov_url(prefix: str) -> Optional[str]
```

#### 2. VocabularyDetector

Analyzes vocabulary usage in RDF data and SPARQL queries.

**Key Features:**
- Term frequency analysis
- Property/class/individual counting
- Vocabulary violation detection
- Domain-based grouping
- Comprehensive usage reports

**Methods:**
```python
# Analysis
analyze_uri(uri: str, context: str = "unknown")
analyze_triple(subject: str, predicate: str, obj: str)

# Statistics
get_vocabulary_statistics() -> Dict[str, VocabularyUsage]
get_top_vocabularies(n: int = 10) -> List[Tuple[str, int]]
identify_ontologies() -> Dict[OntologyDomain, List[str]]

# Reporting
get_coverage_report() -> str
export_statistics() -> Dict
detect_vocabulary_violations() -> Dict[str, List[str]]
```

#### 3. Supporting Data Classes

- **VocabularyInfo**: Metadata about a vocabulary/ontology
- **VocabularyUsage**: Statistics about vocabulary usage
- **OntologyMapping**: Represents mappings between ontology terms
- **OntologyDomain**: Enum for ontology domains (general, life_sciences, bibliographic, web, etc.)

## Supported Vocabularies

### Standard Web & Semantic Web Vocabularies

| Prefix | Name | Namespace |
|--------|------|-----------|
| foaf | Friend of a Friend | http://xmlns.com/foaf/0.1/ |
| dc | Dublin Core Elements | http://purl.org/dc/elements/1.1/ |
| dcterms | Dublin Core Terms | http://purl.org/dc/terms/ |
| schema | Schema.org | http://schema.org/ |
| owl | Web Ontology Language | http://www.w3.org/2002/07/owl# |
| rdf | RDF Syntax | http://www.w3.org/1999/02/22-rdf-syntax-ns# |
| rdfs | RDF Schema | http://www.w3.org/2000/01/rdf-schema# |
| skos | SKOS | http://www.w3.org/2004/02/skos/core# |
| prov | PROV Ontology | http://www.w3.org/ns/prov# |
| dcat | Data Catalog Vocabulary | http://www.w3.org/ns/dcat# |
| void | VoID | http://rdfs.org/ns/void# |
| geo | WGS84 Geo Positioning | http://www.w3.org/2003/01/geo/wgs84_pos# |
| time | Time Ontology | http://www.w3.org/2006/time# |

### Life Science Ontologies

| Prefix | Name | Namespace |
|--------|------|-----------|
| uniprot | UniProt Core Ontology | http://purl.uniprot.org/core/ |
| go | Gene Ontology | http://purl.obolibrary.org/obo/GO_ |
| obo | OBO Foundry | http://purl.obolibrary.org/obo/ |
| sio | Semanticscience Integrated Ontology | http://semanticscience.org/resource/ |
| so | Sequence Ontology | http://purl.obolibrary.org/obo/SO_ |
| ncit | NCI Thesaurus | http://purl.obolibrary.org/obo/NCIT_ |
| efo | Experimental Factor Ontology | http://www.ebi.ac.uk/efo/EFO_ |
| mondo | Mondo Disease Ontology | http://purl.obolibrary.org/obo/MONDO_ |
| hp | Human Phenotype Ontology | http://purl.obolibrary.org/obo/HP_ |
| chebi | Chemical Entities of Biological Interest | http://purl.obolibrary.org/obo/CHEBI_ |
| ensembl | Ensembl RDF | http://rdf.ebi.ac.uk/resource/ensembl/ |
| geno | Genotype Ontology | http://purl.obolibrary.org/obo/GENO_ |

### FAIR Vocabularies

| Prefix | Name | Namespace |
|--------|------|-----------|
| fair | FAIR Principles Vocabulary | https://w3id.org/fair/principles/terms/ |
| fdp | FAIR Data Point Ontology | https://w3id.org/fdp/fdp-o# |

## Usage Examples

### Example 1: Basic Vocabulary Lookup

```python
from sparql_agent.schema import OntologyMapper

mapper = OntologyMapper()

# Look up vocabulary by prefix
foaf = mapper.get_vocabulary_by_prefix("foaf")
print(f"Name: {foaf.name}")
print(f"Namespace: {foaf.namespace}")
print(f"Description: {foaf.description}")

# Extract prefix from URI
uri = "http://xmlns.com/foaf/0.1/Person"
prefix, local_name = mapper.extract_prefix_from_uri(uri)
print(f"Prefix: {prefix}, Local name: {local_name}")
```

### Example 2: Life Science Ontologies

```python
from sparql_agent.schema import OntologyMapper, OntologyDomain

mapper = OntologyMapper()

# List all life science ontologies
life_sci_vocabs = mapper.list_vocabularies_by_domain(OntologyDomain.LIFE_SCIENCES)
for vocab in life_sci_vocabs:
    print(f"{vocab.prefix}: {vocab.name}")

# Look up specific ontology
uniprot = mapper.get_vocabulary_by_prefix("uniprot")
print(f"UniProt homepage: {uniprot.homepage}")
```

### Example 3: owl:sameAs Relationships

```python
from sparql_agent.schema import OntologyMapper

mapper = OntologyMapper()

# Schema.org Person maps to FOAF Person
schema_person = "http://schema.org/Person"
equivalents = mapper.get_equivalent_uris(schema_person)
print(f"Equivalent URIs: {equivalents}")

# Add custom mapping
mapper.add_same_as_mapping(
    "http://example.org/Person",
    schema_person
)

# Resolve to canonical form
resolved = mapper.resolve_uri("http://example.org/Person")
print(f"Canonical URI: {resolved}")
```

### Example 4: Vocabulary Detection

```python
from sparql_agent.schema import detect_vocabularies_in_text

sparql_query = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX uniprot: <http://purl.uniprot.org/core/>

SELECT ?person ?protein WHERE {
    ?person a foaf:Person .
    ?protein a uniprot:Protein .
}
"""

detector = detect_vocabularies_in_text(sparql_query)

# Get top vocabularies
for prefix, count in detector.get_top_vocabularies():
    print(f"{prefix}: {count} occurrences")

# Get vocabularies by domain
for domain, prefixes in detector.identify_ontologies().items():
    print(f"{domain.value}: {prefixes}")
```

### Example 5: Detailed Analysis

```python
from sparql_agent.schema import OntologyMapper, VocabularyDetector

mapper = OntologyMapper()
detector = VocabularyDetector(mapper)

# Analyze triples
triples = [
    ("http://example.org/person1", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
     "http://xmlns.com/foaf/0.1/Person"),
    ("http://example.org/person1", "http://xmlns.com/foaf/0.1/name", "Alice"),
]

for s, p, o in triples:
    detector.analyze_triple(s, p, o)

# Get statistics
stats = detector.export_statistics()
print(f"Total vocabularies: {stats['vocabulary_count']}")
print(f"Total terms: {stats['total_terms']}")

# Generate report
print(detector.get_coverage_report())
```

### Example 6: Cross-Vocabulary Reasoning

```python
from sparql_agent.schema import OntologyMapper, OntologyMapping

mapper = OntologyMapper()

# Add custom mapping
mapping = OntologyMapping(
    source_uri="http://schema.org/name",
    target_uri="http://xmlns.com/foaf/0.1/name",
    mapping_type="owl:sameAs",
    confidence=1.0
)
mapper.add_mapping(mapping)

# Find all equivalent URIs
equivalents = mapper.get_equivalent_uris("http://schema.org/name")
print(f"All equivalent URIs: {equivalents}")
```

## Reasoning Capabilities

The ontology mapper provides several reasoning capabilities:

### 1. Transitive owl:sameAs Closure

The system automatically computes the transitive closure of owl:sameAs relationships:

```
If A sameAs B and B sameAs C, then A sameAs C
```

### 2. URI Normalization

Handles common URI variations:
- Trailing slashes: `http://example.org/` vs `http://example.org`
- HTTP vs HTTPS
- Fragment identifiers

### 3. Vocabulary Misuse Detection

Detects common issues:
- Deprecated terms (e.g., FOAF geekcode)
- Naming convention violations
- Domain-specific best practices

### 4. Cross-Reference Resolution

- Resolves URIs to preferred forms
- Supports namespace preference
- Handles alias mappings

## Integration with LOV

The system includes Linked Open Vocabularies (LOV) URLs for standard vocabularies:

```python
mapper = OntologyMapper()
lov_url = mapper.get_lov_url("foaf")
# Returns: https://lov.linkeddata.es/dataset/lov/vocabs/foaf
```

## Extending the System

### Adding Custom Vocabularies

```python
from sparql_agent.schema import OntologyMapper, VocabularyInfo, OntologyDomain

mapper = OntologyMapper()

custom_vocab = VocabularyInfo(
    prefix="myonto",
    namespace="http://example.org/myonto/",
    name="My Custom Ontology",
    domain=OntologyDomain.GENERAL,
    description="A custom ontology for my domain",
    homepage="http://example.org/myonto",
    aliases=["mo"]
)

mapper.add_vocabulary(custom_vocab)
```

### Adding Custom Mappings

```python
# Add owl:sameAs mapping
mapper.add_same_as_mapping(
    "http://example.org/Term1",
    "http://other.org/Term1"
)

# Add other mapping types
from sparql_agent.schema import OntologyMapping

mapping = OntologyMapping(
    source_uri="http://example.org/Term1",
    target_uri="http://other.org/SimilarTerm",
    mapping_type="skos:closeMatch",
    confidence=0.8
)
mapper.add_mapping(mapping)
```

## Performance Considerations

- **Pre-loaded vocabularies**: Standard vocabularies are loaded once at initialization
- **Graph-based sameAs**: Uses efficient graph traversal for transitive closure
- **Namespace lookup**: O(1) lookup for namespace to prefix mapping
- **URI extraction**: Regex-based pattern matching for fast URI extraction

## Best Practices

1. **Reuse mapper instances**: Create one OntologyMapper and reuse it
2. **Use vocabulary detectors for analysis**: VocabularyDetector is optimized for batch analysis
3. **Reset detectors between analyses**: Call `detector.reset()` when analyzing different datasets
4. **Add domain-specific vocabularies**: Extend with your domain vocabularies before analysis
5. **Check LOV for standard vocabularies**: Use LOV URLs for documentation

## Future Enhancements

Potential areas for expansion:

- SPARQL endpoint queries for vocabulary metadata
- Automatic LOV vocabulary fetching
- Machine learning for mapping confidence
- SKOS hierarchy support
- OWL reasoning integration
- Vocabulary version tracking
- Community mapping contributions

## Dependencies

- Python 3.8+
- Standard library only (no external dependencies)
- Optional: RDFLib for advanced RDF parsing

## Testing

Run the example file to see all capabilities:

```bash
cd /Users/david/git/sparql-agent/src/sparql_agent/schema
python example_usage.py
```

## License

Part of SPARQL Agent project.
