"""
Pytest configuration and fixtures for sparql-agent tests.

This module provides reusable fixtures, mock objects, and test utilities
for the entire test suite.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock

import pytest
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

from sparql_agent.core.types import (
    EndpointInfo,
    OntologyInfo,
    OWLClass,
    OWLProperty,
    OWLPropertyType,
    QueryResult,
    QueryStatus,
    SchemaInfo,
    LLMResponse,
    GeneratedQuery,
    FormattedResult,
)
from sparql_agent.core.exceptions import (
    EndpointConnectionError,
    QuerySyntaxError,
    QueryExecutionError,
)


# =============================================================================
# Fixtures for Test Data Paths
# =============================================================================


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_rdf_file(test_data_dir):
    """Create a sample RDF file."""
    rdf_content = """
    @prefix ex: <http://example.org/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    ex:Alice a foaf:Person ;
        foaf:name "Alice Smith" ;
        foaf:age 30 ;
        foaf:knows ex:Bob .

    ex:Bob a foaf:Person ;
        foaf:name "Bob Jones" ;
        foaf:age 25 .
    """
    rdf_file = test_data_dir / "sample.ttl"
    rdf_file.write_text(rdf_content)
    return str(rdf_file)


@pytest.fixture
def sample_owl_file(test_data_dir):
    """Create a sample OWL ontology file."""
    owl_content = """
    @prefix : <http://example.org/ontology#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    <http://example.org/ontology> a owl:Ontology ;
        rdfs:label "Example Ontology" ;
        rdfs:comment "A simple example ontology" .

    :Person a owl:Class ;
        rdfs:label "Person" ;
        rdfs:comment "A human being" .

    :Organization a owl:Class ;
        rdfs:label "Organization" ;
        rdfs:comment "An organized group of people" .

    :name a owl:DatatypeProperty ;
        rdfs:label "name" ;
        rdfs:domain :Person ;
        rdfs:range xsd:string .

    :worksFor a owl:ObjectProperty ;
        rdfs:label "works for" ;
        rdfs:domain :Person ;
        rdfs:range :Organization .
    """
    owl_file = test_data_dir / "sample.owl"
    owl_file.write_text(owl_content)
    return str(owl_file)


@pytest.fixture
def sample_void_file(test_data_dir):
    """Create a sample VoID description file."""
    void_content = """
    @prefix void: <http://rdfs.org/ns/void#> .
    @prefix dcterms: <http://purl.org/dc/terms/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .

    <http://example.org/dataset> a void:Dataset ;
        dcterms:title "Example Dataset" ;
        dcterms:description "A sample dataset" ;
        void:sparqlEndpoint <http://example.org/sparql> ;
        void:triples 1000 ;
        void:entities 100 ;
        void:classes 5 ;
        void:properties 10 .
    """
    void_file = test_data_dir / "void.ttl"
    void_file.write_text(void_content)
    return str(void_file)


# =============================================================================
# Fixtures for Core Types
# =============================================================================


@pytest.fixture
def sample_endpoint_info():
    """Sample endpoint information."""
    return EndpointInfo(
        url="http://example.org/sparql",
        name="Example SPARQL Endpoint",
        description="A sample SPARQL endpoint for testing",
        timeout=30,
        supports_update=False,
        version="1.1",
    )


@pytest.fixture
def sample_owl_class():
    """Sample OWL class."""
    return OWLClass(
        uri="http://example.org/Person",
        label=["Person", "Human"],
        comment=["A human being"],
        subclass_of=["http://example.org/Agent"],
        properties=["http://example.org/name", "http://example.org/age"],
        instances_count=100,
    )


@pytest.fixture
def sample_owl_property():
    """Sample OWL property."""
    return OWLProperty(
        uri="http://example.org/name",
        label=["name", "full name"],
        comment=["The name of a person"],
        property_type=OWLPropertyType.DATATYPE_PROPERTY,
        domain=["http://example.org/Person"],
        range=["http://www.w3.org/2001/XMLSchema#string"],
        is_functional=True,
        usage_count=100,
    )


@pytest.fixture
def sample_ontology_info(sample_owl_class, sample_owl_property):
    """Sample ontology information."""
    return OntologyInfo(
        uri="http://example.org/ontology",
        title="Example Ontology",
        description="A sample ontology for testing",
        version="1.0",
        classes={sample_owl_class.uri: sample_owl_class},
        properties={sample_owl_property.uri: sample_owl_property},
        namespaces={
            "ex": "http://example.org/",
            "foaf": "http://xmlns.com/foaf/0.1/",
        },
        created=datetime.now(),
    )


@pytest.fixture
def sample_schema_info(sample_endpoint_info, sample_ontology_info):
    """Sample schema information."""
    return SchemaInfo(
        classes={"http://example.org/Person", "http://example.org/Organization"},
        properties={"http://example.org/name", "http://example.org/worksFor"},
        namespaces={
            "ex": "http://example.org/",
            "foaf": "http://xmlns.com/foaf/0.1/",
        },
        class_counts={
            "http://example.org/Person": 50,
            "http://example.org/Organization": 20,
        },
        property_counts={
            "http://example.org/name": 70,
            "http://example.org/worksFor": 40,
        },
        ontology=sample_ontology_info,
        endpoint_info=sample_endpoint_info,
        discovered_at=datetime.now(),
    )


@pytest.fixture
def sample_query_result():
    """Sample successful query result."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        data=[
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ],
        query="SELECT ?name ?age WHERE { ?person foaf:name ?name ; foaf:age ?age }",
        execution_time=0.123,
        bindings=[
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ],
        row_count=2,
        variables=["name", "age"],
    )


@pytest.fixture
def sample_llm_response():
    """Sample LLM response."""
    return LLMResponse(
        content="This is a sample response from the LLM",
        model="claude-3-sonnet-20240229",
        prompt="Generate a SPARQL query...",
        tokens_used=150,
        prompt_tokens=100,
        completion_tokens=50,
        finish_reason="stop",
        cost=0.001,
        latency=1.5,
    )


@pytest.fixture
def sample_generated_query():
    """Sample generated query."""
    return GeneratedQuery(
        query="SELECT ?name WHERE { ?person foaf:name ?name }",
        natural_language="Find all names",
        explanation="This query retrieves all names from the dataset",
        confidence=0.95,
        used_ontology=True,
        ontology_classes=["http://xmlns.com/foaf/0.1/Person"],
        ontology_properties=["http://xmlns.com/foaf/0.1/name"],
    )


# =============================================================================
# Fixtures for Mock Objects
# =============================================================================


@pytest.fixture
def mock_sparql_endpoint():
    """Mock SPARQL endpoint."""
    mock = Mock()
    mock.endpoint_info = EndpointInfo(url="http://example.org/sparql")
    mock.test_connection.return_value = True
    mock.query.return_value = QueryResult(
        status=QueryStatus.SUCCESS,
        data=[],
        row_count=0,
        variables=[],
    )
    return mock


@pytest.fixture
def mock_ontology_provider(sample_ontology_info):
    """Mock ontology provider."""
    mock = Mock()
    mock.load_ontology.return_value = sample_ontology_info
    mock.get_class.return_value = sample_ontology_info.classes.get(
        "http://example.org/Person"
    )
    mock.find_classes_by_label.return_value = ["http://example.org/Person"]
    mock.find_properties_by_label.return_value = ["http://example.org/name"]
    mock.validate_ontology.return_value = []
    return mock


@pytest.fixture
def mock_llm_provider(sample_llm_response):
    """Mock LLM provider."""
    mock = Mock()
    mock.model = "claude-3-sonnet-20240229"
    mock.generate.return_value = sample_llm_response
    mock.generate_with_json_schema.return_value = sample_llm_response
    mock.count_tokens.return_value = 100
    mock.estimate_cost.return_value = 0.001
    mock.test_connection.return_value = True
    mock.get_model_info.return_value = {
        "context_length": 200000,
        "max_output_tokens": 4096,
    }
    return mock


@pytest.fixture
def mock_schema_discoverer(sample_schema_info):
    """Mock schema discoverer."""
    mock = Mock()
    mock.discover_schema.return_value = sample_schema_info
    mock.discover_classes.return_value = sample_schema_info.classes
    mock.discover_properties.return_value = sample_schema_info.properties
    mock.discover_namespaces.return_value = sample_schema_info.namespaces
    mock.get_class_count.return_value = 50
    mock.get_property_count.return_value = 70
    return mock


@pytest.fixture
def mock_http_response():
    """Mock HTTP response for SPARQL endpoint."""
    mock = Mock()
    mock.status_code = 200
    mock.headers = {"Content-Type": "application/sparql-results+json"}
    mock.json.return_value = {
        "head": {"vars": ["name", "age"]},
        "results": {
            "bindings": [
                {
                    "name": {"type": "literal", "value": "Alice"},
                    "age": {"type": "literal", "value": "30"},
                }
            ]
        },
    }
    mock.text = json.dumps(mock.json.return_value)
    return mock


# =============================================================================
# Fixtures for RDFLib Graphs
# =============================================================================


@pytest.fixture
def sample_rdf_graph():
    """Sample RDF graph using rdflib."""
    g = Graph()
    EX = Namespace("http://example.org/")
    FOAF = Namespace("http://xmlns.com/foaf/0.1/")

    g.bind("ex", EX)
    g.bind("foaf", FOAF)

    # Add some sample triples
    alice = EX.Alice
    bob = EX.Bob

    g.add((alice, RDF.type, FOAF.Person))
    g.add((alice, FOAF.name, Literal("Alice Smith")))
    g.add((alice, FOAF.age, Literal(30)))
    g.add((alice, FOAF.knows, bob))

    g.add((bob, RDF.type, FOAF.Person))
    g.add((bob, FOAF.name, Literal("Bob Jones")))
    g.add((bob, FOAF.age, Literal(25)))

    return g


@pytest.fixture
def sample_owl_graph():
    """Sample OWL ontology graph using rdflib."""
    g = Graph()
    EX = Namespace("http://example.org/ontology#")

    g.bind("ex", EX)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)

    # Ontology metadata
    ontology = URIRef("http://example.org/ontology")
    g.add((ontology, RDF.type, OWL.Ontology))
    g.add((ontology, RDFS.label, Literal("Example Ontology")))

    # Classes
    person = EX.Person
    organization = EX.Organization

    g.add((person, RDF.type, OWL.Class))
    g.add((person, RDFS.label, Literal("Person")))
    g.add((person, RDFS.comment, Literal("A human being")))

    g.add((organization, RDF.type, OWL.Class))
    g.add((organization, RDFS.label, Literal("Organization")))

    # Properties
    name_prop = EX.name
    works_for = EX.worksFor

    g.add((name_prop, RDF.type, OWL.DatatypeProperty))
    g.add((name_prop, RDFS.label, Literal("name")))
    g.add((name_prop, RDFS.domain, person))
    g.add((name_prop, RDFS.range, XSD.string))

    g.add((works_for, RDF.type, OWL.ObjectProperty))
    g.add((works_for, RDFS.label, Literal("works for")))
    g.add((works_for, RDFS.domain, person))
    g.add((works_for, RDFS.range, organization))

    return g


# =============================================================================
# Fixtures for SPARQL Queries
# =============================================================================


@pytest.fixture
def sample_sparql_queries():
    """Collection of sample SPARQL queries."""
    return {
        "select_all": "SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        "select_names": "SELECT ?name WHERE { ?person foaf:name ?name }",
        "select_with_filter": """
            SELECT ?name ?age
            WHERE {
                ?person foaf:name ?name ;
                        foaf:age ?age
                FILTER (?age > 25)
            }
        """,
        "construct": """
            CONSTRUCT { ?s ?p ?o }
            WHERE { ?s ?p ?o }
            LIMIT 10
        """,
        "ask": "ASK { ?s a foaf:Person }",
        "describe": "DESCRIBE <http://example.org/Alice>",
        "invalid_syntax": "SELCT ?s WHERE { ?s ?p ?o }",  # Invalid
        "complex_query": """
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX ex: <http://example.org/>

            SELECT ?person ?name ?friend_name
            WHERE {
                ?person a foaf:Person ;
                        foaf:name ?name ;
                        foaf:knows ?friend .
                ?friend foaf:name ?friend_name .
            }
            ORDER BY ?name
            LIMIT 100
        """,
    }


# =============================================================================
# Utility Functions
# =============================================================================


@pytest.fixture
def assert_rdf_graph_equal():
    """Utility to compare two RDF graphs."""
    def _compare(graph1: Graph, graph2: Graph) -> bool:
        """Check if two graphs are isomorphic."""
        return graph1.isomorphic(graph2)
    return _compare


@pytest.fixture
def create_mock_response():
    """Factory for creating mock HTTP responses."""
    def _create(
        status_code: int = 200,
        json_data: Optional[Dict] = None,
        text: Optional[str] = None,
        headers: Optional[Dict] = None,
    ):
        mock = Mock()
        mock.status_code = status_code
        mock.headers = headers or {}
        if json_data:
            mock.json.return_value = json_data
            mock.text = json.dumps(json_data)
        elif text:
            mock.text = text
            mock.json.side_effect = ValueError("Not JSON")
        return mock
    return _create


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_api_key: mark test as requiring API keys"
    )
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """Reset environment variables for each test."""
    # Clear API keys to prevent accidental API calls
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLS_API_KEY", raising=False)
