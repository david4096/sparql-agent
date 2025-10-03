"""
Tests for Ontology-Guided SPARQL Query Generation.

This module tests the ontology-guided query generation functionality including:
- Class hierarchy expansion
- Property path discovery
- Constraint extraction and validation
- OLS integration
"""

import pytest
from datetime import datetime
from pathlib import Path

from ..core.types import (
    OntologyInfo,
    OWLClass,
    OWLProperty,
    OWLPropertyType,
)
from .ontology_generator import (
    OntologyGuidedGenerator,
    OntologyQueryContext,
    PropertyPath,
    PropertyPathType,
    QueryConstraint,
    ExpansionStrategy,
    create_ontology_generator,
    quick_ontology_query,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_ontology() -> OntologyInfo:
    """Create a sample ontology for testing."""
    ontology = OntologyInfo(
        uri="http://example.org/test-ontology#",
        title="Test Ontology",
        description="A test ontology for unit tests",
        version="1.0",
    )

    # Add classes with hierarchy
    # Thing -> Organism -> Protein
    #                   -> Gene
    thing = OWLClass(
        uri="http://example.org/test-ontology#Thing",
        label=["Thing"],
        comment=["Root class"],
    )

    organism = OWLClass(
        uri="http://example.org/test-ontology#Organism",
        label=["Organism", "Living Thing"],
        comment=["Any living organism"],
        subclass_of=["http://example.org/test-ontology#Thing"],
    )

    protein = OWLClass(
        uri="http://example.org/test-ontology#Protein",
        label=["Protein"],
        comment=["A protein molecule"],
        subclass_of=["http://example.org/test-ontology#Organism"],
    )

    gene = OWLClass(
        uri="http://example.org/test-ontology#Gene",
        label=["Gene"],
        comment=["A gene sequence"],
        subclass_of=["http://example.org/test-ontology#Organism"],
    )

    disease = OWLClass(
        uri="http://example.org/test-ontology#Disease",
        label=["Disease"],
        comment=["A disease or disorder"],
        subclass_of=["http://example.org/test-ontology#Thing"],
    )

    ontology.classes = {
        thing.uri: thing,
        organism.uri: organism,
        protein.uri: protein,
        gene.uri: gene,
        disease.uri: disease,
    }

    # Add properties
    encodes = OWLProperty(
        uri="http://example.org/test-ontology#encodes",
        label=["encodes"],
        comment=["Gene encodes protein"],
        property_type=OWLPropertyType.OBJECT_PROPERTY,
        domain=[gene.uri],
        range=[protein.uri],
    )

    causes = OWLProperty(
        uri="http://example.org/test-ontology#causes",
        label=["causes"],
        comment=["Gene causes disease"],
        property_type=OWLPropertyType.OBJECT_PROPERTY,
        domain=[gene.uri],
        range=[disease.uri],
    )

    has_name = OWLProperty(
        uri="http://example.org/test-ontology#hasName",
        label=["has name"],
        comment=["Name of the entity"],
        property_type=OWLPropertyType.DATATYPE_PROPERTY,
        domain=[thing.uri],
        range=["http://www.w3.org/2001/XMLSchema#string"],
    )

    ontology.properties = {
        encodes.uri: encodes,
        causes.uri: causes,
        has_name.uri: has_name,
    }

    return ontology


@pytest.fixture
def generator(sample_ontology: OntologyInfo) -> OntologyGuidedGenerator:
    """Create a generator with sample ontology."""
    return OntologyGuidedGenerator(ontology_info=sample_ontology)


# ============================================================================
# Concept Extraction Tests
# ============================================================================


def test_extract_concepts_simple(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test extracting concepts from simple query."""
    user_query = "Find all proteins"
    concepts = generator._extract_concepts(user_query, sample_ontology)

    assert len(concepts["classes"]) > 0
    assert any(c["label"].lower() == "protein" for c in concepts["classes"])


def test_extract_concepts_with_properties(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test extracting both classes and properties."""
    user_query = "Which genes encode proteins?"
    concepts = generator._extract_concepts(user_query, sample_ontology)

    # Should find gene and protein classes
    class_labels = [c["label"].lower() for c in concepts["classes"]]
    assert "gene" in class_labels or "protein" in class_labels

    # Should find encodes property
    prop_labels = [p["label"].lower() for p in concepts["properties"]]
    assert "encodes" in prop_labels


def test_extract_concepts_with_filters(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test extracting filter keywords."""
    user_query = "Find proteins where expression is greater than 10"
    concepts = generator._extract_concepts(user_query, sample_ontology)

    assert len(concepts["filters"]) > 0
    assert any(f["operator"] == ">" for f in concepts["filters"])


# ============================================================================
# Class Expansion Tests
# ============================================================================


def test_expand_classes_exact(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test exact class expansion (no expansion)."""
    target_classes = [
        {"uri": "http://example.org/test-ontology#Protein", "confidence": 1.0}
    ]

    expanded = generator._expand_classes(
        target_classes,
        ExpansionStrategy.EXACT,
        sample_ontology,
    )

    assert len(expanded) == 1
    assert "http://example.org/test-ontology#Protein" in expanded


def test_expand_classes_children(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test expansion with direct children."""
    target_classes = [
        {"uri": "http://example.org/test-ontology#Organism", "confidence": 1.0}
    ]

    expanded = generator._expand_classes(
        target_classes,
        ExpansionStrategy.CHILDREN,
        sample_ontology,
    )

    # Should include Organism and its children (Protein, Gene)
    assert len(expanded) >= 2
    assert "http://example.org/test-ontology#Organism" in expanded
    assert (
        "http://example.org/test-ontology#Protein" in expanded
        or "http://example.org/test-ontology#Gene" in expanded
    )


def test_expand_classes_descendants(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test expansion with all descendants."""
    target_classes = [
        {"uri": "http://example.org/test-ontology#Thing", "confidence": 1.0}
    ]

    expanded = generator._expand_classes(
        target_classes,
        ExpansionStrategy.DESCENDANTS,
        sample_ontology,
    )

    # Should include Thing and all descendants
    assert len(expanded) >= 3
    assert "http://example.org/test-ontology#Thing" in expanded


def test_expand_classes_ancestors(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test expansion with ancestors."""
    target_classes = [
        {"uri": "http://example.org/test-ontology#Protein", "confidence": 1.0}
    ]

    expanded = generator._expand_classes(
        target_classes,
        ExpansionStrategy.ANCESTORS,
        sample_ontology,
    )

    # Should include Protein, Organism, and Thing
    assert len(expanded) >= 2
    assert "http://example.org/test-ontology#Protein" in expanded
    assert "http://example.org/test-ontology#Organism" in expanded


def test_expand_classes_siblings(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test expansion with siblings."""
    target_classes = [
        {"uri": "http://example.org/test-ontology#Protein", "confidence": 1.0}
    ]

    expanded = generator._expand_classes(
        target_classes,
        ExpansionStrategy.SIBLINGS,
        sample_ontology,
    )

    # Should include Protein and Gene (sibling)
    assert "http://example.org/test-ontology#Protein" in expanded
    # Gene is a sibling (same parent: Organism)
    assert "http://example.org/test-ontology#Gene" in expanded


# ============================================================================
# Property Path Tests
# ============================================================================


def test_find_property_paths_direct(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test finding direct property paths."""
    expanded_classes = {
        "http://example.org/test-ontology#Gene": sample_ontology.classes[
            "http://example.org/test-ontology#Gene"
        ],
        "http://example.org/test-ontology#Protein": sample_ontology.classes[
            "http://example.org/test-ontology#Protein"
        ],
    }

    paths = generator._find_property_paths(
        expanded_classes,
        [],
        sample_ontology,
        max_hops=2,
    )

    # Should find the "encodes" property path from Gene to Protein
    assert len(paths) > 0
    encodes_path = next(
        (p for p in paths if "encodes" in p.properties[0]),
        None,
    )
    assert encodes_path is not None
    assert encodes_path.hops == 1


def test_find_property_paths_multi_hop(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test finding multi-hop property paths."""
    # This would require a more complex ontology with longer paths
    expanded_classes = {
        "http://example.org/test-ontology#Gene": sample_ontology.classes[
            "http://example.org/test-ontology#Gene"
        ],
    }

    paths = generator._find_property_paths(
        expanded_classes,
        [],
        sample_ontology,
        max_hops=3,
    )

    # Should find paths within the ontology
    assert isinstance(paths, list)


def test_property_path_to_sparql(sample_ontology: OntologyInfo):
    """Test converting property path to SPARQL syntax."""
    # Direct path
    direct = PropertyPath(
        properties=["http://example.org/test-ontology#encodes"],
        path_type=PropertyPathType.DIRECT,
    )
    assert "<http://example.org/test-ontology#encodes>" in direct.to_sparql()

    # Sequence path
    sequence = PropertyPath(
        properties=[
            "http://example.org/test-ontology#encodes",
            "http://example.org/test-ontology#causes",
        ],
        path_type=PropertyPathType.SEQUENCE,
    )
    assert "/" in sequence.to_sparql()

    # Inverse path
    inverse = PropertyPath(
        properties=["http://example.org/test-ontology#encodes"],
        path_type=PropertyPathType.INVERSE,
    )
    assert "^" in inverse.to_sparql()


# ============================================================================
# Constraint Extraction Tests
# ============================================================================


def test_extract_constraints(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test extracting OWL constraints."""
    expanded_classes = {
        "http://example.org/test-ontology#Gene": sample_ontology.classes[
            "http://example.org/test-ontology#Gene"
        ],
    }

    property_paths = [
        PropertyPath(
            properties=["http://example.org/test-ontology#encodes"],
            path_type=PropertyPathType.DIRECT,
        )
    ]

    constraints = generator._extract_constraints(
        expanded_classes,
        property_paths,
        sample_ontology,
    )

    # Should find domain/range constraints
    assert len(constraints) > 0
    assert any(c.constraint_type == "domain" for c in constraints)


def test_constraint_to_sparql_filter():
    """Test converting constraint to SPARQL filter."""
    constraint = QueryConstraint(
        constraint_type="datatype",
        property_uri="http://example.org/test#prop",
        value="http://www.w3.org/2001/XMLSchema#string",
    )

    filter_clause = constraint.to_sparql_filter()
    assert filter_clause is not None
    assert "FILTER" in filter_clause


# ============================================================================
# Query Generation Tests
# ============================================================================


def test_generate_query_basic(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test basic query generation."""
    context = OntologyQueryContext(
        ontology_info=sample_ontology,
        expansion_strategy=ExpansionStrategy.EXACT,
    )

    result = generator.generate_query("Find all proteins", context)

    assert result.query is not None
    assert "SELECT" in result.query
    assert result.used_ontology is True
    assert len(result.ontology_classes) > 0


def test_generate_query_with_expansion(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test query generation with class expansion."""
    context = OntologyQueryContext(
        ontology_info=sample_ontology,
        expansion_strategy=ExpansionStrategy.DESCENDANTS,
    )

    result = generator.generate_query("Find all organisms", context)

    assert result.query is not None
    # Should expand to include subclasses
    assert len(result.ontology_classes) >= 1


def test_generate_query_with_properties(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test query generation with properties."""
    context = OntologyQueryContext(
        ontology_info=sample_ontology,
        expansion_strategy=ExpansionStrategy.EXACT,
        max_hops=2,
    )

    result = generator.generate_query("Which genes encode proteins?", context)

    assert result.query is not None
    assert len(result.ontology_properties) > 0


def test_generate_query_with_explanation(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test query generation includes explanation."""
    context = OntologyQueryContext(
        ontology_info=sample_ontology,
        expansion_strategy=ExpansionStrategy.EXACT,
    )

    result = generator.generate_query("Find all proteins", context, include_explanation=True)

    assert result.explanation is not None
    assert len(result.explanation) > 0


# ============================================================================
# Validation Tests
# ============================================================================


def test_validate_query_valid(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test validation of valid query."""
    query = """
    SELECT ?gene ?protein
    WHERE {
        ?gene a <http://example.org/test-ontology#Gene> .
        ?gene <http://example.org/test-ontology#encodes> ?protein .
        ?protein a <http://example.org/test-ontology#Protein> .
    }
    """

    validation = generator.validate_query_against_ontology(query, sample_ontology)

    assert validation["is_valid"] is True
    assert len(validation["errors"]) == 0


def test_validate_query_invalid_class(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test validation detects invalid class."""
    query = """
    SELECT ?x
    WHERE {
        ?x a <http://example.org/test-ontology#InvalidClass> .
    }
    """

    validation = generator.validate_query_against_ontology(query, sample_ontology)

    assert validation["is_valid"] is False
    assert len(validation["errors"]) > 0


# ============================================================================
# Property Suggestion Tests
# ============================================================================


def test_suggest_properties(generator: OntologyGuidedGenerator, sample_ontology: OntologyInfo):
    """Test property suggestions for classes."""
    class_uris = [
        "http://example.org/test-ontology#Gene",
        "http://example.org/test-ontology#Protein",
    ]

    suggestions = generator.suggest_properties_for_classes(
        class_uris,
        "test",
        max_suggestions=5,
    )

    assert len(suggestions) > 0
    # Should suggest "encodes" property
    assert any("encodes" in s["label"].lower() for s in suggestions)


# ============================================================================
# Confidence Calculation Tests
# ============================================================================


def test_calculate_confidence(generator: OntologyGuidedGenerator):
    """Test confidence score calculation."""
    concepts = {
        "classes": [{"confidence": 0.8}, {"confidence": 0.9}],
        "properties": [{"confidence": 0.85}],
    }

    expanded_classes = {}

    property_paths = [
        PropertyPath(properties=["prop1"], confidence=0.9),
        PropertyPath(properties=["prop2"], confidence=0.7),
    ]

    confidence = generator._calculate_confidence(concepts, expanded_classes, property_paths)

    assert 0.0 <= confidence <= 1.0


# ============================================================================
# Convenience Function Tests
# ============================================================================


def test_create_ontology_generator_with_ontology_info(sample_ontology: OntologyInfo):
    """Test creating generator with OntologyInfo."""
    generator = create_ontology_generator(ontology_source=sample_ontology)

    assert generator.ontology_info is not None
    assert generator.ontology_info.uri == sample_ontology.uri


def test_create_ontology_generator_no_source():
    """Test creating generator without source."""
    generator = create_ontology_generator(enable_ols=False)

    assert generator.ontology_info is None
    assert generator.ols_client is None


# ============================================================================
# OLS Integration Tests (mocked)
# ============================================================================


def test_expand_with_ols_mock(generator: OntologyGuidedGenerator, monkeypatch):
    """Test OLS expansion (mocked)."""
    # Mock OLS client search
    def mock_search(*args, **kwargs):
        return [
            {
                "id": "GO_0008150",
                "label": "biological_process",
                "iri": "http://purl.obolibrary.org/obo/GO_0008150",
            }
        ]

    def mock_get_descendants(*args, **kwargs):
        return [
            {
                "id": "GO_0009987",
                "label": "cellular process",
                "iri": "http://purl.obolibrary.org/obo/GO_0009987",
            }
        ]

    monkeypatch.setattr(generator.ols_client, "search", mock_search)
    monkeypatch.setattr(generator.ols_client, "get_term_descendants", mock_get_descendants)

    expanded = generator.expand_with_ols(
        "biological process",
        "go",
        ExpansionStrategy.DESCENDANTS,
    )

    assert len(expanded) > 0


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow(sample_ontology: OntologyInfo):
    """Test full workflow from query to result."""
    generator = create_ontology_generator(ontology_source=sample_ontology)

    context = OntologyQueryContext(
        ontology_info=sample_ontology,
        expansion_strategy=ExpansionStrategy.CHILDREN,
        max_hops=2,
    )

    result = generator.generate_query(
        "Which genes encode proteins that cause diseases?",
        context,
        include_explanation=True,
    )

    # Check result
    assert result.query is not None
    assert result.used_ontology is True
    assert result.explanation is not None
    assert len(result.ontology_classes) > 0
    assert len(result.ontology_properties) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
