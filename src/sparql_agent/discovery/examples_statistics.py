"""
Examples demonstrating the StatisticsCollector usage.

This module provides example code for collecting and analyzing SPARQL dataset statistics.
"""

import logging
import json
from statistics import StatisticsCollector, collect_statistics


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_basic_statistics():
    """Example: Collect basic statistics from a SPARQL endpoint."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Statistics Collection")
    print("=" * 60 + "\n")

    # Use DBpedia as an example endpoint
    endpoint = "https://dbpedia.org/sparql"

    # Simple progress callback
    def progress(message, current=0, total=0):
        if total > 0:
            percentage = (current / total) * 100
            print(f"[{percentage:.1f}%] {message}")
        else:
            print(f"[*] {message}")

    # Collect statistics
    stats = collect_statistics(
        endpoint_url=endpoint,
        timeout=30,
        include_graphs=False,  # Skip graphs for speed
        class_limit=10,
        property_limit=10,
        progress_callback=progress
    )

    # Print summary
    print(stats.summary())


def example_detailed_collection():
    """Example: Detailed statistics collection with caching."""
    print("\n" + "=" * 60)
    print("Example 2: Detailed Statistics with Caching")
    print("=" * 60 + "\n")

    endpoint = "https://dbpedia.org/sparql"

    # Create collector with custom settings
    collector = StatisticsCollector(
        endpoint_url=endpoint,
        timeout=60,
        max_retries=3,
        cache_results=True
    )

    print("Collecting basic counts...")
    total_triples = collector.count_total_triples()
    distinct_subjects = collector.count_distinct_subjects()
    distinct_predicates = collector.count_distinct_predicates()

    print(f"\nResults:")
    print(f"  Total Triples: {total_triples:,}")
    print(f"  Distinct Subjects: {distinct_subjects:,}")
    print(f"  Distinct Predicates: {distinct_predicates:,}")

    print("\nCollecting class information...")
    top_classes = collector.get_top_classes(limit=15)

    print(f"\nTop 15 Classes:")
    for i, (cls, count) in enumerate(top_classes[:15], 1):
        # Extract local name for readability
        local_name = cls.split('/')[-1].split('#')[-1]
        print(f"  {i:2d}. {local_name:40s} {count:>10,} instances")

    print("\nCollecting property information...")
    top_properties = collector.get_top_properties(limit=15)

    print(f"\nTop 15 Properties:")
    for i, (prop, count) in enumerate(top_properties[:15], 1):
        # Extract local name for readability
        local_name = prop.split('/')[-1].split('#')[-1]
        print(f"  {i:2d}. {local_name:40s} {count:>10,} uses")

    # Show cache info
    cache_info = collector.get_cache_info()
    print(f"\nCache Information:")
    print(f"  Cached queries: {cache_info['cache_size']}")
    print(f"  Total queries executed: {cache_info['query_count']}")
    print(f"  Failed queries: {cache_info['failed_queries']}")


def example_literal_analysis():
    """Example: Analyze literal datatypes and languages."""
    print("\n" + "=" * 60)
    print("Example 3: Literal Analysis")
    print("=" * 60 + "\n")

    endpoint = "https://dbpedia.org/sparql"

    collector = StatisticsCollector(
        endpoint_url=endpoint,
        timeout=30
    )

    print("Analyzing literals...")
    total_literals = collector.count_literals()
    print(f"Total literals: {total_literals:,}")

    print("\nAnalyzing datatypes...")
    datatypes = collector.get_datatype_distribution(limit=10)

    print("\nDatatype Distribution:")
    for dtype, count in sorted(datatypes.items(), key=lambda x: x[1], reverse=True):
        # Extract local name
        local_name = dtype.split('/')[-1].split('#')[-1] if dtype else "plain"
        percentage = (count / total_literals * 100) if total_literals > 0 else 0
        print(f"  {local_name:30s} {count:>10,} ({percentage:5.1f}%)")

    print("\nAnalyzing languages...")
    languages = collector.get_language_distribution(limit=10)

    print("\nLanguage Distribution:")
    for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_literals * 100) if total_literals > 0 else 0
        print(f"  {lang:10s} {count:>10,} ({percentage:5.1f}%)")


def example_namespace_analysis():
    """Example: Analyze namespace usage."""
    print("\n" + "=" * 60)
    print("Example 4: Namespace Analysis")
    print("=" * 60 + "\n")

    endpoint = "https://dbpedia.org/sparql"

    collector = StatisticsCollector(
        endpoint_url=endpoint,
        timeout=30
    )

    print("Analyzing namespace usage...")
    namespaces = collector.analyze_namespace_usage()

    print(f"\nFound {len(namespaces)} namespaces\n")
    print("Top 20 Namespaces by Usage:")

    for i, (ns, count) in enumerate(
        sorted(namespaces.items(), key=lambda x: x[1], reverse=True)[:20], 1
    ):
        # Shorten long namespaces for display
        display_ns = ns if len(ns) <= 60 else ns[:57] + "..."
        print(f"  {i:2d}. {display_ns:62s} {count:>10,}")


def example_pattern_detection():
    """Example: Detect common patterns in the dataset."""
    print("\n" + "=" * 60)
    print("Example 5: Pattern Detection")
    print("=" * 60 + "\n")

    endpoint = "https://dbpedia.org/sparql"

    collector = StatisticsCollector(
        endpoint_url=endpoint,
        timeout=30
    )

    print("Detecting patterns...")
    patterns = collector.detect_patterns()

    print(f"\nDetected {len(patterns)} patterns:\n")

    for pattern, value in patterns.items():
        print(f"  {pattern}: {value}")


def example_full_statistics_with_export():
    """Example: Collect full statistics and export to JSON."""
    print("\n" + "=" * 60)
    print("Example 6: Full Statistics with JSON Export")
    print("=" * 60 + "\n")

    endpoint = "https://dbpedia.org/sparql"

    def progress(message, current=0, total=0):
        if total > 0:
            print(f"  [{current}/{total}] {message}")
        else:
            print(f"  [*] {message}")

    print("Collecting comprehensive statistics...")
    print("(This may take several minutes...)\n")

    stats = collect_statistics(
        endpoint_url=endpoint,
        timeout=60,
        include_graphs=False,  # Set to True to include graph analysis
        class_limit=50,
        property_limit=50,
        progress_callback=progress
    )

    # Print summary
    print("\n" + stats.summary())

    # Export to JSON
    output_file = "dbpedia_statistics.json"
    with open(output_file, 'w') as f:
        json.dump(stats.to_dict(), f, indent=2)

    print(f"\nStatistics exported to: {output_file}")

    # Export summary to text file
    summary_file = "dbpedia_statistics.txt"
    with open(summary_file, 'w') as f:
        f.write(stats.summary())

    print(f"Summary exported to: {summary_file}")


def example_compare_endpoints():
    """Example: Compare statistics from multiple endpoints."""
    print("\n" + "=" * 60)
    print("Example 7: Compare Multiple Endpoints")
    print("=" * 60 + "\n")

    endpoints = [
        ("DBpedia", "https://dbpedia.org/sparql"),
        ("Wikidata", "https://query.wikidata.org/sparql"),
    ]

    results = []

    for name, endpoint in endpoints:
        print(f"\nCollecting statistics for {name}...")

        try:
            stats = collect_statistics(
                endpoint_url=endpoint,
                timeout=30,
                include_graphs=False,
                class_limit=5,
                property_limit=5
            )
            results.append((name, stats))
            print(f"  ✓ Completed in {stats.collection_duration_seconds:.1f}s")

        except Exception as e:
            print(f"  ✗ Failed: {str(e)}")

    # Print comparison
    print("\n" + "=" * 60)
    print("Comparison Summary")
    print("=" * 60 + "\n")

    print(f"{'Endpoint':<20} {'Triples':>15} {'Subjects':>15} {'Classes':>10}")
    print("-" * 62)

    for name, stats in results:
        print(f"{name:<20} {stats.total_triples:>15,} {stats.distinct_subjects:>15,} {stats.total_classes:>10,}")


def example_incremental_analysis():
    """Example: Incremental analysis with checkpoint saving."""
    print("\n" + "=" * 60)
    print("Example 8: Incremental Analysis with Checkpoints")
    print("=" * 60 + "\n")

    endpoint = "https://dbpedia.org/sparql"

    collector = StatisticsCollector(
        endpoint_url=endpoint,
        timeout=30,
        cache_results=True
    )

    # Phase 1: Basic counts
    print("Phase 1: Collecting basic counts...")
    basic_stats = {
        'total_triples': collector.count_total_triples(),
        'distinct_subjects': collector.count_distinct_subjects(),
        'distinct_predicates': collector.count_distinct_predicates(),
    }

    with open('checkpoint_basic.json', 'w') as f:
        json.dump(basic_stats, f, indent=2)
    print("  ✓ Saved to checkpoint_basic.json")

    # Phase 2: Class analysis
    print("\nPhase 2: Analyzing classes...")
    class_stats = {
        'top_classes': collector.get_top_classes(limit=20),
        'typed_resources': collector.count_typed_resources(),
    }

    with open('checkpoint_classes.json', 'w') as f:
        json.dump(class_stats, f, indent=2)
    print("  ✓ Saved to checkpoint_classes.json")

    # Phase 3: Property analysis
    print("\nPhase 3: Analyzing properties...")
    property_stats = {
        'top_properties': collector.get_top_properties(limit=20),
    }

    with open('checkpoint_properties.json', 'w') as f:
        json.dump(property_stats, f, indent=2)
    print("  ✓ Saved to checkpoint_properties.json")

    print("\nAll checkpoints saved!")
    print("Cache contains:", collector.get_cache_info()['cache_size'], "entries")


if __name__ == "__main__":
    import sys

    examples = {
        '1': ('Basic Statistics', example_basic_statistics),
        '2': ('Detailed Collection', example_detailed_collection),
        '3': ('Literal Analysis', example_literal_analysis),
        '4': ('Namespace Analysis', example_namespace_analysis),
        '5': ('Pattern Detection', example_pattern_detection),
        '6': ('Full Statistics with Export', example_full_statistics_with_export),
        '7': ('Compare Endpoints', example_compare_endpoints),
        '8': ('Incremental Analysis', example_incremental_analysis),
    }

    if len(sys.argv) > 1:
        choice = sys.argv[1]
        if choice in examples:
            print(f"\nRunning: {examples[choice][0]}")
            examples[choice][1]()
        else:
            print(f"Invalid choice: {choice}")
            print("Available examples:", ', '.join(examples.keys()))
    else:
        print("\nAvailable Examples:")
        print("=" * 60)
        for key, (name, _) in examples.items():
            print(f"  {key}. {name}")
        print("\nUsage: python examples_statistics.py <example_number>")
        print("\nRunning Example 1 by default...\n")
        example_basic_statistics()
