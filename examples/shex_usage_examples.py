#!/usr/bin/env python3
"""
ShEx Parser Usage Examples

This file demonstrates various use cases for the ShEx parser and validator.
"""

import sys
import importlib.util
from pathlib import Path

# Load the module directly without going through package init
module_path = Path(__file__).parent.parent / "src" / "sparql_agent" / "schema" / "shex_parser.py"
spec = importlib.util.spec_from_file_location("shex_parser", module_path)
shex_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shex_parser)

# Extract classes
ShExParser = shex_parser.ShExParser
ShExValidator = shex_parser.ShExValidator
PROTEIN_SHAPE_EXAMPLE = shex_parser.PROTEIN_SHAPE_EXAMPLE


def example_1_basic_parsing():
    """Example 1: Basic ShEx schema parsing."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic ShEx Parsing")
    print("=" * 70)

    shex_text = """
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <PersonShape> {
        foaf:name xsd:string,
        foaf:age xsd:integer?,
        foaf:email xsd:string+
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    print("\nParsed Schema:")
    print(schema)


def example_2_protein_validation():
    """Example 2: Validating protein data."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Protein Data Validation")
    print("=" * 70)

    parser = ShExParser()
    schema = parser.parse(PROTEIN_SHAPE_EXAMPLE)

    # Valid protein data
    valid_protein = {
        "rdf:type": ["up:Protein"],
        "up:name": ["Hemoglobin subunit alpha", "HBA1"],
        "up:organism": "<http://purl.uniprot.org/taxonomy/9606>",
        "up:sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF",
        "up:mnemonic": "HBA_HUMAN",
        "up:mass": "15126"
    }

    is_valid, errors = parser.validate_node(valid_protein, "<ProteinShape>")

    print(f"\nValidation result: {'✓ VALID' if is_valid else '✗ INVALID'}")
    if errors:
        for error in errors:
            print(f"  Error: {error}")
    else:
        print("  No errors found!")


def example_3_cardinality_validation():
    """Example 3: Testing cardinality constraints."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Cardinality Constraints")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <DocumentShape> {
        ex:title xsd:string,        # Exactly one (required)
        ex:author xsd:string+,      # One or more
        ex:tag xsd:string*,         # Zero or more
        ex:subtitle xsd:string?     # Zero or one (optional)
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    # Test data with various cardinalities
    test_data = {
        "ex:title": "My Document",
        "ex:author": ["Alice", "Bob"],
        "ex:tag": ["science", "research", "python"],
        "ex:subtitle": "A comprehensive guide"
    }

    is_valid, errors = parser.validate_node(test_data, "<DocumentShape>")

    print(f"\nValidation result: {'✓ VALID' if is_valid else '✗ INVALID'}")
    if errors:
        for error in errors:
            print(f"  Error: {error}")


def example_4_value_sets():
    """Example 4: Using value sets (enumerations)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Value Sets")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <TaskShape> {
        ex:title xsd:string,
        ex:status [ex:pending ex:in_progress ex:completed ex:cancelled],
        ex:priority [ex:low ex:medium ex:high]
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    # Valid task
    valid_task = {
        "ex:title": "Implement feature X",
        "ex:status": "ex:in_progress",
        "ex:priority": "ex:high"
    }

    is_valid, errors = parser.validate_node(valid_task, "<TaskShape>")
    print(f"\nValid task: {'✓ PASSED' if is_valid else '✗ FAILED'}")

    # Invalid task with wrong status
    invalid_task = {
        "ex:title": "Implement feature Y",
        "ex:status": "ex:unknown_status",
        "ex:priority": "ex:medium"
    }

    is_valid, errors = parser.validate_node(invalid_task, "<TaskShape>")
    print(f"Invalid task: {'✗ REJECTED' if not is_valid else '✓ UNEXPECTED'}")
    if errors:
        print("  Errors (expected):")
        for error in errors:
            print(f"    - {error}")


def example_5_numeric_constraints():
    """Example 5: Numeric facets (range validation)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Numeric Constraints")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <ProductShape> {
        ex:name xsd:string,
        ex:price xsd:decimal MININCLUSIVE 0.0,
        ex:quantity xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 1000,
        ex:rating xsd:decimal MININCLUSIVE 0.0 MAXINCLUSIVE 5.0
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    # Valid product
    valid_product = {
        "ex:name": "Widget Pro",
        "ex:price": "29.99",
        "ex:quantity": "150",
        "ex:rating": "4.5"
    }

    is_valid, errors = parser.validate_node(valid_product, "<ProductShape>")
    print(f"\nValid product: {'✓ PASSED' if is_valid else '✗ FAILED'}")

    # Invalid product with out-of-range rating
    invalid_product = {
        "ex:name": "Widget Deluxe",
        "ex:price": "49.99",
        "ex:quantity": "50",
        "ex:rating": "6.0"  # Too high!
    }

    is_valid, errors = parser.validate_node(invalid_product, "<ProductShape>")
    print(f"Invalid product (rating > 5): {'✗ REJECTED' if not is_valid else '✓ UNEXPECTED'}")
    if errors:
        print("  Errors (expected):")
        for error in errors:
            print(f"    - {error}")


def example_6_node_kinds():
    """Example 6: Node kind constraints."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Node Kind Constraints")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <ArticleShape> {
        ex:title xsd:string,
        ex:author IRI,           # Must be an IRI
        ex:content LITERAL,      # Must be a literal
        ex:relatedTo IRI*        # Zero or more IRIs
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    # Valid article
    valid_article = {
        "ex:title": "Introduction to RDF",
        "ex:author": "<http://example.org/person/alice>",
        "ex:content": "RDF is a framework for representing information...",
        "ex:relatedTo": [
            "<http://example.org/article/1>",
            "<http://example.org/article/2>"
        ]
    }

    is_valid, errors = parser.validate_node(valid_article, "<ArticleShape>")
    print(f"\nValid article: {'✓ PASSED' if is_valid else '✗ FAILED'}")


def example_7_validator_class():
    """Example 7: Using the ShExValidator class."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: ShExValidator Class")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <UserShape> {
        ex:username xsd:string MINLENGTH 3 MAXLENGTH 20,
        ex:email xsd:string,
        ex:age xsd:integer MININCLUSIVE 13
    }
    """

    # Create validator
    validator = ShExValidator(shex_text)

    # Validate user
    user_data = {
        "ex:username": "alice123",
        "ex:email": "alice@example.org",
        "ex:age": "25"
    }

    is_valid, errors = validator.validate(user_data, "<UserShape>")

    print(f"\nUser validation: {'✓ VALID' if is_valid else '✗ INVALID'}")
    if not is_valid:
        for error in errors:
            print(f"  Error: {error}")


def example_8_graph_validation():
    """Example 8: Validating multiple nodes in a graph."""
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Graph Validation")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <PersonShape> {
        ex:name xsd:string,
        ex:age xsd:integer?
    }

    <CompanyShape> {
        ex:name xsd:string,
        ex:founded xsd:integer
    }
    """

    validator = ShExValidator(shex_text)

    # Graph with multiple nodes
    graph_data = {
        "<http://example.org/person/alice>": {
            "ex:name": "Alice Smith",
            "ex:age": "30"
        },
        "<http://example.org/person/bob>": {
            "ex:name": "Bob Jones",
            "ex:age": "25"
        },
        "<http://example.org/company/acme>": {
            "ex:name": "ACME Corp",
            "ex:founded": "1985"
        }
    }

    # Map nodes to shapes
    node_shape_map = {
        "<http://example.org/person/alice>": "<PersonShape>",
        "<http://example.org/person/bob>": "<PersonShape>",
        "<http://example.org/company/acme>": "<CompanyShape>"
    }

    # Validate all
    results = validator.validate_graph(graph_data, node_shape_map)

    print("\nValidation results:")
    for node_iri, (is_valid, errors) in results.items():
        status = "✓ Valid" if is_valid else "✗ Invalid"
        print(f"  {node_iri}: {status}")
        if errors:
            for error in errors:
                print(f"    - {error}")


def example_9_closed_shapes():
    """Example 9: Closed shapes (no extra properties allowed)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 9: Closed Shapes")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <StrictPersonShape> {
        ex:name xsd:string,
        ex:age xsd:integer
    } CLOSED
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    # Data with extra property
    person_data = {
        "ex:name": "Charlie",
        "ex:age": "35",
        "ex:email": "charlie@example.org"  # Not allowed in closed shape!
    }

    is_valid, errors = parser.validate_node(person_data, "<StrictPersonShape>")

    print(f"\nValidation with extra property: {'✓ VALID' if is_valid else '✗ INVALID (expected)'}")
    if errors:
        print("  Errors (expected):")
        for error in errors:
            print(f"    - {error}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("ShEx Parser Usage Examples")
    print("=" * 70)

    examples = [
        example_1_basic_parsing,
        example_2_protein_validation,
        example_3_cardinality_validation,
        example_4_value_sets,
        example_5_numeric_constraints,
        example_6_node_kinds,
        example_7_validator_class,
        example_8_graph_validation,
        example_9_closed_shapes,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n✗ Example failed: {example_func.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
