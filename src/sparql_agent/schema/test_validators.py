"""
Test suite for the validators module.

This test file demonstrates the functionality of the ConstraintValidator
and ValidationReport classes.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sparql_agent.schema.shex_parser import ShExParser
from sparql_agent.schema.validators import (
    ConstraintValidator,
    ValidationReport,
    ViolationType,
    Severity,
    validate_uri_pattern,
    validate_cross_reference,
)


def test_basic_validation():
    """Test basic constraint validation."""
    print("Test 1: Basic Validation")
    print("-" * 70)

    schema_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <PersonShape> {
      ex:name xsd:string,
      ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150
    }
    """

    parser = ShExParser()
    schema = parser.parse(schema_text)
    validator = ConstraintValidator(schema)

    # Valid data
    valid_person = {
        'ex:name': 'Alice Johnson',
        'ex:age': 30
    }

    report = validator.validate(valid_person, '<PersonShape>')
    assert report.is_valid == True
    assert report.error_count == 0
    print("✓ Valid data test passed")

    # Invalid age
    invalid_person = {
        'ex:name': 'Bob Smith',
        'ex:age': 200
    }

    report = validator.validate(invalid_person, '<PersonShape>')
    assert report.is_valid == False
    assert report.error_count > 0
    assert any(v.violation_type == ViolationType.NUMERIC_RANGE for v in report.violations)
    print("✓ Invalid age test passed")
    print()


def test_cardinality_validation():
    """Test cardinality constraint validation."""
    print("Test 2: Cardinality Validation")
    print("-" * 70)

    schema_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <PersonShape> {
      ex:name xsd:string+,
      ex:nickname xsd:string*,
      ex:ssn xsd:string?
    }
    """

    parser = ShExParser()
    schema = parser.parse(schema_text)
    validator = ConstraintValidator(schema)

    # Missing required field (name)
    data = {
        'ex:nickname': ['Bob', 'Bobby']
    }

    report = validator.validate(data, '<PersonShape>')
    assert report.is_valid == False
    assert any(v.violation_type == ViolationType.CARDINALITY for v in report.violations)
    print("✓ Missing required field test passed")

    # Valid with multiple values
    data = {
        'ex:name': ['Robert Smith', 'Bob Smith'],
        'ex:nickname': ['Bob', 'Bobby', 'Rob'],
        'ex:ssn': '123-45-6789'
    }

    report = validator.validate(data, '<PersonShape>')
    assert report.is_valid == True
    print("✓ Multiple values test passed")
    print()


def test_datatype_validation():
    """Test datatype validation."""
    print("Test 3: Datatype Validation")
    print("-" * 70)

    schema_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <DataShape> {
      ex:count xsd:integer,
      ex:price xsd:float,
      ex:active xsd:boolean,
      ex:created xsd:date
    }
    """

    parser = ShExParser()
    schema = parser.parse(schema_text)
    validator = ConstraintValidator(schema)

    # Invalid integer
    data = {
        'ex:count': 'not a number',
        'ex:price': 19.99,
        'ex:active': True,
        'ex:created': '2024-01-01'
    }

    report = validator.validate(data, '<DataShape>')
    assert report.is_valid == False
    assert any(v.violation_type == ViolationType.DATATYPE for v in report.violations)
    print("✓ Invalid integer test passed")

    # All valid datatypes
    data = {
        'ex:count': 42,
        'ex:price': 19.99,
        'ex:active': True,
        'ex:created': '2024-01-01'
    }

    report = validator.validate(data, '<DataShape>')
    assert report.is_valid == True
    print("✓ Valid datatypes test passed")
    print()


def test_string_constraints():
    """Test string pattern and length constraints."""
    print("Test 4: String Constraints")
    print("-" * 70)

    schema_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <ContactShape> {
      ex:email xsd:string PATTERN "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
      ex:phone xsd:string MINLENGTH 10 MAXLENGTH 15,
      ex:zip xsd:string LENGTH 5
    }
    """

    parser = ShExParser()
    schema = parser.parse(schema_text)
    validator = ConstraintValidator(schema)

    # Invalid email pattern
    data = {
        'ex:email': 'invalid-email',
        'ex:phone': '555-123-4567',
        'ex:zip': '12345'
    }

    report = validator.validate(data, '<ContactShape>')
    assert report.is_valid == False
    assert any(v.violation_type == ViolationType.STRING_PATTERN for v in report.violations)
    print("✓ Invalid email pattern test passed")

    # Phone too short
    data = {
        'ex:email': 'user@example.com',
        'ex:phone': '555',
        'ex:zip': '12345'
    }

    report = validator.validate(data, '<ContactShape>')
    assert report.is_valid == False
    assert any(v.violation_type == ViolationType.STRING_LENGTH for v in report.violations)
    print("✓ Phone too short test passed")

    # All valid
    data = {
        'ex:email': 'user@example.com',
        'ex:phone': '555-123-4567',
        'ex:zip': '12345'
    }

    report = validator.validate(data, '<ContactShape>')
    assert report.is_valid == True
    print("✓ Valid string constraints test passed")
    print()


def test_closed_shape():
    """Test closed shape validation."""
    print("Test 5: Closed Shape Validation")
    print("-" * 70)

    schema_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <PersonShape> {
      ex:name xsd:string,
      ex:age xsd:integer
    } CLOSED
    """

    parser = ShExParser()
    schema = parser.parse(schema_text)
    validator = ConstraintValidator(schema)

    # Extra properties on closed shape
    data = {
        'ex:name': 'Alice',
        'ex:age': 30,
        'ex:unexpectedProp': 'value',
        'ex:anotherProp': 'value2'
    }

    report = validator.validate(data, '<PersonShape>')
    assert report.is_valid == False
    assert any(v.violation_type == ViolationType.CLOSED_SHAPE for v in report.violations)
    print("✓ Closed shape violation test passed")

    # Only allowed properties
    data = {
        'ex:name': 'Alice',
        'ex:age': 30
    }

    report = validator.validate(data, '<PersonShape>')
    assert report.is_valid == True
    print("✓ Valid closed shape test passed")
    print()


def test_node_kind_validation():
    """Test node kind (IRI/BNODE/LITERAL) validation."""
    print("Test 6: Node Kind Validation")
    print("-" * 70)

    schema_text = """
    PREFIX ex: <http://example.org/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    <PersonShape> {
      ex:name LITERAL,
      foaf:homepage IRI
    }
    """

    parser = ShExParser()
    schema = parser.parse(schema_text)
    validator = ConstraintValidator(schema)

    # IRI where literal expected
    data = {
        'ex:name': '<http://example.org/name>',
        'foaf:homepage': 'http://example.com'
    }

    report = validator.validate(data, '<PersonShape>')
    assert report.is_valid == False
    assert any(v.violation_type == ViolationType.NODE_KIND for v in report.violations)
    print("✓ Invalid node kind test passed")

    # Correct node kinds
    data = {
        'ex:name': 'Alice Johnson',
        'foaf:homepage': 'http://alice.example.com'
    }

    report = validator.validate(data, '<PersonShape>')
    assert report.is_valid == True
    print("✓ Valid node kind test passed")
    print()


def test_value_set_validation():
    """Test value set validation."""
    print("Test 7: Value Set Validation")
    print("-" * 70)

    schema_text = """
    PREFIX ex: <http://example.org/>

    <StatusShape> {
      ex:status [ex:active ex:inactive ex:pending]
    }
    """

    parser = ShExParser()
    schema = parser.parse(schema_text)
    validator = ConstraintValidator(schema)

    # Invalid value (not in set)
    data = {
        'ex:status': 'ex:invalid'
    }

    report = validator.validate(data, '<StatusShape>')
    assert report.is_valid == False
    assert any(v.violation_type == ViolationType.VALUE_SET for v in report.violations)
    print("✓ Invalid value set test passed")

    # Valid value (in set)
    data = {
        'ex:status': 'ex:active'
    }

    report = validator.validate(data, '<StatusShape>')
    assert report.is_valid == True
    print("✓ Valid value set test passed")
    print()


def test_batch_validation():
    """Test batch validation of multiple nodes."""
    print("Test 8: Batch Validation")
    print("-" * 70)

    schema_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <PersonShape> {
      ex:name xsd:string,
      ex:age xsd:integer MININCLUSIVE 0
    }
    """

    parser = ShExParser()
    schema = parser.parse(schema_text)
    validator = ConstraintValidator(schema)

    people = [
        {'ex:name': 'Alice', 'ex:age': 30},
        {'ex:name': 'Bob', 'ex:age': -5},  # Invalid
        {'ex:name': 'Charlie', 'ex:age': 25},
    ]

    reports = validator.validate_batch(people, '<PersonShape>')

    assert len(reports) == 3
    assert reports[0].is_valid == True
    assert reports[1].is_valid == False
    assert reports[2].is_valid == True

    print("✓ Batch validation test passed")
    print()


def test_validation_report_formatting():
    """Test validation report formatting."""
    print("Test 9: Validation Report Formatting")
    print("-" * 70)

    schema_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    <PersonShape> {
      ex:name xsd:string,
      ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150,
      ex:email xsd:string PATTERN "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    } CLOSED
    """

    parser = ShExParser()
    schema = parser.parse(schema_text)
    validator = ConstraintValidator(schema)

    # Multiple errors
    data = {
        'ex:name': 'Bob',
        'ex:age': 200,
        'ex:email': 'invalid',
        'ex:extraProp': 'value'
    }

    report = validator.validate(data, '<PersonShape>', node_id='person:123')

    # Check report attributes
    assert report.node_id == 'person:123'
    assert report.error_count > 0
    assert report.total_issues > 0

    # Check that fix suggestions are provided
    assert all(v.fix_suggestion for v in report.violations)

    # Get violations by type
    numeric_violations = report.get_violations_by_type(ViolationType.NUMERIC_RANGE)
    assert len(numeric_violations) > 0

    # Get violations by predicate
    age_violations = report.get_violations_by_predicate('ex:age')
    assert len(age_violations) > 0

    # Convert to dict
    report_dict = report.to_dict()
    assert isinstance(report_dict, dict)
    assert 'is_valid' in report_dict
    assert 'violations' in report_dict

    print("✓ Report formatting test passed")
    print()


def test_uri_pattern_validation():
    """Test URI pattern validation helper."""
    print("Test 10: URI Pattern Validation Helper")
    print("-" * 70)

    # Valid URI matching pattern
    assert validate_uri_pattern(
        'http://example.org/person/123',
        r'http://example\.org/person/\d+',
        'http://example.org/'
    )

    # URI not matching pattern
    assert not validate_uri_pattern(
        'http://example.org/person/abc',
        r'http://example\.org/person/\d+',
        'http://example.org/'
    )

    # Wrong namespace
    assert not validate_uri_pattern(
        'http://other.org/person/123',
        r'http://example\.org/person/\d+',
        'http://example.org/'
    )

    print("✓ URI pattern validation test passed")
    print()


def test_cross_reference_validation():
    """Test cross-reference validation helper."""
    print("Test 11: Cross-Reference Validation Helper")
    print("-" * 70)

    graph_data = {
        'person:123': {
            'ex:name': 'Alice',
            'ex:email': 'alice@example.com'
        },
        'person:456': {
            'ex:name': 'Bob'
        }
    }

    # Valid reference
    is_valid, error = validate_cross_reference(
        'person:123',
        graph_data,
        ['ex:name', 'ex:email']
    )
    assert is_valid == True

    # Reference to non-existent node
    is_valid, error = validate_cross_reference(
        'person:999',
        graph_data
    )
    assert is_valid == False
    assert 'not found' in error

    # Missing required properties
    is_valid, error = validate_cross_reference(
        'person:456',
        graph_data,
        ['ex:name', 'ex:email']
    )
    assert is_valid == False
    assert 'missing required properties' in error.lower()

    print("✓ Cross-reference validation test passed")
    print()


def run_all_tests():
    """Run all test functions."""
    print("=" * 70)
    print("CONSTRAINT VALIDATOR TEST SUITE")
    print("=" * 70)
    print()

    test_functions = [
        test_basic_validation,
        test_cardinality_validation,
        test_datatype_validation,
        test_string_constraints,
        test_closed_shape,
        test_node_kind_validation,
        test_value_set_validation,
        test_batch_validation,
        test_validation_report_formatting,
        test_uri_pattern_validation,
        test_cross_reference_validation,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} ERROR: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
