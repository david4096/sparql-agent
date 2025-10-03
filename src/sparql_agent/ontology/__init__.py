"""
Ontology module for SPARQL Agent.

This module provides OWL ontology parsing and integration with the
EMBL-EBI Ontology Lookup Service (OLS4).
"""

from sparql_agent.ontology.ols_client import (
    COMMON_ONTOLOGIES,
    OLSClient,
    get_ontology_config,
    list_common_ontologies,
)
from sparql_agent.ontology.owl_parser import OWLParser

__all__ = [
    # OLS Client
    "OLSClient",
    "COMMON_ONTOLOGIES",
    "get_ontology_config",
    "list_common_ontologies",
    # OWL Parser
    "OWLParser",
]
