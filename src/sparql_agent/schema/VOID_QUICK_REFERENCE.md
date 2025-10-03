# VoID Parser Quick Reference

## Installation

```bash
pip install rdflib SPARQLWrapper
```

## Basic Usage

### Import

```python
from sparql_agent.schema import VoIDParser, VoIDExtractor, VoIDDataset, VoIDLinkset
```

### Parse VoID from String

```python
parser = VoIDParser()
datasets = parser.parse(rdf_data, format='turtle')
```

### Parse VoID from File

```python
parser = VoIDParser()
datasets = parser.parse_from_file('void.ttl', format='turtle')
```

### Extract VoID from Endpoint

```python
extractor = VoIDExtractor("https://example.org/sparql", timeout=30)
datasets = extractor.extract(generate_if_missing=True)
```

### Access Dataset Information

```python
for dataset in datasets:
    print(dataset.title)              # Dataset title
    print(dataset.triples)            # Number of triples
    print(dataset.entities)           # Number of entities
    print(dataset.properties)         # Number of properties
    print(dataset.classes)            # Number of classes
    print(dataset.vocabularies)       # Used vocabularies (set)
    print(dataset.class_partitions)   # Class distribution (dict)
    print(dataset.property_partitions) # Property distribution (dict)
    print(dataset.sparql_endpoint)    # SPARQL endpoint URL
```

### Create Dataset Programmatically

```python
from datetime import datetime

dataset = VoIDDataset(
    uri="http://example.org/dataset",
    title="My Dataset",
    description="Description here",
    sparql_endpoint="http://example.org/sparql",
    triples=100000,
    entities=50000,
    created=datetime.now()
)

dataset.vocabularies.add("http://xmlns.com/foaf/0.1/")
```

### Export to RDF

```python
extractor = VoIDExtractor("http://example.org/sparql")

# Turtle format
turtle = extractor.export_to_rdf(datasets, format='turtle')

# RDF/XML format
xml = extractor.export_to_rdf(datasets, format='xml')

# N3 format
n3 = extractor.export_to_rdf(datasets, format='n3')
```

### Validate Consistency

```python
validation = extractor.validate_consistency(dataset)

if validation['valid']:
    print("Valid!")
else:
    for error in validation['errors']:
        print(f"ERROR: {error}")
    for warning in validation['warnings']:
        print(f"WARNING: {warning}")
```

### Convert to Dictionary

```python
dataset_dict = dataset.to_dict()
# Returns complete dataset as nested dictionary
```

## VoIDDataset Fields

### Basic Metadata
- `uri` - Dataset URI (required)
- `title` - Dataset title
- `description` - Dataset description
- `homepage` - Homepage URL
- `sparql_endpoint` - SPARQL endpoint URL

### Statistics
- `triples` - Number of triples
- `entities` - Number of entities
- `distinct_subjects` - Distinct subject count
- `distinct_objects` - Distinct object count
- `properties` - Number of properties
- `classes` - Number of classes

### Structure
- `vocabularies` - Set of vocabulary URIs
- `class_partitions` - Dict[class_uri, instance_count]
- `property_partitions` - Dict[property_uri, usage_count]
- `linksets` - List[VoIDLinkset]

### Technical
- `uri_space` - URI namespace
- `uri_regex_pattern` - URI pattern regex
- `example_resources` - List of example URIs
- `data_dumps` - List of dump URLs
- `root_resource` - Root resource URI

### Provenance
- `created` - Creation datetime
- `modified` - Modification datetime
- `creator` - Creator name/URI
- `publisher` - Publisher name/URI
- `license` - License URI

## VoIDLinkset Fields

- `uri` - Linkset URI (required)
- `source_dataset` - Source dataset URI
- `target_dataset` - Target dataset URI
- `link_predicate` - Linking predicate URI
- `triples` - Number of linking triples

## SPARQL Query Templates

Available as class attributes on `VoIDExtractor`:

- `VOID_DATASET_QUERY` - Query existing VoID
- `VOID_LINKSET_QUERY` - Query linksets
- `STATISTICS_QUERY` - Basic statistics
- `PROPERTY_COUNT_QUERY` - Property count
- `CLASS_COUNT_QUERY` - Class count
- `CLASS_PARTITION_QUERY` - Class distribution
- `PROPERTY_PARTITION_QUERY` - Property distribution
- `VOCABULARY_QUERY` - Vocabulary detection

## Error Handling

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    extractor = VoIDExtractor(endpoint_url, timeout=30)
    datasets = extractor.extract(generate_if_missing=True)
except Exception as e:
    logger.error(f"Failed to extract VoID: {e}")
```

## Performance Tips

1. **Use existing VoID when available**
   ```python
   datasets = extractor.extract(generate_if_missing=False)
   ```

2. **Adjust timeout for large endpoints**
   ```python
   extractor = VoIDExtractor(url, timeout=120)
   ```

3. **Cache generated VoID**
   ```python
   rdf = extractor.export_to_rdf(datasets, format='turtle')
   with open('void_cache.ttl', 'w') as f:
       f.write(rdf)
   ```

## Common Patterns

### Full Endpoint Analysis

```python
extractor = VoIDExtractor(endpoint_url, timeout=60)
datasets = extractor.extract(generate_if_missing=True)

for dataset in datasets:
    print(f"\n=== {dataset.title} ===")
    print(f"Triples: {dataset.triples:,}")
    print(f"Entities: {dataset.entities:,}")
    print(f"Properties: {dataset.properties}")
    print(f"Classes: {dataset.classes}")

    print("\nTop 5 Classes:")
    sorted_classes = sorted(
        dataset.class_partitions.items(),
        key=lambda x: x[1],
        reverse=True
    )
    for class_uri, count in sorted_classes[:5]:
        print(f"  {class_uri}: {count:,}")

    print("\nTop 5 Properties:")
    sorted_props = sorted(
        dataset.property_partitions.items(),
        key=lambda x: x[1],
        reverse=True
    )
    for prop_uri, count in sorted_props[:5]:
        print(f"  {prop_uri}: {count:,}")

    print("\nVocabularies:")
    for vocab in sorted(dataset.vocabularies)[:10]:
        print(f"  {vocab}")
```

### Compare VoID with Actual Data

```python
# Parse claimed VoID
parser = VoIDParser()
claimed = parser.parse_from_file('claimed_void.ttl')[0]

# Generate actual VoID
extractor = VoIDExtractor(claimed.sparql_endpoint, timeout=60)
actual = extractor.extract(generate_if_missing=True)[0]

# Compare
print(f"Claimed triples: {claimed.triples:,}")
print(f"Actual triples:  {actual.triples:,}")
print(f"Difference:      {abs(claimed.triples - actual.triples):,}")

# Validate
validation = extractor.validate_consistency(claimed)
print(f"\nValidation: {'PASS' if validation['valid'] else 'FAIL'}")
```

### Export Multiple Formats

```python
datasets = extractor.extract(generate_if_missing=True)

formats = ['turtle', 'xml', 'n3', 'nt']
for fmt in formats:
    output = extractor.export_to_rdf(datasets, format=fmt)
    filename = f'void.{fmt}'
    with open(filename, 'w') as f:
        f.write(output)
    print(f"Exported {filename}")
```

## Testing

```bash
# Run all tests
python -m pytest test_void_parser.py -v

# Run specific test
python -m pytest test_void_parser.py::TestVoIDParser::test_parse_basic_dataset -v

# Run with coverage
python -m pytest test_void_parser.py --cov=void_parser --cov-report=html
```

## File Locations

```
/Users/david/git/sparql-agent/src/sparql_agent/schema/
├── void_parser.py              # Core implementation
├── void_example.py             # Usage examples
├── test_void_parser.py         # Unit tests
├── VOID_IMPLEMENTATION.md      # Full documentation
├── VOID_QUICK_REFERENCE.md     # This file
└── __init__.py                 # Package exports
```

## Related Resources

- [VoID Specification](https://www.w3.org/TR/void/)
- [RDFLib Docs](https://rdflib.readthedocs.io/)
- [SPARQLWrapper Docs](https://sparqlwrapper.readthedocs.io/)
