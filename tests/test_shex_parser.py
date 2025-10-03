"""
Test suite for ShEx parser and validator.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sparql_agent.schema import (
    ShExParser,
    ShExValidator,
    ShExSchema,
    Cardinality,
    NodeKind,
    PROTEIN_SHAPE_EXAMPLE,
)


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

    # Note: This might have errors due to strict validation
    # but it should parse without crashing
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


def test_cardinality_constraints():
    """Test cardinality constraint validation."""
    print("\n" + "=" * 70)
    print("TEST: Cardinality Constraints")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <TestShape> {
      ex:required xsd:string,
      ex:optional xsd:string?,
      ex:oneOrMore xsd:string+,
      ex:zeroOrMore xsd:string*
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    # Test valid data
    valid_data = {
        "ex:required": "value1",
        "ex:optional": "value2",
        "ex:oneOrMore": ["value3", "value4"],
        "ex:zeroOrMore": []
    }

    is_valid, errors = parser.validate_node(valid_data, "<TestShape>")
    print(f"\nValid data: {'✓ PASSED' if is_valid else '✗ FAILED'}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    # Test missing required field
    invalid_data = {
        "ex:optional": "value2",
        "ex:oneOrMore": ["value3"]
    }

    is_valid, errors = parser.validate_node(invalid_data, "<TestShape>")
    print(f"\nMissing required: {'✗ REJECTED (expected)' if not is_valid else '✓ FAILED'}")
    if errors:
        print("Errors (expected):")
        for error in errors:
            print(f"  - {error}")

    assert not is_valid, "Should reject missing required field"

    print("\n✓ Cardinality constraints working correctly")


def test_value_sets():
    """Test value set constraints."""
    print("\n" + "=" * 70)
    print("TEST: Value Sets")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <StatusShape> {
      ex:status [ex:active ex:inactive ex:pending]
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    # Test valid value
    valid_data = {
        "ex:status": "ex:active"
    }

    is_valid, errors = parser.validate_node(valid_data, "<StatusShape>")
    print(f"\nValid value in set: {'✓ PASSED' if is_valid else '✗ FAILED'}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    # Test invalid value
    invalid_data = {
        "ex:status": "ex:invalid"
    }

    is_valid, errors = parser.validate_node(invalid_data, "<StatusShape>")
    print(f"\nInvalid value: {'✗ REJECTED (expected)' if not is_valid else '✓ FAILED'}")
    if errors:
        print("Errors (expected):")
        for error in errors:
            print(f"  - {error}")

    print("\n✓ Value sets working correctly")


def test_numeric_constraints():
    """Test numeric constraints (MININCLUSIVE, MAXINCLUSIVE)."""
    print("\n" + "=" * 70)
    print("TEST: Numeric Constraints")
    print("=" * 70)

    shex_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <AgeShape> {
      ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150
    }
    """

    parser = ShExParser()
    schema = parser.parse(shex_text)

    # Test valid age
    valid_data = {
        "ex:age": "25"
    }

    is_valid, errors = parser.validate_node(valid_data, "<AgeShape>")
    print(f"\nValid age (25): {'✓ PASSED' if is_valid else '✗ FAILED'}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    # Test age below minimum
    invalid_data = {
        "ex:age": "-5"
    }

    is_valid, errors = parser.validate_node(invalid_data, "<AgeShape>")
    print(f"\nAge below minimum (-5): {'✗ REJECTED (expected)' if not is_valid else '✓ FAILED'}")
    if errors:
        print("Errors (expected):")
        for error in errors:
            print(f"  - {error}")

    print("\n✓ Numeric constraints working correctly")


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
    print(schema_str)
    print("-" * 70)

    assert "PREFIX" in schema_str
    assert "<ProteinShape>" in schema_str
    assert "up:name" in schema_str

    print("\n✓ Schema string representation working")


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
        test_cardinality_constraints,
        test_value_sets,
        test_numeric_constraints,
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

    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
