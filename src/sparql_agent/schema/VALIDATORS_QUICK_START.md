# Validators Quick Start Guide

## Installation

The validators module is part of the sparql-agent schema package:

```python
from sparql_agent.schema import (
    ShExParser,
    ConstraintValidator,
    ValidationReport,
    ViolationType,
    Severity
)
```

## 5-Minute Quick Start

### 1. Define a Schema

```python
schema_text = """
PREFIX ex: <http://example.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

<PersonShape> {
  ex:name xsd:string,
  ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150,
  ex:email xsd:string PATTERN "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
}
"""
```

### 2. Create Validator

```python
parser = ShExParser()
schema = parser.parse(schema_text)
validator = ConstraintValidator(schema)
```

### 3. Validate Data

```python
person_data = {
    "ex:name": "Alice Johnson",
    "ex:age": 30,
    "ex:email": "alice@example.com"
}

report = validator.validate(person_data, "<PersonShape>")

if report.is_valid:
    print("✓ Data is valid!")
else:
    print(f"✗ Found {report.error_count} errors:")
    for violation in report.violations:
        print(f"  {violation}")
```

## Common Patterns

### Required/Optional Fields

```shex
<Shape> {
  ex:required xsd:string,     # Exactly one (required)
  ex:optional xsd:string?,    # Zero or one (optional)
  ex:multiple xsd:string+,    # One or more (required list)
  ex:list xsd:string*         # Zero or more (optional list)
}
```

### Type Validation

```shex
<DataShape> {
  ex:text xsd:string,
  ex:number xsd:integer,
  ex:price xsd:decimal,
  ex:active xsd:boolean,
  ex:date xsd:date,
  ex:url xsd:anyURI
}
```

### Range Constraints

```shex
<RangeShape> {
  ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150,
  ex:percentage xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 100,
  ex:temperature xsd:float MINEXCLUSIVE -273.15
}
```

### String Patterns

```shex
<StringShape> {
  ex:email xsd:string PATTERN "^[a-z0-9]+@[a-z0-9]+\\.[a-z]+$",
  ex:phone xsd:string MINLENGTH 10 MAXLENGTH 15,
  ex:zip xsd:string LENGTH 5
}
```

### Value Sets

```shex
<StatusShape> {
  ex:status [ex:active ex:inactive ex:pending]
}
```

### Closed Shapes

```shex
<StrictShape> {
  ex:name xsd:string,
  ex:age xsd:integer
} CLOSED
# Only ex:name and ex:age allowed, no other properties
```

## Batch Validation

```python
# Validate multiple nodes
people = [
    {"ex:name": "Alice", "ex:age": 30, "ex:email": "alice@example.com"},
    {"ex:name": "Bob", "ex:age": 25, "ex:email": "bob@example.com"},
    {"ex:name": "Charlie", "ex:age": 35, "ex:email": "charlie@example.com"}
]

reports = validator.validate_batch(people, "<PersonShape>")

# Count results
valid = sum(1 for r in reports if r.is_valid)
print(f"{valid}/{len(reports)} valid")
```

## Graph Validation

```python
# Validate different nodes with different shapes
graph_data = {
    "person:1": {"ex:name": "Alice", "ex:age": 30},
    "org:1": {"ex:name": "Acme Corp", "ex:employees": 100}
}

node_shape_map = {
    "person:1": "<PersonShape>",
    "org:1": "<OrganizationShape>"
}

results = validator.validate_graph(graph_data, node_shape_map)

for node_id, report in results.items():
    print(f"{node_id}: {'✓' if report.is_valid else '✗'}")
```

## Error Handling

```python
report = validator.validate(data, "<Shape>")

if not report.is_valid:
    # Get all errors
    for violation in report.violations:
        print(f"Error: {violation.message}")
        print(f"Fix: {violation.fix_suggestion}")

    # Get specific error types
    cardinality_errors = report.get_violations_by_type(ViolationType.CARDINALITY)
    datatype_errors = report.get_violations_by_type(ViolationType.DATATYPE)

    # Get errors for specific property
    age_errors = report.get_violations_by_predicate("ex:age")

    # Export for logging
    report_dict = report.to_dict()
```

## Helper Functions

### URI Pattern Validation

```python
from sparql_agent.schema import validate_uri_pattern

is_valid = validate_uri_pattern(
    uri="http://example.org/person/123",
    pattern=r"http://example\.org/person/\d+",
    namespace="http://example.org/"
)
```

### Cross-Reference Validation

```python
from sparql_agent.schema import validate_cross_reference

is_valid, error = validate_cross_reference(
    source_value="person:123",
    target_graph=graph_data,
    required_properties=["ex:name", "ex:email"]
)

if not is_valid:
    print(f"Reference error: {error}")
```

## Common Error Types

| Type | Description | Example |
|------|-------------|---------|
| `CARDINALITY` | Wrong number of values | Missing required field |
| `DATATYPE` | Wrong data type | String where integer expected |
| `NUMERIC_RANGE` | Out of range | Age = 200 (max 150) |
| `STRING_PATTERN` | Pattern mismatch | Invalid email format |
| `STRING_LENGTH` | Invalid length | Phone too short |
| `VALUE_SET` | Not in allowed set | Invalid status value |
| `NODE_KIND` | Wrong node type | Literal where IRI expected |
| `CLOSED_SHAPE` | Unexpected property | Extra fields on closed shape |

## Validation Report

```python
report = validator.validate(data, "<Shape>")

# Basic properties
report.is_valid          # True/False
report.error_count       # Number of errors
report.warning_count     # Number of warnings
report.checked_constraints  # Number of constraints checked
report.validation_time   # Time in seconds

# Violations
report.violations        # List of ConstraintViolation objects
report.warnings         # List of warnings
report.info_messages    # List of info messages

# Methods
report.get_violations_by_type(ViolationType.CARDINALITY)
report.get_violations_by_predicate("ex:age")
report.to_dict()        # Convert to dict for JSON
print(report)           # Formatted output
```

## Best Practices

1. **Validate Early**: Check data at ingestion time
2. **Use Closed Shapes**: Catch unexpected properties
3. **Provide Patterns**: Use regex for string validation
4. **Set Ranges**: Define min/max for numeric values
5. **Batch Process**: Use batch validation for efficiency
6. **Log Reports**: Keep validation reports for debugging
7. **Handle Warnings**: Don't ignore warnings

## Performance Tips

- Cache parsed schemas
- Use batch validation for multiple nodes
- Avoid complex regex patterns if performance is critical
- Consider async validation for large datasets

## Complete Example

```python
from sparql_agent.schema import ShExParser, ConstraintValidator

# 1. Define schema
schema = """
PREFIX ex: <http://example.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

<PersonShape> {
  ex:name xsd:string MINLENGTH 1,
  ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150,
  ex:email xsd:string PATTERN "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
  ex:status [ex:active ex:inactive]
} CLOSED
"""

# 2. Parse and create validator
parser = ShExParser()
parsed_schema = parser.parse(schema)
validator = ConstraintValidator(parsed_schema)

# 3. Validate data
data = {
    "ex:name": "John Doe",
    "ex:age": 30,
    "ex:email": "john@example.com",
    "ex:status": "ex:active"
}

report = validator.validate(data, "<PersonShape>")

# 4. Check results
if report.is_valid:
    print("✓ All validation checks passed!")
else:
    print(f"✗ Validation failed with {report.error_count} error(s):")
    for i, violation in enumerate(report.violations, 1):
        print(f"\n{i}. {violation.predicate}")
        print(f"   Error: {violation.message}")
        print(f"   Fix: {violation.fix_suggestion}")
```

## More Information

- Full documentation: [VALIDATORS_README.md](VALIDATORS_README.md)
- Implementation details: [VALIDATION_IMPLEMENTATION_SUMMARY.md](VALIDATION_IMPLEMENTATION_SUMMARY.md)
- Test suite: [test_validators.py](test_validators.py)
- Main module: [validators.py](validators.py)

## Support

For issues or questions:
1. Check the full documentation
2. Review test cases for examples
3. Check the implementation summary for design decisions
