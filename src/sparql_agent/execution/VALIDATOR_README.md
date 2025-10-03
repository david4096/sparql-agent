# SPARQL Query Validator

Comprehensive SPARQL query syntax validation module with detailed error reporting and suggestions.

## Overview

The SPARQL Query Validator provides robust validation for SPARQL 1.1 queries, including:

- **Syntax Validation**: Uses rdflib to parse and validate SPARQL syntax
- **Prefix Management**: Validates prefix declarations and usage
- **Variable Consistency**: Checks variable usage and consistency
- **URI/Literal Validation**: Validates URIs and literal syntax
- **Bracket Balancing**: Ensures balanced parentheses, braces, and brackets
- **Common Error Detection**: Identifies common SPARQL syntax mistakes
- **Best Practice Suggestions**: Provides recommendations in strict mode
- **Detailed Error Reports**: Line/column positions with suggested fixes

## Installation

The validator requires the following dependencies (already included in the project):

```bash
pip install rdflib>=7.0.0
```

## Quick Start

### Basic Validation

```python
from sparql_agent.execution import validate_query

query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?s ?p ?o
WHERE {
    ?s ?p ?o .
}
LIMIT 10
"""

result = validate_query(query)

if result.is_valid:
    print("Query is valid!")
else:
    print("Query has errors:")
    for error in result.errors:
        print(f"  - {error.message}")
```

### Validate and Raise Exception

```python
from sparql_agent.execution import validate_and_raise
from sparql_agent.core.exceptions import QuerySyntaxError

try:
    result = validate_and_raise(query)
    # Query is valid, proceed with execution
    execute(query)
except QuerySyntaxError as e:
    print(f"Invalid query: {e.message}")
    print(f"Suggestion: {e.details.get('suggestion')}")
```

### Strict Mode

```python
from sparql_agent.execution import validate_query

result = validate_query(query, strict=True)

# Strict mode provides additional best practice suggestions
for suggestion in result.info_issues:
    print(f"Suggestion: {suggestion.message}")
```

## API Reference

### Functions

#### `validate_query(query: str, strict: bool = False) -> ValidationResult`

Validates a SPARQL query and returns detailed results.

**Parameters:**
- `query` (str): The SPARQL query string to validate
- `strict` (bool): Enable strict validation mode with best practice checks

**Returns:**
- `ValidationResult`: Validation result with issues and metadata

**Example:**
```python
result = validate_query(query, strict=True)
print(result.get_summary())
print(result.format_report())
```

#### `validate_and_raise(query: str, strict: bool = False) -> ValidationResult`

Validates a query and raises an exception if invalid.

**Parameters:**
- `query` (str): The SPARQL query string to validate
- `strict` (bool): Enable strict validation mode

**Returns:**
- `ValidationResult`: Validation result if query is valid

**Raises:**
- `QuerySyntaxError`: If query has syntax errors
- `QueryValidationError`: If query fails validation

**Example:**
```python
try:
    result = validate_and_raise(query)
except QuerySyntaxError as e:
    handle_error(e)
```

### Classes

#### `QueryValidator`

Main validator class for SPARQL queries.

**Constructor:**
```python
validator = QueryValidator(strict=False)
```

**Parameters:**
- `strict` (bool): Enable strict validation mode

**Methods:**

##### `validate(query: str) -> ValidationResult`

Validates a SPARQL query.

```python
validator = QueryValidator(strict=True)
result = validator.validate(query)
```

**Class Attributes:**
- `KEYWORDS`: Set of SPARQL keywords
- `STANDARD_PREFIXES`: Dictionary of standard namespace prefixes

#### `ValidationResult`

Contains the results of query validation.

**Attributes:**
- `is_valid` (bool): Whether the query is valid
- `query` (str): The original query
- `issues` (List[ValidationIssue]): All validation issues found
- `warnings` (List[str]): Warning messages
- `parsed_query` (Optional[Query]): Parsed query object if successful
- `metadata` (Dict): Validation metadata

**Properties:**
- `errors`: List of error-level issues
- `warning_issues`: List of warning-level issues
- `info_issues`: List of info/suggestion-level issues

**Methods:**

##### `get_summary() -> str`

Returns a summary of validation results.

```python
print(result.get_summary())
# Output: "Query is valid with 2 warnings and 1 suggestion"
```

##### `format_report() -> str`

Formats a detailed validation report.

```python
print(result.format_report())
# Output:
# Query is valid with 2 warnings and 1 suggestion
#
# WARNINGS:
#   [WARNING] Line 3: Prefix 'unused' declared but never used
#     Suggestion: Remove unused PREFIX declaration
# ...
```

#### `ValidationIssue`

Represents a single validation issue.

**Attributes:**
- `severity` (ValidationSeverity): Severity level (ERROR, WARNING, INFO)
- `message` (str): Human-readable description
- `line` (Optional[int]): Line number (1-indexed)
- `column` (Optional[int]): Column number (1-indexed)
- `query_fragment` (Optional[str]): The problematic fragment
- `suggestion` (Optional[str]): Suggested fix
- `rule` (Optional[str]): Rule that detected the issue

**String Representation:**
```python
print(str(issue))
# Output: [ERROR] Line 5:10: Unclosed brace
#   Fragment: WHERE {
#   Suggestion: Add closing '}'
```

#### `ValidationSeverity`

Enum for issue severity levels.

**Values:**
- `ERROR`: Syntax error that prevents execution
- `WARNING`: Potential issue that may cause problems
- `INFO`: Suggestion for best practices

## Validation Rules

### Syntax Validation

The validator checks SPARQL syntax using rdflib's parser:

```python
# Valid syntax
query = """
SELECT ?s WHERE { ?s ?p ?o . }
"""

# Invalid syntax (missing closing brace)
query = """
SELECT ?s WHERE { ?s ?p ?o .
"""
# Error: Unclosed brace
```

### Prefix Validation

#### Undeclared Prefixes

```python
query = """
SELECT ?s WHERE {
    ?s rdf:type ?type .
}
"""
# Error: Prefix 'rdf' used but not declared
# Suggestion: Add: PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
```

#### Unused Prefixes

```python
query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX unused: <http://example.org/unused#>
SELECT ?s WHERE {
    ?s rdf:type ?type .
}
"""
# Warning: Prefix 'unused' declared but never used
# Suggestion: Remove unused PREFIX declaration
```

#### Duplicate Prefixes

```python
query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?s WHERE { ?s rdf:type ?type . }
"""
# Error: Duplicate PREFIX declaration for 'rdf'
```

### Variable Validation

#### Unused Select Variables

```python
query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?s ?p ?unused
WHERE {
    ?s ?p ?o .
}
"""
# Warning: Variable ?unused selected but not used in WHERE clause
# Suggestion: Remove ?unused from SELECT or use it in WHERE clause
```

#### Single-Use Variables

```python
query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?s
WHERE {
    ?s rdf:type ?singleUse .
}
"""
# Info: Variable ?singleUse appears only once (might be intentional)
# Suggestion: Verify ?singleUse is correct or consider using blank node _:singleUse
```

### URI Validation

#### URIs with Spaces

```python
query = """
SELECT ?s WHERE {
    ?s ?p <http://example.org/invalid uri> .
}
"""
# Error: URI contains spaces
# Suggestion: Remove spaces from URI or encode them as %20
```

#### Malformed URIs

```python
query = """
SELECT ?s WHERE {
    ?s ?p <not-a-valid-uri> .
}
"""
# Warning: URI may be malformed
# Suggestion: Ensure URI starts with http://, https://, or urn:
```

### Bracket Balancing

```python
query = """
SELECT ?s WHERE {
    FILTER(?s > 10
}
"""
# Error: Unclosed parenthesis
# Suggestion: Add closing ')'
```

### Common Errors

#### Double Dot

```python
query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?s WHERE {
    ?s rdf:type ?type ..
}
"""
# Error: Double dot found
# Suggestion: Use single '.' to end triple patterns
```

#### Orphan Semicolon/Comma

```python
query = """
SELECT ?s WHERE {
    ; ?p ?o .
}
"""
# Error: Semicolon without previous statement
# Suggestion: Remove semicolon or add subject
```

### Best Practices (Strict Mode)

#### SELECT *

```python
query = """
SELECT * WHERE { ?s ?p ?o . }
"""
# Info: Using SELECT * is discouraged in production
# Suggestion: Explicitly list the variables you need
```

#### Missing LIMIT

```python
query = """
SELECT ?s WHERE { ?s ?p ?o . }
"""
# Info: Query has no LIMIT clause
# Suggestion: Consider adding LIMIT to prevent large result sets
```

## Error Reporting

### Detailed Error Information

Each validation issue includes:

1. **Severity Level**: ERROR, WARNING, or INFO
2. **Message**: Clear description of the issue
3. **Location**: Line and column numbers (when available)
4. **Fragment**: The problematic code fragment
5. **Suggestion**: How to fix the issue
6. **Rule**: The validation rule that detected it

Example:

```python
result = validate_query(invalid_query)
for issue in result.issues:
    print(f"[{issue.severity.value.upper()}]", end=" ")
    if issue.line:
        print(f"Line {issue.line}", end="")
        if issue.column:
            print(f":{issue.column}", end="")
        print(": ", end="")
    print(issue.message)
    if issue.query_fragment:
        print(f"  Fragment: {issue.query_fragment}")
    if issue.suggestion:
        print(f"  Suggestion: {issue.suggestion}")
    print()
```

### Filtering Issues by Severity

```python
result = validate_query(query)

# Get only errors
errors = result.errors
# or: errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]

# Get only warnings
warnings = result.warning_issues

# Get only suggestions
suggestions = result.info_issues
```

## Advanced Usage

### Custom Validation Workflow

```python
from sparql_agent.execution import QueryValidator, ValidationSeverity

def validate_and_fix(query: str, max_attempts: int = 3) -> str:
    """Validate and attempt to fix common issues."""
    validator = QueryValidator(strict=True)

    for attempt in range(max_attempts):
        result = validator.validate(query)

        if result.is_valid:
            return query

        # Try to auto-fix some issues
        for error in result.errors:
            if "undeclared" in error.message.lower() and error.suggestion:
                # Add missing prefix
                query = error.suggestion + "\n" + query
            elif "unclosed" in error.message.lower():
                # Add missing closing bracket
                if "brace" in error.message.lower():
                    query += "\n}"
                elif "parenthesis" in error.message.lower():
                    query += ")"

    return query  # Return last attempt even if not valid
```

### Integration with Query Execution

```python
from sparql_agent.execution import validate_and_raise
from sparql_agent.core.exceptions import QuerySyntaxError

def safe_execute(query: str, endpoint: str):
    """Validate before executing."""
    try:
        # Validate first
        validate_and_raise(query, strict=False)

        # Execute if valid
        results = execute_sparql(endpoint, query)
        return results

    except QuerySyntaxError as e:
        print(f"Query validation failed: {e.message}")
        print(f"Suggestion: {e.details.get('suggestion')}")
        return None
```

### Batch Validation

```python
from sparql_agent.execution import QueryValidator

def validate_query_batch(queries: List[str]) -> Dict[str, ValidationResult]:
    """Validate multiple queries."""
    validator = QueryValidator(strict=True)
    results = {}

    for i, query in enumerate(queries):
        result = validator.validate(query)
        results[f"query_{i}"] = result

        if not result.is_valid:
            print(f"Query {i} failed validation:")
            print(result.format_report())

    return results
```

## Testing

The validator includes comprehensive tests:

```bash
# Run all tests
pytest src/sparql_agent/execution/test_validator.py -v

# Run specific test
pytest src/sparql_agent/execution/test_validator.py::TestQueryValidator::test_valid_simple_query -v

# Run with coverage
pytest src/sparql_agent/execution/test_validator.py --cov=sparql_agent.execution.validator
```

## Examples

See `validator_examples.py` for complete examples:

```bash
# Run all examples
python src/sparql_agent/execution/validator_examples.py

# Run in Python REPL
python
>>> from sparql_agent.execution.validator_examples import *
>>> example_basic_validation()
>>> example_invalid_query()
>>> example_strict_mode()
```

## Standard Prefixes

The validator recognizes common namespace prefixes:

| Prefix | Namespace URI |
|--------|--------------|
| rdf | http://www.w3.org/1999/02/22-rdf-syntax-ns# |
| rdfs | http://www.w3.org/2000/01/rdf-schema# |
| owl | http://www.w3.org/2002/07/owl# |
| xsd | http://www.w3.org/2001/XMLSchema# |
| skos | http://www.w3.org/2004/02/skos/core# |
| dc | http://purl.org/dc/elements/1.1/ |
| dcterms | http://purl.org/dc/terms/ |
| foaf | http://xmlns.com/foaf/0.1/ |
| schema | http://schema.org/ |

These are automatically suggested when an undeclared standard prefix is used.

## Performance

The validator is optimized for performance:

- **Fast parsing**: Uses rdflib's optimized SPARQL parser
- **Efficient regex**: Pre-compiled patterns for common checks
- **Early exit**: Stops on fatal errors when appropriate
- **Caching**: Reuses validator instances for batch processing

Typical validation times:
- Small queries (<100 lines): < 10ms
- Medium queries (100-500 lines): 10-50ms
- Large queries (>500 lines): 50-200ms

## Limitations

Current limitations:

1. **Multi-line string detection**: Heuristic-based, may have false positives
2. **Property path validation**: Limited validation of complex property paths
3. **SPARQL 1.1 features**: Some advanced features have basic validation only
4. **Update operations**: Limited validation for UPDATE queries
5. **Federated queries**: Basic SERVICE clause validation

Future improvements planned:
- Enhanced property path validation
- Deeper SPARQL Update validation
- Query complexity analysis
- Performance estimation
- Auto-fix suggestions

## Contributing

To add new validation rules:

1. Add rule method to `QueryValidator` class:
```python
def _check_my_rule(self, query: str) -> List[ValidationIssue]:
    """Check for my custom rule."""
    issues = []
    # Implement rule logic
    return issues
```

2. Call rule method in `validate()`:
```python
issues.extend(self._check_my_rule(query))
```

3. Add tests in `test_validator.py`:
```python
def test_my_rule(self):
    """Test my custom rule."""
    query = "..."
    result = validate_query(query)
    assert not result.is_valid
```

## License

MIT License - See project LICENSE file for details.
