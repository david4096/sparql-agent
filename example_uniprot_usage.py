#!/usr/bin/env python3
"""
Example: Using the UniProt SPARQL Endpoint Configuration

This script demonstrates practical usage of the UniProt endpoint configuration
with the SPARQL agent, including query generation, execution, and result processing.
"""

import sys
sys.path.insert(0, 'src')

from sparql_agent.endpoints.uniprot import (
    UNIPROT_ENDPOINT,
    UniProtQueryHelper,
    UniProtExampleQueries,
    get_prefix_string,
)


def example_1_basic_protein_lookup():
    """Example 1: Look up basic information for a specific protein."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Protein Lookup")
    print("=" * 80)
    print("\nTask: Get basic information for Amyloid-beta precursor protein (APP)")
    print("UniProt ID: P05067")

    # Generate the query
    query = UniProtExampleQueries.get_protein_basic_info("P05067")

    print("\nGenerated SPARQL Query:")
    print("-" * 80)
    print(query)

    print("\nThis query retrieves:")
    print("  • Protein mnemonic (entry name)")
    print("  • Scientific name of source organism")
    print("  • Recommended protein name")
    print("  • Sequence length and molecular mass")

    # In a real application, you would execute this:
    # from sparql_agent.core.client import SPARQLClient
    # client = SPARQLClient(UNIPROT_ENDPOINT)
    # result = client.execute_query(query)


def example_2_search_human_kinases():
    """Example 2: Search for human protein kinases."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Search Human Protein Kinases")
    print("=" * 80)
    print("\nTask: Find human proteins with 'kinase' in their name")

    # Use helper to build a custom query
    helper = UniProtQueryHelper()

    query = get_prefix_string() + """
SELECT ?protein ?mnemonic ?name ?length ?mass
WHERE {
    # Filter for human proteins first (performance!)
    ?protein up:organism/up:taxon <http://purl.uniprot.org/taxonomy/9606> .

    # Only reviewed entries (SwissProt)
    ?protein up:reviewed true .

    # Get basic information
    ?protein a up:Protein ;
             up:mnemonic ?mnemonic ;
             up:recommendedName/up:fullName ?name .

    # Get sequence properties
    OPTIONAL {
        ?protein up:sequence ?seq .
        ?seq up:length ?length ;
             up:mass ?mass .
    }

    # Filter for kinases
    FILTER(CONTAINS(LCASE(?name), "kinase"))
}
ORDER BY ?name
LIMIT 20
"""

    print("\nCustom SPARQL Query (optimized for performance):")
    print("-" * 80)
    print(query)

    print("\nPerformance optimizations applied:")
    print("  ✓ Filter by taxonomy early")
    print("  ✓ Use reviewed entries only")
    print("  ✓ Apply text filter after structural filters")
    print("  ✓ Use LIMIT clause")
    print("  ✓ Optional blocks for non-essential data")


def example_3_disease_research():
    """Example 3: Research disease-associated proteins."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Disease-Associated Proteins")
    print("=" * 80)
    print("\nTask: Find information about BRCA1 (breast cancer gene)")

    # Step 1: Find the protein by gene name
    query1 = UniProtExampleQueries.get_human_proteins_by_gene("BRCA1")

    print("\nStep 1: Find protein by gene name")
    print("-" * 80)
    print("Query type: get_human_proteins_by_gene('BRCA1')")
    print(f"Query length: {len(query1)} characters")

    # Step 2: Get disease associations (assuming we found P38398)
    query2 = UniProtExampleQueries.get_protein_disease_associations("P38398")

    print("\nStep 2: Get disease associations")
    print("-" * 80)
    print("Query type: get_protein_disease_associations('P38398')")
    print(f"Query length: {len(query2)} characters")

    # Step 3: Get protein function
    query3 = UniProtExampleQueries.get_protein_function("P38398")

    print("\nStep 3: Get functional annotations")
    print("-" * 80)
    print("Query type: get_protein_function('P38398')")
    print(f"Query length: {len(query3)} characters")

    print("\nResearch workflow:")
    print("  1. Find protein by gene name → Get UniProt ID")
    print("  2. Query disease associations → Understand clinical relevance")
    print("  3. Query function annotations → Understand molecular mechanism")
    print("  4. Query interactions → Understand pathway context")
    print("  5. Cross-reference → Link to structural/genomic data")


def example_4_comparative_genomics():
    """Example 4: Comparative genomics across species."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Comparative Genomics")
    print("=" * 80)
    print("\nTask: Compare protein counts across model organisms")

    # Query to count proteins by organism
    query = UniProtExampleQueries.count_proteins_by_organism(limit=10)

    print("\nQuery: Count proteins by organism (top 10)")
    print("-" * 80)
    print(query)

    print("\nCommon model organisms:")
    organisms = [
        ("Human", "9606"),
        ("Mouse", "10090"),
        ("Rat", "10116"),
        ("Zebrafish", "7955"),
        ("Fruit fly", "7227"),
        ("C. elegans", "6239"),
        ("Yeast (S. cerevisiae)", "559292"),
    ]

    for name, taxid in organisms:
        print(f"  • {name:25s} (taxon:{taxid})")


def example_5_structural_biology():
    """Example 5: Structural biology workflow."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Structural Biology Workflow")
    print("=" * 80)
    print("\nTask: Find proteins with PDB structures")

    # Find proteins with structures
    query1 = UniProtExampleQueries.get_proteins_with_pdb_structure(limit=10)

    print("\nStep 1: Find proteins with PDB structures")
    print("-" * 80)
    print("Query type: get_proteins_with_pdb_structure(limit=10)")

    # Get domain information
    query2 = UniProtExampleQueries.get_protein_domains("P12345")

    print("\nStep 2: Get domain information")
    print("-" * 80)
    print("Query type: get_protein_domains('P12345')")

    # Get sequence for modeling
    query3 = UniProtExampleQueries.get_protein_sequence("P12345")

    print("\nStep 3: Get sequence for modeling")
    print("-" * 80)
    print("Query type: get_protein_sequence('P12345')")

    print("\nStructural biology workflow:")
    print("  1. Find proteins with PDB structures")
    print("  2. Get domain annotations → Understand architecture")
    print("  3. Get sequence → Input for modeling")
    print("  4. Cross-reference PDB → Get structure files")
    print("  5. Analyze structure-function relationships")


def example_6_go_enrichment():
    """Example 6: Gene Ontology enrichment analysis."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Gene Ontology Analysis")
    print("=" * 80)
    print("\nTask: Find proteins with specific GO terms")

    # Common GO terms for analysis
    go_terms = [
        ("GO:0005515", "Protein binding"),
        ("GO:0003824", "Catalytic activity"),
        ("GO:0005634", "Nucleus"),
        ("GO:0016020", "Membrane"),
    ]

    print("\nCommon GO terms for enrichment analysis:")
    for go_id, description in go_terms:
        print(f"  • {go_id}: {description}")

    # Example query for protein binding
    query = UniProtExampleQueries.get_proteins_by_go_term("GO:0005515", limit=20)

    print("\nExample: Find proteins with 'protein binding' annotation")
    print("-" * 80)
    print(query[:500] + "...")

    print("\nGO analysis workflow:")
    print("  1. Get proteins for each GO term")
    print("  2. Count proteins per term")
    print("  3. Compare to background distribution")
    print("  4. Calculate enrichment statistics")
    print("  5. Identify overrepresented pathways")


def example_7_custom_query_builder():
    """Example 7: Build custom queries with helper functions."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Custom Query Builder")
    print("=" * 80)
    print("\nTask: Build a complex custom query using helper functions")

    helper = UniProtQueryHelper()

    # Build query components
    print("\nBuilding query components with helpers:")

    print("\n1. Taxonomy filter (human proteins):")
    tax_pattern = helper.build_taxonomy_hierarchy_pattern("9606", "?protein")
    print(tax_pattern)

    print("2. GO term filter (protein binding):")
    go_pattern = helper.build_go_term_pattern("GO:0005515", "?protein")
    print(go_pattern)

    print("3. Reviewed entries filter:")
    reviewed_filter = helper.build_reviewed_only_filter()
    print(reviewed_filter)

    print("4. Text search filter:")
    text_filter = helper.build_text_search_filter("receptor", "?name")
    print(text_filter)

    # Combine into complete query
    custom_query = get_prefix_string() + f"""
SELECT DISTINCT ?protein ?name ?geneName
WHERE {{
    # Taxonomy filter (human)
    {tax_pattern}

    # GO term filter (protein binding)
    {go_pattern}

    # Reviewed entries only
    {reviewed_filter}

    # Get protein information
    ?protein a up:Protein ;
             up:recommendedName/up:fullName ?name .

    # Get gene name (optional)
    OPTIONAL {{
        ?protein up:encodedBy ?gene .
        ?gene skos:prefLabel ?geneName .
    }}

    # Text filter
    {text_filter}
}}
ORDER BY ?name
LIMIT 50
"""

    print("\nComplete custom query:")
    print("-" * 80)
    print(custom_query)

    print("\nHelper functions used:")
    print("  ✓ build_taxonomy_hierarchy_pattern()")
    print("  ✓ build_go_term_pattern()")
    print("  ✓ build_reviewed_only_filter()")
    print("  ✓ build_text_search_filter()")
    print("  ✓ get_prefix_string()")


def example_8_performance_comparison():
    """Example 8: Performance comparison of query strategies."""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Query Performance Comparison")
    print("=" * 80)

    print("\nSCENARIO: Find human membrane kinases")

    print("\n❌ SLOW Query (not optimized):")
    print("-" * 80)
    slow_query = get_prefix_string() + """
SELECT ?protein ?name WHERE {
    ?protein a up:Protein .
    ?protein up:recommendedName/up:fullName ?name .

    # Text searches without early filtering
    FILTER(CONTAINS(LCASE(?name), "kinase"))

    # Late organism filter
    ?protein up:organism/up:scientificName "Homo sapiens" .

    # Check for membrane keyword
    ?protein up:classifiedWith ?keyword .
    ?keyword skos:prefLabel ?label .
    FILTER(REGEX(?label, "Membrane", "i"))
}
LIMIT 100
"""
    print(slow_query)

    print("\nProblems:")
    print("  ✗ No early filtering by taxonomy")
    print("  ✗ Text searches before structural filters")
    print("  ✗ No reviewed-only filter (searches all 250M proteins)")
    print("  ✗ Using scientificName instead of direct taxonomy ID")
    print("  ✗ REGEX on keywords (expensive)")

    print("\n✅ FAST Query (optimized):")
    print("-" * 80)
    fast_query = get_prefix_string() + """
SELECT ?protein ?name WHERE {
    # 1. Filter by taxonomy FIRST (huge reduction)
    ?protein up:organism/up:taxon <http://purl.uniprot.org/taxonomy/9606> .

    # 2. Reviewed entries only (SwissProt)
    ?protein up:reviewed true .

    # 3. Keyword filter (indexed)
    ?protein up:classifiedWith <http://purl.uniprot.org/keywords/472> .  # Membrane

    # 4. Then get other properties
    ?protein a up:Protein ;
             up:recommendedName/up:fullName ?name .

    # 5. Text filter LAST
    FILTER(CONTAINS(LCASE(?name), "kinase"))
}
LIMIT 100
"""
    print(fast_query)

    print("\nOptimizations:")
    print("  ✓ Taxonomy filter FIRST (reduces to ~20,000 human proteins)")
    print("  ✓ Reviewed-only filter (reduces to ~20,000 → ~5,000 SwissProt)")
    print("  ✓ Direct keyword URI (indexed, very fast)")
    print("  ✓ Text filter LAST (on small result set)")
    print("  ✓ Uses direct taxonomy ID (faster than name lookup)")

    print("\n⚡ Expected Performance Difference:")
    print("  Slow query:  30-60 seconds (or timeout)")
    print("  Fast query:  <2 seconds")
    print("  Speedup:     ~15-30x faster!")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print(" UNIPROT SPARQL ENDPOINT - USAGE EXAMPLES")
    print("=" * 80)
    print("\nThese examples demonstrate practical usage of the UniProt endpoint")
    print("configuration with the SPARQL agent.")
    print("\nNote: These examples show query generation only.")
    print("      To execute queries, use SPARQLClient with UNIPROT_ENDPOINT.")

    # Run all examples
    example_1_basic_protein_lookup()
    example_2_search_human_kinases()
    example_3_disease_research()
    example_4_comparative_genomics()
    example_5_structural_biology()
    example_6_go_enrichment()
    example_7_custom_query_builder()
    example_8_performance_comparison()

    print("\n" + "=" * 80)
    print(" SUMMARY")
    print("=" * 80)
    print("\nYou've seen examples of:")
    print("  1. Basic protein lookup")
    print("  2. Search and filtering")
    print("  3. Disease research workflows")
    print("  4. Comparative genomics")
    print("  5. Structural biology")
    print("  6. Gene Ontology analysis")
    print("  7. Custom query building")
    print("  8. Performance optimization")
    print("\nFor more examples, see:")
    print("  • UNIPROT_USAGE_EXAMPLES.md - Comprehensive usage guide")
    print("  • UNIPROT_QUICK_REFERENCE.md - Quick reference card")
    print("  • test_uniprot_endpoint.py - Full test suite")
    print("\nTo execute queries:")
    print("  from sparql_agent.core.client import SPARQLClient")
    print("  client = SPARQLClient(UNIPROT_ENDPOINT)")
    print("  result = client.execute_query(query)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
