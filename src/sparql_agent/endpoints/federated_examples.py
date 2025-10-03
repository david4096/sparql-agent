"""
Federated SPARQL Query Examples and Usage Demonstrations.

This module provides comprehensive examples of using the federated query system
for real-world biomedical research scenarios. Each example demonstrates practical
integration patterns and best practices.

Run individual examples:
    python -m sparql_agent.endpoints.federated_examples

Examples include:
- Protein-disease association discovery
- Structure-function integration
- Drug target identification
- Variant pharmacogenomics
- Pathway systems biology
"""

from typing import Dict, List, Any
import json
from datetime import datetime

from .federated import (
    FederatedQueryBuilder,
    CrossDatasetExamples,
    ResultMerger,
    ResilientFederatedExecutor,
    QueryOptimizationHints,
    OptimizationStrategy,
    BIOMEDICAL_ENDPOINTS,
    get_federated_prefix_string,
    FEDERATED_QUERY_BEST_PRACTICES
)


# =============================================================================
# EXAMPLE 1: Protein-Disease Associations
# =============================================================================

def example_protein_disease_associations():
    """
    Example: Find all disease associations for BRCA1 gene.

    Research Question:
        "What diseases are associated with mutations in the BRCA1 gene?"

    This query integrates:
    - UniProt: Protein information and disease annotations
    - Wikidata: Additional disease context and identifiers

    Use Case:
        Clinical genetics, disease mechanism research, biomarker discovery
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Protein-Disease Associations (BRCA1)")
    print("="*80)

    examples = CrossDatasetExamples()

    # Generate the query
    query = examples.protein_disease_associations(gene_name="BRCA1", limit=20)

    print("\nGenerated Federated Query:")
    print("-" * 80)
    print(query)

    print("\n\nQuery Analysis:")
    print("-" * 80)
    print("Endpoints queried:")
    print("  1. UniProt SPARQL (https://sparql.uniprot.org/sparql)")
    print("     - Protein identification by gene name")
    print("     - Disease annotations")
    print("     - Clinical significance")
    print("  2. Wikidata (https://query.wikidata.org/sparql) [OPTIONAL]")
    print("     - Additional disease identifiers")
    print("     - Disease classifications")

    print("\nOptimization techniques used:")
    print("  - Filter by gene name early (reduces search space)")
    print("  - Restrict to reviewed proteins (SwissProt only)")
    print("  - Wikidata query is OPTIONAL (graceful degradation)")
    print("  - Results limited to 20 (prevents overload)")

    print("\nExpected results:")
    print("  - Breast cancer susceptibility")
    print("  - Ovarian cancer predisposition")
    print("  - Hereditary cancer syndromes")
    print("  - Variant pathogenicity information")

    return query


# =============================================================================
# EXAMPLE 2: Structure-Function Integration
# =============================================================================

def example_structure_function_integration():
    """
    Example: Integrate 3D structure with functional annotations.

    Research Question:
        "What 3D structures are available for BRCA1 protein, and how do they
        relate to functional domains?"

    This query integrates:
    - UniProt: Protein domains and functional regions
    - PDB: 3D structures and experimental details

    Use Case:
        Structural biology, drug design, structure-function analysis
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Structure-Function Integration (BRCA1)")
    print("="*80)

    examples = CrossDatasetExamples()

    # Generate the query for BRCA1 protein
    query = examples.protein_structure_function_integration(
        protein_id="P38398",  # BRCA1 UniProt ID
        limit=10
    )

    print("\nGenerated Federated Query:")
    print("-" * 80)
    print(query)

    print("\n\nQuery Analysis:")
    print("-" * 80)
    print("Endpoints queried:")
    print("  1. UniProt SPARQL")
    print("     - Protein domains and regions")
    print("     - Domain positions (start/end)")
    print("     - Functional annotations")
    print("     - PDB cross-references")
    print("  2. PDB RDF (https://rdf.wwpdb.org/sparql)")
    print("     - Structure details")
    print("     - Experimental method (X-ray, NMR, etc.)")
    print("     - Resolution")

    print("\nOptimization techniques used:")
    print("  - BIND specific protein ID first")
    print("  - Retrieve PDB IDs from UniProt (single source)")
    print("  - PDB query is OPTIONAL (structures may not exist)")
    print("  - SERVICE SILENT for PDB (handles endpoint issues)")

    print("\nExpected results:")
    print("  - RING domain (E3 ubiquitin ligase)")
    print("  - BRCT domains (phospho-protein binding)")
    print("  - Available crystal structures")
    print("  - Structure resolution and methods")

    return query


# =============================================================================
# EXAMPLE 3: Chemical-Protein Interaction Network
# =============================================================================

def example_drug_target_discovery():
    """
    Example: Find protein targets for the drug Imatinib.

    Research Question:
        "What proteins does Imatinib bind to with high affinity, and what
        are their functions and disease associations?"

    This query integrates:
    - ChEMBL: Compound bioactivity data
    - UniProt: Target protein information

    Use Case:
        Drug repurposing, off-target effect prediction, polypharmacology
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Drug Target Discovery (Imatinib)")
    print("="*80)

    examples = CrossDatasetExamples()

    # Generate the query
    query = examples.chemical_protein_interaction_network(
        compound_name="Imatinib",
        activity_threshold=100.0,  # 100 nM
        limit=50
    )

    print("\nGenerated Federated Query:")
    print("-" * 80)
    print(query)

    print("\n\nQuery Analysis:")
    print("-" * 80)
    print("Endpoints queried:")
    print("  1. ChEMBL SPARQL (https://www.ebi.ac.uk/rdf/services/chembl/sparql)")
    print("     - Compound identification")
    print("     - Bioactivity data (IC50, Ki, Kd)")
    print("     - Target protein identifiers")
    print("  2. UniProt SPARQL")
    print("     - Target protein details")
    print("     - Protein functions")
    print("     - Disease associations")

    print("\nOptimization techniques used:")
    print("  - Filter by compound name early")
    print("  - Activity threshold filter (≤100 nM)")
    print("  - UniProt enrichment is OPTIONAL")
    print("  - SERVICE SILENT for ChEMBL (handles availability)")

    print("\nExpected results:")
    print("  - Primary targets: ABL1, KIT, PDGFR")
    print("  - Off-targets: DDR1, CSF1R, others")
    print("  - Target functions (kinase activity)")
    print("  - Associated diseases (CML, GIST)")

    return query


# =============================================================================
# EXAMPLE 4: Precision Medicine Variant Analysis
# =============================================================================

def example_pharmacogenomics_variants():
    """
    Example: Identify genetic variants affecting drug metabolism.

    Research Question:
        "What variants in CYP2D6 affect drug metabolism, and what is their
        clinical significance?"

    This query integrates:
    - UniProt: Natural variants and their effects

    Use Case:
        Precision medicine, pharmacogenomics, clinical decision support
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Pharmacogenomics Variants (CYP2D6)")
    print("="*80)

    examples = CrossDatasetExamples()

    # Generate the query
    query = examples.precision_medicine_variant_drug_response(
        gene_symbol="CYP2D6",
        limit=30
    )

    print("\nGenerated Federated Query:")
    print("-" * 80)
    print(query)

    print("\n\nQuery Analysis:")
    print("-" * 80)
    print("Endpoints queried:")
    print("  1. UniProt SPARQL")
    print("     - Protein identification by gene")
    print("     - Natural variant annotations")
    print("     - Amino acid substitutions")
    print("     - Clinical significance")
    print("     - Disease associations")

    print("\nOptimization techniques used:")
    print("  - Filter by gene symbol (exact match)")
    print("  - Restrict to human proteins (taxon 9606)")
    print("  - Only reviewed entries (SwissProt)")
    print("  - Natural variant annotations specifically")

    print("\nExpected results:")
    print("  - Common variants (*2, *3, *4, *5, etc.)")
    print("  - Poor metabolizer alleles")
    print("  - Ultra-rapid metabolizer variants")
    print("  - Clinical implications for drugs")

    print("\nClinical applications:")
    print("  - Codeine/morphine dosing")
    print("  - Antidepressant selection")
    print("  - Antipsychotic dosing")
    print("  - Pain management")

    return query


# =============================================================================
# EXAMPLE 5: Systems Biology Pathway Integration
# =============================================================================

def example_pathway_systems_biology():
    """
    Example: Reconstruct apoptosis pathway with all components.

    Research Question:
        "What proteins participate in the apoptosis pathway in humans, and
        how do they interact?"

    This query integrates:
    - UniProt: Proteins in pathways and their interactions

    Use Case:
        Systems biology, pathway modeling, network analysis
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Systems Biology - Apoptosis Pathway")
    print("="*80)

    examples = CrossDatasetExamples()

    # Generate the query
    query = examples.systems_biology_pathway_integration(
        pathway_name="Apoptosis",
        organism="Homo sapiens",
        limit=100
    )

    print("\nGenerated Federated Query:")
    print("-" * 80)
    print(query)

    print("\n\nQuery Analysis:")
    print("-" * 80)
    print("Endpoints queried:")
    print("  1. UniProt SPARQL")
    print("     - Pathway annotations")
    print("     - Protein-protein interactions")
    print("     - Gene names")
    print("     - Functional descriptions")
    print("     - Cross-references to Reactome/KEGG")

    print("\nOptimization techniques used:")
    print("  - Filter by organism early")
    print("  - Text search on pathway name (indexed)")
    print("  - Only reviewed proteins")
    print("  - Limited result set")

    print("\nExpected results:")
    print("  - Key proteins: CASP3, CASP8, CASP9, BAX, BCL2")
    print("  - Receptor complexes: FAS, TNFR")
    print("  - Regulatory proteins: APAF1, Cytochrome C")
    print("  - Protein-protein interactions")
    print("  - Pathway cross-references")

    print("\nDownstream analyses:")
    print("  - Network reconstruction")
    print("  - Centrality analysis")
    print("  - Pathway enrichment")
    print("  - Disease perturbation analysis")

    return query


# =============================================================================
# EXAMPLE 6: Advanced Query Optimization
# =============================================================================

def example_optimized_federated_query():
    """
    Example: Build an optimized federated query with hints.

    Demonstrates:
    - Query optimization strategies
    - Service ordering
    - Result caching
    - Error handling
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Advanced Query Optimization")
    print("="*80)

    builder = FederatedQueryBuilder(
        enable_optimization=True,
        cache_results=True,
        timeout=120
    )

    # Define optimization hints
    optimization_hints = QueryOptimizationHints(
        strategies=[
            OptimizationStrategy.MINIMIZE_TRANSFER,
            OptimizationStrategy.EARLY_FILTERING,
            OptimizationStrategy.SERVICE_ORDERING,
        ],
        service_priority=[
            "https://sparql.uniprot.org/sparql",
            "https://query.wikidata.org/sparql",
        ],
        max_results_per_service={
            "https://sparql.uniprot.org/sparql": 100,
            "https://query.wikidata.org/sparql": 50,
        },
        use_optional_for={"https://query.wikidata.org/sparql"},
        estimated_selectivity={
            "https://sparql.uniprot.org/sparql": 0.1,  # Very selective
            "https://query.wikidata.org/sparql": 0.5,  # Less selective
        }
    )

    # Build the query
    query = builder.build_federated_query(
        select_vars=["?protein", "?proteinName", "?drug", "?drugName"],
        services={
            "https://sparql.uniprot.org/sparql": [
                "?protein a up:Protein .",
                "?protein up:organism/up:taxon <http://purl.uniprot.org/taxonomy/9606> .",
                "?protein up:reviewed true .",
                "?protein up:recommendedName/up:fullName ?proteinName .",
                "?protein up:annotation ?diseaseAnnotation .",
                "?diseaseAnnotation a up:Disease_Annotation .",
            ],
            "https://query.wikidata.org/sparql": [
                "?drug wdt:P31 wd:Q12140 .",  # instance of pharmaceutical drug
                "?drug rdfs:label ?drugName .",
                "FILTER(LANG(?drugName) = 'en')",
            ]
        },
        optimization_hints=optimization_hints,
        limit=50
    )

    print("\nGenerated Optimized Query:")
    print("-" * 80)
    print(query)

    print("\n\nOptimization Features:")
    print("-" * 80)
    print("1. Service Ordering:")
    print("   - UniProt first (high selectivity: 0.1)")
    print("   - Wikidata second (lower selectivity: 0.5)")

    print("\n2. Data Transfer Minimization:")
    print("   - Early filtering by organism")
    print("   - Reviewed proteins only")
    print("   - Result limits per service")

    print("\n3. Graceful Degradation:")
    print("   - Wikidata marked as OPTIONAL")
    print("   - SERVICE SILENT for non-critical services")

    print("\n4. Performance Estimation:")
    cost = builder.estimate_query_cost(
        {
            "https://sparql.uniprot.org/sparql": 6,
            "https://query.wikidata.org/sparql": 3,
        },
        optimization_hints
    )
    print(f"   - Estimated time: {cost['estimated_time_seconds']:.1f} seconds")
    print(f"   - Complexity score: {cost['complexity_score']}/100")
    print(f"   - Recommended timeout: {cost['recommended_timeout']} seconds")

    return query


# =============================================================================
# EXAMPLE 7: Error Handling and Resilience
# =============================================================================

def example_resilient_execution():
    """
    Example: Execute federated query with error handling.

    Demonstrates:
    - Retry logic
    - Fallback queries
    - Partial result handling
    - Error recovery
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: Resilient Query Execution")
    print("="*80)

    executor = ResilientFederatedExecutor(
        max_retries=2,
        retry_delay=1.0,
        allow_partial_results=True
    )

    examples = CrossDatasetExamples()

    # Primary query (comprehensive)
    primary_query = examples.protein_disease_associations("BRCA1", limit=20)

    # Fallback query (simpler, UniProt only)
    fallback_query = get_federated_prefix_string() + """
SELECT DISTINCT ?protein ?proteinName ?disease ?diseaseName
WHERE {
    SERVICE <https://sparql.uniprot.org/sparql> {
        ?protein a up:Protein ;
                 up:encodedBy ?gene ;
                 up:reviewed true .

        ?gene skos:prefLabel "BRCA1" .

        OPTIONAL {
            ?protein up:recommendedName/up:fullName ?proteinName .
        }

        ?protein up:annotation ?diseaseAnnotation .
        ?diseaseAnnotation a up:Disease_Annotation ;
                          up:disease ?disease .

        ?disease skos:prefLabel ?diseaseName .
    }
}
LIMIT 20
"""

    print("Primary Query Strategy:")
    print("-" * 80)
    print("  - Query UniProt + Wikidata")
    print("  - Rich disease information")
    print("  - Cross-reference validation")

    print("\nFallback Query Strategy:")
    print("-" * 80)
    print("  - Query UniProt only")
    print("  - Essential information only")
    print("  - Guaranteed to work if UniProt is available")

    print("\nError Handling Features:")
    print("-" * 80)
    print("  - Maximum 2 retry attempts")
    print("  - 1 second delay between retries")
    print("  - Exponential backoff on failures")
    print("  - Automatic fallback to simpler query")
    print("  - Partial results accepted")

    print("\nExample Execution Flow:")
    print("-" * 80)
    print("  1. Try primary query")
    print("     → If Wikidata timeout: proceed with UniProt results only")
    print("  2. If primary fails completely:")
    print("     → Retry with exponential backoff")
    print("  3. If retries exhausted:")
    print("     → Try fallback query (UniProt only)")
    print("  4. Return best available results")

    # In actual use:
    # result = executor.execute_with_fallback(primary_query, [fallback_query])

    return primary_query, fallback_query


# =============================================================================
# EXAMPLE 8: Result Merging Strategies
# =============================================================================

def example_result_merging():
    """
    Example: Merge results from multiple queries.

    Demonstrates:
    - UNION merge (combine all)
    - JOIN merge (combine on keys)
    - Handling missing data
    """
    print("\n" + "="*80)
    print("EXAMPLE 8: Result Merging Strategies")
    print("="*80)

    merger = ResultMerger()

    print("Scenario: Querying multiple endpoints separately and merging results")
    print("-" * 80)

    print("\n1. UNION Merge (Combine All Results):")
    print("   Use case: Getting protein info from multiple databases")
    print("   - Combines all rows from all queries")
    print("   - Removes duplicates")
    print("   - Keeps all variables")
    print("   Example:")
    print("     Query 1: Human proteins from UniProt")
    print("     Query 2: Mouse proteins from UniProt")
    print("     Result: All proteins from both species")

    print("\n2. JOIN Merge (Combine on Common Keys):")
    print("   Use case: Enriching protein data with structure data")
    print("   - Inner join: Only proteins with structures")
    print("   - Left join: All proteins, structures if available")
    print("   - Full join: All proteins and all structures")
    print("   Example:")
    print("     Query 1: Proteins with ?protein ?name")
    print("     Query 2: Structures with ?protein ?pdbId")
    print("     Join on: ?protein")
    print("     Result: ?protein ?name ?pdbId")

    print("\n3. Handling Missing Optional Data:")
    print("   Use case: Filling in N/A for optional fields")
    print("   - OPTIONAL clauses may not return values")
    print("   - Fill with default values for display")
    print("   - Distinguish missing from empty")
    print("   Example:")
    print("     Original: {protein: 'P12345', name: 'BRCA1', pdbId: null}")
    print("     Filled:   {protein: 'P12345', name: 'BRCA1', pdbId: 'N/A'}")

    # Demonstrate merge strategies
    print("\n" + "-" * 80)
    print("Pseudocode Examples:")
    print("-" * 80)

    print("""
# UNION merge
result1 = query_endpoint("uniprot", "SELECT ?protein ?name WHERE {...}")
result2 = query_endpoint("uniprot", "SELECT ?protein ?name WHERE {...}")
merged = merger.merge_with_union([result1, result2], deduplicate=True)

# JOIN merge
protein_query = "SELECT ?protein ?name WHERE {...}"
structure_query = "SELECT ?protein ?pdbId WHERE {...}"
result1 = query_endpoint("uniprot", protein_query)
result2 = query_endpoint("pdb", structure_query)
merged = merger.merge_with_join(
    [result1, result2],
    join_keys=["?protein"],
    join_type="left"  # Keep all proteins
)

# Handle missing data
merged = merger.handle_missing_optional_data(
    merged,
    optional_vars=["?pdbId", "?resolution"],
    default_value="N/A"
)
""")

    return None


# =============================================================================
# MAIN DEMONSTRATION
# =============================================================================

def run_all_examples():
    """Run all federated query examples."""
    print("\n" + "="*80)
    print("FEDERATED SPARQL QUERY EXAMPLES")
    print("Biomedical Research Cross-Dataset Integration")
    print("="*80)

    examples_list = [
        ("Protein-Disease Associations", example_protein_disease_associations),
        ("Structure-Function Integration", example_structure_function_integration),
        ("Drug Target Discovery", example_drug_target_discovery),
        ("Pharmacogenomics Variants", example_pharmacogenomics_variants),
        ("Pathway Systems Biology", example_pathway_systems_biology),
        ("Query Optimization", example_optimized_federated_query),
        ("Resilient Execution", example_resilient_execution),
        ("Result Merging", example_result_merging),
    ]

    for i, (name, func) in enumerate(examples_list, 1):
        try:
            print(f"\n\n{'='*80}")
            print(f"Example {i}/{len(examples_list)}: {name}")
            print(f"{'='*80}")
            func()
        except Exception as e:
            print(f"\nError in example '{name}': {e}")

    # Print best practices
    print("\n\n" + "="*80)
    print("BEST PRACTICES SUMMARY")
    print("="*80)
    print(FEDERATED_QUERY_BEST_PRACTICES)


def print_endpoint_registry():
    """Print available biomedical endpoints."""
    print("\n" + "="*80)
    print("BIOMEDICAL SPARQL ENDPOINTS REGISTRY")
    print("="*80)

    for key, endpoint in BIOMEDICAL_ENDPOINTS.items():
        print(f"\n{endpoint.name} ({key})")
        print("-" * 80)
        print(f"  URL: {endpoint.url}")
        print(f"  Description: {endpoint.description}")
        print(f"  Timeout: {endpoint.timeout}s")
        print(f"  Rate Limit: {endpoint.rate_limit} req/s")

        if "data_types" in endpoint.metadata:
            print(f"  Data Types: {', '.join(endpoint.metadata['data_types'])}")

        if "preferred_for" in endpoint.metadata:
            print(f"  Best For: {', '.join(endpoint.metadata['preferred_for'])}")


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        example_name = sys.argv[1].lower()

        if example_name == "endpoints":
            print_endpoint_registry()
        elif example_name == "disease":
            example_protein_disease_associations()
        elif example_name == "structure":
            example_structure_function_integration()
        elif example_name == "drug":
            example_drug_target_discovery()
        elif example_name == "variant":
            example_pharmacogenomics_variants()
        elif example_name == "pathway":
            example_pathway_systems_biology()
        elif example_name == "optimize":
            example_optimized_federated_query()
        elif example_name == "resilient":
            example_resilient_execution()
        elif example_name == "merge":
            example_result_merging()
        else:
            print(f"Unknown example: {example_name}")
            print("\nAvailable examples:")
            print("  endpoints  - Show endpoint registry")
            print("  disease    - Protein-disease associations")
            print("  structure  - Structure-function integration")
            print("  drug       - Drug target discovery")
            print("  variant    - Pharmacogenomics variants")
            print("  pathway    - Pathway systems biology")
            print("  optimize   - Query optimization")
            print("  resilient  - Resilient execution")
            print("  merge      - Result merging")
    else:
        # Run all examples
        run_all_examples()
        print("\n\nTo run individual examples:")
        print("  python -m sparql_agent.endpoints.federated_examples <example_name>")
