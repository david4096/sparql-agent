# Ontology Mapper Quick Reference

Quick reference guide for common operations.

## Import

```python
from sparql_agent.schema import (
    OntologyMapper,
    VocabularyDetector,
    OntologyDomain,
    create_default_mapper,
    detect_vocabularies_in_text
)
```

## Quick Start

### 1. Create Mapper

```python
# Create default mapper (includes all standard vocabularies)
mapper = OntologyMapper()

# Or use factory function
mapper = create_default_mapper()
```

### 2. Look Up Vocabulary

```python
# By prefix
foaf = mapper.get_vocabulary_by_prefix("foaf")
print(foaf.name)        # "Friend of a Friend"
print(foaf.namespace)   # "http://xmlns.com/foaf/0.1/"

# By namespace
vocab = mapper.get_vocabulary_by_namespace("http://schema.org/")

# By URI
vocab = mapper.get_vocabulary_for_uri("http://xmlns.com/foaf/0.1/Person")
```

### 3. Parse URI

```python
uri = "http://xmlns.com/foaf/0.1/Person"
prefix, local_name = mapper.extract_prefix_from_uri(uri)
# prefix = "foaf", local_name = "Person"
```

### 4. Find Equivalent URIs

```python
# Get all owl:sameAs equivalent URIs
equivalents = mapper.get_equivalent_uris("http://schema.org/Person")
# Returns: {"http://schema.org/Person", "http://xmlns.com/foaf/0.1/Person"}
```

### 5. Detect Vocabularies in Text

```python
sparql_query = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT ?person WHERE { ?person a foaf:Person }
"""

detector = detect_vocabularies_in_text(sparql_query)

# Get top vocabularies
for prefix, count in detector.get_top_vocabularies(5):
    print(f"{prefix}: {count} uses")

# Generate report
print(detector.get_coverage_report())
```

## Common Operations

### Search Vocabularies

```python
# Search by keyword
results = mapper.search_vocabularies("protein")
for vocab in results:
    print(f"{vocab.prefix}: {vocab.name}")
```

### List by Domain

```python
# Get all life science ontologies
life_sci = mapper.list_vocabularies_by_domain(OntologyDomain.LIFE_SCIENCES)
for vocab in life_sci:
    print(f"{vocab.prefix}: {vocab.name}")
```

### Add Custom Vocabulary

```python
from sparql_agent.schema import VocabularyInfo

custom = VocabularyInfo(
    prefix="myonto",
    namespace="http://example.org/myonto/",
    name="My Ontology",
    domain=OntologyDomain.GENERAL,
    description="Custom ontology",
    homepage="http://example.org"
)

mapper.add_vocabulary(custom)
```

### Add Mappings

```python
# Add owl:sameAs
mapper.add_same_as_mapping(
    "http://example.org/Term1",
    "http://other.org/Term1"
)

# Add typed mapping
from sparql_agent.schema import OntologyMapping

mapping = OntologyMapping(
    source_uri="http://example.org/Term1",
    target_uri="http://other.org/Term2",
    mapping_type="skos:closeMatch",
    confidence=0.8
)
mapper.add_mapping(mapping)
```

### Analyze RDF Data

```python
detector = VocabularyDetector(mapper)

# Analyze individual URIs
detector.analyze_uri("http://xmlns.com/foaf/0.1/Person", "class")
detector.analyze_uri("http://xmlns.com/foaf/0.1/name", "property")

# Analyze triples
detector.analyze_triple(
    "http://example.org/person1",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    "http://xmlns.com/foaf/0.1/Person"
)

# Get statistics
stats = detector.export_statistics()
print(f"Vocabularies: {stats['vocabulary_count']}")
print(f"Total terms: {stats['total_terms']}")
```

## Vocabulary Prefixes Reference

### Standard Web/Semantic Web

```python
"foaf"     # Friend of a Friend
"dc"       # Dublin Core Elements
"dcterms"  # Dublin Core Terms
"schema"   # Schema.org
"owl"      # Web Ontology Language
"rdf"      # RDF Syntax
"rdfs"     # RDF Schema
"skos"     # SKOS
"prov"     # PROV Ontology
"dcat"     # Data Catalog Vocabulary
"void"     # VoID
"geo"      # WGS84 Geo
"time"     # Time Ontology
```

### Life Sciences

```python
"uniprot"  # UniProt Core Ontology
"go"       # Gene Ontology
"obo"      # OBO Foundry
"sio"      # Semanticscience Integrated Ontology
"so"       # Sequence Ontology
"ncit"     # NCI Thesaurus
"efo"      # Experimental Factor Ontology
"mondo"    # Mondo Disease Ontology
"hp"       # Human Phenotype Ontology
"chebi"    # Chemical Entities of Biological Interest
"ensembl"  # Ensembl RDF
"geno"     # Genotype Ontology
```

### FAIR

```python
"fair"     # FAIR Principles Vocabulary
"fdp"      # FAIR Data Point Ontology
```

## OntologyDomain Values

```python
OntologyDomain.GENERAL
OntologyDomain.LIFE_SCIENCES
OntologyDomain.BIBLIOGRAPHIC
OntologyDomain.WEB
OntologyDomain.PROVENANCE
OntologyDomain.GEOSPATIAL
OntologyDomain.TIME
OntologyDomain.MULTIMEDIA
```

## Common Patterns

### Pattern 1: Analyze SPARQL Endpoint

```python
# Fetch sample data from endpoint
# ... (get triples)

detector = VocabularyDetector()
for s, p, o in triples:
    detector.analyze_triple(s, p, o)

print(detector.get_coverage_report())
```

### Pattern 2: Cross-Vocabulary Query Translation

```python
# Original query uses schema:name
# Translate to foaf:name

schema_name = "http://schema.org/name"
equivalents = mapper.get_equivalent_uris(schema_name)

# Check if foaf:name is equivalent
foaf_name = "http://xmlns.com/foaf/0.1/name"
if foaf_name in equivalents:
    print("Can translate between schema:name and foaf:name")
```

### Pattern 3: Dataset Profiling

```python
# Profile a dataset
detector = VocabularyDetector()

# Analyze all triples in dataset
for triple in dataset:
    detector.analyze_triple(*triple)

# Get domain breakdown
domains = detector.identify_ontologies()
for domain, prefixes in domains.items():
    print(f"{domain.value}:")
    for prefix in prefixes:
        usage = detector.usage_stats[prefix]
        print(f"  {prefix}: {usage.term_count} uses")
```

### Pattern 4: Vocabulary Recommendation

```python
# Recommend vocabularies for a domain
life_sci = mapper.list_vocabularies_by_domain(OntologyDomain.LIFE_SCIENCES)

print("Recommended life science vocabularies:")
for vocab in life_sci:
    print(f"  {vocab.prefix:12s} - {vocab.name}")
    print(f"    Use for: {vocab.description}")
    print(f"    Docs: {vocab.homepage}")
```

### Pattern 5: Data Quality Check

```python
detector = VocabularyDetector()

# Analyze dataset
for triple in dataset:
    detector.analyze_triple(*triple)

# Check for violations
violations = detector.detect_vocabulary_violations()
if violations:
    print("Vocabulary usage warnings:")
    for prefix, warnings in violations.items():
        print(f"  {prefix}:")
        for warning in warnings:
            print(f"    - {warning}")
```

## Tips & Tricks

### Tip 1: Reuse Mapper Instance
```python
# Good - create once, use many times
mapper = OntologyMapper()
for query in queries:
    detector = VocabularyDetector(mapper)
    # ... analyze
```

### Tip 2: Reset Detector Between Analyses
```python
detector = VocabularyDetector()

# Analyze dataset 1
for triple in dataset1:
    detector.analyze_triple(*triple)
print(detector.get_coverage_report())

# Reset for dataset 2
detector.reset()
for triple in dataset2:
    detector.analyze_triple(*triple)
print(detector.get_coverage_report())
```

### Tip 3: Use LOV URLs for Documentation
```python
vocab = mapper.get_vocabulary_by_prefix("foaf")
print(f"Documentation: {vocab.homepage}")
print(f"LOV page: {vocab.lov_url}")
```

### Tip 4: Handle Unknown Vocabularies
```python
vocab = mapper.get_vocabulary_for_uri(unknown_uri)
if vocab:
    print(f"Known vocabulary: {vocab.prefix}")
else:
    print("Unknown vocabulary - consider adding it")
    # Extract namespace for manual addition
    namespace = unknown_uri.rsplit('#', 1)[0] + '#'
```

### Tip 5: Export Statistics for Analysis
```python
detector = VocabularyDetector()
# ... analyze data

# Export as dict for further processing
stats = detector.export_statistics()

# Save to JSON
import json
with open('vocab_stats.json', 'w') as f:
    json.dump(stats, f, indent=2, default=str)
```

## Error Handling

```python
# Safe vocabulary lookup
vocab = mapper.get_vocabulary_by_prefix("unknown")
if vocab is None:
    print("Vocabulary not found")

# Safe URI extraction
result = mapper.extract_prefix_from_uri(uri)
if result is None:
    print("Could not extract prefix from URI")
else:
    prefix, local_name = result
```

## Performance Notes

- Mapper initialization: ~1ms (loads 27 vocabularies)
- Vocabulary lookup: O(1)
- URI extraction: O(1) average
- owl:sameAs closure: O(n) where n = size of equivalence set
- Text detection: O(m) where m = number of URIs

## See Also

- **ONTOLOGY_MAPPER_README.md** - Complete documentation
- **example_usage.py** - 10 working examples
- **IMPLEMENTATION_SUMMARY.md** - Technical details
