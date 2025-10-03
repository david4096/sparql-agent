"""
Test suite and examples for metadata inference.
"""

import pytest
from metadata_inference import (
    MetadataInferencer,
    DataType,
    CardinalityType,
)


class TestMetadataInferencer:
    """Test cases for MetadataInferencer"""

    def test_basic_triple_analysis(self):
        """Test analyzing basic RDF triples"""
        inferencer = MetadataInferencer()

        # Analyze some triples
        triples = [
            ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/name", "Alice"),
            ("http://example.org/person/2", "http://xmlns.com/foaf/0.1/name", "Bob"),
            ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/age", "30"),
            ("http://example.org/person/2", "http://xmlns.com/foaf/0.1/age", "25"),
        ]

        inferencer.analyze_sample_data(triples)

        # Check that properties were discovered
        assert "http://xmlns.com/foaf/0.1/name" in inferencer.metadata.properties
        assert "http://xmlns.com/foaf/0.1/age" in inferencer.metadata.properties

        # Check usage counts
        name_prop = inferencer.metadata.properties["http://xmlns.com/foaf/0.1/name"]
        assert name_prop.usage_count == 2

        age_prop = inferencer.metadata.properties["http://xmlns.com/foaf/0.1/age"]
        assert age_prop.usage_count == 2

    def test_data_type_inference(self):
        """Test data type inference"""
        inferencer = MetadataInferencer()

        # Test different data types
        assert inferencer._infer_data_type("http://example.org") == DataType.URI
        assert inferencer._infer_data_type("123") == DataType.INTEGER
        assert inferencer._infer_data_type("123.45") == DataType.FLOAT
        assert inferencer._infer_data_type("true") == DataType.BOOLEAN
        assert inferencer._infer_data_type("2024-01-15") == DataType.DATE
        assert inferencer._infer_data_type("2024-01-15T10:30:00") == DataType.DATETIME
        assert inferencer._infer_data_type("Hello") == DataType.STRING

    def test_uri_pattern_extraction(self):
        """Test URI pattern extraction"""
        inferencer = MetadataInferencer()

        # Test numeric ID pattern
        pattern = inferencer._extract_uri_pattern("http://example.org/person/123")
        assert pattern == "http://example.org/person/{id}"

        # Test UUID pattern
        uri = "http://example.org/item/550e8400-e29b-41d4-a716-446655440000"
        pattern = inferencer._extract_uri_pattern(uri)
        assert "{uuid}" in pattern

        # Test alphanumeric code pattern
        pattern = inferencer._extract_uri_pattern("http://example.org/product/ABC123DEF")
        assert "{code}" in pattern

    def test_cardinality_inference(self):
        """Test cardinality constraint inference"""
        inferencer = MetadataInferencer()

        # Create triples with one-to-many relationship
        triples = [
            ("http://example.org/person/1", "http://example.org/owns", "http://example.org/car/1"),
            ("http://example.org/person/1", "http://example.org/owns", "http://example.org/car/2"),
            ("http://example.org/person/2", "http://example.org/owns", "http://example.org/car/3"),
        ]

        inferencer.analyze_sample_data(triples)

        owns_prop = inferencer.metadata.properties["http://example.org/owns"]
        # Should detect one-to-many (person can own multiple cars)
        assert owns_prop.cardinality in [CardinalityType.ONE_TO_MANY, CardinalityType.MANY_TO_MANY]

    def test_functional_property_detection(self):
        """Test functional property detection"""
        inferencer = MetadataInferencer()

        # Create triples where each subject has exactly one value
        triples = [
            ("http://example.org/person/1", "http://example.org/hasSSN", "123-45-6789"),
            ("http://example.org/person/2", "http://example.org/hasSSN", "987-65-4321"),
            ("http://example.org/person/3", "http://example.org/hasSSN", "555-55-5555"),
        ]

        inferencer.analyze_sample_data(triples)

        ssn_prop = inferencer.metadata.properties["http://example.org/hasSSN"]
        assert ssn_prop.is_functional

    def test_query_pattern_extraction(self):
        """Test extracting patterns from SPARQL queries"""
        inferencer = MetadataInferencer()

        query = """
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        SELECT ?name ?age WHERE {
            ?person foaf:name ?name .
            ?person foaf:age ?age .
        }
        """

        patterns = inferencer._extract_query_patterns(query)

        # Should extract two triple patterns
        assert len(patterns) >= 2

    def test_namespace_extraction(self):
        """Test namespace extraction"""
        inferencer = MetadataInferencer()

        # Analyze triples with different namespaces
        triples = [
            ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/name", "Alice"),
            ("http://example.org/person/1", "http://purl.org/dc/terms/created", "2024-01-01"),
        ]

        inferencer.analyze_sample_data(triples)

        # Should have extracted namespaces
        assert len(inferencer.metadata.namespaces) >= 2

    def test_quality_issue_detection(self):
        """Test data quality issue detection"""
        inferencer = MetadataInferencer()

        # Create data with inconsistent types
        triples = [
            ("http://example.org/person/1", "http://example.org/value", "123"),
            ("http://example.org/person/2", "http://example.org/value", "abc"),
            ("http://example.org/person/3", "http://example.org/value", "true"),
            ("http://example.org/person/4", "http://example.org/value", "http://example.org/ref"),
        ]

        inferencer.analyze_sample_data(triples)

        # Should detect inconsistent types
        assert len(inferencer.metadata.quality_issues) > 0

    def test_relationship_discovery(self):
        """Test implicit relationship discovery"""
        inferencer = MetadataInferencer()

        type_map = {
            "http://example.org/person/1": ["http://example.org/Person"],
            "http://example.org/company/1": ["http://example.org/Company"],
            "http://example.org/person/2": ["http://example.org/Person"],
        }

        triples = [
            ("http://example.org/person/1", "http://example.org/worksFor", "http://example.org/company/1"),
            ("http://example.org/person/2", "http://example.org/worksFor", "http://example.org/company/1"),
        ]

        inferencer.analyze_sample_data(triples, type_map)

        # Should discover Person->Company relationship
        assert len(inferencer.metadata.relationships) > 0

    def test_class_metadata(self):
        """Test class metadata collection"""
        inferencer = MetadataInferencer()

        type_map = {
            "http://example.org/person/1": ["http://example.org/Person"],
            "http://example.org/person/2": ["http://example.org/Person"],
            "http://example.org/person/3": ["http://example.org/Person"],
        }

        triples = [
            ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/name", "Alice"),
            ("http://example.org/person/2", "http://xmlns.com/foaf/0.1/name", "Bob"),
            ("http://example.org/person/3", "http://xmlns.com/foaf/0.1/name", "Charlie"),
        ]

        inferencer.analyze_sample_data(triples, type_map)

        # Check class metadata
        person_class = inferencer.metadata.classes.get("http://example.org/Person")
        assert person_class is not None
        assert person_class.instance_count == 3

    def test_numeric_statistics(self):
        """Test numeric value statistics"""
        inferencer = MetadataInferencer()

        triples = [
            ("http://example.org/person/1", "http://example.org/age", "25"),
            ("http://example.org/person/2", "http://example.org/age", "30"),
            ("http://example.org/person/3", "http://example.org/age", "35"),
            ("http://example.org/person/4", "http://example.org/age", "40"),
        ]

        inferencer.analyze_sample_data(triples)

        age_prop = inferencer.metadata.properties["http://example.org/age"]
        assert age_prop.min_value == 25.0
        assert age_prop.max_value == 40.0
        assert age_prop.avg_value == 32.5

    def test_summary_report_generation(self):
        """Test summary report generation"""
        inferencer = MetadataInferencer()

        triples = [
            ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/name", "Alice"),
            ("http://example.org/person/2", "http://xmlns.com/foaf/0.1/name", "Bob"),
        ]

        inferencer.analyze_sample_data(triples)

        report = inferencer.generate_summary_report()

        # Should contain key sections
        assert "DATASET METADATA INFERENCE REPORT" in report
        assert "STATISTICS" in report
        assert "NAMESPACES" in report
        assert "DISCOVERED CLASSES" in report or "TOP PROPERTIES" in report


def example_usage():
    """Example usage of MetadataInferencer"""
    print("=" * 80)
    print("METADATA INFERENCE EXAMPLE")
    print("=" * 80)
    print()

    # Create inferencer
    inferencer = MetadataInferencer(min_confidence=0.7, max_samples=100)

    # Sample data about people and organizations
    triples = [
        # People
        ("http://example.org/person/001", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://xmlns.com/foaf/0.1/Person"),
        ("http://example.org/person/001", "http://xmlns.com/foaf/0.1/name", "Alice Smith"),
        ("http://example.org/person/001", "http://xmlns.com/foaf/0.1/age", "30"),
        ("http://example.org/person/001", "http://xmlns.com/foaf/0.1/email", "alice@example.org"),
        ("http://example.org/person/001", "http://example.org/worksFor", "http://example.org/org/1"),

        ("http://example.org/person/002", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://xmlns.com/foaf/0.1/Person"),
        ("http://example.org/person/002", "http://xmlns.com/foaf/0.1/name", "Bob Johnson"),
        ("http://example.org/person/002", "http://xmlns.com/foaf/0.1/age", "35"),
        ("http://example.org/person/002", "http://xmlns.com/foaf/0.1/email", "bob@example.org"),
        ("http://example.org/person/002", "http://example.org/worksFor", "http://example.org/org/1"),

        ("http://example.org/person/003", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://xmlns.com/foaf/0.1/Person"),
        ("http://example.org/person/003", "http://xmlns.com/foaf/0.1/name", "Charlie Davis"),
        ("http://example.org/person/003", "http://xmlns.com/foaf/0.1/age", "28"),
        ("http://example.org/person/003", "http://example.org/worksFor", "http://example.org/org/2"),

        # Organizations
        ("http://example.org/org/1", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://xmlns.com/foaf/0.1/Organization"),
        ("http://example.org/org/1", "http://xmlns.com/foaf/0.1/name", "Tech Corp"),
        ("http://example.org/org/1", "http://example.org/founded", "2010"),

        ("http://example.org/org/2", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://xmlns.com/foaf/0.1/Organization"),
        ("http://example.org/org/2", "http://xmlns.com/foaf/0.1/name", "Data Inc"),
        ("http://example.org/org/2", "http://example.org/founded", "2015"),
    ]

    # Type map
    type_map = {
        "http://example.org/person/001": ["http://xmlns.com/foaf/0.1/Person"],
        "http://example.org/person/002": ["http://xmlns.com/foaf/0.1/Person"],
        "http://example.org/person/003": ["http://xmlns.com/foaf/0.1/Person"],
        "http://example.org/org/1": ["http://xmlns.com/foaf/0.1/Organization"],
        "http://example.org/org/2": ["http://xmlns.com/foaf/0.1/Organization"],
    }

    # Analyze the data
    print("Analyzing sample data...")
    inferencer.analyze_sample_data(triples, type_map)

    # Analyze a sample query
    query = """
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT ?name ?orgName WHERE {
        ?person a foaf:Person .
        ?person foaf:name ?name .
        ?person <http://example.org/worksFor> ?org .
        ?org foaf:name ?orgName .
    }
    """

    print("Analyzing sample query...")
    inferencer.analyze_query(query)

    # Generate and print report
    print()
    report = inferencer.generate_summary_report()
    print(report)

    # Access specific metadata
    print("\nDETAILED PROPERTY INFORMATION")
    print("-" * 80)

    name_prop = inferencer.get_property_info("http://xmlns.com/foaf/0.1/name")
    if name_prop:
        print(f"Property: foaf:name")
        print(f"  Usage: {name_prop.usage_count} times")
        print(f"  Domains: {list(name_prop.domains.keys())}")
        print(f"  Data Types: {list(name_prop.data_types.keys())}")
        print(f"  Functional: {name_prop.is_functional}")
        print(f"  Sample Values: {name_prop.sample_values[:3]}")

    print()
    print("\nDETAILED CLASS INFORMATION")
    print("-" * 80)

    person_class = inferencer.get_class_info("http://xmlns.com/foaf/0.1/Person")
    if person_class:
        print(f"Class: foaf:Person")
        print(f"  Instances: {person_class.instance_count}")
        print(f"  Properties: {len(person_class.properties)}")
        print(f"  Property List: {list(person_class.properties)}")
        print(f"  URI Patterns: {list(person_class.uri_patterns)}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    # Run tests
    print("Running tests...")
    pytest.main([__file__, "-v"])

    print("\n\n")

    # Run example
    example_usage()
