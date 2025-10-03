"""
SPARQL endpoints configuration module.

This module provides predefined SPARQL endpoint configurations for common
biological and knowledge graph endpoints, including UniProt, Wikidata, DBpedia,
and others. It also includes federated query support for cross-dataset integration.
"""

from .uniprot import (
    UNIPROT_ENDPOINT,
    UNIPROT_PREFIXES,
    UNIPROT_SCHEMA_INFO,
    UniProtSchema,
    UniProtQueryHelper,
    UniProtExampleQueries,
    PERFORMANCE_TIPS as UNIPROT_PERFORMANCE_TIPS,
    get_prefix_string as get_uniprot_prefix_string,
)

from .clinvar import (
    CLINVAR_ENDPOINT,
    GT2RDF_ENDPOINT,
    CLINVAR_PREFIXES,
    CLINVAR_SCHEMA_INFO,
    ClinVarSchema,
    ClinVarQueryHelper,
    ClinVarExampleQueries,
    CLINICAL_WORKFLOWS,
    CLINICAL_INTERPRETATION_GUIDE,
    PERFORMANCE_TIPS as CLINVAR_PERFORMANCE_TIPS,
    get_prefix_string as get_clinvar_prefix_string,
)

from .federated import (
    FederatedQueryBuilder,
    CrossDatasetExamples,
    ResultMerger,
    ResilientFederatedExecutor,
    EndpointCapabilities,
    QueryOptimizationHints,
    OptimizationStrategy,
    BIOMEDICAL_ENDPOINTS,
    FEDERATED_PREFIXES,
    get_federated_prefix_string,
    FederatedQueryError,
    FEDERATED_QUERY_BEST_PRACTICES,
)

__all__ = [
    # UniProt
    "UNIPROT_ENDPOINT",
    "UNIPROT_PREFIXES",
    "UNIPROT_SCHEMA_INFO",
    "UniProtSchema",
    "UniProtQueryHelper",
    "UniProtExampleQueries",
    "UNIPROT_PERFORMANCE_TIPS",
    "get_uniprot_prefix_string",

    # ClinVar
    "CLINVAR_ENDPOINT",
    "GT2RDF_ENDPOINT",
    "CLINVAR_PREFIXES",
    "CLINVAR_SCHEMA_INFO",
    "ClinVarSchema",
    "ClinVarQueryHelper",
    "ClinVarExampleQueries",
    "CLINICAL_WORKFLOWS",
    "CLINICAL_INTERPRETATION_GUIDE",
    "CLINVAR_PERFORMANCE_TIPS",
    "get_clinvar_prefix_string",

    # Federated
    "FederatedQueryBuilder",
    "CrossDatasetExamples",
    "ResultMerger",
    "ResilientFederatedExecutor",
    "EndpointCapabilities",
    "QueryOptimizationHints",
    "OptimizationStrategy",
    "BIOMEDICAL_ENDPOINTS",
    "FEDERATED_PREFIXES",
    "get_federated_prefix_string",
    "FederatedQueryError",
    "FEDERATED_QUERY_BEST_PRACTICES",
]
