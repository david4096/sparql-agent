# Constraint Validation and Rules

## Overview

The `validators.py` module provides comprehensive constraint checking and validation of RDF data against ShEx (Shape Expressions) shapes. It offers detailed error reporting, fix suggestions, and support for all common ShEx constraints.

## Key Features

- ✅ **Cardinality Validation**: Required/optional properties, one-or-more, zero-or-more
- ✅ **Datatype Validation**: Full XSD datatype support (string, integer, date, boolean, etc.)
- ✅ **Value Set Validation**: Enumerated values with stem matching and exclusions
- ✅ **Numeric Range Validation**: Min/max inclusive/exclusive constraints
- ✅ **String Constraints**: Pattern matching, length validation (min/max/exact)
- ✅ **Node Kind Validation**: IRI, blank node, literal constraints
- ✅ **Closed/Open Shapes**: Validate unexpected properties
- ✅ **Cross-Reference Validation**: Validate references between nodes
- ✅ **URI Pattern Validation**: Validate URI structure and namespaces
- ✅ **Batch Validation**: Validate multiple nodes efficiently
- ✅ **Detailed Error Reports**: User-friendly messages with fix suggestions

## Quick Start

```python
from sparql_agent.schema import ShExParser, ConstraintValidator

# Define a ShEx schema
schema_text = """
PREFIX ex: <http://example.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

<PersonShape> {
  ex:name xsd:string,
  ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150,
  ex:email xsd:string PATTERN "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
}
"""

# Parse schema and create validator
parser = ShExParser()
schema = parser.parse(schema_text)
validator = ConstraintValidator(schema)

# Validate data
person_data = {
    "ex:name": "Alice Johnson",
    "ex:age": 30,
    "ex:email": "alice@example.com"
}

report = validator.validate(person_data, "<PersonShape>")

if report.is_valid:
    print("✓ Validation passed!")
else:
    print(f"✗ Found {report.error_count} error(s)")
    for violation in report.violations:
        print(f"  - {violation}")
```

## Core Classes

### ConstraintValidator

The main validator class that checks RDF data against ShEx shapes.

```python
validator = ConstraintValidator(schema)

# Validate a single node
report = validator.validate(node_data, "<ShapeID>", node_id="optional_node_id")

# Validate multiple nodes with a mapping
graph_results = validator.validate_graph(
    graph_data={"node1": {...}, "node2": {...}},
    node_shape_map={"node1": "<Shape1>", "node2": "<Shape2>"}
)

# Validate a batch of nodes against the same shape
reports = validator.validate_batch(
    nodes=[{...}, {...}, {...}],
    shape_id="<PersonShape>"
)
```

### ValidationReport

Comprehensive validation report with detailed information.

```python
report = validator.validate(data, "<Shape>")

# Check validation result
if report.is_valid:
    print("Validation passed!")

# Access violations
for violation in report.violations:
    print(f"Type: {violation.violation_type}")
    print(f"Predicate: {violation.predicate}")
    print(f"Message: {violation.message}")
    print(f"Fix: {violation.fix_suggestion}")

# Get violations by type
cardinality_errors = report.get_violations_by_type(ViolationType.CARDINALITY)
datatype_errors = report.get_violations_by_type(ViolationType.DATATYPE)

# Get violations for a specific predicate
name_errors = report.get_violations_by_predicate("ex:name")

# Convert to dictionary (for JSON serialization)
report_dict = report.to_dict()

# Display formatted report
print(report)  # Shows formatted output with errors, warnings, and suggestions
```

### ConstraintViolation

Represents a single constraint violation with detailed information.

```python
violation = ConstraintViolation(
    violation_type=ViolationType.NUMERIC_RANGE,
    severity=Severity.ERROR,
    predicate="ex:age",
    message="Value is above maximum",
    actual_value=200,
    expected="<= 150",
    fix_suggestion="Use a value <= 150"
)
```

## Violation Types

```python
class ViolationType(Enum):
    CARDINALITY = "cardinality"           # Wrong number of values
    DATATYPE = "datatype"                 # Wrong data type
    NODE_KIND = "node_kind"               # Wrong node kind (IRI/literal/bnode)
    VALUE_SET = "value_set"               # Value not in allowed set
    NUMERIC_RANGE = "numeric_range"       # Numeric value out of range
    STRING_PATTERN = "string_pattern"     # String doesn't match pattern
    STRING_LENGTH = "string_length"       # String length invalid
    CLOSED_SHAPE = "closed_shape"         # Unexpected properties
    REQUIRED_PROPERTY = "required_property"  # Required property missing
    CROSS_REFERENCE = "cross_reference"   # Invalid reference
    URI_PATTERN = "uri_pattern"           # Invalid URI format
```

## Constraint Examples

### 1. Cardinality Constraints

```shex
<PersonShape> {
  ex:name xsd:string,      # Exactly one (default)
  ex:nickname xsd:string?, # Zero or one (optional)
  ex:email xsd:string+,    # One or more (required, multiple)
  ex:phone xsd:string*     # Zero or more (optional, multiple)
}
```

```python
# Valid: Exactly one name
data = {"ex:name": "Alice"}

# Valid: Multiple emails
data = {"ex:name": "Alice", "ex:email": ["alice@work.com", "alice@home.com"]}

# Invalid: No name (required)
data = {"ex:email": "alice@example.com"}
```

### 2. Datatype Validation

```shex
<DataShape> {
  ex:count xsd:integer,
  ex:price xsd:decimal,
  ex:score xsd:float,
  ex:active xsd:boolean,
  ex:created xsd:date,
  ex:updated xsd:dateTime,
  ex:website xsd:anyURI
}
```

Supported XSD datatypes:
- `xsd:string`, `xsd:integer`, `xsd:decimal`, `xsd:float`, `xsd:double`
- `xsd:boolean`, `xsd:date`, `xsd:dateTime`, `xsd:time`
- `xsd:anyURI`, `xsd:positiveInteger`, `xsd:nonNegativeInteger`
- `xsd:negativeInteger`, `xsd:nonPositiveInteger`

### 3. Numeric Range Constraints

```shex
<PersonShape> {
  ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150,
  ex:temperature xsd:float MINEXCLUSIVE -273.15,
  ex:percentage xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 100
}
```

### 4. String Constraints

```shex
<ContactShape> {
  # Pattern matching
  ex:email xsd:string PATTERN "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",

  # Length constraints
  ex:phone xsd:string MINLENGTH 10 MAXLENGTH 15,
  ex:zip xsd:string LENGTH 5,
  ex:username xsd:string MINLENGTH 3 MAXLENGTH 20
}
```

### 5. Value Sets

```shex
<StatusShape> {
  # Enumerated values
  ex:status [ex:active ex:inactive ex:pending],

  # With stem (prefix matching)
  ex:country [us:~ ca:~ mx:~],

  # With exclusion
  ex:role [ex:admin ex:user - ex:guest]
}
```

### 6. Node Kind Constraints

```shex
<PersonShape> {
  ex:name LITERAL,           # Must be a literal value
  ex:homepage IRI,           # Must be an IRI
  ex:relatedNode BNODE,      # Must be a blank node
  ex:organization NONLITERAL # Must be IRI or blank node (not literal)
}
```

### 7. Closed Shapes

```shex
<PersonShape> {
  ex:name xsd:string,
  ex:age xsd:integer
} CLOSED

# Only ex:name and ex:age are allowed
# Any other properties will cause a validation error
```

### 8. Cross-Reference Validation

```python
from sparql_agent.schema import validate_cross_reference

graph_data = {
    "person:123": {
        "ex:name": "Alice",
        "ex:email": "alice@example.com"
    },
    "person:456": {
        "ex:name": "Bob",
        "ex:manager": "person:123"  # Reference to Alice
    }
}

# Validate that the reference exists and has required properties
is_valid, error = validate_cross_reference(
    source_value="person:123",
    target_graph=graph_data,
    required_properties=["ex:name", "ex:email"]
)

if not is_valid:
    print(f"Cross-reference error: {error}")
```

### 9. URI Pattern Validation

```python
from sparql_agent.schema import validate_uri_pattern

# Validate URI structure
is_valid = validate_uri_pattern(
    uri="http://example.org/person/123",
    pattern=r"http://example\.org/person/\d+",
    namespace="http://example.org/"
)

if not is_valid:
    print("URI does not match expected pattern")
```

## Common Patterns

### Required/Optional Properties

```python
from sparql_agent.schema import create_required_optional_validator

# Generate a ShEx schema from property lists
schema_text = create_required_optional_validator(
    required_properties=["ex:name", "ex:email"],
    optional_properties=["ex:phone", "ex:address"],
    datatype_map={
        "ex:name": "xsd:string",
        "ex:email": "xsd:string",
        "ex:phone": "xsd:string",
        "ex:address": "xsd:string"
    }
)

parser = ShExParser()
schema = parser.parse(schema_text)
validator = ConstraintValidator(schema)
```

## Validation Report Format

The validation report provides rich, structured information:

```
======================================================================
Validation Report for Shape: <PersonShape>
Node: person:123
======================================================================
✗ VALIDATION FAILED with 3 error(s)

Errors:
----------------------------------------------------------------------
1. [ERROR] ex:age: Value is above maximum (got: 200) (expected: <= 150)
  💡 Fix: Use a value <= 150

2. [ERROR] ex:email: Value does not match required pattern (got: "invalid")
  💡 Fix: Ensure value matches the pattern ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$

3. [ERROR] Closed shape violation: found 1 unexpected predicate(s) (got: ['ex:extraProp'])
  💡 Fix: Remove these predicates: ex:extraProp

⚠ 1 warning(s) found

Warnings:
----------------------------------------------------------------------
1. [WARNING] ex:phone: Value is too short (got: "123" (length: 3)) (expected: length >= 10)
  💡 Fix: Use a value with at least 10 characters

Validation completed in 0.003s
======================================================================
```

## Error Messages and Fix Suggestions

The validator provides user-friendly error messages with actionable fix suggestions:

| Error Type | Example Message | Fix Suggestion |
|------------|----------------|----------------|
| Cardinality | "Property must have exactly one value" | "Add a value for ex:name" |
| Datatype | "Expected integer, got invalid value" | "Use a valid integer value" |
| Numeric Range | "Value is above maximum" | "Use a value <= 150" |
| String Pattern | "Value does not match required pattern" | "Ensure value matches the pattern ..." |
| String Length | "Value is too short" | "Use a value with at least 10 characters" |
| Node Kind | "Value must be an IRI" | "Use a valid IRI for ex:homepage" |
| Value Set | "Value not in allowed value set" | "Use one of the allowed values: ex:active, ex:inactive" |
| Closed Shape | "Closed shape violation: unexpected predicates" | "Remove these predicates: ex:extraProp" |

## Advanced Usage

### Custom Validation Rules

You can extend the validator with custom rules:

```python
class CustomValidator(ConstraintValidator):
    def validate(self, node_data, shape_id, node_id=None):
        # Get base validation report
        report = super().validate(node_data, shape_id, node_id)

        # Add custom validation logic
        if "ex:email" in node_data:
            email = node_data["ex:email"]
            if isinstance(email, str) and "example.com" in email:
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.DATATYPE,
                    severity=Severity.WARNING,
                    predicate="ex:email",
                    message="Email uses example.com domain",
                    actual_value=email,
                    fix_suggestion="Use a real email domain"
                ))

        return report
```

### Filtering Validation Results

```python
# Get only errors (not warnings)
errors = [v for v in report.violations if v.severity == Severity.ERROR]

# Get violations for specific predicates
critical_props = ["ex:name", "ex:email"]
critical_violations = [
    v for v in report.violations
    if v.predicate in critical_props
]

# Get specific types of violations
datatype_errors = report.get_violations_by_type(ViolationType.DATATYPE)
cardinality_errors = report.get_violations_by_type(ViolationType.CARDINALITY)
```

### Batch Processing with Statistics

```python
reports = validator.validate_batch(nodes, "<PersonShape>")

# Calculate statistics
total = len(reports)
valid = sum(1 for r in reports if r.is_valid)
invalid = total - valid
total_errors = sum(r.error_count for r in reports)
total_warnings = sum(r.warning_count for r in reports)

print(f"Validated {total} nodes:")
print(f"  ✓ {valid} valid ({100*valid/total:.1f}%)")
print(f"  ✗ {invalid} invalid ({100*invalid/total:.1f}%)")
print(f"  Total errors: {total_errors}")
print(f"  Total warnings: {total_warnings}")

# Find most common error types
from collections import Counter
error_types = Counter(
    v.violation_type
    for r in reports
    for v in r.violations
)

print("\nMost common errors:")
for error_type, count in error_types.most_common(5):
    print(f"  {error_type.value}: {count}")
```

## Integration with SPARQL Agent

The validator integrates seamlessly with the SPARQL agent workflow:

```python
from sparql_agent.schema import (
    VoIDParser,
    SchemaInferencer,
    ConstraintValidator
)

# 1. Discover schema from endpoint
void_parser = VoIDParser()
void_data = void_parser.discover_endpoint("http://example.org/sparql")

# 2. Infer constraints from data patterns
inferencer = SchemaInferencer()
schema = inferencer.infer_from_void(void_data)

# 3. Validate new data against inferred schema
validator = ConstraintValidator(schema.to_shex())
report = validator.validate(new_data, "<InferredShape>")

if not report.is_valid:
    print("Data quality issues found:")
    for violation in report.violations:
        print(f"  - {violation}")
```

## Performance Considerations

- Batch validation is more efficient than individual validation
- Validation time scales linearly with number of constraints
- Complex regex patterns in string constraints may impact performance
- Consider caching validators for frequently-used shapes

## Best Practices

1. **Use Closed Shapes**: Define closed shapes to catch unexpected properties
2. **Provide Fix Suggestions**: Custom validators should include fix suggestions
3. **Validate Early**: Validate data at ingestion time to catch errors early
4. **Log Validation Reports**: Keep validation reports for auditing and debugging
5. **Use Batch Validation**: Process multiple nodes together for better performance
6. **Handle Warnings**: Don't ignore warnings - they often indicate data quality issues
7. **Test Schemas**: Validate your schemas with test data before production use

## Comparison with PyShEx

This implementation provides several advantages over PyShEx:

| Feature | validators.py | PyShEx |
|---------|--------------|---------|
| User-friendly errors | ✅ | ❌ |
| Fix suggestions | ✅ | ❌ |
| Batch validation | ✅ | Limited |
| Cross-reference validation | ✅ | ❌ |
| URI pattern validation | ✅ | ❌ |
| Structured reports | ✅ | ❌ |
| No external dependencies | ✅ | ❌ |
| Detailed violation info | ✅ | Basic |

## Troubleshooting

### Common Issues

**Issue**: Validation fails for valid data
- **Solution**: Check that prefixes are correctly defined and expanded

**Issue**: Pattern matching fails
- **Solution**: Escape special regex characters (especially backslashes in patterns)

**Issue**: Cardinality errors for optional properties
- **Solution**: Ensure optional properties use `?` or `*` modifiers

**Issue**: Closed shape violations
- **Solution**: Either add properties to the shape or remove CLOSED constraint

## See Also

- [shex_parser.py](shex_parser.py) - ShEx schema parsing
- [metadata_inference.py](metadata_inference.py) - Schema inference from data
- [void_parser.py](void_parser.py) - VoID metadata parsing
- [ontology_mapper.py](ontology_mapper.py) - Vocabulary detection

## References

- [ShEx Specification](https://shex.io/shex-semantics/)
- [XSD Datatypes](https://www.w3.org/TR/xmlschema-2/)
- [RDF Validation Requirements](https://www.w3.org/2014/data-shapes/wiki/Requirements)
