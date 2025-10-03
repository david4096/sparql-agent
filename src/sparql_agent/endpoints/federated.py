"""
Federated SPARQL Query Builder and Cross-Dataset Integration.

This module provides comprehensive support for federated SPARQL queries that span
multiple endpoints, enabling cross-dataset integration for complex biomedical research
scenarios. It includes query generation, optimization, and real-world examples for
integrating data from UniProt, PDB, ClinVar, ChEBI, Gene Ontology, and other sources.

Federated SPARQL queries use the SERVICE keyword to query multiple endpoints within
a single query, enabling complex analyses that combine data from heterogeneous sources.

Key Features:
- Federated query generation with SERVICE clauses
- Query optimization for minimal cross-service data transfer
- Error handling and graceful degradation
- Result merging strategies
- Real-world biomedical research scenarios
- Performance monitoring and caching

Official Documentation:
- SPARQL 1.1 Federated Query: https://www.w3.org/TR/sparql11-federated-query/
- UniProt SPARQL: https://sparql.uniprot.org/
- PDB SPARQL: https://rdf.wwpdb.org/sparql
- Wikidata SPARQL: https://query.wikidata.org/sparql
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from enum import Enum
import time
import logging
from datetime import datetime, timedelta

from ..core.types import EndpointInfo, QueryResult, QueryStatus
from .uniprot import UNIPROT_PREFIXES, get_prefix_string as uniprot_prefixes


# =============================================================================
# ENDPOINT REGISTRY
# =============================================================================

@dataclass
class EndpointCapabilities:
    """
    Capabilities and limitations of a SPARQL endpoint.

    Attributes:
        supports_federation: Whether endpoint can act as federation coordinator
        max_query_complexity: Maximum query complexity score (0-100)
        timeout_seconds: Maximum query timeout
        rate_limit: Requests per second limit
        supports_optional: Whether OPTIONAL clauses work reliably
        supports_filters: Filter capabilities
        supports_aggregation: Whether GROUP BY/aggregates work
        supports_subqueries: Whether subqueries are supported
        reliability_score: Historical reliability (0-1)
    """
    supports_federation: bool = True
    max_query_complexity: int = 50
    timeout_seconds: int = 60
    rate_limit: float = 5.0
    supports_optional: bool = True
    supports_filters: bool = True
    supports_aggregation: bool = True
    supports_subqueries: bool = True
    reliability_score: float = 1.0


# Biomedical SPARQL Endpoints Registry
BIOMEDICAL_ENDPOINTS = {
    "uniprot": EndpointInfo(
        url="https://sparql.uniprot.org/sparql",
        name="UniProt",
        description="Universal Protein Resource - protein sequences and functional information",
        supports_update=False,
        timeout=60,
        rate_limit=5.0,
        metadata={
            "capabilities": EndpointCapabilities(
                max_query_complexity=70,
                reliability_score=0.95
            ),
            "data_types": ["proteins", "genes", "taxonomy", "function", "disease"],
            "preferred_for": ["protein_info", "sequence", "function", "go_terms"]
        }
    ),

    "pdb": EndpointInfo(
        url="https://rdf.wwpdb.org/sparql",
        name="Protein Data Bank",
        description="3D protein structures and crystallography data",
        supports_update=False,
        timeout=45,
        rate_limit=3.0,
        metadata={
            "capabilities": EndpointCapabilities(
                max_query_complexity=60,
                reliability_score=0.90
            ),
            "data_types": ["structures", "molecules", "chains", "ligands"],
            "preferred_for": ["3d_structure", "crystallography", "binding_sites"]
        }
    ),

    "wikidata": EndpointInfo(
        url="https://query.wikidata.org/sparql",
        name="Wikidata",
        description="Free knowledge base with biomedical entities and relationships",
        supports_update=False,
        timeout=60,
        rate_limit=10.0,
        metadata={
            "capabilities": EndpointCapabilities(
                max_query_complexity=80,
                supports_federation=True,
                reliability_score=0.98
            ),
            "data_types": ["diseases", "chemicals", "genes", "proteins", "drugs"],
            "preferred_for": ["drug_info", "disease_info", "general_knowledge"]
        }
    ),

    "chembl": EndpointInfo(
        url="https://www.ebi.ac.uk/rdf/services/chembl/sparql",
        name="ChEMBL",
        description="Bioactive molecules with drug-like properties",
        supports_update=False,
        timeout=45,
        rate_limit=5.0,
        metadata={
            "capabilities": EndpointCapabilities(
                max_query_complexity=60,
                reliability_score=0.92
            ),
            "data_types": ["compounds", "bioactivity", "targets", "assays"],
            "preferred_for": ["drug_discovery", "compound_activity", "target_interactions"]
        }
    ),

    "disgenet": EndpointInfo(
        url="http://rdf.disgenet.org/sparql/",
        name="DisGeNET",
        description="Gene-disease associations",
        supports_update=False,
        timeout=30,
        rate_limit=3.0,
        metadata={
            "capabilities": EndpointCapabilities(
                max_query_complexity=50,
                reliability_score=0.88
            ),
            "data_types": ["genes", "diseases", "variants", "associations"],
            "preferred_for": ["gene_disease", "variant_associations"]
        }
    ),

    "bio2rdf": EndpointInfo(
        url="http://bio2rdf.org/sparql",
        name="Bio2RDF",
        description="Linked data for life sciences",
        supports_update=False,
        timeout=45,
        rate_limit=5.0,
        metadata={
            "capabilities": EndpointCapabilities(
                max_query_complexity=65,
                reliability_score=0.85
            ),
            "data_types": ["genes", "proteins", "diseases", "pathways", "publications"],
            "preferred_for": ["cross_references", "integrated_queries"]
        }
    ),
}


# Common prefixes for federated queries
FEDERATED_PREFIXES = {
    **UNIPROT_PREFIXES,

    # PDB prefixes
    "pdb": "http://rdf.wwpdb.org/schema/pdbx-v50.owl#",
    "pdbo": "http://rdf.wwpdb.org/schema/pdbx-v50.owl#",
    "pdbr": "http://rdf.wwpdb.org/pdb/",

    # Wikidata prefixes
    "wd": "http://www.wikidata.org/entity/",
    "wdt": "http://www.wikidata.org/prop/direct/",
    "wikibase": "http://wikiba.se/ontology#",
    "bd": "http://www.bigdata.com/rdf#",

    # ChEMBL prefixes
    "chembl": "http://rdf.ebi.ac.uk/resource/chembl/",
    "cco": "http://rdf.ebi.ac.uk/terms/chembl#",

    # DisGeNET prefixes
    "dgn": "http://rdf.disgenet.org/resource/disgenet/",
    "sio": "http://semanticscience.org/resource/",
    "ncit": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#",

    # Bio2RDF prefixes
    "bio2rdf": "http://bio2rdf.org/",

    # Additional ontology prefixes
    "chebi": "http://purl.obolibrary.org/obo/CHEBI_",
    "mondo": "http://purl.obolibrary.org/obo/MONDO_",
    "hp": "http://purl.obolibrary.org/obo/HP_",
    "doid": "http://purl.obolibrary.org/obo/DOID_",
}


def get_federated_prefix_string() -> str:
    """
    Generate SPARQL PREFIX declarations for federated queries.

    Returns:
        String containing all PREFIX declarations
    """
    return "\n".join(
        f"PREFIX {prefix}: <{uri}>"
        for prefix, uri in FEDERATED_PREFIXES.items()
    ) + "\n\n"


# =============================================================================
# QUERY OPTIMIZATION STRATEGIES
# =============================================================================

class OptimizationStrategy(Enum):
    """Strategies for optimizing federated queries."""
    MINIMIZE_TRANSFER = "minimize_transfer"  # Reduce data transfer between services
    EARLY_FILTERING = "early_filtering"      # Apply filters before federation
    SERVICE_ORDERING = "service_ordering"    # Order services by selectivity
    OPTIONAL_SERVICES = "optional_services"   # Use OPTIONAL for non-critical data
    RESULT_CACHING = "result_caching"        # Cache intermediate results
    PARALLEL_EXECUTION = "parallel_execution" # Execute services in parallel where possible


@dataclass
class QueryOptimizationHints:
    """
    Hints for optimizing federated query execution.

    Attributes:
        strategies: List of optimization strategies to apply
        service_priority: Ordered list of services by priority
        max_results_per_service: Limit results from each service
        use_optional_for: Services that can be optional
        filter_early: Filters to apply before federation
        estimated_selectivity: Expected selectivity of each service (0-1)
    """
    strategies: List[OptimizationStrategy] = field(default_factory=list)
    service_priority: List[str] = field(default_factory=list)
    max_results_per_service: Dict[str, int] = field(default_factory=dict)
    use_optional_for: Set[str] = field(default_factory=set)
    filter_early: List[str] = field(default_factory=list)
    estimated_selectivity: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# FEDERATED QUERY BUILDER
# =============================================================================

class FederatedQueryBuilder:
    """
    Builder for federated SPARQL queries spanning multiple endpoints.

    This class generates SPARQL queries with SERVICE clauses to query multiple
    endpoints, with built-in optimization and error handling.
    """

    def __init__(
        self,
        coordinator_endpoint: Optional[str] = None,
        enable_optimization: bool = True,
        cache_results: bool = True,
        timeout: int = 120
    ):
        """
        Initialize the federated query builder.

        Args:
            coordinator_endpoint: Endpoint to coordinate federation (None = use primary)
            enable_optimization: Enable query optimization
            cache_results: Cache intermediate results
            timeout: Default timeout for federated queries
        """
        self.coordinator_endpoint = coordinator_endpoint
        self.enable_optimization = enable_optimization
        self.cache_results = cache_results
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self._result_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(hours=1)

    def build_service_clause(
        self,
        endpoint_url: str,
        patterns: List[str],
        use_optional: bool = False,
        silent: bool = True
    ) -> str:
        """
        Build a SERVICE clause for federated query.

        Args:
            endpoint_url: URL of the remote SPARQL endpoint
            patterns: List of SPARQL triple patterns
            use_optional: Wrap in OPTIONAL block
            silent: Use SERVICE SILENT (ignore endpoint errors)

        Returns:
            SERVICE clause string

        Example:
            >>> builder = FederatedQueryBuilder()
            >>> patterns = ["?protein up:name 'BRCA1' .", "?protein up:sequence ?seq ."]
            >>> clause = builder.build_service_clause(
            ...     "https://sparql.uniprot.org/sparql",
            ...     patterns,
            ...     silent=True
            ... )
        """
        service_keyword = "SERVICE SILENT" if silent else "SERVICE"
        patterns_str = "\n        ".join(patterns)

        service_clause = f"""    {service_keyword} <{endpoint_url}> {{
        {patterns_str}
    }}"""

        if use_optional:
            service_clause = f"""    OPTIONAL {{
{service_clause}
    }}"""

        return service_clause

    def build_federated_query(
        self,
        select_vars: List[str],
        services: Dict[str, List[str]],
        filters: Optional[List[str]] = None,
        additional_patterns: Optional[List[str]] = None,
        optimization_hints: Optional[QueryOptimizationHints] = None,
        limit: Optional[int] = None,
        order_by: Optional[List[str]] = None
    ) -> str:
        """
        Build a complete federated SPARQL query.

        Args:
            select_vars: Variables to select
            services: Dict mapping endpoint URLs to list of patterns
            filters: Filter clauses to apply
            additional_patterns: Non-federated patterns
            optimization_hints: Query optimization hints
            limit: Result limit
            order_by: Variables to order by

        Returns:
            Complete SPARQL query string

        Example:
            >>> builder = FederatedQueryBuilder()
            >>> query = builder.build_federated_query(
            ...     select_vars=["?protein", "?structure"],
            ...     services={
            ...         "https://sparql.uniprot.org/sparql": [
            ...             "?protein a up:Protein .",
            ...             "?protein up:name 'BRCA1' ."
            ...         ],
            ...         "https://rdf.wwpdb.org/sparql": [
            ...             "?structure pdb:has_entity ?entity .",
            ...             "?entity pdb:entity_uniprot ?protein ."
            ...         ]
            ...     },
            ...     limit=10
            ... )
        """
        if optimization_hints and self.enable_optimization:
            services = self._optimize_service_order(services, optimization_hints)

        # Build query components
        select_clause = f"SELECT {' '.join(select_vars)}"

        # Build WHERE clause
        where_patterns = []

        # Add non-federated patterns first
        if additional_patterns:
            where_patterns.extend(additional_patterns)

        # Add SERVICE clauses
        for endpoint_url, patterns in services.items():
            use_optional = (
                optimization_hints and
                endpoint_url in optimization_hints.use_optional_for
            ) if optimization_hints else False

            service_clause = self.build_service_clause(
                endpoint_url,
                patterns,
                use_optional=use_optional,
                silent=True
            )
            where_patterns.append(service_clause)

        # Add filters
        if filters:
            where_patterns.extend([f"    {f}" for f in filters])

        where_clause = "WHERE {\n" + "\n\n".join(where_patterns) + "\n}"

        # Build query
        query_parts = [
            get_federated_prefix_string(),
            select_clause,
            where_clause
        ]

        # Add ORDER BY
        if order_by:
            query_parts.append(f"ORDER BY {' '.join(order_by)}")

        # Add LIMIT
        if limit:
            query_parts.append(f"LIMIT {limit}")

        return "\n".join(query_parts)

    def _optimize_service_order(
        self,
        services: Dict[str, List[str]],
        hints: QueryOptimizationHints
    ) -> Dict[str, List[str]]:
        """
        Optimize the order of SERVICE clauses based on selectivity.

        Args:
            services: Original service patterns
            hints: Optimization hints

        Returns:
            Reordered services dictionary
        """
        if not hints.estimated_selectivity:
            return services

        # Sort by selectivity (most selective first)
        sorted_endpoints = sorted(
            services.keys(),
            key=lambda ep: hints.estimated_selectivity.get(ep, 0.5),
            reverse=False  # Lower selectivity = fewer results = first
        )

        return {ep: services[ep] for ep in sorted_endpoints if ep in services}

    def add_result_limit_per_service(
        self,
        patterns: List[str],
        limit: int
    ) -> List[str]:
        """
        Add a LIMIT clause within SERVICE patterns.

        Args:
            patterns: Original patterns
            limit: Maximum results

        Returns:
            Patterns with limit
        """
        # This is a simplified approach - proper implementation would need
        # to wrap patterns in a subquery
        return patterns + [f"# LIMIT {limit}"]

    def estimate_query_cost(
        self,
        services: Dict[str, List[str]],
        optimization_hints: Optional[QueryOptimizationHints] = None
    ) -> Dict[str, Any]:
        """
        Estimate the computational cost of a federated query.

        Args:
            services: Service patterns
            optimization_hints: Optimization hints

        Returns:
            Dictionary with cost estimates
        """
        total_services = len(services)
        total_patterns = sum(len(patterns) for patterns in services.values())

        # Estimate based on service count and pattern complexity
        estimated_time = total_services * 2.0  # Base 2 seconds per service
        estimated_time += total_patterns * 0.5  # +0.5 seconds per pattern

        # Adjust for optimization
        if optimization_hints and OptimizationStrategy.MINIMIZE_TRANSFER in optimization_hints.strategies:
            estimated_time *= 0.7  # 30% reduction with optimization

        return {
            "estimated_time_seconds": estimated_time,
            "service_count": total_services,
            "pattern_count": total_patterns,
            "complexity_score": min(100, total_services * 10 + total_patterns * 2),
            "recommended_timeout": max(60, int(estimated_time * 2))
        }


# =============================================================================
# CROSS-DATASET INTEGRATION EXAMPLES
# =============================================================================

class CrossDatasetExamples:
    """
    Real-world examples of cross-dataset federated queries for biomedical research.

    These examples demonstrate practical integration patterns for combining data
    from multiple sources to answer complex biological questions.
    """

    def __init__(self):
        self.builder = FederatedQueryBuilder()

    def protein_disease_associations(
        self,
        gene_name: str = "BRCA1",
        limit: int = 20
    ) -> str:
        """
        Query UniProt proteins and associated diseases with variant information.

        Integrates:
        - UniProt: Protein information and disease annotations
        - Wikidata: Additional disease information and identifiers

        Args:
            gene_name: Gene name to search
            limit: Maximum results

        Returns:
            Federated SPARQL query

        Research Use Case:
            Identify all known disease associations for a gene/protein, combining
            curated data from UniProt with broader knowledge from Wikidata.
        """
        return get_federated_prefix_string() + f"""
SELECT DISTINCT ?protein ?proteinName ?disease ?diseaseName ?diseaseId ?significance
WHERE {{
    # Query UniProt for protein and disease information
    SERVICE <https://sparql.uniprot.org/sparql> {{
        # Find protein by gene name
        ?protein a up:Protein ;
                 up:encodedBy ?gene ;
                 up:organism ?organism ;
                 up:reviewed true .

        ?gene skos:prefLabel ?geneName .
        FILTER(REGEX(?geneName, "^{gene_name}$", "i"))

        # Get protein name
        OPTIONAL {{
            ?protein up:recommendedName ?recName .
            ?recName up:fullName ?proteinName .
        }}

        # Get disease annotations
        ?protein up:annotation ?diseaseAnnotation .
        ?diseaseAnnotation a up:Disease_Annotation ;
                          up:disease ?disease .

        ?disease skos:prefLabel ?diseaseName .

        # Get clinical significance if available
        OPTIONAL {{
            ?diseaseAnnotation rdfs:comment ?significance .
        }}
    }}

    # Optionally enrich with Wikidata disease information
    OPTIONAL {{
        SERVICE <https://query.wikidata.org/sparql> {{
            ?wikidataDisease wdt:P699 ?diseaseId .
            ?wikidataDisease rdfs:label ?wdLabel .
            FILTER(CONTAINS(LCASE(?diseaseName), LCASE(?wdLabel)))
        }}
    }}
}}
ORDER BY ?diseaseName
LIMIT {limit}
"""

    def protein_structure_function_integration(
        self,
        protein_id: str = "P38398",
        limit: int = 10
    ) -> str:
        """
        Integrate protein structure from PDB with functional annotations from UniProt.

        Integrates:
        - UniProt: Protein sequence, domains, and functional annotations
        - PDB: 3D structure information and resolution

        Args:
            protein_id: UniProt accession
            limit: Maximum structures to return

        Returns:
            Federated SPARQL query

        Research Use Case:
            Structure-function analysis: correlate protein domains and functions
            with available 3D structures for structural biology research.
        """
        return get_federated_prefix_string() + f"""
SELECT DISTINCT ?protein ?proteinName ?pdbId ?resolution ?method
                ?domain ?domainStart ?domainEnd ?function
WHERE {{
    # Get protein information from UniProt
    SERVICE <https://sparql.uniprot.org/sparql> {{
        BIND(<http://purl.uniprot.org/uniprot/{protein_id}> AS ?protein)

        # Protein name
        OPTIONAL {{
            ?protein up:recommendedName ?recName .
            ?recName up:fullName ?proteinName .
        }}

        # Domain information
        OPTIONAL {{
            ?protein up:annotation ?domainAnnotation .
            ?domainAnnotation a up:Domain_Annotation ;
                             rdfs:comment ?domain .

            OPTIONAL {{
                ?domainAnnotation up:range ?range .
                ?range faldo:begin/faldo:position ?domainStart ;
                       faldo:end/faldo:position ?domainEnd .
            }}
        }}

        # Functional annotation
        OPTIONAL {{
            ?protein up:annotation ?funcAnnotation .
            ?funcAnnotation a up:Function_Annotation ;
                           rdfs:comment ?function .
        }}

        # PDB cross-references
        ?protein rdfs:seeAlso ?pdbXref .
        ?pdbXref up:database <http://purl.uniprot.org/database/PDB> ;
                 up:id ?pdbId .
    }}

    # Get structure details from PDB
    OPTIONAL {{
        SERVICE SILENT <https://rdf.wwpdb.org/sparql> {{
            ?pdbEntry pdb:has_pdbx_database_statusCode ?pdbId ;
                     pdb:has_exptl ?exptl .

            # Experimental method
            ?exptl pdb:has_method ?methodNode .
            ?methodNode pdb:method_name ?method .

            # Resolution
            OPTIONAL {{
                ?pdbEntry pdb:has_refine ?refine .
                ?refine pdb:has_ls_d_res_high ?resolution .
            }}
        }}
    }}
}}
ORDER BY ?pdbId ?domainStart
LIMIT {limit}
"""

    def gene_ontology_protein_expression(
        self,
        go_term: str = "GO:0005634",  # nucleus
        taxon_id: str = "9606",        # human
        limit: int = 50
    ) -> str:
        """
        Find proteins with specific GO terms and their expression patterns.

        Integrates:
        - UniProt: GO annotations and subcellular location
        - Bgee/other: Expression data (placeholder - would need actual endpoint)

        Args:
            go_term: Gene Ontology term ID
            taxon_id: NCBI taxonomy ID
            limit: Maximum results

        Returns:
            Federated SPARQL query

        Research Use Case:
            Identify all proteins localized to a specific cellular compartment
            (via GO terms) and analyze their expression patterns across tissues.
        """
        go_id_normalized = go_term.replace("GO:", "GO_")

        return get_federated_prefix_string() + f"""
SELECT DISTINCT ?protein ?proteinName ?geneName ?goLabel
                ?location ?tissue ?expression
WHERE {{
    # Query UniProt for proteins with specific GO term
    SERVICE <https://sparql.uniprot.org/sparql> {{
        # Filter by taxonomy first (optimization)
        ?protein up:organism/up:taxon <http://purl.uniprot.org/taxonomy/{taxon_id}> .
        ?protein up:reviewed true .
        ?protein a up:Protein .

        # GO term annotation
        ?protein up:classifiedWith <http://purl.obolibrary.org/obo/{go_id_normalized}> .

        <http://purl.obolibrary.org/obo/{go_id_normalized}> rdfs:label ?goLabel .

        # Protein name
        OPTIONAL {{
            ?protein up:recommendedName ?recName .
            ?recName up:fullName ?proteinName .
        }}

        # Gene name
        OPTIONAL {{
            ?protein up:encodedBy ?gene .
            ?gene skos:prefLabel ?geneName .
        }}

        # Subcellular location
        OPTIONAL {{
            ?protein up:annotation ?locAnnotation .
            ?locAnnotation a up:Subcellular_Location_Annotation ;
                          up:locatedIn ?locNode .
            ?locNode skos:prefLabel ?location .
        }}

        # Tissue specificity
        OPTIONAL {{
            ?protein up:annotation ?tissueAnnotation .
            ?tissueAnnotation a up:Tissue_Specificity_Annotation ;
                             rdfs:comment ?tissue .
        }}
    }}

    # Could add expression data from Bgee or other sources
    # OPTIONAL {{
    #     SERVICE <expression-endpoint> {{
    #         ?expressionData sio:hasAttribute ?protein ;
    #                        sio:hasValue ?expression .
    #     }}
    # }}
}}
ORDER BY ?proteinName
LIMIT {limit}
"""

    def taxonomic_phylogenetic_protein_families(
        self,
        protein_family: str = "Kinase",
        root_taxon: str = "33208",  # Metazoa
        limit: int = 100
    ) -> str:
        """
        Explore protein families across taxonomic groups for comparative genomics.

        Integrates:
        - UniProt: Protein families and taxonomic information
        - Tree of Life: Phylogenetic relationships (conceptual)

        Args:
            protein_family: Protein family or domain name
            root_taxon: Root taxonomy ID for the clade
            limit: Maximum results

        Returns:
            Federated SPARQL query

        Research Use Case:
            Comparative genomics: trace the evolution of protein families
            across species, identifying orthologs and paralogs.
        """
        return get_federated_prefix_string() + f"""
SELECT DISTINCT ?protein ?proteinName ?species ?scientificName
                ?taxonRank ?family ?interpro
WHERE {{
    SERVICE <https://sparql.uniprot.org/sparql> {{
        # Find proteins in the taxonomic clade
        ?protein a up:Protein ;
                 up:organism ?organism ;
                 up:reviewed true .

        ?organism up:taxon ?species .

        # Taxonomic hierarchy
        ?species rdfs:subClassOf* <http://purl.uniprot.org/taxonomy/{root_taxon}> ;
                 up:scientificName ?scientificName .

        OPTIONAL {{ ?species up:rank ?taxonRank . }}

        # Protein family/domain
        {{
            # Via InterPro
            ?protein rdfs:seeAlso ?interproXref .
            ?interproXref up:database <http://purl.uniprot.org/database/InterPro> ;
                         up:id ?interpro .
            FILTER(CONTAINS(?interpro, "{protein_family}"))
        }} UNION {{
            # Via protein name
            ?protein up:recommendedName ?recName .
            ?recName up:fullName ?proteinName .
            FILTER(CONTAINS(LCASE(?proteinName), LCASE("{protein_family}")))
        }} UNION {{
            # Via keyword
            ?protein up:classifiedWith ?keyword .
            ?keyword a up:Keyword ;
                    skos:prefLabel ?keywordLabel .
            FILTER(CONTAINS(LCASE(?keywordLabel), LCASE("{protein_family}")))
        }}

        # Get protein name if not already retrieved
        OPTIONAL {{
            ?protein up:recommendedName ?recName2 .
            ?recName2 up:fullName ?proteinName .
        }}

        # Get family annotation
        OPTIONAL {{
            ?protein up:annotation ?familyAnnotation .
            ?familyAnnotation a up:Family_Annotation ;
                             rdfs:comment ?family .
        }}
    }}
}}
ORDER BY ?scientificName ?proteinName
LIMIT {limit}
"""

    def chemical_protein_interaction_network(
        self,
        compound_name: str = "Imatinib",
        activity_threshold: float = 100.0,  # nM
        limit: int = 50
    ) -> str:
        """
        Map chemical-protein interactions for drug discovery.

        Integrates:
        - ChEMBL: Compound bioactivity data
        - UniProt: Protein/target information
        - ChEBI: Chemical entity information

        Args:
            compound_name: Compound/drug name
            activity_threshold: Maximum IC50/Ki (nanomolar)
            limit: Maximum results

        Returns:
            Federated SPARQL query

        Research Use Case:
            Drug discovery: identify all proteins that bind to a compound
            with high affinity, along with their functions and pathways.
        """
        return get_federated_prefix_string() + f"""
SELECT DISTINCT ?compound ?compoundName ?target ?targetName
                ?activity ?activityType ?targetFunction ?disease
WHERE {{
    # Get compound and activity data from ChEMBL
    SERVICE SILENT <https://www.ebi.ac.uk/rdf/services/chembl/sparql> {{
        ?compound a cco:Substance ;
                 rdfs:label ?compoundName .

        FILTER(CONTAINS(LCASE(?compoundName), LCASE("{compound_name}")))

        # Activity data
        ?activity cco:hasMolecule ?compound ;
                 cco:hasTarget ?chemblTarget ;
                 cco:standardValue ?activityValue ;
                 cco:standardType ?activityType .

        # Filter by activity threshold
        FILTER(?activityValue <= {activity_threshold})
        FILTER(?activityType IN ("IC50", "Ki", "Kd", "EC50"))

        # Get target identifier
        ?chemblTarget cco:hasTargetComponent ?component .
        ?component cco:targetCmptXref ?xref .
        ?xref a cco:UniprotRef ;
             rdfs:label ?uniprotId .

        BIND(URI(CONCAT("http://purl.uniprot.org/uniprot/", ?uniprotId)) AS ?target)
    }}

    # Get target protein information from UniProt
    OPTIONAL {{
        SERVICE <https://sparql.uniprot.org/sparql> {{
            ?target up:recommendedName ?recName .
            ?recName up:fullName ?targetName .

            # Function
            OPTIONAL {{
                ?target up:annotation ?funcAnnotation .
                ?funcAnnotation a up:Function_Annotation ;
                               rdfs:comment ?targetFunction .
            }}

            # Disease associations
            OPTIONAL {{
                ?target up:annotation ?diseaseAnnotation .
                ?diseaseAnnotation a up:Disease_Annotation ;
                                  up:disease ?diseaseNode .
                ?diseaseNode skos:prefLabel ?disease .
            }}
        }}
    }}
}}
ORDER BY ?activityValue
LIMIT {limit}
"""

    def precision_medicine_variant_drug_response(
        self,
        gene_symbol: str = "CYP2D6",
        limit: int = 30
    ) -> str:
        """
        Integrate genetic variants with drug response for precision medicine.

        Integrates:
        - UniProt: Protein variants and their effects
        - Wikidata: Drug information
        - PharmGKB (conceptual): Pharmacogenomics data

        Args:
            gene_symbol: Gene symbol
            limit: Maximum results

        Returns:
            Federated SPARQL query

        Research Use Case:
            Precision medicine: identify genetic variants that affect drug
            metabolism or response, enabling personalized treatment decisions.
        """
        return get_federated_prefix_string() + f"""
SELECT DISTINCT ?protein ?proteinName ?variant ?variantDescription
                ?position ?original ?variation ?clinicalSignificance
WHERE {{
    SERVICE <https://sparql.uniprot.org/sparql> {{
        # Find protein by gene name
        ?protein a up:Protein ;
                 up:encodedBy ?gene ;
                 up:organism/up:taxon <http://purl.uniprot.org/taxonomy/9606> ;
                 up:reviewed true .

        ?gene skos:prefLabel ?geneName .
        FILTER(REGEX(?geneName, "^{gene_symbol}$", "i"))

        # Protein name
        OPTIONAL {{
            ?protein up:recommendedName ?recName .
            ?recName up:fullName ?proteinName .
        }}

        # Natural variants
        ?protein up:annotation ?variant .
        ?variant a up:Natural_Variant_Annotation .

        OPTIONAL {{ ?variant rdfs:comment ?variantDescription . }}

        # Position and substitution
        OPTIONAL {{
            ?variant up:range ?range .
            ?range faldo:begin/faldo:position ?position .
        }}

        OPTIONAL {{
            ?variant up:substitution ?sub .
            ?sub up:original ?original ;
                up:variation ?variation .
        }}

        # Clinical significance
        OPTIONAL {{
            ?variant up:disease ?diseaseNode .
            ?diseaseNode skos:prefLabel ?clinicalSignificance .
        }}
    }}

    # Could add PharmGKB data for drug-gene interactions
    # OPTIONAL {{
    #     SERVICE <pharmgkb-endpoint> {{
    #         ?interaction pharmgkb:hasGene ?gene ;
    #                     pharmgkb:hasDrug ?drug ;
    #                     pharmgkb:hasVariant ?variantId .
    #     }}
    # }}
}}
ORDER BY ?position
LIMIT {limit}
"""

    def systems_biology_pathway_integration(
        self,
        pathway_name: str = "Apoptosis",
        organism: str = "Homo sapiens",
        limit: int = 100
    ) -> str:
        """
        Integrate pathway, protein, and interaction data for systems biology.

        Integrates:
        - UniProt: Proteins in pathways
        - Reactome/KEGG: Pathway information (via UniProt cross-refs)
        - STRING: Protein-protein interactions (conceptual)

        Args:
            pathway_name: Pathway name or term
            organism: Organism name
            limit: Maximum results

        Returns:
            Federated SPARQL query

        Research Use Case:
            Systems biology: reconstruct biological pathways with all
            participating proteins, their interactions, and regulatory relationships.
        """
        return get_federated_prefix_string() + f"""
SELECT DISTINCT ?protein ?proteinName ?geneName ?pathway ?pathwayDb
                ?interaction ?interactant ?interactantName ?function
WHERE {{
    SERVICE <https://sparql.uniprot.org/sparql> {{
        # Find proteins in organism
        ?protein a up:Protein ;
                 up:organism ?org ;
                 up:reviewed true .

        ?org up:scientificName "{organism}" .

        # Pathway annotations
        ?protein up:annotation ?pathwayAnnotation .
        ?pathwayAnnotation a up:Pathway_Annotation ;
                          rdfs:comment ?pathway .

        FILTER(CONTAINS(LCASE(?pathway), LCASE("{pathway_name}")))

        # Protein name
        OPTIONAL {{
            ?protein up:recommendedName ?recName .
            ?recName up:fullName ?proteinName .
        }}

        # Gene name
        OPTIONAL {{
            ?protein up:encodedBy ?gene .
            ?gene skos:prefLabel ?geneName .
        }}

        # Pathway database cross-references
        OPTIONAL {{
            ?protein rdfs:seeAlso ?pathwayXref .
            ?pathwayXref up:database ?pathwayDbNode .
            ?pathwayDbNode skos:prefLabel ?pathwayDb .
            FILTER(?pathwayDb IN ("Reactome", "KEGG"))
        }}

        # Protein-protein interactions
        OPTIONAL {{
            ?protein up:annotation ?interaction .
            ?interaction a up:Interaction_Annotation ;
                        up:interactant ?interactant .

            OPTIONAL {{
                ?interactant up:recommendedName/up:fullName ?interactantName .
            }}
        }}

        # Function
        OPTIONAL {{
            ?protein up:annotation ?funcAnnotation .
            ?funcAnnotation a up:Function_Annotation ;
                           rdfs:comment ?function .
        }}
    }}
}}
ORDER BY ?proteinName
LIMIT {limit}
"""


# =============================================================================
# RESULT MERGING STRATEGIES
# =============================================================================

class ResultMerger:
    """
    Strategies for merging results from heterogeneous federated queries.

    When querying multiple endpoints, results may have different schemas,
    missing data, or conflicts. This class provides strategies for handling
    these situations.
    """

    @staticmethod
    def merge_with_union(
        results: List[QueryResult],
        deduplicate: bool = True
    ) -> QueryResult:
        """
        Merge results using UNION semantics (combine all rows).

        Args:
            results: List of query results to merge
            deduplicate: Remove duplicate rows

        Returns:
            Merged query result
        """
        if not results:
            return QueryResult(status=QueryStatus.SUCCESS, row_count=0)

        # Combine all bindings
        all_bindings = []
        all_variables = set()

        for result in results:
            if result.is_success:
                all_bindings.extend(result.bindings)
                all_variables.update(result.variables)

        # Deduplicate if requested
        if deduplicate:
            seen = set()
            unique_bindings = []
            for binding in all_bindings:
                # Create a hashable representation
                binding_tuple = tuple(sorted(binding.items()))
                if binding_tuple not in seen:
                    seen.add(binding_tuple)
                    unique_bindings.append(binding)
            all_bindings = unique_bindings

        return QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=all_bindings,
            row_count=len(all_bindings),
            variables=sorted(all_variables),
            data=all_bindings
        )

    @staticmethod
    def merge_with_join(
        results: List[QueryResult],
        join_keys: List[str],
        join_type: str = "inner"
    ) -> QueryResult:
        """
        Merge results using JOIN semantics (combine on common keys).

        Args:
            results: List of query results to merge
            join_keys: Variables to join on
            join_type: Type of join (inner, left, full)

        Returns:
            Merged query result
        """
        if not results or len(results) < 2:
            return results[0] if results else QueryResult(status=QueryStatus.SUCCESS)

        # Start with first result
        merged_bindings = results[0].bindings
        all_variables = set(results[0].variables)

        # Join with each subsequent result
        for result in results[1:]:
            if not result.is_success:
                continue

            all_variables.update(result.variables)
            new_bindings = []

            for left_binding in merged_bindings:
                matched = False

                for right_binding in result.bindings:
                    # Check if join keys match
                    if all(
                        left_binding.get(key) == right_binding.get(key)
                        for key in join_keys
                    ):
                        # Merge bindings
                        merged_binding = {**left_binding, **right_binding}
                        new_bindings.append(merged_binding)
                        matched = True

                # Handle outer join
                if not matched and join_type in ("left", "full"):
                    new_bindings.append(left_binding)

            # Handle full outer join (right side)
            if join_type == "full":
                for right_binding in result.bindings:
                    if not any(
                        all(
                            left_binding.get(key) == right_binding.get(key)
                            for key in join_keys
                        )
                        for left_binding in merged_bindings
                    ):
                        new_bindings.append(right_binding)

            merged_bindings = new_bindings

        return QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=merged_bindings,
            row_count=len(merged_bindings),
            variables=sorted(all_variables),
            data=merged_bindings
        )

    @staticmethod
    def handle_missing_optional_data(
        result: QueryResult,
        optional_vars: List[str],
        default_value: str = "N/A"
    ) -> QueryResult:
        """
        Fill in missing data from OPTIONAL clauses.

        Args:
            result: Query result with potential missing data
            optional_vars: Variables that were OPTIONAL
            default_value: Default value for missing data

        Returns:
            Result with filled missing values
        """
        for binding in result.bindings:
            for var in optional_vars:
                if var not in binding or binding[var] is None:
                    binding[var] = default_value

        return result


# =============================================================================
# ERROR HANDLING AND RESILIENCE
# =============================================================================

@dataclass
class FederatedQueryError:
    """Information about a federated query error."""
    endpoint: str
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_recoverable: bool = True


class ResilientFederatedExecutor:
    """
    Execute federated queries with error handling and graceful degradation.

    This executor can handle endpoint failures, timeouts, and partial results,
    providing the best possible results even when some services fail.
    """

    def __init__(
        self,
        max_retries: int = 2,
        retry_delay: float = 1.0,
        allow_partial_results: bool = True
    ):
        """
        Initialize the resilient executor.

        Args:
            max_retries: Maximum retry attempts per service
            retry_delay: Delay between retries (seconds)
            allow_partial_results: Return partial results if some services fail
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.allow_partial_results = allow_partial_results
        self.errors: List[FederatedQueryError] = []
        self.logger = logging.getLogger(__name__)

    def execute_with_fallback(
        self,
        query: str,
        fallback_queries: Optional[List[str]] = None
    ) -> QueryResult:
        """
        Execute query with fallback options if primary query fails.

        Args:
            query: Primary federated query
            fallback_queries: Alternative queries to try if primary fails

        Returns:
            Query result from successful query
        """
        # Try primary query
        result = self._try_execute(query)

        if result.is_success:
            return result

        # Try fallback queries
        if fallback_queries:
            for i, fallback in enumerate(fallback_queries):
                self.logger.info(f"Trying fallback query {i+1}/{len(fallback_queries)}")
                result = self._try_execute(fallback)
                if result.is_success:
                    result.metadata["fallback_used"] = True
                    result.metadata["fallback_index"] = i
                    return result

        return result

    def _try_execute(self, query: str) -> QueryResult:
        """
        Try to execute a query with retries.

        Args:
            query: SPARQL query

        Returns:
            Query result
        """
        # This is a placeholder - actual implementation would use SPARQLWrapper
        # or similar to execute the query

        for attempt in range(self.max_retries + 1):
            try:
                # Simulate execution
                # In real implementation:
                # from SPARQLWrapper import SPARQLWrapper
                # sparql = SPARQLWrapper(endpoint_url)
                # sparql.setQuery(query)
                # results = sparql.query().convert()

                return QueryResult(
                    status=QueryStatus.SUCCESS,
                    query=query,
                    row_count=0,
                    metadata={"attempt": attempt + 1}
                )

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return QueryResult(
                        status=QueryStatus.FAILED,
                        query=query,
                        error_message=str(e),
                        metadata={"attempts": attempt + 1}
                    )


# =============================================================================
# PERFORMANCE OPTIMIZATION GUIDELINES
# =============================================================================

FEDERATED_QUERY_BEST_PRACTICES = """
Federated SPARQL Query Best Practices and Optimization Guidelines
===================================================================

1. MINIMIZE DATA TRANSFER
   - Filter within each SERVICE clause before transferring data
   - Use LIMIT within SERVICE blocks when possible
   - Request only necessary variables
   - Example:
     SERVICE <endpoint> {
       ?s a :Class .
       FILTER(?s = <specific-uri>)  # Filter early
     } LIMIT 100  # Limit results

2. ORDER SERVICES BY SELECTIVITY
   - Execute most selective services first
   - Start with services that return fewer results
   - Use BIND for known values before SERVICE calls
   - Example:
     BIND(<specific-protein> AS ?protein)  # Known value first
     SERVICE <endpoint1> { ?protein :property ?value }  # Then query

3. USE SERVICE SILENT FOR NON-CRITICAL DATA
   - SERVICE SILENT continues if endpoint fails
   - Use for optional data enrichment
   - Don't use for critical data
   - Example:
     SERVICE SILENT <optional-endpoint> {
       ?s :enrichment ?data .
     }

4. LEVERAGE OPTIONAL CLAUSES WISELY
   - Use OPTIONAL for data that may not exist
   - Place OPTIONAL blocks after required patterns
   - Be aware that OPTIONAL can slow queries
   - Example:
     SERVICE <critical-endpoint> {
       ?s :required ?data .  # Required first
       OPTIONAL { ?s :optional ?extra . }  # Then optional
     }

5. CACHE INTERMEDIATE RESULTS
   - Store frequently accessed federated results
   - Use local cache for repeated queries
   - Implement cache invalidation strategy
   - Consider result freshness requirements

6. HANDLE ENDPOINT FAILURES GRACEFULLY
   - Always use SERVICE SILENT for optional endpoints
   - Implement retry logic with exponential backoff
   - Provide fallback queries
   - Monitor endpoint availability

7. OPTIMIZE QUERY COMPLEXITY
   - Avoid nested SERVICE calls when possible
   - Minimize number of SERVICE blocks
   - Combine patterns within same SERVICE
   - Example (good):
     SERVICE <endpoint> {
       ?s :prop1 ?v1 .
       ?s :prop2 ?v2 .  # Combined in one SERVICE
     }

   Example (bad):
     SERVICE <endpoint> { ?s :prop1 ?v1 }
     SERVICE <endpoint> { ?s :prop2 ?v2 }  # Separate SERVICE calls

8. USE SPECIFIC IDENTIFIERS
   - Bind specific URIs when known
   - Filter by IDs before federation
   - Avoid broad pattern matching across services
   - Example:
     VALUES ?protein { <protein1> <protein2> }  # Specific set
     SERVICE <endpoint> { ?protein :data ?value }

9. SET APPROPRIATE TIMEOUTS
   - Configure longer timeouts for federated queries
   - Consider endpoint response times
   - Implement client-side timeouts
   - Default: 60-120 seconds for federated queries

10. MONITOR AND LOG PERFORMANCE
    - Track query execution times
    - Log endpoint failures
    - Monitor data transfer volumes
    - Identify slow services for optimization

11. TEST QUERIES INCREMENTALLY
    - Start with single SERVICE
    - Add services one at a time
    - Test with LIMIT before full execution
    - Verify each service works independently

12. CONSIDER ALTERNATIVE ARCHITECTURES
    - For frequent queries, consider data replication
    - Use materialized views for common joins
    - Implement query result caching
    - Consider batch data import for static data

Example of Well-Optimized Federated Query:
------------------------------------------
PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?protein ?name ?structure WHERE {
  # Start with most selective constraint
  BIND(<http://purl.uniprot.org/uniprot/P38398> AS ?protein)

  # Query UniProt (critical data)
  SERVICE <https://sparql.uniprot.org/sparql> {
    ?protein up:recommendedName/up:fullName ?name .
    ?protein rdfs:seeAlso ?pdbXref .
    ?pdbXref up:database <http://purl.uniprot.org/database/PDB> ;
             up:id ?pdbId .
  } LIMIT 10  # Limit within service

  # Query PDB (optional enrichment)
  OPTIONAL {
    SERVICE SILENT <https://rdf.wwpdb.org/sparql> {
      ?structure pdb:pdbx_database_status_code ?pdbId .
      ?structure pdb:has_exptl ?exptl .
    }
  }
}
LIMIT 10  # Final limit
"""


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Core classes
    "FederatedQueryBuilder",
    "CrossDatasetExamples",
    "ResultMerger",
    "ResilientFederatedExecutor",

    # Configuration
    "EndpointCapabilities",
    "QueryOptimizationHints",
    "OptimizationStrategy",

    # Endpoints and prefixes
    "BIOMEDICAL_ENDPOINTS",
    "FEDERATED_PREFIXES",
    "get_federated_prefix_string",

    # Error handling
    "FederatedQueryError",

    # Documentation
    "FEDERATED_QUERY_BEST_PRACTICES",
]
