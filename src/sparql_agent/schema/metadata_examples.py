"""
Example usage of MetadataInferencer for various scenarios.
"""

from metadata_inference import MetadataInferencer, DataType, CardinalityType


def example_1_basic_analysis():
    """Example 1: Basic triple analysis"""
    print("=" * 80)
    print("EXAMPLE 1: Basic Triple Analysis")
    print("=" * 80)

    inferencer = MetadataInferencer()

    # Sample triples about people
    triples = [
        ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/name", "Alice Smith"),
        ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/age", "30"),
        ("http://example.org/person/1", "http://xmlns.com/foaf/0.1/email", "alice@example.org"),
        ("http://example.org/person/2", "http://xmlns.com/foaf/0.1/name", "Bob Johnson"),
        ("http://example.org/person/2", "http://xmlns.com/foaf/0.1/age", "35"),
        ("http://example.org/person/2", "http://xmlns.com/foaf/0.1/email", "bob@example.org"),
    ]

    inferencer.analyze_sample_data(triples)

    print("\nDiscovered Properties:")
    for prop_uri, prop_meta in inferencer.metadata.properties.items():
        print(f"\n  {prop_uri}")
        print(f"    Usage: {prop_meta.usage_count} times")
        print(f"    Data Types: {list(prop_meta.data_types.keys())}")
        print(f"    Functional: {prop_meta.is_functional}")

    print("\n" + "=" * 80 + "\n")


def example_2_query_analysis():
    """Example 2: Learning from SPARQL queries"""
    print("=" * 80)
    print("EXAMPLE 2: Query Pattern Learning")
    print("=" * 80)

    inferencer = MetadataInferencer()

    # Sample query
    query = """
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX org: <http://example.org/>

    SELECT ?personName ?companyName WHERE {
        ?person a foaf:Person .
        ?person foaf:name ?personName .
        ?person org:worksFor ?company .
        ?company a foaf:Organization .
        ?company foaf:name ?companyName .
    }
    """

    # Sample results
    results = [
        {"personName": "Alice", "companyName": "Tech Corp"},
        {"personName": "Bob", "companyName": "Data Inc"},
    ]

    inferencer.analyze_query(query, results)

    print("\nExtracted Query Patterns:")
    patterns = inferencer._extract_query_patterns(query)
    for subj, pred, obj in patterns:
        print(f"  {subj} {pred} {obj}")

    print("\nDiscovered Relationships:")
    for rel in inferencer.metadata.relationships:
        print(f"  {rel.subject_type} --[{rel.predicate}]--> {rel.object_type}")
        print(f"    Confidence: {rel.confidence:.2f}")

    print("\n" + "=" * 80 + "\n")


def example_3_uri_patterns():
    """Example 3: URI pattern discovery"""
    print("=" * 80)
    print("EXAMPLE 3: URI Pattern Discovery")
    print("=" * 80)

    inferencer = MetadataInferencer()

    # Triples with various URI patterns
    triples = [
        ("http://example.org/person/001", "http://xmlns.com/foaf/0.1/name", "Alice"),
        ("http://example.org/person/002", "http://xmlns.com/foaf/0.1/name", "Bob"),
        ("http://example.org/person/003", "http://xmlns.com/foaf/0.1/name", "Charlie"),
        ("http://example.org/item/550e8400-e29b-41d4-a716-446655440000", "http://purl.org/dc/terms/title", "Item A"),
        ("http://example.org/item/650e8400-e29b-41d4-a716-446655440001", "http://purl.org/dc/terms/title", "Item B"),
        ("http://example.org/product/ABC123", "http://schema.org/name", "Product A"),
        ("http://example.org/product/XYZ789", "http://schema.org/name", "Product B"),
    ]

    inferencer.analyze_sample_data(triples)

    print("\nDiscovered URI Patterns:")
    for pattern in inferencer.metadata.uri_patterns:
        print(f"\n  Pattern: {pattern.pattern}")
        print(f"    Regex: {pattern.regex}")
        print(f"    Frequency: {pattern.frequency}")
        print(f"    Examples: {pattern.examples[:2]}")

    print("\n" + "=" * 80 + "\n")


def example_4_comprehensive_analysis():
    """Example 4: Comprehensive dataset analysis with full report"""
    print("=" * 80)
    print("EXAMPLE 4: Comprehensive Dataset Analysis")
    print("=" * 80)

    inferencer = MetadataInferencer(min_confidence=0.7, max_samples=100)

    # Type map
    type_map = {
        "http://example.org/person/001": ["http://xmlns.com/foaf/0.1/Person"],
        "http://example.org/person/002": ["http://xmlns.com/foaf/0.1/Person"],
        "http://example.org/person/003": ["http://xmlns.com/foaf/0.1/Person"],
        "http://example.org/org/1": ["http://xmlns.com/foaf/0.1/Organization"],
        "http://example.org/org/2": ["http://xmlns.com/foaf/0.1/Organization"],
    }

    # Comprehensive dataset
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
        ("http://example.org/org/1", "http://example.org/employees", "150"),
        ("http://example.org/org/2", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://xmlns.com/foaf/0.1/Organization"),
        ("http://example.org/org/2", "http://xmlns.com/foaf/0.1/name", "Data Inc"),
        ("http://example.org/org/2", "http://example.org/founded", "2015"),
        ("http://example.org/org/2", "http://example.org/employees", "75"),
    ]

    # Analyze
    inferencer.analyze_sample_data(triples, type_map)

    # Sample query
    query = """
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT ?personName ?orgName WHERE {
        ?person a foaf:Person .
        ?person foaf:name ?personName .
        ?person <http://example.org/worksFor> ?org .
        ?org foaf:name ?orgName .
    }
    """

    inferencer.analyze_query(query)

    # Generate full report
    report = inferencer.generate_summary_report()
    print(report)


def main():
    """Run all examples"""
    examples = [
        example_1_basic_analysis,
        example_2_query_analysis,
        example_3_uri_patterns,
        example_4_comprehensive_analysis,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\nAll examples completed!")


if __name__ == "__main__":
    main()
