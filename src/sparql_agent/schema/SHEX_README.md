# ShEx Parser and Validator

A comprehensive Python implementation of a ShEx (Shape Expressions) parser and validator for RDF data validation.

## Features

- **ShEx 2.0+ Syntax Support**
  - Shape definitions with IRI and label identifiers
  - Triple constraints with predicates and value expressions
  - Cardinality modifiers (`?`, `+`, `*`, exact counts)
  - Node kinds (IRI, BNODE, LITERAL, NONLITERAL)
  - Value sets and enumerations
  - Datatype constraints (xsd:string, xsd:integer, etc.)
  - Numeric facets (MININCLUSIVE, MAXINCLUSIVE, etc.)
  - String facets (LENGTH, MINLENGTH, MAXLENGTH, PATTERN)
  - PREFIX and BASE declarations
  - Shape inheritance (EXTENDS)
  - Closed shapes

- **Validation Engine**
  - Validate RDF nodes against shape definitions
  - Cardinality checking
  - Datatype validation
  - Value set membership checking
  - Numeric range validation
  - String pattern matching
  - Comprehensive error reporting

- **PyShEx Integration**
  - Optional integration with PyShEx library when available
  - Falls back to built-in parser when PyShEx is not installed

## Installation

The ShEx parser is included in the `sparql_agent.schema` module:

```python
from sparql_agent.schema import ShExParser, ShExValidator
```

## Usage

### Basic Parsing

```python
from sparql_agent.schema import ShExParser

# Define a ShEx schema
shex_text = """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

<ProteinShape> {
  up:name xsd:string+,
  up:organism IRI,
  up:sequence xsd:string?
}
"""

# Parse the schema
parser = ShExParser()
schema = parser.parse(shex_text)

# Access parsed components
print(f"Shapes: {list(schema.shapes.keys())}")
print(f"Prefixes: {schema.prefixes}")
```

### Validating Data

```python
from sparql_agent.schema import ShExParser

# Parse schema
parser = ShExParser()
schema = parser.parse(shex_text)

# Define RDF node data
protein_data = {
    "up:name": ["Hemoglobin subunit alpha"],
    "up:organism": "<http://purl.uniprot.org/taxonomy/9606>",
    "up:sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF"
}

# Validate
is_valid, errors = parser.validate_node(protein_data, "<ProteinShape>")

if is_valid:
    print("✓ Data is valid")
else:
    print("✗ Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

### Using the Validator Class

```python
from sparql_agent.schema import ShExValidator

# Create validator from schema text
validator = ShExValidator(shex_text)

# Validate data
is_valid, errors = validator.validate(protein_data, "<ProteinShape>")
```

### Validating Multiple Nodes

```python
# Define graph data
graph_data = {
    "<http://example.org/protein1>": {
        "up:name": ["Hemoglobin alpha"],
        "up:organism": "<http://purl.uniprot.org/taxonomy/9606>"
    },
    "<http://example.org/protein2>": {
        "up:name": ["Myoglobin"],
        "up:organism": "<http://purl.uniprot.org/taxonomy/9606>"
    }
}

# Map nodes to shapes
node_shape_map = {
    "<http://example.org/protein1>": "<ProteinShape>",
    "<http://example.org/protein2>": "<ProteinShape>"
}

# Validate all nodes
results = validator.validate_graph(graph_data, node_shape_map)

for node_iri, (is_valid, errors) in results.items():
    print(f"{node_iri}: {'Valid' if is_valid else 'Invalid'}")
    if errors:
        for error in errors:
            print(f"  - {error}")
```

## ShEx Syntax Reference

### Shape Definitions

```shex
<ShapeName> {
  # Triple constraints go here
}
```

### Cardinality Modifiers

- No modifier: Exactly one (required)
- `?`: Zero or one (optional)
- `+`: One or more (required, repeatable)
- `*`: Zero or more (optional, repeatable)
- `{n}`: Exactly n occurrences
- `{n,m}`: Between n and m occurrences
- `{n,}`: At least n occurrences

### Node Kinds

```shex
predicate IRI         # Must be an IRI
predicate BNODE       # Must be a blank node
predicate LITERAL     # Must be a literal
predicate NONLITERAL  # Must be IRI or blank node
```

### Datatypes

```shex
predicate xsd:string
predicate xsd:integer
predicate xsd:decimal
predicate xsd:boolean
predicate xsd:date
predicate xsd:dateTime
```

### Value Sets

```shex
# Enumeration of allowed values
predicate [value1 value2 value3]

# With namespace prefixes
predicate [ex:active ex:inactive ex:pending]

# With stems (prefix matching)
predicate [ex:~]  # Matches anything starting with ex:

# With exclusions
predicate [ex:~ - ex:excluded]
```

### Numeric Facets

```shex
predicate xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 100
predicate xsd:decimal MINEXCLUSIVE 0.0 MAXEXCLUSIVE 1.0
```

### String Facets

```shex
predicate xsd:string LENGTH 10
predicate xsd:string MINLENGTH 5 MAXLENGTH 50
predicate xsd:string PATTERN "^[A-Z]+$"
```

### Closed Shapes

```shex
<ClosedShape> {
  predicate1 xsd:string,
  predicate2 xsd:integer
} CLOSED
```

Closed shapes only allow the predicates explicitly listed.

### Shape Inheritance

```shex
<BaseShape> {
  shared:property xsd:string
}

<ExtendedShape> EXTENDS <BaseShape> {
  additional:property xsd:integer
}
```

### Prefixes and Base

```shex
BASE <http://example.org/>
PREFIX ex: <http://example.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

<Shape> {
  ex:predicate xsd:string
}
```

## Protein Shape Example

The module includes a comprehensive example for validating UniProt protein data:

```python
from sparql_agent.schema import PROTEIN_SHAPE_EXAMPLE, ShExParser

parser = ShExParser()
schema = parser.parse(PROTEIN_SHAPE_EXAMPLE)

# The example includes three shapes:
# - <ProteinShape>: For protein entities
# - <OrganismShape>: For organism data
# - <SequenceShape>: For sequence information
```

### Example Protein Shape

```shex
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

<ProteinShape> {
  rdf:type [up:Protein],
  up:name xsd:string+,
  up:organism IRI,
  up:sequence xsd:string?,
  up:mnemonic xsd:string,
  up:mass xsd:integer?,
  up:created xsd:date?,
  up:modified xsd:date?
}
```

## API Reference

### ShExParser

```python
class ShExParser:
    """Parser for ShEx schemas."""

    def parse(self, shex_text: str) -> ShExSchema:
        """Parse a ShEx schema from text."""

    def validate_node(self, node_data: Dict[str, Any], shape_id: str) -> Tuple[bool, List[str]]:
        """Validate an RDF node against a shape."""
```

### ShExValidator

```python
class ShExValidator:
    """Validator for RDF data against ShEx schemas."""

    def __init__(self, schema: Union[str, ShExSchema]):
        """Initialize with a schema string or parsed schema."""

    def validate(self, node_data: Dict[str, Any], shape_id: str) -> Tuple[bool, List[str]]:
        """Validate RDF node data against a shape."""

    def validate_graph(self, graph_data: Dict[str, Dict[str, Any]],
                      node_shape_map: Dict[str, str]) -> Dict[str, Tuple[bool, List[str]]]:
        """Validate multiple nodes in an RDF graph."""
```

### ShExSchema

```python
class ShExSchema:
    """A complete ShEx schema."""

    prefixes: Dict[str, str]  # Prefix definitions
    shapes: Dict[str, Shape]  # Shape definitions
    base: Optional[str]       # Base IRI
    start: Optional[str]      # Start shape

    def add_prefix(self, prefix: str, iri: str):
        """Add a prefix to the schema."""

    def add_shape(self, shape: Shape):
        """Add a shape to the schema."""

    def get_shape(self, shape_id: str) -> Optional[Shape]:
        """Get a shape by ID."""

    def expand_prefix(self, prefixed_name: str) -> str:
        """Expand a prefixed name to a full IRI."""
```

### Shape

```python
class Shape:
    """A ShEx shape definition."""

    id: str                              # Shape identifier
    closed: bool                         # Whether the shape is closed
    extra: List[str]                     # Extra allowed predicates
    expression: List[TripleConstraint]   # Triple constraints
    extends: Optional[str]               # Parent shape ID

    def add_constraint(self, constraint: TripleConstraint):
        """Add a triple constraint to the shape."""
```

### TripleConstraint

```python
class TripleConstraint:
    """A constraint on a single property in a ShEx shape."""

    predicate: str
    value_expr: Optional[Union[str, ValueSet, Shape]]
    cardinality: Cardinality
    node_kind: Optional[NodeKind]
    datatype: Optional[str]
    min_inclusive: Optional[Any]
    max_inclusive: Optional[Any]
    min_exclusive: Optional[Any]
    max_exclusive: Optional[Any]
    pattern: Optional[str]
    length: Optional[int]
    min_length: Optional[int]
    max_length: Optional[int]
```

## Testing

Run the test suite:

```bash
python3 test_shex_direct.py
```

Run the module demo:

```bash
python3 -m sparql_agent.schema.shex_parser
```

## Implementation Details

### Comment Handling

The parser correctly handles comments while preserving `#` characters inside IRIs:

```shex
PREFIX ex: <http://example.org/schema#>  # This is a comment
```

### Brace Matching

The parser uses careful brace counting to properly parse nested shape definitions and handle complex structures.

### Prefix Expansion

Prefixed names are automatically expanded to full IRIs during validation and schema manipulation.

## Limitations

- The current implementation provides basic ShEx 2.0 support
- Some advanced ShEx features may not be fully implemented
- For production use with complex schemas, consider using PyShEx library
- The validator performs structural validation but may not catch all semantic issues

## Future Enhancements

- Full ShEx 2.1+ support
- SHACL-like advanced features
- Graph pattern matching
- Semantic actions
- Better error messages with line numbers
- Schema composition and modularization
- Performance optimizations for large schemas

## References

- [ShEx Specification](http://shex.io/shex-semantics/)
- [ShEx Primer](http://shex.io/shex-primer/)
- [PyShEx](https://github.com/hsolbrig/PyShEx)
- [UniProt RDF](https://www.uniprot.org/help/rdf_schema)

## License

MIT

## Author

Part of the SPARQL Agent project.
