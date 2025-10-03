"""
Example usage of OWL ontology parsing and EBI OLS4 integration.

This module demonstrates how to use the OLSClient and OWLParser
to work with life science ontologies.
"""

import logging
from pathlib import Path

from sparql_agent.ontology import (
    COMMON_ONTOLOGIES,
    OLSClient,
    OWLParser,
    get_ontology_config,
    list_common_ontologies,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_ols_search():
    """Example: Search for terms using OLS4."""
    print("\n" + "=" * 80)
    print("Example 1: Search for terms using OLS4")
    print("=" * 80)

    client = OLSClient()

    # Search for diabetes terms
    print("\nSearching for 'diabetes' terms...")
    results = client.search("diabetes", limit=5)

    for term in results:
        print(f"\n  Term: {term['label']}")
        print(f"  ID: {term['id']}")
        print(f"  Ontology: {term['ontology']}")
        print(f"  Description: {term['description']}")
        if term.get('synonyms'):
            print(f"  Synonyms: {', '.join(term['synonyms'][:3])}")


def example_ols_ontology_info():
    """Example: Get ontology information from OLS4."""
    print("\n" + "=" * 80)
    print("Example 2: Get ontology information")
    print("=" * 80)

    client = OLSClient()

    # Get info about Gene Ontology
    print("\nGetting Gene Ontology information...")
    go_info = client.get_ontology("go")

    print(f"\n  Title: {go_info['title']}")
    print(f"  Description: {go_info['description']}")
    print(f"  Version: {go_info['version']}")
    print(f"  Number of terms: {go_info['num_terms']:,}")
    print(f"  Number of properties: {go_info['num_properties']:,}")


def example_ols_hierarchy():
    """Example: Browse term hierarchies using OLS4."""
    print("\n" + "=" * 80)
    print("Example 3: Browse term hierarchies")
    print("=" * 80)

    client = OLSClient()

    # Get a specific term
    print("\nGetting term: GO:0008150 (biological_process)...")
    term = client.get_term("go", "GO_0008150")

    print(f"\n  Label: {term['label']}")
    print(f"  Definition: {term['description']}")

    # Get children
    print("\n  Getting child terms...")
    children = client.get_term_children("go", "GO_0008150")

    print(f"\n  Found {len(children)} child terms:")
    for child in children[:5]:
        print(f"    - {child['label']} ({child['id']})")


def example_common_ontologies():
    """Example: List common life science ontologies."""
    print("\n" + "=" * 80)
    print("Example 4: Common life science ontologies")
    print("=" * 80)

    print("\nAvailable common ontologies:")
    for onto in list_common_ontologies():
        print(f"\n  {onto['name']} ({onto['id']})")
        print(f"    {onto['description']}")
        print(f"    Homepage: {onto['homepage']}")


def example_download_ontology():
    """Example: Download an ontology file."""
    print("\n" + "=" * 80)
    print("Example 5: Download ontology file")
    print("=" * 80)

    client = OLSClient()

    # Note: This will download a small ontology (HP is ~14MB)
    # For larger ontologies like GO (~500MB) or ChEBI (~100MB), be patient!
    print("\nDownloading Human Phenotype Ontology (HP)...")
    print("(This may take a few moments...)")

    try:
        output_path = client.download_ontology("hp")
        print(f"\n  Downloaded to: {output_path}")
        print(f"  File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        return output_path
    except Exception as e:
        print(f"\n  Failed to download: {e}")
        print("  This is normal if the ontology is not available or too large")
        return None


def example_parse_owl_file():
    """Example: Parse an OWL file with owlready2."""
    print("\n" + "=" * 80)
    print("Example 6: Parse OWL file with owlready2")
    print("=" * 80)

    # First, try to download a small ontology
    client = OLSClient()

    print("\nDownloading a small test ontology...")
    try:
        # Try to download PATO (a small ontology)
        owl_file = client.download_ontology("pato")
    except Exception as e:
        print(f"Could not download ontology: {e}")
        print("Using local file if available...")
        # You can specify a local OWL file here for testing
        return

    print(f"\nParsing OWL file: {owl_file}")

    # Parse the ontology
    parser = OWLParser(enable_reasoning=False)

    try:
        ontology_info = parser.load_ontology(owl_file)

        print(f"\n  Ontology URI: {ontology_info.uri}")
        print(f"  Title: {ontology_info.title}")
        print(f"  Version: {ontology_info.version}")
        print(f"  Number of classes: {len(ontology_info.classes)}")
        print(f"  Number of properties: {len(ontology_info.properties)}")

        # Show some example classes
        print("\n  Example classes:")
        for uri, owl_class in list(ontology_info.classes.items())[:5]:
            print(f"\n    {owl_class.get_primary_label()}")
            print(f"      URI: {uri}")
            if owl_class.comment:
                comment = owl_class.get_primary_comment()
                if comment and len(comment) > 80:
                    comment = comment[:80] + "..."
                print(f"      Comment: {comment}")
            if owl_class.subclass_of:
                print(f"      Parent classes: {len(owl_class.subclass_of)}")

        # Show some example properties
        print("\n  Example properties:")
        for uri, owl_prop in list(ontology_info.properties.items())[:5]:
            print(f"\n    {owl_prop.get_primary_label()}")
            print(f"      URI: {uri}")
            print(f"      Type: {owl_prop.property_type.value}")
            if owl_prop.domain:
                print(f"      Domain: {len(owl_prop.domain)} classes")
            if owl_prop.range:
                print(f"      Range: {len(owl_prop.range)} classes")

        parser.close()

    except Exception as e:
        print(f"\n  Failed to parse ontology: {e}")
        logger.exception("Parsing failed")


def example_search_classes():
    """Example: Search for classes in a parsed ontology."""
    print("\n" + "=" * 80)
    print("Example 7: Search for classes in ontology")
    print("=" * 80)

    client = OLSClient()

    print("\nDownloading and parsing ontology...")
    try:
        owl_file = client.download_ontology("pato")
        parser = OWLParser(enable_reasoning=False)
        ontology_info = parser.load_ontology(owl_file)

        # Search for classes containing "color"
        print("\nSearching for classes containing 'color'...")
        matches = parser.search_classes("color", case_sensitive=False)

        print(f"\n  Found {len(matches)} matching classes:")
        for owl_class in matches[:5]:
            print(f"\n    {owl_class.get_primary_label()}")
            print(f"      URI: {owl_class.uri}")
            if owl_class.comment:
                comment = owl_class.get_primary_comment()
                if comment and len(comment) > 60:
                    comment = comment[:60] + "..."
                print(f"      Definition: {comment}")

        parser.close()

    except Exception as e:
        print(f"\n  Failed: {e}")


def example_class_hierarchy():
    """Example: Get class hierarchy."""
    print("\n" + "=" * 80)
    print("Example 8: Get class hierarchy")
    print("=" * 80)

    client = OLSClient()

    print("\nDownloading and parsing ontology...")
    try:
        owl_file = client.download_ontology("pato")
        parser = OWLParser(enable_reasoning=False)
        ontology_info = parser.load_ontology(owl_file)

        # Get a class and show its hierarchy
        if ontology_info.classes:
            # Get first class with children
            for uri, owl_class in ontology_info.classes.items():
                children = ontology_info.get_subclasses(uri)
                if children:
                    print(f"\nClass: {owl_class.get_primary_label()}")
                    print(f"  URI: {uri}")

                    print(f"\n  Direct subclasses ({len(children)}):")
                    for child_uri in children[:5]:
                        child_class = ontology_info.classes.get(child_uri)
                        if child_class:
                            print(f"    - {child_class.get_primary_label()}")

                    # Get all ancestors
                    ancestors = ontology_info.get_superclasses(uri, recursive=True)
                    print(f"\n  All ancestor classes: {len(ancestors)}")

                    break

        parser.close()

    except Exception as e:
        print(f"\n  Failed: {e}")


def example_ontology_integration():
    """Example: Complete workflow combining OLS and local parsing."""
    print("\n" + "=" * 80)
    print("Example 9: Complete ontology integration workflow")
    print("=" * 80)

    # Step 1: Suggest ontologies
    print("\n1. Finding relevant ontologies...")
    client = OLSClient()
    suggestions = client.suggest_ontology("gene", limit=3)

    print("   Suggested ontologies for 'gene':")
    for onto in suggestions:
        print(f"     - {onto['title']} ({onto['id']})")

    # Step 2: Get ontology info
    print("\n2. Getting ontology metadata...")
    onto_config = get_ontology_config("GO")
    print(f"   {onto_config['name']}")
    print(f"   {onto_config['description']}")

    # Step 3: Search for specific terms
    print("\n3. Searching for terms...")
    terms = client.search("apoptosis", ontology="go", limit=3)
    print(f"   Found {len(terms)} terms related to apoptosis")

    for term in terms:
        print(f"\n     {term['label']} ({term['id']})")
        if term.get('description'):
            desc = term['description']
            if len(desc) > 80:
                desc = desc[:80] + "..."
            print(f"     {desc}")

    # Step 4: Explore term relationships
    if terms:
        term_id = terms[0]['id'].replace(":", "_")
        print(f"\n4. Exploring relationships for {terms[0]['label']}...")

        parents = client.get_term_parents("go", term_id)
        print(f"   Parent terms: {len(parents)}")

        children = client.get_term_children("go", term_id)
        print(f"   Child terms: {len(children)}")

    print("\n   Workflow complete!")


def main():
    """Run all examples."""
    print("\n")
    print("=" * 80)
    print(" OWL Ontology Parser & EBI OLS4 Integration Examples")
    print("=" * 80)

    examples = [
        ("OLS Search", example_ols_search),
        ("OLS Ontology Info", example_ols_ontology_info),
        ("OLS Hierarchy Browsing", example_ols_hierarchy),
        ("Common Ontologies", example_common_ontologies),
        ("Download Ontology", example_download_ontology),
        ("Parse OWL File", example_parse_owl_file),
        ("Search Classes", example_search_classes),
        ("Class Hierarchy", example_class_hierarchy),
        ("Complete Integration", example_ontology_integration),
    ]

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\n" + "=" * 80)
    print("Note: Some examples require internet connection and may take time")
    print("to download ontologies. Large ontologies (GO, ChEBI) can be 100MB+")
    print("=" * 80)

    # Run quick examples that don't require downloads
    try:
        example_common_ontologies()
        example_ols_ontology_info()
        example_ols_search()
        example_ontology_integration()

        print("\n" + "=" * 80)
        print("Quick examples completed!")
        print("\nTo run examples that download and parse OWL files,")
        print("uncomment the function calls below:")
        print("  - example_download_ontology()")
        print("  - example_parse_owl_file()")
        print("  - example_search_classes()")
        print("  - example_class_hierarchy()")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.exception("Example failed")
        print(f"\nError running examples: {e}")


if __name__ == "__main__":
    main()
