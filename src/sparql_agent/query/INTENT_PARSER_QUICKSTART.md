# Intent Parser Quick Start Guide

## Installation

The Intent Parser is part of the SPARQL Agent framework. No additional dependencies required.

```python
from sparql_agent.query import IntentParser, parse_query, classify_query
```

## 5-Minute Quick Start

### 1. Basic Parsing

```python
from sparql_agent.query import parse_query

# Parse a natural language query
intent = parse_query("Find all proteins from human")

print(f"Query Type: {intent.query_type.value}")
print(f"Entities: {[e.text for e in intent.entities]}")
print(f"Confidence: {intent.confidence}")
```

### 2. Query Classification

```python
from sparql_agent.query import classify_query

# Classify query pattern
pattern = classify_query("How many proteins are there?")
print(f"Pattern: {pattern}")  # Output: COUNT_SIMPLE
```

### 3. Advanced Parsing

```python
from sparql_agent.query import IntentParser

parser = IntentParser()
intent = parser.parse("Top 10 genes by expression")

print(f"Type: {intent.query_type.value}")
print(f"Order: {intent.order_by[0].variable} {intent.order_by[0].direction.value}")
print(f"Limit: {intent.limit}")
```

## Common Use Cases

### Aggregation Queries

```python
intent = parse_query("Count proteins per organism")

# Check if aggregation is present
if intent.aggregations:
    agg = intent.aggregations[0]
    print(f"Aggregation: {agg.type.value}")
    print(f"Variable: {agg.variable}")
    print(f"Group By: {agg.group_by}")
```

### Filter Queries

```python
intent = parse_query("Find genes with expression greater than 100")

# Check filters
for filter_obj in intent.filters:
    print(f"Filter: {filter_obj.variable} {filter_obj.operator.value} {filter_obj.value}")
```

### Text Search Queries

```python
intent = parse_query("Search for proteins containing 'kinase'")

# Check text search terms
print(f"Search terms: {intent.text_search}")
```

### ASK Queries

```python
intent = parse_query("Is TP53 a gene?")

print(f"Type: {intent.query_type.value}")  # ASK
```

## With Ontology

```python
from sparql_agent.query import IntentParser
from sparql_agent.core.types import OntologyInfo, OWLClass

# Create ontology
ontology = OntologyInfo(uri="http://example.org/ontology")
protein_class = OWLClass(
    uri="http://purl.uniprot.org/core/Protein",
    label=["Protein", "protein"]
)
ontology.classes = {protein_class.uri: protein_class}

# Parse with ontology
parser = IntentParser(ontology_info=ontology)
intent = parser.parse("Find all proteins")

# Check resolved entities
for entity in intent.entities:
    if entity.uri:
        print(f"{entity.text} -> {entity.uri}")
```

## Query Structure Suggestion

```python
parser = IntentParser()
intent = parser.parse("Count proteins per organism")
structure = parser.suggest_query_structure(intent)

print(f"Pattern: {structure['pattern']}")
print(f"SELECT: {structure['select_variables']}")
print(f"WHERE: {structure['where_patterns']}")
print(f"MODIFIERS: {structure['modifiers']}")
```

## Handling Ambiguities

```python
intent = parse_query("Find high expression genes")

if intent.ambiguities:
    print("Ambiguities detected:")
    for amb in intent.ambiguities:
        print(f"  - {amb['type']}: {amb['message']}")

print(f"Confidence: {intent.confidence}")
```

## Supported Query Types

| Type | Example | Pattern |
|------|---------|---------|
| SELECT | "Find all proteins" | BASIC_LIST |
| COUNT | "How many genes?" | COUNT_SIMPLE |
| ASK | "Is TP53 a gene?" | ASK_VERIFICATION |
| DESCRIBE | "Describe TP53" | DESCRIBE_ENTITY |
| TOP N | "Top 10 by score" | TOP_N_AGGREGATION |
| FILTER | "Proteins with mass > 50000" | SIMPLE_FILTER |
| JOIN | "Genes and their diseases" | COMPLEX_JOIN |
| SEARCH | "Search for kinase" | FULL_TEXT_SEARCH |

## ParsedIntent Fields

```python
intent.original_query      # Original query string
intent.query_type         # QueryType enum (SELECT, COUNT, ASK, etc.)
intent.entities           # List[Entity] - extracted entities
intent.filters            # List[Filter] - filter constraints
intent.aggregations       # List[Aggregation] - aggregation operations
intent.order_by           # List[OrderClause] - ordering information
intent.limit              # Optional[int] - result limit
intent.offset             # Optional[int] - result offset
intent.distinct           # bool - use DISTINCT
intent.optional_patterns  # List[str] - optional patterns
intent.property_paths     # List[str] - property paths
intent.text_search        # List[str] - text search terms
intent.confidence         # float - confidence score (0-1)
intent.ambiguities        # List[Dict] - detected ambiguities
intent.metadata           # Dict - additional metadata
```

## Pattern Recognition Cheat Sheet

### Query Type Keywords

- **SELECT**: find, list, show, get, retrieve, display, what, which
- **COUNT**: how many, count, number of, total
- **ASK**: is, are, does, do, has, have, can
- **DESCRIBE**: describe, tell me about, information about
- **CONSTRUCT**: build, construct, create graph

### Aggregation Keywords

- **COUNT**: count, number of, how many, total number
- **SUM**: sum, total, add up
- **AVG**: average, mean, avg
- **MIN**: minimum, smallest, lowest
- **MAX**: maximum, largest, highest

### Filter Keywords

- **Equals**: is, equals, equal to, named, called
- **Not Equals**: is not, not equal, different from
- **Greater**: greater than, more than, above, exceeds
- **Less**: less than, fewer than, below
- **Contains**: contains, containing, includes, including
- **Regex**: matches, matching, pattern, like

### Order Keywords

- **Ascending**: ascending, asc, lowest first, increasing
- **Descending**: descending, desc, highest first, top, best

## Tips

1. **Use quotes** for exact entity values: `"TP53"`, `"Alzheimer's"`
2. **Be specific** with filters: `"greater than 100"` not just `"high"`
3. **Use clear aggregations**: `"count proteins"` not just `"proteins"`
4. **Specify ordering**: `"order by score descending"` for clarity
5. **Check confidence**: Low confidence (<0.7) means ambiguity
6. **Review ambiguities**: They indicate what needs clarification

## Next Steps

- See `INTENT_PARSER_README.md` for complete documentation
- See `intent_parser_examples.py` for more examples
- See `test_intent_parser.py` for comprehensive tests
- Integrate with `PromptEngine` for query generation
- Integrate with `SPARQLGenerator` for SPARQL creation

## Common Patterns

### Basic Query
```python
intent = parse_query("Find all X")
# → SELECT ?x WHERE { ?x a <X> }
```

### Count Query
```python
intent = parse_query("How many X are there?")
# → SELECT (COUNT(?x) AS ?count) WHERE { ?x a <X> }
```

### Filtered Query
```python
intent = parse_query("Find X where Y is Z")
# → SELECT ?x WHERE { ?x a <X> ; <Y> "Z" }
```

### Top N Query
```python
intent = parse_query("Top 10 X by Y")
# → SELECT ?x ?y WHERE { ?x a <X> ; <property> ?y } ORDER BY DESC(?y) LIMIT 10
```

### Grouped Count
```python
intent = parse_query("Count X per Y")
# → SELECT ?y (COUNT(?x) AS ?count) WHERE { ?x a <X> ; <property> ?y } GROUP BY ?y
```

## Troubleshooting

### Low Confidence Score
- Add more specific entity names
- Use quotes for exact values
- Clarify filters and constraints
- Provide explicit ordering

### Unresolved Entities
- Provide ontology or schema information
- Use standard entity names from your domain
- Check spelling of entity names

### Ambiguous Filters
- Be specific with filter targets
- Use explicit variable names
- Avoid vague terms like "high" or "low"

### No Pattern Match
- Check query structure
- Ensure clear intent
- Use supported keyword patterns
- Break complex queries into parts

## Support

For issues or questions:
1. Check the examples in `intent_parser_examples.py`
2. Review the full documentation in `INTENT_PARSER_README.md`
3. Run the test suite to see expected behavior
4. Check the integration examples with other modules
