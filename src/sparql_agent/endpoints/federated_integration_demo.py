#!/usr/bin/env python3
"""
Federated Query Integration Demo - Complete Workflow Example.

This script demonstrates a complete workflow for federated SPARQL queries,
showing how all components work together for a real biomedical research question.

Research Question:
    "For the BRCA1 gene, find all proteins, their associated diseases,
    available 3D structures, and drug compounds that target them."

This integrates data from:
- UniProt: Protein information, disease associations
- PDB: 3D structures
- ChEMBL: Drug compounds targeting the proteins

Run with:
    python federated_integration_demo.py
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
)


# =============================================================================
# COMPLETE RESEARCH WORKFLOW
# =============================================================================

def research_workflow_brca1():
    """
    Complete research workflow: BRCA1 proteins, diseases, structures, and drugs.

    This example demonstrates:
    1. Query generation with optimization
    2. Cost estimation
    3. Resilient execution with fallbacks
    4. Result merging from multiple queries
    5. Error handling
    """
    print("="*80)
    print("FEDERATED QUERY RESEARCH WORKFLOW")
    print("Research Question: Complete BRCA1 analysis")
    print("="*80)

    # Step 1: Initialize components
    print("\n[1] Initializing components...")

    builder = FederatedQueryBuilder(
        enable_optimization=True,
        cache_results=True,
        timeout=120
    )

    examples = CrossDatasetExamples()
    merger = ResultMerger()
    executor = ResilientFederatedExecutor(
        max_retries=2,
        retry_delay=1.0,
        allow_partial_results=True
    )

    print("    ✓ FederatedQueryBuilder initialized")
    print("    ✓ CrossDatasetExamples loaded")
    print("    ✓ ResultMerger ready")
    print("    ✓ ResilientFederatedExecutor ready")

    # Step 2: Generate queries for each data source
    print("\n[2] Generating federated queries...")

    # Query 1: Protein and disease information
    query_disease = examples.protein_disease_associations(
        gene_name="BRCA1",
        limit=20
    )
    print("    ✓ Disease association query generated")

    # Query 2: Structure information
    query_structure = examples.protein_structure_function_integration(
        protein_id="P38398",  # BRCA1 UniProt ID
        limit=10
    )
    print("    ✓ Structure-function query generated")

    # Query 3: Custom optimized query for drugs
    optimization_hints = QueryOptimizationHints(
        strategies=[
            OptimizationStrategy.MINIMIZE_TRANSFER,
            OptimizationStrategy.EARLY_FILTERING,
        ],
        estimated_selectivity={
            "https://sparql.uniprot.org/sparql": 0.05,
            "https://www.ebi.ac.uk/rdf/services/chembl/sparql": 0.3,
        },
        use_optional_for={"https://www.ebi.ac.uk/rdf/services/chembl/sparql"}
    )

    query_drugs = builder.build_federated_query(
        select_vars=["?protein", "?compound", "?compoundName", "?activity"],
        services={
            "https://sparql.uniprot.org/sparql": [
                "BIND(<http://purl.uniprot.org/uniprot/P38398> AS ?protein)",
                "?protein a up:Protein .",
                "?protein up:recommendedName/up:fullName ?proteinName .",
            ],
        },
        optimization_hints=optimization_hints,
        limit=20
    )
    print("    ✓ Drug targeting query generated")

    # Step 3: Estimate query costs
    print("\n[3] Estimating query costs...")

    cost_disease = builder.estimate_query_cost({
        "https://sparql.uniprot.org/sparql": 6,
        "https://query.wikidata.org/sparql": 3
    })

    cost_structure = builder.estimate_query_cost({
        "https://sparql.uniprot.org/sparql": 8,
        "https://rdf.wwpdb.org/sparql": 3
    })

    cost_drugs = builder.estimate_query_cost({
        "https://sparql.uniprot.org/sparql": 3,
        "https://www.ebi.ac.uk/rdf/services/chembl/sparql": 5
    }, optimization_hints)

    print(f"\n    Disease Query:")
    print(f"      Estimated time: {cost_disease['estimated_time_seconds']:.1f}s")
    print(f"      Complexity: {cost_disease['complexity_score']}/100")
    print(f"      Recommended timeout: {cost_disease['recommended_timeout']}s")

    print(f"\n    Structure Query:")
    print(f"      Estimated time: {cost_structure['estimated_time_seconds']:.1f}s")
    print(f"      Complexity: {cost_structure['complexity_score']}/100")
    print(f"      Recommended timeout: {cost_structure['recommended_timeout']}s")

    print(f"\n    Drug Query:")
    print(f"      Estimated time: {cost_drugs['estimated_time_seconds']:.1f}s")
    print(f"      Complexity: {cost_drugs['complexity_score']}/100")
    print(f"      Recommended timeout: {cost_drugs['recommended_timeout']}s")

    total_time = (
        cost_disease['estimated_time_seconds'] +
        cost_structure['estimated_time_seconds'] +
        cost_drugs['estimated_time_seconds']
    )
    print(f"\n    Total estimated time: {total_time:.1f}s")

    # Step 4: Display queries
    print("\n[4] Generated SPARQL Queries:")
    print("\n" + "-"*80)
    print("Query 1: Protein-Disease Associations")
    print("-"*80)
    print(query_disease[:500] + "..." if len(query_disease) > 500 else query_disease)

    print("\n" + "-"*80)
    print("Query 2: Structure-Function Integration")
    print("-"*80)
    print(query_structure[:500] + "..." if len(query_structure) > 500 else query_structure)

    print("\n" + "-"*80)
    print("Query 3: Drug Targeting")
    print("-"*80)
    print(query_drugs[:500] + "..." if len(query_drugs) > 500 else query_drugs)

    # Step 5: Execution strategy
    print("\n[5] Execution Strategy:")
    print("\n    Queries will be executed with:")
    print("      - Automatic retry on failure (max 2 retries)")
    print("      - Exponential backoff between retries")
    print("      - SERVICE SILENT for optional data")
    print("      - Fallback queries if primary fails")
    print("      - Partial result acceptance")

    print("\n    Error handling:")
    print("      - Timeout → Retry with simpler query")
    print("      - Endpoint down → Use alternative endpoint")
    print("      - No results → Try broader query")
    print("      - Rate limit → Exponential backoff")

    # Step 6: Simulated result processing
    print("\n[6] Result Processing Strategy:")
    print("\n    After execution, results would be:")
    print("      1. Validated for schema correctness")
    print("      2. Merged across queries using JOIN on ?protein")
    print("      3. Missing optional data filled with defaults")
    print("      4. Duplicates removed")
    print("      5. Formatted for presentation")

    print("\n    Expected result schema:")
    print("      - ?protein: UniProt URI")
    print("      - ?proteinName: Protein name")
    print("      - ?disease: Disease name")
    print("      - ?significance: Clinical significance")
    print("      - ?pdbId: PDB structure ID")
    print("      - ?resolution: Structure resolution")
    print("      - ?compound: Drug compound")
    print("      - ?activity: Bioactivity value")

    # Step 7: Demonstrate result merging
    print("\n[7] Demonstrating Result Merging:")

    # Simulate query results
    from ..core.types import QueryResult, QueryStatus

    # Simulated disease query results
    result_disease = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                "protein": "http://purl.uniprot.org/uniprot/P38398",
                "proteinName": "Breast cancer type 1 susceptibility protein",
                "disease": "Breast-ovarian cancer, familial 1",
                "significance": "Pathogenic"
            },
            {
                "protein": "http://purl.uniprot.org/uniprot/P38398",
                "proteinName": "Breast cancer type 1 susceptibility protein",
                "disease": "Breast cancer, early-onset",
                "significance": "Pathogenic"
            }
        ],
        variables=["protein", "proteinName", "disease", "significance"],
        row_count=2
    )

    # Simulated structure query results
    result_structure = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                "protein": "http://purl.uniprot.org/uniprot/P38398",
                "pdbId": "1JM7",
                "resolution": "2.5"
            },
            {
                "protein": "http://purl.uniprot.org/uniprot/P38398",
                "pdbId": "1T29",
                "resolution": "2.0"
            }
        ],
        variables=["protein", "pdbId", "resolution"],
        row_count=2
    )

    print("\n    Disease results: 2 rows")
    print("    Structure results: 2 rows")

    # Merge results
    merged = merger.merge_with_join(
        [result_disease, result_structure],
        join_keys=["protein"],
        join_type="left"
    )

    print(f"\n    Merged results: {merged.row_count} rows")
    print(f"    Variables: {', '.join(merged.variables)}")

    print("\n    Sample merged result:")
    if merged.bindings:
        sample = merged.bindings[0]
        print("    {")
        for key, value in sample.items():
            print(f"      {key}: {value}")
        print("    }")

    # Step 8: Summary and recommendations
    print("\n[8] Research Summary:")
    print("\n    This workflow demonstrates:")
    print("      ✓ Multi-endpoint data integration")
    print("      ✓ Query optimization for performance")
    print("      ✓ Cost estimation and planning")
    print("      ✓ Resilient execution with error handling")
    print("      ✓ Result merging and processing")

    print("\n    Key findings (example):")
    print("      - BRCA1 protein identified")
    print("      - 2 disease associations found")
    print("      - 2 crystal structures available")
    print("      - Drug targeting data retrievable")

    print("\n    Next steps in research:")
    print("      - Analyze variant effects on structure")
    print("      - Correlate mutations with disease severity")
    print("      - Identify drug targets in functional domains")
    print("      - Design precision medicine strategies")

    return {
        "queries": {
            "disease": query_disease,
            "structure": query_structure,
            "drugs": query_drugs
        },
        "costs": {
            "disease": cost_disease,
            "structure": cost_structure,
            "drugs": cost_drugs,
            "total": total_time
        },
        "merged_result": merged
    }


# =============================================================================
# COMPARISON: FEDERATED vs SEQUENTIAL QUERIES
# =============================================================================

def compare_federated_vs_sequential():
    """
    Compare federated query approach vs sequential queries.

    Shows the advantages of federated queries for cross-dataset integration.
    """
    print("\n" + "="*80)
    print("FEDERATED vs SEQUENTIAL QUERIES COMPARISON")
    print("="*80)

    print("\n[A] Sequential Approach (Traditional):")
    print("-" * 80)
    print("""
    1. Query UniProt for proteins
       - Execute query, wait for results
       - Parse and store results locally
       - Extract protein IDs

    2. For each protein, query PDB
       - Make N separate requests
       - Wait for each response
       - Handle rate limiting

    3. For each protein, query ChEMBL
       - Make N more requests
       - More waiting
       - More rate limiting

    4. Manually merge all results
       - Join data by protein ID
       - Handle missing data
       - Resolve conflicts

    Total time: ~5-10 minutes (with rate limiting)
    Network requests: 1 + N + N = 2N + 1
    Data transfer: High (full result sets)
    Complexity: High (manual coordination)
    """)

    print("\n[B] Federated Approach (Modern):")
    print("-" * 80)
    print("""
    1. Build single federated query
       - Define SERVICE clauses
       - Specify join conditions
       - Apply filters

    2. Execute query once
       - Endpoint coordinates federation
       - Results pre-joined
       - Only relevant data returned

    3. Process unified results
       - Single result set
       - Already merged
       - Consistent schema

    Total time: ~30-60 seconds
    Network requests: 1
    Data transfer: Low (filtered results)
    Complexity: Low (SPARQL handles it)
    """)

    print("\n[C] Comparison Table:")
    print("-" * 80)
    print(f"{'Metric':<30} {'Sequential':<20} {'Federated':<20}")
    print("-" * 80)
    print(f"{'Execution Time':<30} {'5-10 minutes':<20} {'30-60 seconds':<20}")
    print(f"{'Network Requests':<30} {'2N + 1 (many)':<20} {'1 (single)':<20}")
    print(f"{'Data Transfer':<30} {'High':<20} {'Low':<20}")
    print(f"{'Implementation':<30} {'Complex':<20} {'Simple':<20}")
    print(f"{'Error Handling':<30} {'Manual':<20} {'Built-in':<20}")
    print(f"{'Rate Limiting':<30} {'Problem':<20} {'Handled':<20}")
    print(f"{'Result Merging':<30} {'Manual':<20} {'Automatic':<20}")

    print("\n[D] Use Case Recommendations:")
    print("-" * 80)
    print("""
    Use Federated Queries When:
    ✓ Joining data across multiple sources
    ✓ Complex relationships between datasets
    ✓ Real-time analysis required
    ✓ Large-scale data integration
    ✓ Reproducible workflows needed

    Use Sequential Queries When:
    ✓ Simple single-endpoint queries
    ✓ Offline batch processing
    ✓ Endpoints don't support federation
    ✓ Complex local processing needed
    ✓ Results need extensive caching
    """)


# =============================================================================
# ENDPOINT CAPABILITIES OVERVIEW
# =============================================================================

def show_endpoint_capabilities():
    """Display capabilities of available biomedical endpoints."""
    print("\n" + "="*80)
    print("BIOMEDICAL SPARQL ENDPOINTS - CAPABILITIES OVERVIEW")
    print("="*80)

    for key, endpoint in BIOMEDICAL_ENDPOINTS.items():
        print(f"\n[{key.upper()}] {endpoint.name}")
        print("-" * 80)
        print(f"URL:         {endpoint.url}")
        print(f"Timeout:     {endpoint.timeout}s")
        print(f"Rate Limit:  {endpoint.rate_limit} req/s")
        print(f"Updates:     {'Yes' if endpoint.supports_update else 'No'}")

        if "capabilities" in endpoint.metadata:
            caps = endpoint.metadata["capabilities"]
            print(f"\nCapabilities:")
            print(f"  Federation:   {'Yes' if caps.supports_federation else 'No'}")
            print(f"  Complexity:   {caps.max_query_complexity}/100")
            print(f"  Reliability:  {caps.reliability_score*100:.0f}%")
            print(f"  Optional:     {'Yes' if caps.supports_optional else 'No'}")
            print(f"  Aggregation:  {'Yes' if caps.supports_aggregation else 'No'}")

        if "data_types" in endpoint.metadata:
            print(f"\nData Types: {', '.join(endpoint.metadata['data_types'])}")

        if "preferred_for" in endpoint.metadata:
            print(f"Best For: {', '.join(endpoint.metadata['preferred_for'])}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Run complete integration demonstration."""
    print("\n" + "="*80)
    print("FEDERATED SPARQL QUERY SYSTEM")
    print("Complete Integration Demonstration")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Run workflow
    result = research_workflow_brca1()

    # Show comparison
    compare_federated_vs_sequential()

    # Show endpoints
    show_endpoint_capabilities()

    # Final summary
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nFor more information:")
    print("  - Read FEDERATED_QUERIES.md")
    print("  - Run examples: python -m sparql_agent.endpoints.federated_examples")
    print("  - Run tests: pytest test_federated.py -v")
    print("\nKey takeaways:")
    print("  ✓ Federated queries simplify cross-dataset integration")
    print("  ✓ Optimization strategies improve performance significantly")
    print("  ✓ Error handling ensures robust execution")
    print("  ✓ Pre-built examples cover common research scenarios")
    print("  ✓ Result merging handles heterogeneous data")

    return result


if __name__ == "__main__":
    result = main()
