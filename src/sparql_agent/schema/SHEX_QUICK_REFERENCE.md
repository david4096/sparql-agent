# ShEx Quick Reference Guide

## Import

```python
from sparql_agent.schema import ShExParser, ShExValidator
```

## Parse Schema

```python
parser = ShExParser()
schema = parser.parse(shex_text)
```

## Validate Data

```python
is_valid, errors = parser.validate_node(data, "<ShapeName>")
```

## Cardinality

| Symbol | Meaning | Example |
|--------|---------|---------|
| (none) | Exactly one (required) | `ex:name xsd:string` |
| `?` | Zero or one (optional) | `ex:age xsd:integer?` |
| `+` | One or more | `ex:email xsd:string+` |
| `*` | Zero or more | `ex:tag xsd:string*` |

## Node Kinds

```shex
predicate IRI         # Must be an IRI
predicate BNODE       # Must be a blank node
predicate LITERAL     # Must be a literal value
predicate NONLITERAL  # IRI or blank node
```

## Datatypes

```shex
xsd:string
xsd:integer
xsd:decimal
xsd:boolean
xsd:date
xsd:dateTime
```

## Value Sets

```shex
ex:status [ex:pending ex:active ex:completed]
```

## Numeric Constraints

```shex
ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 120
ex:price xsd:decimal MINEXCLUSIVE 0.0
```

## String Constraints

```shex
ex:code xsd:string LENGTH 5
ex:name xsd:string MINLENGTH 1 MAXLENGTH 100
ex:id xsd:string PATTERN "^[A-Z]{3}[0-9]{3}$"
```

## Closed Shapes

```shex
<StrictShape> {
  ex:name xsd:string,
  ex:value xsd:integer
} CLOSED
```

Only allows listed predicates.

## Complete Example

```shex
PREFIX ex: <http://example.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

<PersonShape> {
  ex:name xsd:string MINLENGTH 1,
  ex:age xsd:integer MININCLUSIVE 0?,
  ex:email xsd:string+,
  ex:status [ex:active ex:inactive]
}
```

## Python Usage

```python
# Parse
parser = ShExParser()
schema = parser.parse(shex_text)

# Validate
person = {
    "ex:name": "Alice",
    "ex:age": "30",
    "ex:email": ["alice@example.org"],
    "ex:status": "ex:active"
}

is_valid, errors = parser.validate_node(person, "<PersonShape>")

if is_valid:
    print("Valid!")
else:
    for error in errors:
        print(f"Error: {error}")
```

## Common Patterns

### Required Fields
```shex
ex:required_field xsd:string
```

### Optional Fields
```shex
ex:optional_field xsd:string?
```

### Multiple Values
```shex
ex:tags xsd:string*
ex:authors xsd:string+
```

### IRI References
```shex
ex:relatedTo IRI*
```

### Constrained Values
```shex
ex:priority [ex:low ex:medium ex:high]
```

### Ranges
```shex
ex:percentage xsd:decimal MININCLUSIVE 0.0 MAXINCLUSIVE 100.0
```

### String Patterns
```shex
ex:zipcode xsd:string PATTERN "^[0-9]{5}$"
```
