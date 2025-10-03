#!/usr/bin/env python3
"""
Batch Processing Usage Examples.

Demonstrates how to use the SPARQL Agent batch processing module
programmatically and via CLI.
"""

import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any


# ============================================================================
# CLI Examples
# ============================================================================

def example_batch_query_text():
    """Example: Execute queries from text file."""
    print("="*60)
    print("Example 1: Batch Query from Text File")
    print("="*60)

    cmd = [
        "sparql-agent", "batch", "batch-query",
        "queries.txt",
        "--endpoint", "https://sparql.uniprot.org/sparql",
        "--parallel",
        "--workers", "4",
        "--output", "results-text/",
        "--verbose"
    ]

    print(f"\nCommand:\n{' '.join(cmd)}\n")
    print("This will:")
    print("- Read queries from queries.txt (one per line)")
    print("- Execute against UniProt SPARQL endpoint")
    print("- Process 4 queries in parallel")
    print("- Save results to results-text/ directory")
    print()


def example_batch_query_json():
    """Example: Execute queries from JSON file with metadata."""
    print("="*60)
    print("Example 2: Batch Query from JSON with Metadata")
    print("="*60)

    cmd = [
        "sparql-agent", "batch", "batch-query",
        "queries.json",
        "--endpoint", "https://query.wikidata.org/sparql",
        "--format", "json",
        "--parallel",
        "--workers", "8",
        "--timeout", "120",
        "--retry", "3",
        "--output-mode", "both",
        "--output", "results-json/"
    ]

    print(f"\nCommand:\n{' '.join(cmd)}\n")
    print("This will:")
    print("- Read queries from queries.json with metadata")
    print("- Execute against Wikidata endpoint")
    print("- Use 8 parallel workers")
    print("- 120s timeout per query")
    print("- Retry failed queries up to 3 times")
    print("- Save both individual and consolidated results")
    print()


def example_bulk_discover():
    """Example: Discover multiple endpoints."""
    print("="*60)
    print("Example 3: Bulk Endpoint Discovery")
    print("="*60)

    cmd = [
        "sparql-agent", "batch", "bulk-discover",
        "endpoints.yaml",
        "--format", "yaml",
        "--parallel",
        "--workers", "4",
        "--timeout", "30",
        "--output", "discovery-results/"
    ]

    print(f"\nCommand:\n{' '.join(cmd)}\n")
    print("This will:")
    print("- Read endpoints from endpoints.yaml")
    print("- Discover capabilities in parallel")
    print("- Use 4 parallel workers")
    print("- 30s timeout per endpoint")
    print("- Save discovery results")
    print()


def example_generate_examples():
    """Example: Generate query examples from schema."""
    print("="*60)
    print("Example 4: Generate Query Examples")
    print("="*60)

    cmd = [
        "sparql-agent", "batch", "generate-examples",
        "schema.ttl",
        "--count", "100",
        "--patterns", "basic,filter,aggregate,optional,union",
        "--format", "json",
        "--output", "generated-examples.json"
    ]

    print(f"\nCommand:\n{' '.join(cmd)}\n")
    print("This will:")
    print("- Analyze schema.ttl")
    print("- Generate 100 example queries")
    print("- Cover 5 different query patterns")
    print("- Save as JSON")
    print()


def example_production_workflow():
    """Example: Production batch processing workflow."""
    print("="*60)
    print("Example 5: Production Workflow")
    print("="*60)

    cmd = [
        "sparql-agent", "batch", "batch-query",
        "production-queries.json",
        "--endpoint", "https://production.endpoint/sparql",
        "--format", "json",
        "--parallel",
        "--workers", "16",
        "--timeout", "300",
        "--retry", "3",
        "--strategy", "hybrid",
        "--output-mode", "both",
        "--output", "production-results/"
    ]

    print(f"\nCommand:\n{' '.join(cmd)}\n")
    print("This will:")
    print("- Process production queries from JSON")
    print("- Use 16 parallel workers for high throughput")
    print("- 5-minute timeout for complex queries")
    print("- Retry failed queries 3 times")
    print("- Use hybrid generation strategy")
    print("- Save comprehensive results")
    print()


# ============================================================================
# Programmatic Examples
# ============================================================================

def create_sample_queries_file():
    """Create sample queries file programmatically."""
    print("="*60)
    print("Creating Sample Queries File")
    print("="*60)

    queries = [
        {
            "id": "basic_001",
            "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
            "metadata": {
                "description": "Basic triple pattern",
                "expected_results": 10,
                "priority": "high"
            }
        },
        {
            "id": "protein_001",
            "query": "Find all human proteins",
            "metadata": {
                "description": "Natural language protein query",
                "type": "natural_language",
                "domain": "proteins"
            }
        },
        {
            "id": "class_discovery",
            "query": "SELECT DISTINCT ?class WHERE { ?s a ?class } LIMIT 50",
            "metadata": {
                "description": "Discover all classes",
                "pattern": "type_discovery"
            }
        }
    ]

    output_file = Path("sample-queries.json")
    with open(output_file, 'w') as f:
        json.dump(queries, f, indent=2)

    print(f"\nCreated {output_file} with {len(queries)} queries")
    print(f"File contents:\n{json.dumps(queries, indent=2)}")
    print()


def create_sample_endpoints_file():
    """Create sample endpoints file programmatically."""
    print("="*60)
    print("Creating Sample Endpoints File")
    print("="*60)

    endpoints = [
        {
            "id": "uniprot",
            "endpoint": "https://sparql.uniprot.org/sparql",
            "metadata": {
                "name": "UniProt SPARQL",
                "description": "Universal Protein Resource",
                "domain": "proteins",
                "organization": "UniProt Consortium"
            }
        },
        {
            "id": "wikidata",
            "endpoint": "https://query.wikidata.org/sparql",
            "metadata": {
                "name": "Wikidata Query Service",
                "description": "Free knowledge base",
                "domain": "general"
            }
        }
    ]

    output_file = Path("sample-endpoints.json")
    with open(output_file, 'w') as f:
        json.dump(endpoints, f, indent=2)

    print(f"\nCreated {output_file} with {len(endpoints)} endpoints")
    print()


def parse_batch_results(results_file: Path) -> Dict[str, Any]:
    """Parse and analyze batch processing results."""
    print("="*60)
    print("Parsing Batch Results")
    print("="*60)

    with open(results_file) as f:
        results = json.load(f)

    summary = results.get('summary', {})
    items = results.get('items', [])

    print(f"\nResults Summary:")
    print(f"  Total Items: {summary.get('total_items', 0)}")
    print(f"  Successful: {summary.get('successful_items', 0)}")
    print(f"  Failed: {summary.get('failed_items', 0)}")
    print(f"  Success Rate: {summary.get('success_rate', '0%')}")
    print(f"  Total Time: {summary.get('total_time', '0s')}")
    print(f"  Average Time: {summary.get('average_time', '0s')}")

    # Analyze successful items
    successful = [item for item in items if item['status'] == 'success']
    if successful:
        print(f"\nSuccessful Queries ({len(successful)}):")
        for item in successful[:5]:  # Show first 5
            print(f"  - {item['id']}: {item.get('execution_time', 0):.2f}s")

    # Analyze failed items
    failed = [item for item in items if item['status'] == 'failed']
    if failed:
        print(f"\nFailed Queries ({len(failed)}):")
        for item in failed[:5]:  # Show first 5
            print(f"  - {item['id']}: {item.get('error', 'Unknown error')}")

    print()
    return results


def monitor_batch_progress(output_dir: Path):
    """Monitor batch processing progress."""
    print("="*60)
    print("Monitoring Batch Progress")
    print("="*60)

    progress_file = output_dir / "progress.json"

    if progress_file.exists():
        with open(progress_file) as f:
            progress = json.load(f)

        summary = progress.get('summary', {})
        print(f"\nCurrent Progress:")
        print(f"  Completed: {summary.get('successful_items', 0)} / {summary.get('total_items', 0)}")
        print(f"  Failed: {summary.get('failed_items', 0)}")
        print(f"  Success Rate: {summary.get('success_rate', '0%')}")
    else:
        print("\nNo progress file found yet")

    print()


# ============================================================================
# Advanced Examples
# ============================================================================

def example_filtered_processing():
    """Example: Process only high-priority queries."""
    print("="*60)
    print("Example 6: Filtered Processing")
    print("="*60)

    # Create queries with priorities
    queries = [
        {"id": f"high_{i}", "query": f"Query {i}", "metadata": {"priority": "high"}}
        for i in range(5)
    ] + [
        {"id": f"low_{i}", "query": f"Query {i}", "metadata": {"priority": "low"}}
        for i in range(10)
    ]

    # Filter high priority
    high_priority = [q for q in queries if q['metadata']['priority'] == 'high']

    output_file = Path("high-priority-queries.json")
    with open(output_file, 'w') as f:
        json.dump(high_priority, f, indent=2)

    print(f"\nFiltered {len(high_priority)} high-priority queries from {len(queries)} total")
    print(f"Saved to {output_file}")
    print()


def example_result_aggregation():
    """Example: Aggregate results from multiple batches."""
    print("="*60)
    print("Example 7: Result Aggregation")
    print("="*60)

    # Simulate multiple batch results
    batch_dirs = [
        Path("batch-1/results.json"),
        Path("batch-2/results.json"),
        Path("batch-3/results.json"),
    ]

    aggregated = {
        "total_batches": len(batch_dirs),
        "total_queries": 0,
        "successful_queries": 0,
        "failed_queries": 0,
        "total_time": 0.0,
        "batches": []
    }

    print("\nAggregating results from multiple batches...")

    for batch_file in batch_dirs:
        if batch_file.exists():
            with open(batch_file) as f:
                batch_results = json.load(f)

            summary = batch_results.get('summary', {})
            aggregated["total_queries"] += summary.get('total_items', 0)
            aggregated["successful_queries"] += summary.get('successful_items', 0)
            aggregated["failed_queries"] += summary.get('failed_items', 0)

            aggregated["batches"].append({
                "file": str(batch_file),
                "summary": summary
            })

    # Calculate overall statistics
    if aggregated["total_queries"] > 0:
        aggregated["overall_success_rate"] = (
            aggregated["successful_queries"] / aggregated["total_queries"] * 100
        )

    print(f"\nAggregated Statistics:")
    print(f"  Total Batches: {aggregated['total_batches']}")
    print(f"  Total Queries: {aggregated['total_queries']}")
    print(f"  Successful: {aggregated['successful_queries']}")
    print(f"  Failed: {aggregated['failed_queries']}")
    print(f"  Overall Success Rate: {aggregated.get('overall_success_rate', 0):.2f}%")
    print()


def example_error_analysis():
    """Example: Analyze errors from batch processing."""
    print("="*60)
    print("Example 8: Error Analysis")
    print("="*60)

    errors_file = Path("batch-results/errors.json")

    if errors_file.exists():
        with open(errors_file) as f:
            errors = json.load(f)

        # Categorize errors
        error_types = {}
        for error in errors:
            error_msg = error.get('error', 'Unknown')

            # Extract error type
            if 'timeout' in error_msg.lower():
                error_type = 'Timeout'
            elif 'connection' in error_msg.lower():
                error_type = 'Connection'
            elif 'authentication' in error_msg.lower():
                error_type = 'Authentication'
            else:
                error_type = 'Other'

            error_types[error_type] = error_types.get(error_type, 0) + 1

        print(f"\nError Analysis ({len(errors)} total errors):")
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(errors)) * 100
            print(f"  {error_type}: {count} ({percentage:.1f}%)")
    else:
        print("\nNo errors file found")

    print()


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("SPARQL Agent - Batch Processing Examples")
    print("="*60 + "\n")

    # CLI Examples
    example_batch_query_text()
    example_batch_query_json()
    example_bulk_discover()
    example_generate_examples()
    example_production_workflow()

    # Programmatic Examples
    create_sample_queries_file()
    create_sample_endpoints_file()

    # Advanced Examples
    example_filtered_processing()
    example_result_aggregation()
    example_error_analysis()

    print("\n" + "="*60)
    print("Examples Complete")
    print("="*60)
    print("\nTo run these examples:")
    print("1. Create input files using the provided templates")
    print("2. Execute the CLI commands shown above")
    print("3. Analyze results using the programmatic examples")
    print("\nFor more information, see:")
    print("- README.md in this directory")
    print("- Main documentation at docs/batch-processing.md")
    print()


if __name__ == '__main__':
    main()
