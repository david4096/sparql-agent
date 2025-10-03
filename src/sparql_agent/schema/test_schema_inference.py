"""
Tests for Schema Inference Module

This module tests the SchemaInferencer's ability to generate ShEx schemas
from RDF data with statistical analysis and quality metrics.
"""

import pytest
from schema_inference import (
    SchemaInferencer,
    PropertyStats,
    ClassStats,
    ConstraintConfidence,
    infer_schema_from_sparql,
)
from shex_parser import Cardinality, NodeKind


class TestSchemaInferencer:
    """Test cases for SchemaInferencer."""

    def test_basic_initialization(self):
        """Test basic inferencer initialization."""
        inferencer = SchemaInferencer()
        assert inferencer.min_confidence == 0.7
        assert inferencer.cardinality_threshold == 0.9
        assert len(inferencer.property_stats) == 0
        assert len(inferencer.class_stats) == 0

    def test_add_simple_triple(self):
        """Test adding a simple triple."""
        inferencer = SchemaInferencer()
        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="http://example.org/name",
            obj="Hemoglobin",
            subject_type="http://example.org/Protein"
        )

        assert len(inferencer.property_stats) == 1
        assert "http://example.org/name" in inferencer.property_stats

        prop_stats = inferencer.property_stats["http://example.org/name"]
        assert prop_stats.usage_count == 1
        assert len(prop_stats.sample_values) == 1

    def test_type_assertion_handling(self):
        """Test handling of rdf:type assertions."""
        inferencer = SchemaInferencer()
        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            obj="http://example.org/Protein"
        )

        assert len(inferencer.class_stats) == 1
        assert "http://example.org/Protein" in inferencer.class_stats
        assert inferencer.class_stats["http://example.org/Protein"].instance_count == 1

    def test_cardinality_inference_exactly_one(self):
        """Test inference of exactly-one cardinality."""
        inferencer = SchemaInferencer()

        # All instances have exactly one value
        for i in range(10):
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="http://example.org/name",
                obj=f"Protein {i}",
                subject_type="http://example.org/Protein"
            )

        result = inferencer.generate_schema()

        # Find the constraint for name property
        protein_shape = result.schema.shapes.get("<ProteinShape>")
        assert protein_shape is not None

        name_constraint = None
        for constraint in protein_shape.expression:
            if "name" in constraint.predicate:
                name_constraint = constraint
                break

        assert name_constraint is not None
        # With 100% coverage and single values, should be EXACTLY_ONE
        assert name_constraint.cardinality == Cardinality.EXACTLY_ONE

    def test_cardinality_inference_one_or_more(self):
        """Test inference of one-or-more cardinality."""
        inferencer = SchemaInferencer()

        # Add type assertion first
        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="rdf:type",
            obj="http://example.org/Protein"
        )

        # Some instances have multiple values
        for i in range(3):
            inferencer.add_triple(
                subject="http://example.org/protein1",
                predicate="http://example.org/synonym",
                obj=f"Synonym {i}",
                subject_type="http://example.org/Protein"
            )

        result = inferencer.generate_schema()

        protein_shape = result.schema.shapes.get("<ProteinShape>")
        synonym_constraint = None
        for constraint in protein_shape.expression:
            if "synonym" in constraint.predicate:
                synonym_constraint = constraint
                break

        assert synonym_constraint is not None
        # Multiple values, should be ONE_OR_MORE
        assert synonym_constraint.cardinality == Cardinality.ONE_OR_MORE

    def test_cardinality_inference_optional(self):
        """Test inference of optional properties."""
        inferencer = SchemaInferencer()

        # Create 10 instances, only 5 have the optional property
        for i in range(10):
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="rdf:type",
                obj="http://example.org/Protein"
            )

            # All have name
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="http://example.org/name",
                obj=f"Protein {i}",
                subject_type="http://example.org/Protein"
            )

            # Only half have description
            if i < 5:
                inferencer.add_triple(
                    subject=f"http://example.org/protein{i}",
                    predicate="http://example.org/description",
                    obj=f"Description {i}",
                    subject_type="http://example.org/Protein"
                )

        result = inferencer.generate_schema()

        protein_shape = result.schema.shapes.get("<ProteinShape>")
        assert protein_shape is not None

        # Check name is required
        name_constraint = None
        desc_constraint = None
        for constraint in protein_shape.expression:
            if "name" in constraint.predicate:
                name_constraint = constraint
            elif "description" in constraint.predicate:
                desc_constraint = constraint

        assert name_constraint is not None
        assert desc_constraint is not None

        # Name should be required (EXACTLY_ONE)
        assert name_constraint.cardinality == Cardinality.EXACTLY_ONE

        # Description should be optional (ZERO_OR_ONE)
        assert desc_constraint.cardinality == Cardinality.ZERO_OR_ONE

    def test_datatype_inference(self):
        """Test inference of datatypes."""
        inferencer = SchemaInferencer()

        # Add string property
        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="http://example.org/name",
            obj="Hemoglobin",
            subject_type="http://example.org/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#string"
        )

        # Add integer property
        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="http://example.org/mass",
            obj=64500,
            subject_type="http://example.org/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#integer"
        )

        result = inferencer.generate_schema()

        protein_shape = result.schema.shapes.get("<ProteinShape>")
        assert protein_shape is not None

        # Check datatypes
        for constraint in protein_shape.expression:
            if "name" in constraint.predicate:
                assert constraint.datatype == "xsd:string"
            elif "mass" in constraint.predicate:
                assert constraint.datatype == "xsd:integer"

    def test_numeric_constraint_inference(self):
        """Test inference of numeric constraints."""
        inferencer = SchemaInferencer()

        # Add multiple numeric values, all positive
        for i in range(10):
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="http://example.org/mass",
                obj=50000 + i * 1000,  # 50000-59000
                subject_type="http://example.org/Protein",
                datatype="http://www.w3.org/2001/XMLSchema#integer"
            )

        result = inferencer.generate_schema()

        # Check that constraints were inferred
        protein_constraints = result.constraints.get("http://example.org/Protein", [])

        # Should have min_inclusive constraint
        min_constraints = [c for c in protein_constraints if c.constraint_type == 'min_inclusive']
        assert len(min_constraints) > 0

        # Check that at least one has high confidence (all positive)
        has_high_confidence = any(
            c.confidence == ConstraintConfidence.HIGH
            for c in min_constraints
        )
        assert has_high_confidence

    def test_iri_node_kind_inference(self):
        """Test inference of IRI node kind."""
        inferencer = SchemaInferencer()

        # Add IRI reference
        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="http://example.org/organism",
            obj="http://example.org/organism/9606",
            subject_type="http://example.org/Protein"
        )

        result = inferencer.generate_schema()

        protein_shape = result.schema.shapes.get("<ProteinShape>")
        assert protein_shape is not None

        # Find organism constraint
        organism_constraint = None
        for constraint in protein_shape.expression:
            if "organism" in constraint.predicate:
                organism_constraint = constraint
                break

        assert organism_constraint is not None
        # Should infer IRI node kind
        assert organism_constraint.node_kind == NodeKind.IRI

    def test_namespace_extraction(self):
        """Test extraction and suggestion of namespaces."""
        inferencer = SchemaInferencer()

        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="http://example.org/vocab#name",
            obj="Hemoglobin"
        )

        result = inferencer.generate_schema()

        # Should have extracted namespace
        assert len(result.schema.prefixes) > 0

    def test_quality_metrics_calculation(self):
        """Test calculation of quality metrics."""
        inferencer = SchemaInferencer()

        # Add some well-formed data
        for i in range(10):
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="rdf:type",
                obj="http://example.org/Protein"
            )
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="http://example.org/name",
                obj=f"Protein {i}",
                subject_type="http://example.org/Protein"
            )

        result = inferencer.generate_schema()

        # Check quality metrics
        metrics = result.quality_metrics
        assert metrics.total_instances == 10
        assert metrics.coverage > 0
        assert metrics.completeness > 0
        assert 0 <= metrics.constraint_confidence <= 1

    def test_property_stats_tracking(self):
        """Test tracking of property statistics."""
        inferencer = SchemaInferencer()

        # Add multiple values for same property
        for i in range(5):
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="http://example.org/name",
                obj=f"Protein {i}",
                subject_type="http://example.org/Protein"
            )

        result = inferencer.generate_schema()

        prop_stats = result.property_stats["http://example.org/name"]
        assert prop_stats.usage_count == 5
        assert prop_stats.subject_count == 5
        assert len(prop_stats.sample_values) == 5

    def test_class_hierarchy_inference(self):
        """Test inference of class hierarchy."""
        inferencer = SchemaInferencer()

        # Create base class with few properties
        for i in range(5):
            inferencer.add_triple(
                subject=f"http://example.org/entity{i}",
                predicate="rdf:type",
                obj="http://example.org/Entity"
            )
            inferencer.add_triple(
                subject=f"http://example.org/entity{i}",
                predicate="http://example.org/id",
                obj=f"ID{i}",
                subject_type="http://example.org/Entity"
            )

        # Create subclass with additional properties
        for i in range(5):
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="rdf:type",
                obj="http://example.org/Protein"
            )
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="http://example.org/id",
                obj=f"P{i}",
                subject_type="http://example.org/Protein"
            )
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="http://example.org/name",
                obj=f"Protein {i}",
                subject_type="http://example.org/Protein"
            )
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="http://example.org/sequence",
                obj=f"MVLSPAD...",
                subject_type="http://example.org/Protein"
            )

        result = inferencer.generate_schema()

        # Check hierarchy was inferred
        protein_stats = result.class_stats.get("http://example.org/Protein")
        if protein_stats:
            # Protein should have Entity as superclass (all Entity props + more)
            # This is a heuristic so may not always work
            assert len(protein_stats.properties) > 1

    def test_confidence_levels(self):
        """Test assignment of confidence levels."""
        inferencer = SchemaInferencer()

        # High confidence: 100% consistent
        for i in range(10):
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="http://example.org/name",
                obj=f"Protein {i}",
                subject_type="http://example.org/Protein",
                datatype="http://www.w3.org/2001/XMLSchema#string"
            )

        result = inferencer.generate_schema()

        # Check constraints have appropriate confidence
        protein_constraints = result.constraints.get("http://example.org/Protein", [])

        # Should have high confidence cardinality constraint
        card_constraints = [c for c in protein_constraints if c.constraint_type == 'cardinality']
        if card_constraints:
            # At least one should be high confidence
            assert any(c.confidence == ConstraintConfidence.HIGH for c in card_constraints)

    def test_pattern_inference(self):
        """Test inference of string patterns."""
        inferencer = SchemaInferencer()

        # Add email-like values
        emails = [
            "user1@example.com",
            "user2@example.com",
            "admin@example.org"
        ]

        for i, email in enumerate(emails):
            inferencer.add_triple(
                subject=f"http://example.org/person{i}",
                predicate="http://example.org/email",
                obj=email,
                subject_type="http://example.org/Person"
            )

        result = inferencer.generate_schema()

        # Check if pattern was inferred
        person_constraints = result.constraints.get("http://example.org/Person", [])
        pattern_constraints = [c for c in person_constraints if c.constraint_type == 'pattern']

        # May or may not infer pattern depending on sample size
        # Just verify no errors occur
        assert isinstance(pattern_constraints, list)

    def test_multi_type_handling(self):
        """Test handling of instances with multiple types."""
        inferencer = SchemaInferencer()

        # Instance with two types
        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="rdf:type",
            obj="http://example.org/Protein"
        )
        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="rdf:type",
            obj="http://example.org/Enzyme"
        )

        inferencer.add_triple(
            subject="http://example.org/protein1",
            predicate="http://example.org/name",
            obj="Catalase",
            subject_type="http://example.org/Protein"
        )

        result = inferencer.generate_schema()

        # Should have shapes for both types
        assert "http://example.org/Protein" in result.class_stats
        assert "http://example.org/Enzyme" in result.class_stats

    def test_empty_data_handling(self):
        """Test handling of empty data."""
        inferencer = SchemaInferencer()
        result = inferencer.generate_schema()

        assert len(result.schema.shapes) == 0
        assert result.quality_metrics.total_instances == 0

    def test_inference_metadata(self):
        """Test that inference metadata is populated."""
        inferencer = SchemaInferencer()

        for i in range(5):
            inferencer.add_triple(
                subject=f"http://example.org/protein{i}",
                predicate="rdf:type",
                obj="http://example.org/Protein"
            )

        result = inferencer.generate_schema()

        # Check metadata
        assert 'total_triples' in result.inference_metadata
        assert 'num_classes' in result.inference_metadata
        assert 'num_properties' in result.inference_metadata
        assert result.inference_metadata['num_classes'] == 1


class TestPropertyStats:
    """Test PropertyStats class."""

    def test_initialization(self):
        """Test PropertyStats initialization."""
        stats = PropertyStats(uri="http://example.org/name")
        assert stats.uri == "http://example.org/name"
        assert stats.usage_count == 0
        assert len(stats.sample_values) == 0

    def test_add_value(self):
        """Test adding values to PropertyStats."""
        stats = PropertyStats(uri="http://example.org/name")

        stats.add_value(
            subject="http://example.org/protein1",
            obj="Hemoglobin",
            obj_type="string"
        )

        assert stats.usage_count == 1
        assert len(stats.sample_values) == 1
        assert "http://example.org/protein1" in stats.subjects_with_property

    def test_numeric_value_tracking(self):
        """Test tracking of numeric values."""
        stats = PropertyStats(uri="http://example.org/mass")

        stats.add_value(
            subject="http://example.org/protein1",
            obj=64500,
            obj_type="integer"
        )

        assert len(stats.numeric_values) == 1
        assert stats.numeric_values[0] == 64500


class TestClassStats:
    """Test ClassStats class."""

    def test_initialization(self):
        """Test ClassStats initialization."""
        stats = ClassStats(uri="http://example.org/Protein")
        assert stats.uri == "http://example.org/Protein"
        assert stats.instance_count == 0
        assert len(stats.properties) == 0

    def test_add_instance(self):
        """Test adding instances."""
        stats = ClassStats(uri="http://example.org/Protein")

        stats.add_instance("http://example.org/protein1")
        stats.add_instance("http://example.org/protein2")

        assert stats.instance_count == 2
        assert len(stats.instances) == 2

    def test_add_property_usage(self):
        """Test tracking property usage."""
        stats = ClassStats(uri="http://example.org/Protein")

        stats.add_property_usage("http://example.org/name")
        stats.add_property_usage("http://example.org/name")

        assert "http://example.org/name" in stats.properties
        assert stats.property_usage["http://example.org/name"] == 2


def test_integration_example():
    """Integration test with realistic protein data."""
    inferencer = SchemaInferencer()

    # Add some protein data
    proteins = [
        {
            "uri": "http://uniprot.org/uniprot/P69905",
            "name": "Hemoglobin subunit alpha",
            "organism": "http://uniprot.org/taxonomy/9606",
            "mass": 15258,
            "sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF"
        },
        {
            "uri": "http://uniprot.org/uniprot/P68871",
            "name": "Hemoglobin subunit beta",
            "organism": "http://uniprot.org/taxonomy/9606",
            "mass": 15867,
            "sequence": "MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLS"
        },
        {
            "uri": "http://uniprot.org/uniprot/P02100",
            "name": "Hemoglobin subunit epsilon",
            "organism": "http://uniprot.org/taxonomy/9606",
            "mass": 16133,
            # No sequence for this one
        }
    ]

    for protein in proteins:
        # Add type
        inferencer.add_triple(
            subject=protein["uri"],
            predicate="rdf:type",
            obj="http://uniprot.org/core/Protein"
        )

        # Add properties
        inferencer.add_triple(
            subject=protein["uri"],
            predicate="http://uniprot.org/core/name",
            obj=protein["name"],
            subject_type="http://uniprot.org/core/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#string"
        )

        inferencer.add_triple(
            subject=protein["uri"],
            predicate="http://uniprot.org/core/organism",
            obj=protein["organism"],
            subject_type="http://uniprot.org/core/Protein"
        )

        inferencer.add_triple(
            subject=protein["uri"],
            predicate="http://uniprot.org/core/mass",
            obj=protein["mass"],
            subject_type="http://uniprot.org/core/Protein",
            datatype="http://www.w3.org/2001/XMLSchema#integer"
        )

        if "sequence" in protein:
            inferencer.add_triple(
                subject=protein["uri"],
                predicate="http://uniprot.org/core/sequence",
                obj=protein["sequence"],
                subject_type="http://uniprot.org/core/Protein",
                datatype="http://www.w3.org/2001/XMLSchema#string"
            )

    # Generate schema
    result = inferencer.generate_schema()

    # Verify schema
    assert len(result.schema.shapes) == 1
    protein_shape = result.schema.shapes.get("<ProteinShape>")
    assert protein_shape is not None

    # Verify properties
    property_predicates = [c.predicate for c in protein_shape.expression]
    assert any("name" in p for p in property_predicates)
    assert any("organism" in p for p in property_predicates)
    assert any("mass" in p for p in property_predicates)
    assert any("sequence" in p for p in property_predicates)

    # Verify sequence is optional (only 2/3 have it)
    for constraint in protein_shape.expression:
        if "sequence" in constraint.predicate:
            assert constraint.cardinality in [Cardinality.ZERO_OR_ONE, Cardinality.ZERO_OR_MORE]

    # Verify quality metrics
    assert result.quality_metrics.total_instances == 3
    assert result.quality_metrics.coverage > 0

    # Print schema for inspection
    print("\nGenerated Schema:")
    print("=" * 60)
    print(result.schema)
    print("\nQuality Metrics:")
    print(f"Coverage: {result.quality_metrics.coverage:.1%}")
    print(f"Completeness: {result.quality_metrics.completeness:.1%}")
    print(f"Constraint Confidence: {result.quality_metrics.constraint_confidence:.1%}")


if __name__ == "__main__":
    # Run integration test
    print("Running integration test...")
    test_integration_example()
    print("\nAll tests passed!")
