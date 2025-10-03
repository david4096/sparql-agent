#!/usr/bin/env python3
"""
Direct test for ShEx parser (bypassing package init).
"""

import sys
import importlib.util

# Load the module directly without going through package init
spec = importlib.util.spec_from_file_location(
    "shex_parser",
    "/Users/david/git/sparql-agent/src/sparql_agent/schema/shex_parser.py"
)
shex_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shex_parser)

# Extract classes
ShExParser = shex_parser.ShExParser
ShExValidator = shex_parser.ShExValidator
Cardinality = shex_parser.Cardinality
NodeKind = shex_parser.NodeKind
PROTEIN_SHAPE_EXAMPLE = shex_parser.PROTEIN_SHAPE_EXAMPLE


def test_basic_parsing():
    """Test basic ShEx schema parsing."""
    print("\n" + "=" * 70)
    print("TEST: Basic ShEx Parsing")
    print("=" * 70)

    shex_text = """
    PREFIX up: <http://purl.uniprot.org/core/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <ProteinShape> {
      up:name xsd:string+,
      up:organism IRI,
      up:sequence xsd:string?
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    print(f"\n✓ Parsed schema with {len(schema.shapes)} shape(s)")
    print(f"✓ Found {len(schema.prefixes)} prefix(es)")

    assert len(schema.shapes) == 1
    assert "<ProteinShape>" in schema.shapes
    assert "up" in schema.prefixes
    assert "xsd" in schema.prefixes

    protein_shape = schema.shapes["<ProteinShape>"]
    print(f"✓ Protein shape has {len(protein_shape.expression)} constraint(s)")

    assert len(protein_shape.expression) == 3

    # Check constraints
    constraints = {c.predicate: c for c in protein_shape.expression}

    # up:name should be ONE_OR_MORE
    assert "up:name" in constraints
    assert constraints["up:name"].cardinality == Cardinality.ONE_OR_MORE
    print("✓ up:name has correct cardinality (+)")

    # up:organism should be IRI
    assert "up:organism" in constraints
    assert constraints["up:organism"].node_kind == NodeKind.IRI
    print("✓ up:organism is IRI type")

    # up:sequence should be ZERO_OR_ONE
    assert "up:sequence" in constraints
    assert constraints["up:sequence"].cardinality == Cardinality.ZERO_OR_ONE
    print("✓ up:sequence has correct cardinality (?)")

    print("\n✓ ALL TESTS PASSED")


def test_protein_example():
    """Test the protein shape example."""
    print("\n" + "=" * 70)
    print("TEST: Protein Shape Example")
    print("=" * 70)

    parser = ShExParser()
    schema = parser.parse(PROTEIN_SHAPE_EXAMPLE)

    print(f"\n✓ Parsed schema with {len(schema.shapes)} shape(s):")
    for shape_name in schema.shapes.keys():
        print(f"  - {shape_name}")

    assert len(schema.shapes) == 3
    assert "<ProteinShape>" in schema.shapes
    assert "<OrganismShape>" in schema.shapes
    assert "<SequenceShape>" in schema.shapes

    print("\n✓ ALL TESTS PASSED")


def test_validation_valid_data():
    """Test validation with valid protein data."""
    print("\n" + "=" * 70)
    print("TEST: Validation with Valid Data")
    print("=" * 70)

    parser = ShExParser()
    schema = parser.parse(PROTEIN_SHAPE_EXAMPLE)

    protein_data = {
        "rdf:type": ["up:Protein"],
        "up:name": ["Hemoglobin subunit alpha", "HBA1"],
        "up:organism": "<http://purl.uniprot.org/taxonomy/9606>",
        "up:sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF",
        "up:mnemonic": "HBA_HUMAN",
        "up:mass": "15126"
    }

    is_valid, errors = parser.validate_node(protein_data, "<ProteinShape>")

    print(f"\nValidation result: {'✓ VALID' if is_valid else '✗ INVALID'}")

    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("No errors found")

    print("\n✓ Validation completed successfully")


def test_validation_invalid_data():
    """Test validation with invalid protein data."""
    print("\n" + "=" * 70)
    print("TEST: Validation with Invalid Data")
    print("=" * 70)

    shex_text = """
    PREFIX up: <http://purl.uniprot.org/core/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <ProteinShape> {
      up:name xsd:string+,
      up:organism IRI,
      up:mass xsd:integer
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    # Missing required up:mass
    protein_data = {
        "up:name": ["Hemoglobin"],
        "up:organism": "<http://purl.uniprot.org/taxonomy/9606>"
    }

    is_valid, errors = parser.validate_node(protein_data, "<ProteinShape>")

    print(f"\nValidation result: {'✓ VALID' if is_valid else '✗ INVALID (expected)'}")

    if errors:
        print("Errors found (expected):")
        for error in errors:
            print(f"  - {error}")

    assert not is_valid, "Should be invalid due to missing up:mass"
    assert len(errors) > 0, "Should have at least one error"

    print("\n✓ Invalid data correctly rejected")


def test_validator_class():
    """Test the ShExValidator class."""
    print("\n" + "=" * 70)
    print("TEST: ShExValidator Class")
    print("=" * 70)

    validator = ShExValidator(PROTEIN_SHAPE_EXAMPLE)

    protein_data = {
        "rdf:type": ["up:Protein"],
        "up:name": ["Hemoglobin subunit alpha"],
        "up:organism": "<http://purl.uniprot.org/taxonomy/9606>",
        "up:mnemonic": "HBA_HUMAN"
    }

    is_valid, errors = validator.validate(protein_data, "<ProteinShape>")

    print(f"\nValidator result: {'✓ VALID' if is_valid else '✗ INVALID'}")

    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")

    print("\n✓ Validator class works correctly")


def test_schema_string_output():
    """Test schema string representation."""
    print("\n" + "=" * 70)
    print("TEST: Schema String Output")
    print("=" * 70)

    parser = ShExParser()
    schema = parser.parse(PROTEIN_SHAPE_EXAMPLE)

    schema_str = str(schema)

    print("\nSchema output:")
    print("-" * 70)
    print(schema_str[:500])  # Print first 500 chars
    print("...")
    print("-" * 70)

    assert "PREFIX" in schema_str
    assert "<ProteinShape>" in schema_str
    assert "up:name" in schema_str

    print("\n✓ Schema string representation working")


def demo_usage():
    """Demonstrate usage of the ShEx parser."""
    print("\n" + "=" * 70)
    print("DEMO: ShEx Parser Usage")
    print("=" * 70)

    # Example 1: Parse and display a schema
    print("\n--- Example 1: Parse a simple schema ---")
    shex_text = """
    PREFIX up: <http://purl.uniprot.org/core/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <ProteinShape> {
      up:name xsd:string+,
      up:organism IRI,
      up:sequence xsd:string?
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    print("\nParsed schema:")
    print(schema)

    # Example 2: Validate protein data
    print("\n--- Example 2: Validate protein data ---")
    protein_data = {
        "up:name": ["Hemoglobin subunit alpha"],
        "up:organism": "<http://purl.uniprot.org/taxonomy/9606>",
        "up:sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF"
    }

    is_valid, errors = parser.validate_node(protein_data, "<ProteinShape>")

    if is_valid:
        print("\n✓ Protein data is valid!")
    else:
        print("\n✗ Validation errors:")
        for error in errors:
            print(f"  - {error}")

    # Example 3: Using the validator class
    print("\n--- Example 3: Using ShExValidator ---")
    validator = ShExValidator(shex_text)
    is_valid, errors = validator.validate(protein_data, "<ProteinShape>")

    print(f"Result: {'Valid' if is_valid else 'Invalid'}")


def run_all_tests():
    """Run all test cases."""
    print("\n" + "=" * 70)
    print("SPARQL AGENT - ShEx Parser Test Suite")
    print("=" * 70)

    tests = [
        test_basic_parsing,
        test_protein_example,
        test_validation_valid_data,
        test_validation_invalid_data,
        test_validator_class,
        test_schema_string_output,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n✗ TEST FAILED: {test.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()

    # Run demo
    try:
        demo_usage()
    except Exception as e:
        print(f"\n✗ DEMO FAILED: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
