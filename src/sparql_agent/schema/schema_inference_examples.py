"""
Schema Inference Examples

Demonstrates the schema inference capabilities for generating ShEx schemas
from RDF data with statistical analysis and quality metrics.
"""

from schema_inference import (
    SchemaInferencer,
    infer_schema_from_sparql,
    ConstraintConfidence
)
from shex_parser import Cardinality


def example_1_basic_inference():
    """Example 1: Basic schema inference from simple data."""
    print("=" * 80)
    print("Example 1: Basic Schema Inference")
    print("=" * 80)

    inferencer = SchemaInferencer()

    # Add some protein data
    proteins = [
        ("http://example.org/protein1", "Hemoglobin", "http://example.org/organism/9606", 64500),
        ("http://example.org/protein2", "Insulin", "http://example.org/organism/9606", 5808),
        ("http://example.org/protein3", "Catalase", "http://example.org/organism/9606", 240000),
    ]

    for uri, name, organism, mass in proteins:
        # Add type
        inferencer.add_triple(uri, "rdf:type", "http://example.org/Protein")

        # Add properties
        inferencer.add_triple(
            uri, "http://example.org/name", name,
            subject_type="http://example.org/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#string"
        )
        inferencer.add_triple(
            uri, "http://example.org/organism", organism,
            subject_type="http://example.org/Protein"
        )
        inferencer.add_triple(
            uri, "http://example.org/mass", mass,
            subject_type="http://example.org/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#integer"
        )

    # Generate schema
    result = inferencer.generate_schema()

    print("\nGenerated ShEx Schema:")
    print("-" * 80)
    print(result.schema)

    print("\nQuality Metrics:")
    print("-" * 80)
    print(f"Total Instances: {result.quality_metrics.total_instances}")
    print(f"Coverage: {result.quality_metrics.coverage:.1%}")
    print(f"Completeness: {result.quality_metrics.completeness:.1%}")
    print(f"Constraint Confidence: {result.quality_metrics.constraint_confidence:.1%}")

    print("\nInference Metadata:")
    print("-" * 80)
    for key, value in result.inference_metadata.items():
        print(f"{key}: {value}")


def example_2_cardinality_inference():
    """Example 2: Inferring different cardinalities."""
    print("\n" + "=" * 80)
    print("Example 2: Cardinality Inference")
    print("=" * 80)

    inferencer = SchemaInferencer()

    # Add proteins with varying property patterns
    for i in range(10):
        protein_uri = f"http://example.org/protein{i}"

        # Type (always present)
        inferencer.add_triple(protein_uri, "rdf:type", "http://example.org/Protein")

        # Name (always present, single value)
        inferencer.add_triple(
            protein_uri, "http://example.org/name", f"Protein {i}",
            subject_type="http://example.org/Protein"
        )

        # Synonyms (always present, multiple values)
        for j in range(3):
            inferencer.add_triple(
                protein_uri, "http://example.org/synonym", f"Synonym {i}-{j}",
                subject_type="http://example.org/Protein"
            )

        # Description (optional, single value)
        if i % 2 == 0:
            inferencer.add_triple(
                protein_uri, "http://example.org/description", f"Description for protein {i}",
                subject_type="http://example.org/Protein"
            )

        # Keywords (optional, multiple values)
        if i % 3 == 0:
            for k in range(2):
                inferencer.add_triple(
                    protein_uri, "http://example.org/keyword", f"Keyword {k}",
                    subject_type="http://example.org/Protein"
                )

    result = inferencer.generate_schema()

    print("\nInferred Cardinalities:")
    print("-" * 80)

    protein_shape = result.schema.shapes.get("<ProteinShape>")
    if protein_shape:
        for constraint in protein_shape.expression:
            prop_name = constraint.predicate.split('/')[-1]
            print(f"{prop_name:20s} -> {constraint.cardinality.value:5s}")

            # Explain the inference
            if constraint.cardinality == Cardinality.EXACTLY_ONE:
                print(f"  {'':20s}    (required, single value)")
            elif constraint.cardinality == Cardinality.ONE_OR_MORE:
                print(f"  {'':20s}    (required, multiple values)")
            elif constraint.cardinality == Cardinality.ZERO_OR_ONE:
                print(f"  {'':20s}    (optional, single value)")
            elif constraint.cardinality == Cardinality.ZERO_OR_MORE:
                print(f"  {'':20s}    (optional, multiple values)")

    print("\nConstraint Confidence Scores:")
    print("-" * 80)
    for class_uri, constraints in result.constraints.items():
        print(f"\nClass: {class_uri.split('/')[-1]}")
        for constraint in constraints:
            if constraint.constraint_type == 'cardinality':
                print(f"  {constraint.confidence.value}: {constraint.explanation}")


def example_3_datatype_inference():
    """Example 3: Inferring datatypes and value constraints."""
    print("\n" + "=" * 80)
    print("Example 3: Datatype and Value Constraint Inference")
    print("=" * 80)

    inferencer = SchemaInferencer()

    # Add diverse data types
    for i in range(5):
        protein_uri = f"http://example.org/protein{i}"

        inferencer.add_triple(protein_uri, "rdf:type", "http://example.org/Protein")

        # String
        inferencer.add_triple(
            protein_uri, "http://example.org/name", f"Protein {i}",
            subject_type="http://example.org/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#string"
        )

        # Integer with range
        inferencer.add_triple(
            protein_uri, "http://example.org/mass", 50000 + i * 1000,
            subject_type="http://example.org/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#integer"
        )

        # Float
        inferencer.add_triple(
            protein_uri, "http://example.org/pi_value", 7.5 + i * 0.1,
            subject_type="http://example.org/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#float"
        )

        # Boolean
        inferencer.add_triple(
            protein_uri, "http://example.org/is_reviewed", i % 2 == 0,
            subject_type="http://example.org/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#boolean"
        )

        # IRI reference
        inferencer.add_triple(
            protein_uri, "http://example.org/organism",
            "http://example.org/organism/9606",
            subject_type="http://example.org/Protein"
        )

    result = inferencer.generate_schema()

    print("\nInferred Datatypes:")
    print("-" * 80)

    protein_shape = result.schema.shapes.get("<ProteinShape>")
    if protein_shape:
        for constraint in protein_shape.expression:
            prop_name = constraint.predicate.split('/')[-1]
            if constraint.datatype:
                print(f"{prop_name:20s} -> {constraint.datatype}")
            elif constraint.node_kind:
                print(f"{prop_name:20s} -> {constraint.node_kind.value}")

    print("\nNumeric Constraints:")
    print("-" * 80)
    for class_uri, constraints in result.constraints.items():
        for constraint in constraints:
            if constraint.constraint_type in ['min_inclusive', 'max_inclusive']:
                print(f"{constraint.constraint_type}: {constraint.value}")
                print(f"  Confidence: {constraint.confidence.value}")
                print(f"  {constraint.explanation}")


def example_4_statistical_analysis():
    """Example 4: Property statistics and quality analysis."""
    print("\n" + "=" * 80)
    print("Example 4: Statistical Analysis and Quality Metrics")
    print("=" * 80)

    inferencer = SchemaInferencer()

    # Add data with varying quality
    for i in range(20):
        protein_uri = f"http://example.org/protein{i}"

        inferencer.add_triple(protein_uri, "rdf:type", "http://example.org/Protein")

        # Well-formed data (all instances)
        inferencer.add_triple(
            protein_uri, "http://example.org/name", f"Protein {i}",
            subject_type="http://example.org/Protein"
        )

        # Moderately consistent data (80% coverage)
        if i < 16:
            inferencer.add_triple(
                protein_uri, "http://example.org/organism",
                "http://example.org/organism/9606",
                subject_type="http://example.org/Protein"
            )

        # Inconsistent data (40% coverage)
        if i < 8:
            inferencer.add_triple(
                protein_uri, "http://example.org/description", f"Description {i}",
                subject_type="http://example.org/Protein"
            )

    result = inferencer.generate_schema()

    print("\nProperty Statistics:")
    print("-" * 80)
    print(f"{'Property':40s} {'Usage':>10s} {'Subjects':>10s} {'Coverage':>10s}")
    print("-" * 80)

    for prop_uri, stats in result.property_stats.items():
        prop_name = prop_uri.split('/')[-1]
        coverage = (stats.subject_count / 20) * 100  # 20 total instances
        print(f"{prop_name:40s} {stats.usage_count:>10d} {stats.subject_count:>10d} {coverage:>9.1f}%")

    print("\nClass Statistics:")
    print("-" * 80)
    for class_uri, stats in result.class_stats.items():
        class_name = class_uri.split('/')[-1]
        print(f"\nClass: {class_name}")
        print(f"  Instances: {stats.instance_count}")
        print(f"  Properties: {len(stats.properties)}")
        print(f"  Required Properties: {len(stats.required_properties)}")
        print(f"  Optional Properties: {len(stats.optional_properties)}")

    print("\nOverall Quality Metrics:")
    print("-" * 80)
    metrics = result.quality_metrics
    print(f"Coverage: {metrics.coverage:.1%}")
    print(f"Completeness: {metrics.completeness:.1%}")
    print(f"Constraint Confidence: {metrics.constraint_confidence:.1%}")
    print(f"Consistency: {metrics.consistency:.1%}")

    if metrics.validation_errors:
        print("\nValidation Errors:")
        for error in metrics.validation_errors[:5]:  # Show first 5
            print(f"  - {error}")


def example_5_real_world_uniprot():
    """Example 5: Real-world UniProt protein data."""
    print("\n" + "=" * 80)
    print("Example 5: Real-World UniProt Protein Data")
    print("=" * 80)

    inferencer = SchemaInferencer(
        min_confidence=0.8,
        cardinality_threshold=0.9,
        optional_threshold=0.85
    )

    # Realistic UniProt protein data
    proteins = [
        {
            "uri": "http://purl.uniprot.org/uniprot/P69905",
            "name": "Hemoglobin subunit alpha",
            "mnemonic": "HBA_HUMAN",
            "organism": "http://purl.uniprot.org/taxonomy/9606",
            "mass": 15258,
            "sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF",
            "function": "Involved in oxygen transport from the lung to various tissues",
            "keywords": ["Oxygen transport", "Heme", "Transport"]
        },
        {
            "uri": "http://purl.uniprot.org/uniprot/P68871",
            "name": "Hemoglobin subunit beta",
            "mnemonic": "HBB_HUMAN",
            "organism": "http://purl.uniprot.org/taxonomy/9606",
            "mass": 15867,
            "sequence": "MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLS",
            "function": "Involved in oxygen transport from the lung to various tissues",
            "keywords": ["Oxygen transport", "Heme", "Transport"]
        },
        {
            "uri": "http://purl.uniprot.org/uniprot/P02100",
            "name": "Hemoglobin subunit epsilon",
            "mnemonic": "HBE_HUMAN",
            "organism": "http://purl.uniprot.org/taxonomy/9606",
            "mass": 16133,
            "keywords": ["Oxygen transport", "Developmental protein"]
        }
    ]

    for protein in proteins:
        # Type
        inferencer.add_triple(
            protein["uri"],
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://purl.uniprot.org/core/Protein"
        )

        # Required properties
        inferencer.add_triple(
            protein["uri"],
            "http://purl.uniprot.org/core/name",
            protein["name"],
            subject_type="http://purl.uniprot.org/core/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#string"
        )

        inferencer.add_triple(
            protein["uri"],
            "http://purl.uniprot.org/core/mnemonic",
            protein["mnemonic"],
            subject_type="http://purl.uniprot.org/core/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#string"
        )

        inferencer.add_triple(
            protein["uri"],
            "http://purl.uniprot.org/core/organism",
            protein["organism"],
            subject_type="http://purl.uniprot.org/core/Protein"
        )

        inferencer.add_triple(
            protein["uri"],
            "http://purl.uniprot.org/core/mass",
            protein["mass"],
            subject_type="http://purl.uniprot.org/core/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#integer"
        )

        # Optional properties
        if "sequence" in protein:
            inferencer.add_triple(
                protein["uri"],
                "http://purl.uniprot.org/core/sequence",
                protein["sequence"],
                subject_type="http://purl.uniprot.org/core/Protein",
                datatype="http://www.w3.org/2001/XMLSchema#string"
            )

        if "function" in protein:
            inferencer.add_triple(
                protein["uri"],
                "http://purl.uniprot.org/core/function",
                protein["function"],
                subject_type="http://purl.uniprot.org/core/Protein",
                datatype="http://www.w3.org/2001/XMLSchema#string"
            )

        # Multi-valued property
        for keyword in protein.get("keywords", []):
            inferencer.add_triple(
                protein["uri"],
                "http://purl.uniprot.org/core/keyword",
                keyword,
                subject_type="http://purl.uniprot.org/core/Protein",
                datatype="http://www.w3.org/2001/XMLSchema#string"
            )

    # Generate schema
    result = inferencer.generate_schema(base_uri="http://purl.uniprot.org/shapes/")

    print("\nGenerated UniProt Protein Shape:")
    print("=" * 80)
    print(result.schema)

    print("\nProperty Analysis:")
    print("-" * 80)
    protein_shape = result.schema.shapes.get("<ProteinShape>")
    if protein_shape:
        print(f"\nTotal constraints: {len(protein_shape.expression)}")
        print("\nConstraint Details:")
        for constraint in protein_shape.expression:
            prop_name = constraint.predicate.split('/')[-1]
            card = constraint.cardinality.value
            dtype = constraint.datatype or (constraint.node_kind.value if constraint.node_kind else "any")
            print(f"  {prop_name:20s} {card:5s} {dtype}")

    print("\nQuality Assessment:")
    print("-" * 80)
    print(f"Total Instances Analyzed: {result.inference_metadata['num_instances']}")
    print(f"Schema Coverage: {result.quality_metrics.coverage:.1%}")
    print(f"Property Completeness: {result.quality_metrics.completeness:.1%}")
    print(f"Constraint Confidence: {result.quality_metrics.constraint_confidence:.1%}")

    print("\nWarnings:")
    print("-" * 80)
    if result.warnings:
        for warning in result.warnings:
            print(f"  - {warning}")
    else:
        print("  No warnings")


def example_6_sparql_endpoint_inference():
    """Example 6: Infer schema from SPARQL endpoint (demo)."""
    print("\n" + "=" * 80)
    print("Example 6: SPARQL Endpoint Schema Inference (Demo)")
    print("=" * 80)

    print("""
This example shows how to use the convenience function to infer schema
directly from a SPARQL endpoint:

from schema_inference import infer_schema_from_sparql

# Infer schema from endpoint
result = infer_schema_from_sparql(
    endpoint_url="https://sparql.uniprot.org/sparql",
    limit=1000,
    min_confidence=0.8
)

# Access the generated schema
print(result.schema)

# Examine quality metrics
print(f"Coverage: {result.quality_metrics.coverage:.1%}")
print(f"Confidence: {result.quality_metrics.constraint_confidence:.1%}")

# Get detailed statistics
for prop_uri, stats in result.property_stats.items():
    print(f"{prop_uri}: {stats.usage_count} uses")
    """)

    print("\nNote: This is a demonstration. To actually query a live endpoint,")
    print("uncomment the code and ensure the endpoint is accessible.")


def main():
    """Run all examples."""
    examples = [
        example_1_basic_inference,
        example_2_cardinality_inference,
        example_3_datatype_inference,
        example_4_statistical_analysis,
        example_5_real_world_uniprot,
        example_6_sparql_endpoint_inference,
    ]

    print("\n")
    print("#" * 80)
    print("# Schema Inference Examples")
    print("#" * 80)
    print()

    for example in examples:
        try:
            example()
            print()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
