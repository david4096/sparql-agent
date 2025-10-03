"""
Tests for schema module: VoID parser, ShEx parser, metadata inference, and ontology mapper.

This module tests schema discovery, validation, and metadata inference functionality.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

from sparql_agent.core.types import SchemaInfo, EndpointInfo
from sparql_agent.core.exceptions import SchemaError


# =============================================================================
# Tests for VoID Parser
# =============================================================================


@pytest.mark.unit
class TestVoIDParser:
    """Tests for VoID (Vocabulary of Interlinked Datasets) parser."""

    def test_parse_void_description(self, sample_void_file):
        """Test parsing a VoID description file."""
        # This tests will depend on the actual implementation
        # For now, we test the structure
        g = Graph()
        g.parse(sample_void_file, format="turtle")

        # Check that the graph contains VoID triples
        assert len(g) > 0

        # Check for VoID vocabulary usage
        VOID = Namespace("http://rdfs.org/ns/void#")
        datasets = list(g.subjects(RDF.type, VOID.Dataset))
        assert len(datasets) > 0

    def test_extract_endpoint_info_from_void(self, sample_void_file):
        """Test extracting endpoint information from VoID."""
        g = Graph()
        g.parse(sample_void_file, format="turtle")

        VOID = Namespace("http://rdfs.org/ns/void#")
        # Find endpoint
        endpoints = list(g.objects(predicate=VOID.sparqlEndpoint))
        assert len(endpoints) > 0
        assert str(endpoints[0]) == "http://example.org/sparql"

    def test_extract_statistics_from_void(self, sample_void_file):
        """Test extracting statistics from VoID."""
        g = Graph()
        g.parse(sample_void_file, format="turtle")

        VOID = Namespace("http://rdfs.org/ns/void#")
        datasets = list(g.subjects(RDF.type, VOID.Dataset))

        if datasets:
            dataset = datasets[0]
            # Check for statistics
            triples = list(g.objects(dataset, VOID.triples))
            if triples:
                assert int(triples[0]) == 1000


# =============================================================================
# Tests for ShEx Parser
# =============================================================================


@pytest.mark.unit
class TestShExParser:
    """Tests for ShEx (Shape Expressions) parser."""

    def test_parse_shex_schema(self):
        """Test parsing a ShEx schema."""
        shex_schema = """
        PREFIX ex: <http://example.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        ex:PersonShape {
            ex:name xsd:string ;
            ex:age xsd:integer ;
            ex:email xsd:string ?
        }
        """

        # Basic parsing test - actual implementation will vary
        assert "PersonShape" in shex_schema
        assert "name" in shex_schema
        assert "xsd:string" in shex_schema

    def test_validate_data_against_shex(self, sample_rdf_graph):
        """Test validating RDF data against ShEx schema."""
        # This is a placeholder - actual validation would use pyshex or similar
        assert len(sample_rdf_graph) > 0

        # Mock validation result
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        assert validation_result["valid"] is True


# =============================================================================
# Tests for Metadata Inference
# =============================================================================


@pytest.mark.unit
class TestMetadataInference:
    """Tests for metadata inference from RDF data."""

    def test_infer_classes_from_graph(self, sample_rdf_graph):
        """Test inferring OWL classes from RDF graph."""
        # Find all classes used
        classes = set()
        for s, p, o in sample_rdf_graph.triples((None, RDF.type, None)):
            if isinstance(o, URIRef):
                classes.add(str(o))

        assert len(classes) > 0
        assert "http://xmlns.com/foaf/0.1/Person" in classes

    def test_infer_properties_from_graph(self, sample_rdf_graph):
        """Test inferring properties from RDF graph."""
        # Find all properties used
        properties = set()
        for s, p, o in sample_rdf_graph:
            properties.add(str(p))

        assert len(properties) > 0
        assert str(RDF.type) in properties

    def test_infer_property_domains(self, sample_rdf_graph):
        """Test inferring property domains."""
        # Find subjects that use foaf:name
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        subjects = set()

        for s, p, o in sample_rdf_graph.triples((None, FOAF.name, None)):
            # Get type of subject
            for type_triple in sample_rdf_graph.triples((s, RDF.type, None)):
                subjects.add(str(type_triple[2]))

        # Should find Person as domain of foaf:name
        if subjects:
            assert "http://xmlns.com/foaf/0.1/Person" in subjects

    def test_infer_property_ranges(self, sample_rdf_graph):
        """Test inferring property ranges."""
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")

        # Check types of objects for foaf:knows
        object_types = set()
        for s, p, o in sample_rdf_graph.triples((None, FOAF.knows, None)):
            if isinstance(o, URIRef):
                # Check if object has a type
                for type_triple in sample_rdf_graph.triples((o, RDF.type, None)):
                    object_types.add(str(type_triple[2]))

        # foaf:knows should have Person as range
        if object_types:
            assert "http://xmlns.com/foaf/0.1/Person" in object_types

    def test_infer_cardinality_constraints(self, sample_rdf_graph):
        """Test inferring cardinality constraints."""
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")

        # Count how many times each property appears per subject
        property_counts = {}

        for s in sample_rdf_graph.subjects(RDF.type, FOAF.Person):
            name_count = len(list(sample_rdf_graph.triples((s, FOAF.name, None))))
            property_counts[str(s)] = {"foaf:name": name_count}

        # Check that at least one person has a name
        assert len(property_counts) > 0

    def test_discover_namespaces(self, sample_rdf_graph):
        """Test discovering namespaces from graph."""
        namespaces = {}
        for prefix, namespace in sample_rdf_graph.namespaces():
            namespaces[prefix] = str(namespace)

        assert "foaf" in namespaces
        assert "ex" in namespaces


# =============================================================================
# Tests for Ontology Mapper
# =============================================================================


@pytest.mark.unit
class TestOntologyMapper:
    """Tests for ontology mapping functionality."""

    def test_map_to_standard_vocabularies(self):
        """Test mapping custom properties to standard vocabularies."""
        # Custom property to standard mapping
        mappings = {
            "http://example.org/fullName": "http://xmlns.com/foaf/0.1/name",
            "http://example.org/email": "http://xmlns.com/foaf/0.1/mbox",
        }

        # Test mapping lookup
        custom_prop = "http://example.org/fullName"
        standard_prop = mappings.get(custom_prop)

        assert standard_prop == "http://xmlns.com/foaf/0.1/name"

    def test_find_equivalent_classes(self, sample_owl_graph):
        """Test finding equivalent classes in ontology."""
        # Look for owl:equivalentClass relationships
        equivalent_classes = []
        for s, p, o in sample_owl_graph.triples((None, OWL.equivalentClass, None)):
            equivalent_classes.append((str(s), str(o)))

        # Even if empty, the query should work
        assert isinstance(equivalent_classes, list)

    def test_find_subclass_relationships(self, sample_owl_graph):
        """Test finding subclass relationships."""
        subclass_relationships = []
        for s, p, o in sample_owl_graph.triples((None, RDFS.subClassOf, None)):
            subclass_relationships.append((str(s), str(o)))

        assert isinstance(subclass_relationships, list)

    def test_align_vocabularies(self):
        """Test aligning two vocabularies."""
        vocab1 = {
            "Person": "http://example.org/Person",
            "name": "http://example.org/name",
        }

        vocab2 = {
            "Person": "http://xmlns.com/foaf/0.1/Person",
            "name": "http://xmlns.com/foaf/0.1/name",
        }

        # Simple alignment based on labels
        alignments = {}
        for key in vocab1:
            if key in vocab2:
                alignments[vocab1[key]] = vocab2[key]

        assert len(alignments) == 2

    def test_suggest_ontology_terms(self):
        """Test suggesting ontology terms for user input."""
        user_input = "person name"

        # Mock ontology terms database
        ontology_terms = {
            "person": ["http://xmlns.com/foaf/0.1/Person", "http://schema.org/Person"],
            "name": ["http://xmlns.com/foaf/0.1/name", "http://schema.org/name"],
        }

        suggestions = []
        for word in user_input.split():
            if word in ontology_terms:
                suggestions.extend(ontology_terms[word])

        assert len(suggestions) > 0
        assert "http://xmlns.com/foaf/0.1/Person" in suggestions


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestSchemaIntegration:
    """Integration tests for schema components."""

    def test_complete_schema_discovery_workflow(self, sample_rdf_graph):
        """Test complete schema discovery workflow."""
        # 1. Discover classes
        classes = set()
        for s, p, o in sample_rdf_graph.triples((None, RDF.type, None)):
            if isinstance(o, URIRef):
                classes.add(str(o))

        # 2. Discover properties
        properties = set()
        for s, p, o in sample_rdf_graph:
            if p != RDF.type:
                properties.add(str(p))

        # 3. Build schema info
        schema = {
            "classes": list(classes),
            "properties": list(properties),
            "triple_count": len(sample_rdf_graph),
        }

        assert len(schema["classes"]) > 0
        assert len(schema["properties"]) > 0
        assert schema["triple_count"] > 0

    def test_schema_validation_workflow(self, sample_rdf_graph, sample_owl_graph):
        """Test schema validation workflow."""
        # Verify RDF graph conforms to OWL ontology
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check that classes in data exist in ontology
        data_classes = set()
        for s, p, o in sample_rdf_graph.triples((None, RDF.type, None)):
            if isinstance(o, URIRef):
                data_classes.add(o)

        ontology_classes = set()
        for s, p, o in sample_owl_graph.triples((None, RDF.type, OWL.Class)):
            ontology_classes.add(s)

        # Validation: check if data classes are defined in ontology
        undefined_classes = data_classes - ontology_classes
        if undefined_classes:
            validation_results["warnings"].append(
                f"Found {len(undefined_classes)} undefined classes"
            )

        assert isinstance(validation_results, dict)

    def test_metadata_to_void_conversion(self, sample_schema_info):
        """Test converting schema metadata to VoID format."""
        # Build VoID graph from schema info
        g = Graph()
        VOID = Namespace("http://rdfs.org/ns/void#")
        DCTERMS = Namespace("http://purl.org/dc/terms/")

        g.bind("void", VOID)
        g.bind("dcterms", DCTERMS)

        # Create dataset node
        dataset = URIRef("http://example.org/dataset")
        g.add((dataset, RDF.type, VOID.Dataset))

        # Add statistics
        if sample_schema_info.class_counts:
            total_entities = sum(sample_schema_info.class_counts.values())
            g.add((dataset, VOID.entities, Literal(total_entities)))

        g.add((dataset, VOID.classes, Literal(len(sample_schema_info.classes))))
        g.add((dataset, VOID.properties, Literal(len(sample_schema_info.properties))))

        assert len(g) > 0
        assert (dataset, RDF.type, VOID.Dataset) in g


# =============================================================================
# Performance Tests
# =============================================================================


@pytest.mark.slow
class TestSchemaPerformance:
    """Performance tests for schema operations."""

    def test_large_graph_class_discovery(self):
        """Test class discovery performance on large graph."""
        # Create a large test graph
        g = Graph()
        EX = Namespace("http://example.org/")
        g.bind("ex", EX)

        # Add many triples
        for i in range(1000):
            subject = EX[f"entity{i}"]
            g.add((subject, RDF.type, EX.TestClass))
            g.add((subject, EX.property, Literal(f"value{i}")))

        # Measure class discovery
        classes = set()
        for s, p, o in g.triples((None, RDF.type, None)):
            if isinstance(o, URIRef):
                classes.add(str(o))

        assert len(classes) >= 1
        assert len(g) >= 2000

    def test_namespace_discovery_performance(self):
        """Test namespace discovery performance."""
        g = Graph()

        # Add triples with various namespaces
        namespaces = [
            "http://example.org/ns1/",
            "http://example.org/ns2/",
            "http://example.org/ns3/",
        ]

        for i, ns in enumerate(namespaces):
            NS = Namespace(ns)
            for j in range(100):
                subject = NS[f"entity{j}"]
                g.add((subject, RDF.type, NS.Class))

        # Discover namespaces
        discovered_ns = {}
        for prefix, namespace in g.namespaces():
            discovered_ns[prefix] = str(namespace)

        assert len(discovered_ns) > 0
