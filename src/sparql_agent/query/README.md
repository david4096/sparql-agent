# Prompt Engineering and Template System

This module provides a comprehensive prompt engineering and template system for generating SPARQL queries from natural language using LLMs. It includes Jinja2-based templates, context-aware generation, few-shot examples, and ontology integration.

## Features

- **Jinja2-based Templates**: Flexible templating with context injection
- **Context-Aware Generation**: Automatic inclusion of schema, ontology, and vocabulary information
- **Few-Shot Examples**: Built-in example library for different query scenarios
- **Scenario Detection**: Automatic detection of query patterns (basic, aggregation, joins, full-text search)
- **Ontology Integration**: Seamless integration with OWL ontologies and vocabularies
- **Customizable**: Easy to extend with custom templates and examples

## Architecture

```
prompt_engine.py
├── PromptEngine         # Main orchestrator
├── PromptTemplate       # Jinja2 template wrapper
├── PromptContext        # Context data container
├── FewShotExample       # Few-shot example definition
└── QueryScenario        # Query scenario enumeration
```

## Quick Start

### Basic Usage

```python
from sparql_agent.query import create_prompt_engine

# Create engine
engine = create_prompt_engine()

# Generate a prompt
prompt = engine.generate_prompt(
    user_query="Find all proteins from human organism"
)

print(prompt)
```

### With Schema Information

```python
from sparql_agent.core.types import SchemaInfo
from sparql_agent.query import create_prompt_engine

# Create schema info
schema_info = SchemaInfo()
schema_info.namespaces = {
    "up": "http://purl.uniprot.org/core/",
    "taxon": "http://purl.uniprot.org/taxonomy/"
}
schema_info.class_counts = {
    "http://purl.uniprot.org/core/Protein": 500000
}

# Generate prompt with schema
engine = create_prompt_engine()
prompt = engine.generate_prompt(
    user_query="Find proteins encoded by genes on chromosome 7",
    schema_info=schema_info
)
```

### With Ontology Integration

```python
from sparql_agent.core.types import OntologyInfo, OWLClass, OWLProperty, OWLPropertyType
from sparql_agent.query import create_prompt_engine

# Create ontology info
ontology_info = OntologyInfo(
    uri="http://purl.uniprot.org/core/",
    title="UniProt Core Ontology",
    description="Ontology for protein and gene data"
)

# Add classes
protein_class = OWLClass(
    uri="http://purl.uniprot.org/core/Protein",
    label=["Protein"],
    comment=["A biological macromolecule composed of amino acids"]
)
ontology_info.classes[protein_class.uri] = protein_class

# Add properties
organism_prop = OWLProperty(
    uri="http://purl.uniprot.org/core/organism",
    label=["organism"],
    comment=["Links a protein to its source organism"],
    property_type=OWLPropertyType.OBJECT_PROPERTY
)
ontology_info.properties[organism_prop.uri] = organism_prop

# Generate prompt
engine = create_prompt_engine()
prompt = engine.generate_prompt(
    user_query="Find all human proteins and their functions",
    ontology_info=ontology_info
)
```

## Query Scenarios

The system automatically detects and generates prompts for different query scenarios:

### 1. BASIC
Simple SELECT queries to retrieve data.

**Example**: "Find all proteins from human"

### 2. COMPLEX_JOIN
Queries that join across multiple datasets or entities.

**Example**: "Find genes associated with diseases and their pathways"

### 3. AGGREGATION
Queries using aggregate functions (COUNT, SUM, AVG, etc.).

**Example**: "Count the number of proteins per organism"

### 4. FULL_TEXT
Queries that perform full-text search.

**Example**: "Search for genes related to cancer"

### 5. GRAPH_PATTERN
Complex graph pattern matching.

### 6. FEDERATION
Federated queries across multiple endpoints.

### 7. PROPERTY_PATH
Queries using property paths for transitive relationships.

### 8. OPTIONAL
Queries with optional patterns.

### 9. FILTER
Queries with complex filtering.

### 10. SUBQUERY
Queries using subqueries.

## Automatic Scenario Detection

The engine can automatically detect the query scenario:

```python
engine = create_prompt_engine()

# Detects AGGREGATION
scenario = engine.detect_scenario("Count the number of proteins per organism")

# Detects FULL_TEXT
scenario = engine.detect_scenario("Search for genes related to cancer")

# Detects COMPLEX_JOIN
scenario = engine.detect_scenario("Find genes and their associated diseases")
```

## Few-Shot Examples

The system includes a built-in library of few-shot examples:

```python
from sparql_agent.query import FewShotExample, QueryScenario

# Create custom example
example = FewShotExample(
    question="Find proteins with molecular weight > 50000",
    sparql="""PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?protein ?weight
WHERE {
  ?protein a up:Protein ;
           up:molecularWeight ?weight .
  FILTER(?weight > 50000)
}
LIMIT 100""",
    explanation="Filter proteins by molecular weight",
    scenario=QueryScenario.FILTER,
    difficulty=2,
    tags=["protein", "filter", "numeric"]
)

# Add to engine
engine = create_prompt_engine()
engine.add_example(example)
```

## Custom Templates

You can create custom Jinja2 templates:

```python
from sparql_agent.query import PromptTemplate, PromptContext

# Define custom template
custom_template = """
Generate a SPARQL query for: {{ user_query }}

Available Ontologies:
{{ ontology_context }}

Requirements:
1. Use proper PREFIX declarations
2. Include LIMIT clause
3. Add explanatory comments

SPARQL Query:
"""

# Create template
template = PromptTemplate(template_string=custom_template)

# Create context
context = PromptContext(
    user_query="Find all diseases",
    available_prefixes={
        "mondo": "http://purl.obolibrary.org/obo/MONDO_",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
    }
)

# Render
prompt = template.render(context)
```

## Template Variables

Templates have access to the following variables:

- `user_query`: The natural language query
- `ontology_context`: Formatted ontology information
- `schema_summary`: Formatted schema statistics
- `prefix_declarations`: PREFIX statements for SPARQL
- `examples`: Few-shot examples
- `constraints`: User-defined constraints
- `metadata`: Additional metadata
- `scenario`: Query scenario name

## Prompt Context

The `PromptContext` class provides helpful methods:

```python
from sparql_agent.query import PromptContext

context = PromptContext(
    user_query="Find proteins",
    schema_info=schema_info,
    ontology_info=ontology_info
)

# Get formatted components
ontology_text = context.get_ontology_context()
schema_text = context.get_schema_summary()
prefixes = context.get_prefix_declarations()
examples = context.get_examples_formatted()
```

## Advanced Features

### Multi-Scenario Generation

Generate prompts for multiple scenarios to create query candidates:

```python
engine = create_prompt_engine()

scenarios = [QueryScenario.BASIC, QueryScenario.COMPLEX_JOIN]
prompts = engine.generate_multi_scenario_prompts(
    user_query="Find genes and their diseases",
    scenarios=scenarios
)

for scenario, prompt in prompts.items():
    print(f"=== {scenario.value} ===")
    print(prompt)
```

### Constraints

Add constraints to guide query generation:

```python
engine = create_prompt_engine()

prompt = engine.generate_prompt(
    user_query="Find all proteins",
    constraints={
        "LIMIT": 100,
        "timeout": "30 seconds",
        "distinct": "required",
        "performance": "optimize for speed"
    }
)
```

### Example Filtering

Get examples with specific characteristics:

```python
engine = create_prompt_engine()

# Get easy examples for basic queries
examples = engine.get_examples(
    scenario=QueryScenario.BASIC,
    max_difficulty=2,
    limit=3
)

# Get examples with specific tags
examples = engine.get_examples(
    scenario=QueryScenario.AGGREGATION,
    tags=["count", "group-by"],
    limit=5
)
```

## Built-in Templates

The system includes templates for each scenario:

### Basic Template
- Simple SELECT query generation
- Basic PREFIX usage
- Single entity retrieval

### Complex Join Template
- Multi-entity joins
- OPTIONAL patterns
- SERVICE for federation
- Property paths

### Aggregation Template
- COUNT, SUM, AVG, MIN, MAX
- GROUP BY clauses
- HAVING filters
- Subqueries for complex aggregations

### Full-Text Search Template
- FILTER with CONTAINS/REGEX
- Virtuoso bif:contains
- Blazegraph bds:search
- Apache Jena text:query

## Integration with Other Modules

The prompt engine integrates seamlessly with other system components:

```python
from sparql_agent.schema import SchemaInferenceEngine
from sparql_agent.ontology import OWLParser
from sparql_agent.query import create_prompt_engine

# Infer schema
schema_engine = SchemaInferenceEngine(endpoint_url)
schema_info = schema_engine.infer_schema()

# Parse ontology
owl_parser = OWLParser()
ontology_info = owl_parser.parse("path/to/ontology.owl")

# Generate prompt
prompt_engine = create_prompt_engine()
prompt = prompt_engine.generate_prompt(
    user_query="Find human genes associated with cancer",
    schema_info=schema_info,
    ontology_info=ontology_info
)
```

## Utility Functions

### quick_prompt

Quick utility for one-off prompt generation:

```python
from sparql_agent.query import quick_prompt

prompt = quick_prompt(
    user_query="Find all proteins",
    schema_info=schema_info,
    ontology_info=ontology_info
)
```

### create_prompt_engine

Create a configured prompt engine:

```python
from sparql_agent.query import create_prompt_engine
from sparql_agent.schema.ontology_mapper import OntologyMapper

mapper = OntologyMapper()
engine = create_prompt_engine(
    template_dir=Path("/path/to/templates"),
    ontology_mapper=mapper
)
```

## Example Prompts

### Example 1: Basic Query

**Input**: "Find all proteins from human"

**Generated Prompt**:
```
You are a SPARQL query generation expert. Generate a valid SPARQL query for the following natural language question.

## Question
Find all proteins from human

## Available Ontologies
Ontology: UniProt Core Ontology
Description: Ontology for protein and gene data

Key Classes:
  - Protein: A biological macromolecule
  - Taxon: A group of organisms

Key Properties:
  - organism: Links a protein to its source organism

## Schema Information
Most Common Classes:
  - http://purl.uniprot.org/core/Protein (500,000 instances)

## Available Prefixes
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX up: <http://purl.uniprot.org/core/>

## Examples
Example 1:
Question: Find all proteins from human
SPARQL:
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX taxon: <http://purl.uniprot.org/taxonomy/>

SELECT ?protein ?name
WHERE {
  ?protein a up:Protein ;
           up:organism taxon:9606 ;
           up:recommendedName ?name .
}
LIMIT 100

## Instructions
1. Generate a valid SPARQL 1.1 query
2. Use appropriate prefixes from the available list
3. Leverage ontology classes and properties when available
4. Include comments explaining the query logic
5. Use proper indentation and formatting
6. Consider query performance and avoid expensive patterns

## Generated SPARQL Query
Please provide the SPARQL query below:
```

## Testing

Run the tests:

```bash
pytest src/sparql_agent/query/test_prompt_engine.py -v
```

Run the examples:

```bash
# Run all examples
python -m sparql_agent.query.example_usage all

# Run specific example
python -m sparql_agent.query.example_usage 1
```

## Performance Considerations

1. **Example Selection**: Limit the number of examples (default: 5) to keep prompts concise
2. **Schema Summary**: Only include top classes and properties to avoid token bloat
3. **Ontology Context**: Summarize large ontologies rather than including all details
4. **Template Caching**: Templates are cached internally for performance

## Best Practices

1. **Provide Schema Information**: Always include schema info when available for better results
2. **Use Ontology Context**: Ontology information significantly improves query quality
3. **Add Examples**: Include domain-specific examples for better results
4. **Specify Constraints**: Add constraints to guide the LLM
5. **Validate Scenario**: Verify auto-detected scenarios are correct for your use case

## Extension Points

### Custom Scenarios

Add custom query scenarios:

```python
from enum import Enum

class CustomScenario(Enum):
    TEMPORAL = "temporal"
    GEOSPATIAL = "geospatial"
```

### Custom Templates

Create templates for custom scenarios:

```python
template_str = """
Generate a temporal SPARQL query...
{{ user_query }}
"""

template = PromptTemplate(
    template_string=template_str,
    scenario=CustomScenario.TEMPORAL
)
```

### Custom Example Sources

Load examples from external sources:

```python
import json

with open("examples.json") as f:
    examples_data = json.load(f)

for ex_data in examples_data:
    example = FewShotExample(**ex_data)
    engine.add_example(example)
```

## API Reference

See the module docstrings for detailed API documentation:

```python
from sparql_agent.query import PromptEngine
help(PromptEngine)
```

## Contributing

To add new templates or examples:

1. Add template to `prompt_engine.py`
2. Add examples to `_load_default_examples()`
3. Add tests to `test_prompt_engine.py`
4. Update documentation

## License

MIT License - see LICENSE file for details
