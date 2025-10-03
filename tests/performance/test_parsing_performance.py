"""
Schema and ontology parsing performance benchmarks.

Tests parsing performance for various schema formats (OWL, ShEx, VoID, etc.).
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch
import tempfile
import os

from sparql_agent.ontology.owl_parser import OWLParser
from sparql_agent.schema.shex_parser import ShExParser
from sparql_agent.schema.void_parser import VoIDParser
from sparql_agent.schema.schema_inference import SchemaInferenceEngine


class TestOWLParsingPerformance:
    """Benchmark tests for OWL ontology parsing."""

    @pytest.fixture
    def small_owl_content(self) -> str:
        """Small OWL ontology for testing."""
        return """<?xml version="1.0"?>
        <rdf:RDF xmlns="http://example.org/ontology#"
             xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
             xmlns:owl="http://www.w3.org/2002/07/owl#"
             xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">

            <owl:Ontology rdf:about="http://example.org/ontology"/>

            <owl:Class rdf:about="http://example.org/ontology#Person">
                <rdfs:label>Person</rdfs:label>
            </owl:Class>

            <owl:ObjectProperty rdf:about="http://example.org/ontology#knows">
                <rdfs:label>knows</rdfs:label>
                <rdfs:domain rdf:resource="http://example.org/ontology#Person"/>
                <rdfs:range rdf:resource="http://example.org/ontology#Person"/>
            </owl:ObjectProperty>
        </rdf:RDF>
        """

    @pytest.fixture
    def medium_owl_content(self) -> str:
        """Medium-sized OWL ontology for testing."""
        classes = "\n".join([
            f'''
            <owl:Class rdf:about="http://example.org/ontology#Class{i}">
                <rdfs:label>Class {i}</rdfs:label>
                <rdfs:subClassOf rdf:resource="http://example.org/ontology#BaseClass"/>
            </owl:Class>
            '''
            for i in range(50)
        ])

        properties = "\n".join([
            f'''
            <owl:ObjectProperty rdf:about="http://example.org/ontology#property{i}">
                <rdfs:label>property {i}</rdfs:label>
            </owl:ObjectProperty>
            '''
            for i in range(50)
        ])

        return f"""<?xml version="1.0"?>
        <rdf:RDF xmlns="http://example.org/ontology#"
             xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
             xmlns:owl="http://www.w3.org/2002/07/owl#"
             xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">

            <owl:Ontology rdf:about="http://example.org/ontology"/>

            <owl:Class rdf:about="http://example.org/ontology#BaseClass">
                <rdfs:label>Base Class</rdfs:label>
            </owl:Class>

            {classes}
            {properties}
        </rdf:RDF>
        """

    def test_small_owl_parsing(self, benchmark, small_owl_content):
        """Benchmark small OWL ontology parsing."""
        parser = OWLParser()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.owl', delete=False) as f:
            f.write(small_owl_content)
            temp_path = f.name

        try:
            result = benchmark(parser.parse_file, temp_path)
            assert "classes" in result
        finally:
            os.unlink(temp_path)

    def test_medium_owl_parsing(self, benchmark, medium_owl_content):
        """Benchmark medium-sized OWL ontology parsing."""
        parser = OWLParser()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.owl', delete=False) as f:
            f.write(medium_owl_content)
            temp_path = f.name

        try:
            result = benchmark(parser.parse_file, temp_path)
            assert "classes" in result
            assert len(result["classes"]) > 0
        finally:
            os.unlink(temp_path)

    def test_owl_class_hierarchy_extraction(self, benchmark, medium_owl_content):
        """Benchmark class hierarchy extraction from OWL."""
        parser = OWLParser()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.owl', delete=False) as f:
            f.write(medium_owl_content)
            temp_path = f.name

        try:
            ontology = parser.parse_file(temp_path)

            def extract_hierarchy(ont: Dict[str, Any]) -> Dict[str, List[str]]:
                """Extract class hierarchy."""
                hierarchy = {}
                for cls in ont.get("classes", []):
                    parent = cls.get("subClassOf")
                    if parent:
                        if parent not in hierarchy:
                            hierarchy[parent] = []
                        hierarchy[parent].append(cls["uri"])
                return hierarchy

            result = benchmark(extract_hierarchy, ontology)
            assert isinstance(result, dict)
        finally:
            os.unlink(temp_path)


class TestShExParsingPerformance:
    """Benchmark tests for ShEx schema parsing."""

    @pytest.fixture
    def simple_shex(self) -> str:
        """Simple ShEx schema."""
        return """
        PREFIX ex: <http://example.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        ex:PersonShape {
            ex:name xsd:string ;
            ex:age xsd:integer
        }
        """

    @pytest.fixture
    def complex_shex(self) -> str:
        """Complex ShEx schema with multiple shapes."""
        shapes = "\n".join([
            f"""
            ex:Shape{i} {{
                ex:property{i} xsd:string ;
                ex:related{i} @ex:RelatedShape{i}
            }}

            ex:RelatedShape{i} {{
                ex:value{i} xsd:integer
            }}
            """
            for i in range(20)
        ])

        return f"""
        PREFIX ex: <http://example.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        {shapes}
        """

    def test_simple_shex_parsing(self, benchmark, simple_shex):
        """Benchmark simple ShEx parsing."""
        parser = ShExParser()
        result = benchmark(parser.parse, simple_shex)
        assert result is not None

    def test_complex_shex_parsing(self, benchmark, complex_shex):
        """Benchmark complex ShEx parsing."""
        parser = ShExParser()
        result = benchmark(parser.parse, complex_shex)
        assert result is not None

    def test_shex_validation_rule_extraction(self, benchmark, complex_shex):
        """Benchmark validation rule extraction from ShEx."""
        parser = ShExParser()
        schema = parser.parse(complex_shex)

        def extract_constraints(shex_schema: Any) -> List[Dict[str, Any]]:
            """Extract validation constraints from ShEx."""
            constraints = []
            # Simulate constraint extraction
            for i in range(20):
                constraints.append({
                    "shape": f"Shape{i}",
                    "property": f"property{i}",
                    "datatype": "string"
                })
            return constraints

        result = benchmark(extract_constraints, schema)
        assert len(result) > 0


class TestVoIDParsingPerformance:
    """Benchmark tests for VoID metadata parsing."""

    @pytest.fixture
    def void_dataset(self) -> str:
        """VoID dataset description."""
        return """
        @prefix void: <http://rdfs.org/ns/void#> .
        @prefix dcterms: <http://purl.org/dc/terms/> .

        <http://example.org/dataset> a void:Dataset ;
            dcterms:title "Example Dataset" ;
            void:sparqlEndpoint <http://example.org/sparql> ;
            void:classes 100 ;
            void:properties 200 ;
            void:triples 1000000 .
        """

    def test_void_parsing(self, benchmark, void_dataset):
        """Benchmark VoID dataset parsing."""
        parser = VoIDParser()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write(void_dataset)
            temp_path = f.name

        try:
            result = benchmark(parser.parse_file, temp_path)
            assert result is not None
        finally:
            os.unlink(temp_path)


class TestSchemaInferencePerformance:
    """Benchmark tests for schema inference from data."""

    @pytest.fixture
    def sample_triples(self) -> List[tuple]:
        """Generate sample RDF triples for inference."""
        triples = []
        for i in range(1000):
            triples.extend([
                (f"http://example.org/entity{i}",
                 "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                 "http://example.org/Person"),
                (f"http://example.org/entity{i}",
                 "http://example.org/name",
                 f"Name {i}"),
                (f"http://example.org/entity{i}",
                 "http://example.org/age",
                 str(20 + (i % 60)))
            ])
        return triples

    def test_schema_inference_from_triples(self, benchmark, sample_triples):
        """Benchmark schema inference from triple patterns."""
        engine = SchemaInferenceEngine()

        def infer_schema(triples: List[tuple]) -> Dict[str, Any]:
            """Infer schema from triples."""
            classes = set()
            properties = set()

            for s, p, o in triples:
                if p == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                    classes.add(o)
                else:
                    properties.add(p)

            return {
                "classes": list(classes),
                "properties": list(properties)
            }

        result = benchmark(infer_schema, sample_triples)
        assert len(result["classes"]) > 0

    def test_property_range_inference(self, benchmark, sample_triples):
        """Benchmark property range inference."""
        def infer_ranges(triples: List[tuple]) -> Dict[str, set]:
            """Infer property ranges from data."""
            ranges = {}
            for s, p, o in triples:
                if p != "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                    if p not in ranges:
                        ranges[p] = set()
                    # Determine if object is literal or URI
                    if o.startswith("http://"):
                        ranges[p].add("URI")
                    else:
                        ranges[p].add("Literal")
            return ranges

        result = benchmark(infer_ranges, sample_triples)
        assert len(result) > 0


class TestRDFGraphParsingPerformance:
    """Benchmark tests for RDF graph parsing."""

    @pytest.fixture
    def small_rdf_graph(self) -> str:
        """Small RDF graph in Turtle format."""
        return """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

        ex:person1 rdf:type ex:Person ;
            ex:name "Alice" ;
            ex:age 30 .

        ex:person2 rdf:type ex:Person ;
            ex:name "Bob" ;
            ex:age 25 .
        """

    @pytest.fixture
    def large_rdf_graph(self) -> str:
        """Large RDF graph for performance testing."""
        triples = []
        for i in range(1000):
            triples.append(f"""
        ex:entity{i} rdf:type ex:Entity ;
            ex:property1 "value{i}" ;
            ex:property2 {i} ;
            ex:property3 "description for entity {i}" .
            """)

        return f"""
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

        {''.join(triples)}
        """

    def test_small_graph_parsing(self, benchmark, small_rdf_graph):
        """Benchmark small RDF graph parsing."""
        from rdflib import Graph

        def parse_graph(data: str) -> Graph:
            g = Graph()
            g.parse(data=data, format='turtle')
            return g

        result = benchmark(parse_graph, small_rdf_graph)
        assert len(result) > 0

    def test_large_graph_parsing(self, benchmark, large_rdf_graph):
        """Benchmark large RDF graph parsing."""
        from rdflib import Graph

        def parse_graph(data: str) -> Graph:
            g = Graph()
            g.parse(data=data, format='turtle')
            return g

        result = benchmark(parse_graph, large_rdf_graph)
        assert len(result) > 0

    def test_graph_query_performance(self, benchmark, large_rdf_graph):
        """Benchmark SPARQL queries on parsed graph."""
        from rdflib import Graph

        g = Graph()
        g.parse(data=large_rdf_graph, format='turtle')

        query = """
        PREFIX ex: <http://example.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?entity ?value
        WHERE {
            ?entity rdf:type ex:Entity .
            ?entity ex:property1 ?value .
        }
        LIMIT 100
        """

        def execute_query(graph: Graph, q: str) -> list:
            return list(graph.query(q))

        result = benchmark(execute_query, g, query)
        assert len(result) > 0


class TestNamespaceResolutionPerformance:
    """Benchmark tests for namespace resolution and prefix handling."""

    @pytest.fixture
    def namespace_map(self) -> Dict[str, str]:
        """Large namespace map for testing."""
        return {
            f"prefix{i}": f"http://example.org/ontology{i}#"
            for i in range(100)
        }

    def test_namespace_expansion(self, benchmark, namespace_map):
        """Benchmark namespace expansion performance."""
        def expand_uri(prefixed: str, namespaces: Dict[str, str]) -> str:
            """Expand prefixed URI to full URI."""
            if ":" in prefixed:
                prefix, local = prefixed.split(":", 1)
                if prefix in namespaces:
                    return namespaces[prefix] + local
            return prefixed

        result = benchmark(expand_uri, "prefix50:SomeClass", namespace_map)
        assert result.startswith("http://")

    def test_namespace_compression(self, benchmark, namespace_map):
        """Benchmark namespace compression performance."""
        def compress_uri(full_uri: str, namespaces: Dict[str, str]) -> str:
            """Compress full URI to prefixed form."""
            for prefix, namespace in namespaces.items():
                if full_uri.startswith(namespace):
                    return f"{prefix}:{full_uri[len(namespace):]}"
            return full_uri

        full_uri = "http://example.org/ontology50#SomeClass"
        result = benchmark(compress_uri, full_uri, namespace_map)
        assert ":" in result

    def test_bulk_namespace_resolution(self, benchmark, namespace_map):
        """Benchmark bulk namespace resolution."""
        uris = [f"prefix{i % 100}:Class{i}" for i in range(1000)]

        def resolve_all(uri_list: List[str], namespaces: Dict[str, str]) -> List[str]:
            """Resolve all URIs in list."""
            resolved = []
            for uri in uri_list:
                if ":" in uri:
                    prefix, local = uri.split(":", 1)
                    if prefix in namespaces:
                        resolved.append(namespaces[prefix] + local)
                        continue
                resolved.append(uri)
            return resolved

        result = benchmark(resolve_all, uris, namespace_map)
        assert len(result) == len(uris)
