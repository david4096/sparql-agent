"""
Example script demonstrating capabilities detection and prefix extraction.

This script shows how to use the CapabilitiesDetector and PrefixExtractor
to discover SPARQL endpoint features and manage prefix mappings.
"""

import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sparql_agent.discovery import CapabilitiesDetector, PrefixExtractor


def test_wikidata_endpoint():
    """Test capabilities detection on Wikidata SPARQL endpoint."""
    print("=" * 80)
    print("Testing Wikidata SPARQL Endpoint")
    print("=" * 80)

    endpoint = "https://query.wikidata.org/sparql"
    detector = CapabilitiesDetector(endpoint, timeout=10)

    # Detect SPARQL version
    print("\n1. Detecting SPARQL version...")
    version = detector.detect_sparql_version()
    print(f"   SPARQL Version: {version}")

    # Find named graphs
    print("\n2. Finding named graphs...")
    graphs = detector.find_named_graphs(limit=5)
    print(f"   Found {len(graphs)} named graphs:")
    for graph in graphs[:5]:
        print(f"   - {graph}")

    # Discover namespaces
    print("\n3. Discovering namespaces...")
    namespaces = detector.discover_namespaces(limit=100)
    print(f"   Found {len(namespaces)} namespaces:")
    for ns in namespaces[:10]:
        print(f"   - {ns}")

    # Detect features
    print("\n4. Detecting SPARQL features...")
    features = detector.detect_features()
    supported_features = [k for k, v in features.items() if v]
    print(f"   Supported features ({len(supported_features)}/{len(features)}):")
    for feature in supported_features:
        print(f"   ✓ {feature}")

    # Get statistics
    print("\n5. Gathering endpoint statistics...")
    stats = detector.get_endpoint_statistics()
    print(f"   Statistics:")
    for key, value in stats.items():
        print(f"   - {key}: {value}")


def test_prefix_extractor():
    """Test prefix extraction and management."""
    print("\n" + "=" * 80)
    print("Testing Prefix Extraction")
    print("=" * 80)

    extractor = PrefixExtractor()

    # Test extracting from query
    print("\n1. Extracting prefixes from SPARQL query...")
    sample_query = """
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?item ?label WHERE {
        ?item wdt:P31 wd:Q5 .
        ?item rdfs:label ?label .
    }
    """
    extracted = extractor.extract_from_query(sample_query)
    print(f"   Extracted {len(extracted)} prefixes:")
    for prefix, namespace in extracted.items():
        print(f"   - {prefix}: {namespace}")

    # Test generating prefixes from namespaces
    print("\n2. Generating prefixes for discovered namespaces...")
    sample_namespaces = [
        "http://example.org/ontology/",
        "http://purl.org/vocab/bio/0.1/",
        "http://xmlns.com/foaf/0.1/",
    ]
    generated = extractor.extract_from_namespaces(sample_namespaces)
    print(f"   Generated {len(generated)} new prefixes:")
    for prefix, namespace in generated.items():
        print(f"   - {prefix}: {namespace}")

    # Test URI shortening
    print("\n3. Testing URI shortening...")
    test_uris = [
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        "http://www.w3.org/2000/01/rdf-schema#label",
        "http://xmlns.com/foaf/0.1/name",
        "http://example.org/unknown/property",
    ]
    for uri in test_uris:
        shortened = extractor.shorten_uri(uri)
        print(f"   {uri}")
        print(f"   → {shortened}")

    # Test URI expansion
    print("\n4. Testing URI expansion...")
    test_prefixed = ["rdf:type", "rdfs:label", "foaf:name", "unknown:prop"]
    for prefixed in test_prefixed:
        expanded = extractor.expand_uri(prefixed)
        print(f"   {prefixed}")
        print(f"   → {expanded}")

    # Generate prefix declarations
    print("\n5. Generating PREFIX declarations...")
    declarations = extractor.get_prefix_declarations()
    print("   SPARQL PREFIX declarations:")
    print("   " + "\n   ".join(declarations.split('\n')[:5]))
    print(f"   ... ({len(declarations.split(chr(10)))} total)")

    # Get mapping summary
    print("\n6. Prefix mapping summary...")
    summary = extractor.get_mapping_summary()
    print(f"   Total prefixes: {summary['total_prefixes']}")
    print(f"   Common prefixes: {', '.join(sorted(summary['prefixes'])[:10])}")


def test_dbpedia_endpoint():
    """Test capabilities detection on DBpedia SPARQL endpoint."""
    print("\n" + "=" * 80)
    print("Testing DBpedia SPARQL Endpoint")
    print("=" * 80)

    endpoint = "https://dbpedia.org/sparql"
    detector = CapabilitiesDetector(endpoint, timeout=10)

    try:
        # Detect all capabilities
        print("\nDetecting all capabilities...")
        capabilities = detector.detect_all_capabilities()

        print(f"\nCapabilities Summary:")
        print(f"- SPARQL Version: {capabilities['sparql_version']}")
        print(f"- Named Graphs: {len(capabilities['named_graphs'])}")
        print(f"- Namespaces: {len(capabilities['namespaces'])}")

        supported_funcs = sum(1 for v in capabilities['supported_functions'].values() if v)
        print(f"- Supported Functions: {supported_funcs}/{len(capabilities['supported_functions'])}")

        supported_feats = sum(1 for v in capabilities['features'].values() if v)
        print(f"- Supported Features: {supported_feats}/{len(capabilities['features'])}")

        print(f"\nStatistics:")
        for key, value in capabilities['statistics'].items():
            print(f"- {key}: {value}")

    except Exception as e:
        print(f"Error testing DBpedia endpoint: {e}")


def main():
    """Run all tests."""
    print("\nSPARQL Capabilities Detection and Prefix Extraction Examples")
    print("=" * 80)

    # Test prefix extractor (doesn't require network)
    test_prefix_extractor()

    # Test endpoints (requires network)
    print("\n\nTesting live endpoints (requires network connection)...")
    try:
        test_wikidata_endpoint()
    except Exception as e:
        print(f"\nWarning: Could not test Wikidata endpoint: {e}")

    try:
        test_dbpedia_endpoint()
    except Exception as e:
        print(f"\nWarning: Could not test DBpedia endpoint: {e}")

    print("\n" + "=" * 80)
    print("Tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
