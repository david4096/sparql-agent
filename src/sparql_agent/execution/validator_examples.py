"""
Example usage of the SPARQL Query Validator.

This module demonstrates various ways to use the QueryValidator class
to validate SPARQL queries and handle validation results.
"""

from sparql_agent.execution.validator import (
    QueryValidator,
    ValidationSeverity,
    validate_and_raise,
    validate_query,
)
from sparql_agent.core.exceptions import QuerySyntaxError


def example_basic_validation():
    """Example: Basic query validation."""
    print("=" * 70)
    print("Example 1: Basic Validation")
    print("=" * 70)

    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?person ?name
    WHERE {
        ?person rdf:type foaf:Person .
        ?person foaf:name ?name .
    }
    LIMIT 100
    """

    result = validate_query(query)

    print(f"Query is valid: {result.is_valid}")
    print(f"Total issues: {len(result.issues)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warning_issues)}")
    print(f"Suggestions: {len(result.info_issues)}")
    print()


def example_invalid_query():
    """Example: Validating an invalid query."""
    print("=" * 70)
    print("Example 2: Invalid Query with Missing Brace")
    print("=" * 70)

    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?s ?p ?o
    WHERE {
        ?s ?p ?o .
    """  # Missing closing brace

    result = validate_query(query)

    print(f"Query is valid: {result.is_valid}")
    print()
    print("Validation Report:")
    print(result.format_report())
    print()


def example_undeclared_prefix():
    """Example: Query with undeclared prefixes."""
    print("=" * 70)
    print("Example 3: Undeclared Prefixes")
    print("=" * 70)

    query = """
    SELECT ?person ?name
    WHERE {
        ?person rdf:type foaf:Person .
        ?person foaf:name ?name .
    }
    """

    result = validate_query(query)

    print(f"Query is valid: {result.is_valid}")
    print()

    if result.errors:
        print("Errors found:")
        for error in result.errors:
            print(f"  - {error.message}")
            if error.suggestion:
                print(f"    Suggestion: {error.suggestion}")
        print()


def example_unused_variables():
    """Example: Query with unused variables."""
    print("=" * 70)
    print("Example 4: Unused Variables")
    print("=" * 70)

    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?person ?name ?age ?unused
    WHERE {
        ?person rdf:type foaf:Person .
        ?person foaf:name ?name .
    }
    """

    result = validate_query(query)

    print(f"Query is valid: {result.is_valid}")
    print()

    if result.warning_issues:
        print("Warnings found:")
        for warning in result.warning_issues:
            print(f"  - {warning.message}")
            if warning.suggestion:
                print(f"    Suggestion: {warning.suggestion}")
        print()


def example_strict_mode():
    """Example: Strict validation mode."""
    print("=" * 70)
    print("Example 5: Strict Mode Validation")
    print("=" * 70)

    query = """
    SELECT *
    WHERE {
        ?s ?p ?o .
    }
    """

    # Normal validation
    result_normal = validate_query(query, strict=False)
    print("Normal mode:")
    print(f"  Valid: {result_normal.is_valid}")
    print(f"  Issues: {len(result_normal.issues)}")
    print()

    # Strict validation
    result_strict = validate_query(query, strict=True)
    print("Strict mode:")
    print(f"  Valid: {result_strict.is_valid}")
    print(f"  Issues: {len(result_strict.issues)}")
    print()

    if result_strict.info_issues:
        print("Suggestions in strict mode:")
        for info in result_strict.info_issues:
            print(f"  - {info.message}")
            if info.suggestion:
                print(f"    Suggestion: {info.suggestion}")
        print()


def example_invalid_uris():
    """Example: Query with invalid URIs."""
    print("=" * 70)
    print("Example 6: Invalid URIs")
    print("=" * 70)

    query = """
    PREFIX ex: <http://example.org/>
    SELECT ?s
    WHERE {
        ?s ex:property <http://example.org/invalid uri with spaces> .
        ?s ex:other <not-a-valid-uri> .
    }
    """

    result = validate_query(query)

    print(f"Query is valid: {result.is_valid}")
    print()

    if result.errors:
        print("Errors found:")
        for error in result.errors:
            print(f"  - {error.message}")
            if error.query_fragment:
                print(f"    Fragment: {error.query_fragment}")
            if error.suggestion:
                print(f"    Suggestion: {error.suggestion}")
        print()


def example_validator_class():
    """Example: Using QueryValidator class directly."""
    print("=" * 70)
    print("Example 7: Using QueryValidator Class")
    print("=" * 70)

    # Create validator instance
    validator = QueryValidator(strict=True)

    queries = [
        """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s WHERE { ?s rdf:type ?type . }
        """,
        """
        SELECT ?s WHERE { ?s ?p ?o }
        """,  # Missing dot
        """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT * WHERE { ?s rdf:type ?type . }
        """,  # SELECT * in strict mode
    ]

    for i, query in enumerate(queries, 1):
        print(f"Query {i}:")
        result = validator.validate(query)
        print(f"  Valid: {result.is_valid}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warning_issues)}")
        print(f"  Suggestions: {len(result.info_issues)}")
        print()


def example_validate_and_raise():
    """Example: Using validate_and_raise function."""
    print("=" * 70)
    print("Example 8: Validate and Raise")
    print("=" * 70)

    # Valid query
    valid_query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?s WHERE { ?s rdf:type ?type . }
    """

    try:
        result = validate_and_raise(valid_query)
        print("Valid query - no exception raised")
        print(f"Result: {result.is_valid}")
    except QuerySyntaxError as e:
        print(f"Unexpected error: {e}")

    print()

    # Invalid query
    invalid_query = """
    SELECT ?s WHERE { ?s ?p ?o
    """  # Missing closing brace

    try:
        result = validate_and_raise(invalid_query)
        print("Query validated successfully")
    except QuerySyntaxError as e:
        print("Expected error caught:")
        print(f"  Message: {e.message}")
        if e.details:
            print(f"  Line: {e.details.get('line')}")
            print(f"  Column: {e.details.get('column')}")
            print(f"  Suggestion: {e.details.get('suggestion')}")

    print()


def example_complex_query():
    """Example: Validating a complex query."""
    print("=" * 70)
    print("Example 9: Complex Query Validation")
    print("=" * 70)

    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX ex: <http://example.org/>

    SELECT DISTINCT ?person ?name ?friendName ?age
    WHERE {
        # Find people
        ?person rdf:type foaf:Person .
        ?person foaf:name ?name .

        # Optional age
        OPTIONAL {
            ?person foaf:age ?age .
            FILTER(?age >= 18 && ?age <= 65)
        }

        # Friends or colleagues
        {
            ?person foaf:knows ?friend .
            ?friend foaf:name ?friendName .
        } UNION {
            ?person ex:colleague ?friend .
            ?friend foaf:name ?friendName .
        }

        # Must have email
        FILTER EXISTS {
            ?person foaf:mbox ?email .
        }

        # Must not be deprecated
        MINUS {
            ?person ex:deprecated "true"^^xsd:boolean .
        }
    }
    GROUP BY ?person ?name ?friendName ?age
    HAVING (COUNT(?friend) > 0)
    ORDER BY DESC(?age) ?name
    LIMIT 100
    OFFSET 0
    """

    result = validate_query(query, strict=True)

    print(f"Query is valid: {result.is_valid}")
    print(f"Total issues: {len(result.issues)}")
    print()

    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  - {error.message}")
        print()

    if result.warning_issues:
        print("Warnings:")
        for warning in result.warning_issues:
            print(f"  - {warning.message}")
        print()

    if result.info_issues:
        print("Suggestions:")
        for info in result.info_issues:
            print(f"  - {info.message}")
        print()


def example_issue_details():
    """Example: Accessing detailed issue information."""
    print("=" * 70)
    print("Example 10: Detailed Issue Information")
    print("=" * 70)

    query = """
    SELECT ?s WHERE {
        ?s ?p ?o .
        ?s rdf:type ?type .
    """  # Missing closing brace and undeclared rdf prefix

    result = validate_query(query)

    print(f"Query is valid: {result.is_valid}")
    print()

    print("Detailed issue information:")
    for i, issue in enumerate(result.issues, 1):
        print(f"\nIssue {i}:")
        print(f"  Severity: {issue.severity.value}")
        print(f"  Message: {issue.message}")
        if issue.line:
            print(f"  Line: {issue.line}")
        if issue.column:
            print(f"  Column: {issue.column}")
        if issue.query_fragment:
            print(f"  Fragment: {issue.query_fragment}")
        if issue.suggestion:
            print(f"  Suggestion: {issue.suggestion}")
        if issue.rule:
            print(f"  Rule: {issue.rule}")

    print()


def example_validation_summary():
    """Example: Using validation summary and report."""
    print("=" * 70)
    print("Example 11: Validation Summary and Report")
    print("=" * 70)

    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX unused: <http://example.org/unused#>

    SELECT ?s ?p ?unused_var
    WHERE {
        ?s ?p ?o .
    }
    """

    result = validate_query(query, strict=True)

    # Short summary
    print("Summary:")
    print(result.get_summary())
    print()

    # Full report
    print("Full Report:")
    print(result.format_report())


def example_filtering_issues():
    """Example: Filtering validation issues by severity."""
    print("=" * 70)
    print("Example 12: Filtering Issues by Severity")
    print("=" * 70)

    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX unused: <http://example.org/unused#>

    SELECT *
    WHERE {
        ?s rdf:type ?singleUse .
    """  # Multiple issues: missing brace, unused prefix, SELECT *, single-use variable

    result = validate_query(query, strict=True)

    print(f"Total issues: {len(result.issues)}")
    print()

    # Filter by severity
    errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
    warnings = [i for i in result.issues if i.severity == ValidationSeverity.WARNING]
    info = [i for i in result.issues if i.severity == ValidationSeverity.INFO]

    print(f"Errors ({len(errors)}):")
    for error in errors:
        print(f"  - {error.message}")
    print()

    print(f"Warnings ({len(warnings)}):")
    for warning in warnings:
        print(f"  - {warning.message}")
    print()

    print(f"Info/Suggestions ({len(info)}):")
    for i in info:
        print(f"  - {i.message}")
    print()


def example_metadata():
    """Example: Accessing validation metadata."""
    print("=" * 70)
    print("Example 13: Validation Metadata")
    print("=" * 70)

    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?s WHERE { ?s rdf:type ?type . }
    """

    result = validate_query(query, strict=True)

    print("Validation Metadata:")
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")
    print()


def main():
    """Run all examples."""
    examples = [
        example_basic_validation,
        example_invalid_query,
        example_undeclared_prefix,
        example_unused_variables,
        example_strict_mode,
        example_invalid_uris,
        example_validator_class,
        example_validate_and_raise,
        example_complex_query,
        example_issue_details,
        example_validation_summary,
        example_filtering_issues,
        example_metadata,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"Error in {example_func.__name__}: {e}")
            print()


if __name__ == "__main__":
    main()
