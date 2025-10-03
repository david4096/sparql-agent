# Intent Parser for SPARQL Query Generation

## Overview

The Intent Parser is a comprehensive natural language processing module that analyzes user queries and extracts structured information for SPARQL query generation. It detects query types, entities, filters, aggregations, and constraints from natural language input.

## Key Components

### 1. IntentParser Class

The main parser class that orchestrates all intent detection and parsing operations.

```python
from sparql_agent.query import IntentParser

parser = IntentParser(
    schema_info=schema_info,      # Optional schema information
    ontology_info=ontology_info,  # Optional ontology information
    custom_patterns=custom_patterns  # Optional custom pattern definitions
)

intent = parser.parse("Find all proteins from human")
```

### 2. Query Types

Supported SPARQL query types:

- **SELECT**: Standard data retrieval queries
- **COUNT**: Counting/aggregation queries
- **ASK**: Yes/no verification queries
- **DESCRIBE**: Entity description queries
- **CONSTRUCT**: Graph construction queries

### 3. Data Classes

#### Entity
Represents extracted entities from the query:
- Text, type, URI
- Confidence score
- Alternative interpretations
- Context information

#### Filter
Represents filter constraints:
- Variable, operator, value
- Datatype and language information
- Negation support

#### Aggregation
Represents aggregation operations:
- Type (COUNT, SUM, AVG, MIN, MAX)
- Variable to aggregate
- Result variable name
- DISTINCT flag
- GROUP BY variables

#### OrderClause
Represents ordering information:
- Variable to order by
- Direction (ASC/DESC)

#### ParsedIntent
Complete parsed intent structure containing:
- Original query
- Query type
- Entities, filters, aggregations
- Order clauses, limit, offset
- Optional patterns
- Property paths
- Text search terms
- Confidence score
- Detected ambiguities

## Pattern Recognition

### Query Type Patterns

**SELECT Queries:**
```
"Find all proteins"
"List diseases"
"Show me genes"
"Get publications"
```

**COUNT Queries:**
```
"How many proteins are there?"
"Count the diseases"
"What is the number of genes?"
"Total number of publications"
```

**ASK Queries:**
```
"Is TP53 a gene?"
"Does this protein have activity?"
"Are there any diseases?"
```

**DESCRIBE Queries:**
```
"Describe the gene TP53"
"Tell me about Alzheimer's"
"What is UniProt?"
```

### Aggregation Patterns

- **COUNT**: "how many", "count", "number of", "total"
- **SUM**: "sum", "total", "add up"
- **AVG**: "average", "mean", "avg"
- **MIN**: "minimum", "smallest", "lowest"
- **MAX**: "maximum", "largest", "highest"

### Filter Patterns

**Equality:**
```
"where X is Y"
"where X equals Y"
"X named Y"
```

**Comparison:**
```
"with X greater than Y"
"X less than Y"
"X at least Y"
"X at most Y"
```

**Contains:**
```
"containing X"
"including X"
"with X"
```

### Order and Limit Patterns

**Ordering:**
```
"order by X"
"order by X descending"
"top 10 X by Y"
"highest X"
```

**Limit:**
```
"top 10"
"first 5"
"limit 20"
"maximum 100"
```

## Entity Resolution

The parser can resolve entities using:

1. **Ontology Information**: Matches entities to OWL classes and properties
2. **Schema Information**: Matches entities to discovered schema elements
3. **Fuzzy Matching**: Handles partial matches and variations

```python
# With ontology
parser = IntentParser(ontology_info=ontology)
intent = parser.parse("Find all proteins")
# Entities will be resolved to ontology URIs

# With schema
parser = IntentParser(schema_info=schema)
intent = parser.parse("Find all proteins")
# Entities will be resolved to schema URIs
```

## Query Pattern Classification

The parser classifies queries into common SPARQL patterns:

- **COUNT_SIMPLE**: Simple counting query
- **COUNT_GROUP_BY**: Counting with grouping
- **TOP_N_AGGREGATION**: Top N with ordering
- **FULL_TEXT_SEARCH**: Text search query
- **COMPLEX_JOIN**: Multi-entity join query
- **SIMPLE_FILTER**: Basic filtering query
- **PROPERTY_PATH**: Property path traversal
- **BASIC_LIST**: Simple listing query
- **ASK_VERIFICATION**: Yes/no verification
- **DESCRIBE_ENTITY**: Entity description
- **GENERIC_SELECT**: Generic SELECT query

```python
parser = IntentParser()
intent = parser.parse("Top 10 genes by expression")
pattern = parser.classify_query_pattern(intent)
# Returns: "TOP_N_AGGREGATION"
```

## Query Structure Suggestion

The parser can suggest a SPARQL query structure:

```python
parser = IntentParser()
intent = parser.parse("Count proteins per organism")
structure = parser.suggest_query_structure(intent)

# Returns:
{
    'pattern': 'COUNT_GROUP_BY',
    'query_type': 'COUNT',
    'select_variables': ['(COUNT(?protein) AS ?count)', '?organism'],
    'where_patterns': ['?protein a <Protein>', '?protein <organism> ?organism'],
    'filters': [],
    'aggregations': [...],
    'modifiers': {'group_by': ['organism']}
}
```

## Confidence Scoring

The parser assigns confidence scores based on:

- Entity resolution success
- Query pattern clarity
- Ambiguity detection
- Filter specificity

High confidence (>0.9): Clear entities, well-defined patterns
Medium confidence (0.7-0.9): Some ambiguity, partial resolution
Low confidence (<0.7): Significant ambiguity or missing information

## Ambiguity Detection

The parser detects and reports ambiguities:

```python
intent = parser.parse("Find high expression genes")

for ambiguity in intent.ambiguities:
    print(f"{ambiguity['type']}: {ambiguity['message']}")

# Output:
# unresolved_entity: Could not resolve 'high' to a known URI
# ambiguous_filter: Filter target for 'high' is ambiguous
```

## Usage Examples

### Basic Parsing

```python
from sparql_agent.query import parse_query, classify_query

# Quick parse
intent = parse_query("Find all proteins from human")
print(f"Type: {intent.query_type.value}")
print(f"Entities: {len(intent.entities)}")

# Quick classify
pattern = classify_query("Count proteins per organism")
print(f"Pattern: {pattern}")
```

### Complex Query Parsing

```python
parser = IntentParser()

query = "Top 10 proteins from human with expression greater than 100 order by score"
intent = parser.parse(query)

print(f"Query Type: {intent.query_type.value}")
print(f"Entities: {[e.text for e in intent.entities]}")
print(f"Filters: {[(f.variable, f.operator.value, f.value) for f in intent.filters]}")
print(f"Order: {[(o.variable, o.direction.value) for o in intent.order_by]}")
print(f"Limit: {intent.limit}")
print(f"Confidence: {intent.confidence}")
```

### With Ontology

```python
from sparql_agent.core.types import OntologyInfo, OWLClass

ontology = OntologyInfo(uri="http://example.org/ontology")
protein_class = OWLClass(
    uri="http://purl.uniprot.org/core/Protein",
    label=["Protein", "protein"]
)
ontology.classes = {protein_class.uri: protein_class}

parser = IntentParser(ontology_info=ontology)
intent = parser.parse("Find all proteins")

# Entities will be resolved to URIs
for entity in intent.entities:
    if entity.uri:
        print(f"{entity.text} -> {entity.uri}")
```

## Integration with Query Generation

The Intent Parser is designed to work seamlessly with the SPARQL query generator:

```python
from sparql_agent.query import IntentParser, PromptEngine

# Parse intent
parser = IntentParser(schema_info=schema, ontology_info=ontology)
intent = parser.parse("Count proteins per organism")

# Use intent to guide query generation
prompt_engine = PromptEngine()
scenario = prompt_engine.detect_scenario(intent.original_query)
structure = parser.suggest_query_structure(intent)

# Generate SPARQL using the parsed intent and suggested structure
# ... (integrate with your query generator)
```

## Advanced Features

### Custom Patterns

Add custom pattern definitions:

```python
custom_patterns = {
    'custom_entity_type': ['custom1', 'custom2'],
    'custom_aggregation': [r'\bcustom_agg\b']
}

parser = IntentParser(custom_patterns=custom_patterns)
```

### Property Path Detection

Detects transitive and complex property paths:

```python
intent = parser.parse("Find all ancestors of this gene")
print(intent.property_paths)  # ['transitive']
```

### Optional Pattern Detection

Detects optional/nullable patterns:

```python
intent = parser.parse("Find genes with optional interactions")
print(intent.optional_patterns)  # ['interactions']
```

### Text Search Extraction

Extracts text search terms:

```python
intent = parser.parse("Search for proteins related to 'immune response'")
print(intent.text_search)  # ['immune response']
```

## Performance Considerations

- Pattern matching uses compiled regex for efficiency
- Entity resolution caching can improve performance
- Consider limiting fuzzy matching depth for large ontologies
- Batch processing of multiple queries is supported

## Error Handling

The parser is designed to be robust:

- Returns default values for missing information
- Provides confidence scores for uncertain interpretations
- Reports ambiguities without failing
- Handles malformed or unclear queries gracefully

## Testing

Comprehensive test suite available in `test_intent_parser.py`:

```bash
pytest src/sparql_agent/query/test_intent_parser.py -v
```

## Examples

See `intent_parser_examples.py` for extensive usage examples covering:
- Basic queries
- Aggregation queries
- Filter queries
- Ordering queries
- Text search queries
- Complex queries
- ASK/DESCRIBE queries
- Entity resolution
- Query structure suggestion

## Future Enhancements

Potential areas for extension:

1. Machine learning-based entity recognition
2. Context-aware disambiguation
3. Multi-language support
4. Domain-specific pattern libraries
5. Query intent history and learning
6. Semantic similarity matching
7. Named entity recognition (NER) integration
8. Coreference resolution

## License

Part of the SPARQL Agent framework (MIT License)

## Related Modules

- `prompt_engine.py`: Uses intent information for prompt generation
- `generator.py`: Converts parsed intent to SPARQL queries
- `ontology_generator.py`: Leverages intent for ontology-guided generation
