"""
SPARQL Agent - Intelligent SPARQL query agent with OWL ontology support.

This package provides a comprehensive framework for working with SPARQL endpoints,
OWL ontologies, and LLM-powered natural language query translation.
"""

__version__ = "0.1.0"
__author__ = "David"
__license__ = "MIT"

# Core abstractions available at package level
from sparql_agent.core import (
    SPARQLEndpoint,
    OntologyProvider,
    SchemaDiscoverer,
    QueryGenerator,
    LLMProvider,
    ResultFormatter,
    SPARQLAgentError,
)

__all__ = [
    "SPARQLEndpoint",
    "OntologyProvider",
    "SchemaDiscoverer",
    "QueryGenerator",
    "LLMProvider",
    "ResultFormatter",
    "SPARQLAgentError",
    "__version__",
]
