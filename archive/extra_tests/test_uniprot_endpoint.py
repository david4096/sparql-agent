#!/usr/bin/env python3
"""
Test script for the UniProt SPARQL endpoint configuration.

This script demonstrates the functionality of the UniProt endpoint module,
including endpoint configuration, helper functions, and example queries.
"""

import sys
sys.path.insert(0, 'src')

from sparql_agent.endpoints.uniprot import (
    UNIPROT_ENDPOINT,
    UNIPROT_PREFIXES,
    UNIPROT_SCHEMA_INFO,
    UniProtSchema,
    UniProtQueryHelper,
    UniProtExampleQueries,
    PERFORMANCE_TIPS,
    get_prefix_string,
)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")


def test_endpoint_info():
    """Test endpoint configuration."""
    print_section("ENDPOINT CONFIGURATION")

    print(f"Endpoint Name: {UNIPROT_ENDPOINT.name}")
    print(f"URL: {UNIPROT_ENDPOINT.url}")
    print(f"Description: {UNIPROT_ENDPOINT.description}")
    print(f"Timeout: {UNIPROT_ENDPOINT.timeout}s")
    print(f"Rate Limit: {UNIPROT_ENDPOINT.rate_limit} req/s")
    print(f"Supports Update: {UNIPROT_ENDPOINT.supports_update}")
    print(f"Authentication Required: {UNIPROT_ENDPOINT.authentication_required}")
    print(f"\nMetadata:")
    for key, value in UNIPROT_ENDPOINT.metadata.items():
        if isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    - {item}")
        else:
            print(f"  {key}: {value}")


def test_prefixes():
    """Test namespace prefixes."""
    print_section("NAMESPACE PREFIXES")

    print(f"Total prefixes: {len(UNIPROT_PREFIXES)}")
    print("\nCore UniProt Prefixes:")
    for prefix, uri in list(UNIPROT_PREFIXES.items())[:10]:
        print(f"  {prefix}: {uri}")

    print("\nGenerated PREFIX string (first 300 chars):")
    prefix_string = get_prefix_string()
    print(prefix_string[:300] + "...")


def test_schema_info():
    """Test schema information."""
    print_section("SCHEMA INFORMATION")

    print(f"Number of classes: {len(UniProtSchema.CORE_CLASSES)}")
    print("\nCore Classes:")
    for cls, desc in list(UniProtSchema.CORE_CLASSES.items())[:10]:
        print(f"  {cls}: {desc}")

    print(f"\nNumber of protein properties: {len(UniProtSchema.PROTEIN_PROPERTIES)}")
    print("\nKey Protein Properties:")
    for prop, desc in list(UniProtSchema.PROTEIN_PROPERTIES.items())[:10]:
        print(f"  {prop}: {desc}")

    print(f"\nNumber of annotation types: {len(UniProtSchema.ANNOTATION_TYPES)}")
    print("\nAnnotation Types:")
    for ann_type, desc in list(UniProtSchema.ANNOTATION_TYPES.items())[:5]:
        print(f"  {ann_type}: {desc}")

    print(f"\nNumber of cross-reference databases: {len(UniProtSchema.CROSS_REFERENCE_DBS)}")
    print("\nSample Cross-Reference Databases:")
    for db, desc in list(UniProtSchema.CROSS_REFERENCE_DBS.items())[:5]:
        print(f"  {db}: {desc}")


def test_helper_functions():
    """Test helper functions."""
    print_section("HELPER FUNCTIONS")

    helper = UniProtQueryHelper()

    print("1. Protein ID Resolution:")
    print(f"   Input: 'P12345'")
    print(f"   Output: {helper.resolve_protein_id('P12345')}")

    print("\n2. Taxonomy ID Resolution:")
    print(f"   Input: '9606' (Human)")
    print(f"   Output: {helper.resolve_taxon_id('9606')}")

    print("\n3. Text Search Filter:")
    text_filter = helper.build_text_search_filter("insulin", "?proteinName")
    print(f"   Input: 'insulin' in ?proteinName")
    print(f"   Output: {text_filter}")

    print("\n4. Taxonomy Hierarchy Pattern:")
    tax_pattern = helper.build_taxonomy_hierarchy_pattern("9606", "?protein")
    print(f"   Input: Taxon 9606 (Human)")
    print(f"   Output:\n{tax_pattern}")

    print("\n5. GO Term Pattern:")
    go_pattern = helper.build_go_term_pattern("GO:0005515", "?protein")
    print(f"   Input: GO:0005515 (protein binding)")
    print(f"   Output:\n{go_pattern}")

    print("\n6. Reviewed Only Filter:")
    reviewed_filter = helper.build_reviewed_only_filter()
    print(f"   Output:\n{reviewed_filter}")

    print("\n7. Cross-Reference Pattern:")
    xref_pattern = helper.build_cross_reference_pattern("PDB", "1HHO", "?protein")
    print(f"   Input: Database=PDB, ID=1HHO")
    print(f"   Output:\n{xref_pattern}")


def test_example_queries():
    """Test example query generation."""
    print_section("EXAMPLE QUERIES")

    examples = [
        ("Get Protein Basic Info",
         UniProtExampleQueries.get_protein_basic_info("P05067")),

        ("Search Proteins by Name",
         UniProtExampleQueries.search_proteins_by_name("insulin", limit=5)),

        ("Get Human Proteins by Gene",
         UniProtExampleQueries.get_human_proteins_by_gene("BRCA1")),

        ("Get Protein Sequence",
         UniProtExampleQueries.get_protein_sequence("P12345")),

        ("Get Protein Function",
         UniProtExampleQueries.get_protein_function("P12345")),

        ("Get Disease Associations",
         UniProtExampleQueries.get_protein_disease_associations("P12345")),

        ("Get Subcellular Location",
         UniProtExampleQueries.get_protein_subcellular_location("P12345")),

        ("Get Protein Domains",
         UniProtExampleQueries.get_protein_domains("P12345")),

        ("Get Cross-References",
         UniProtExampleQueries.get_protein_cross_references("P12345")),

        ("Get Proteins by Taxonomy",
         UniProtExampleQueries.get_proteins_by_taxonomy("9606", limit=10)),

        ("Get Proteins by GO Term",
         UniProtExampleQueries.get_proteins_by_go_term("GO:0005515", limit=10)),

        ("Get Proteins by Keyword",
         UniProtExampleQueries.get_proteins_by_keyword("Membrane", limit=10)),

        ("Get Enzyme by EC Number",
         UniProtExampleQueries.get_enzyme_by_ec_number("1.1.1.1")),

        ("Get Proteins with PDB Structure",
         UniProtExampleQueries.get_proteins_with_pdb_structure(limit=10)),

        ("Get Protein Interactions",
         UniProtExampleQueries.get_protein_interactions("P12345")),

        ("Get Proteins by Mass Range",
         UniProtExampleQueries.get_proteins_by_mass_range(50000, 60000, limit=10)),

        ("Get Taxonomy Lineage",
         UniProtExampleQueries.get_taxonomy_lineage("9606")),

        ("Count Proteins by Organism",
         UniProtExampleQueries.count_proteins_by_organism(limit=10)),

        ("Get Protein Publications",
         UniProtExampleQueries.get_protein_publications("P12345")),
    ]

    for i, (title, query) in enumerate(examples, 1):
        print(f"\n{i}. {title}")
        print("-" * 60)
        # Show first 400 characters of query
        query_preview = query[:400].replace('\n', '\n   ')
        print(f"   {query_preview}...")


def test_performance_tips():
    """Display performance optimization tips."""
    print_section("PERFORMANCE OPTIMIZATION TIPS")
    print(PERFORMANCE_TIPS)


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print(" UNIPROT SPARQL ENDPOINT CONFIGURATION TEST SUITE")
    print("=" * 80)

    try:
        test_endpoint_info()
        test_prefixes()
        test_schema_info()
        test_helper_functions()
        test_example_queries()
        test_performance_tips()

        print_section("TEST SUMMARY")
        print("✓ All tests completed successfully!")
        print(f"✓ Total prefixes: {len(UNIPROT_PREFIXES)}")
        print(f"✓ Total core classes: {len(UniProtSchema.CORE_CLASSES)}")
        print(f"✓ Total protein properties: {len(UniProtSchema.PROTEIN_PROPERTIES)}")
        print(f"✓ Total annotation types: {len(UniProtSchema.ANNOTATION_TYPES)}")
        print(f"✓ Total cross-reference databases: {len(UniProtSchema.CROSS_REFERENCE_DBS)}")

        example_methods = [m for m in dir(UniProtExampleQueries)
                          if not m.startswith('_') and
                          callable(getattr(UniProtExampleQueries, m))]
        print(f"✓ Total example query methods: {len(example_methods)}")

        helper_methods = [m for m in dir(UniProtQueryHelper)
                         if not m.startswith('_') and
                         callable(getattr(UniProtQueryHelper, m))]
        print(f"✓ Total helper methods: {len(helper_methods)}")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
