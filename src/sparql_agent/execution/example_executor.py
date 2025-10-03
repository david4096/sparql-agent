"""
Example usage of the QueryExecutor for SPARQL query execution.

This module demonstrates various features of the query executor including:
- Basic query execution
- Different result formats
- Streaming results
- Federated queries
- Performance monitoring
- Error handling
"""

import logging
from typing import List

from ..core.types import EndpointInfo, QueryResult
from .executor import (
    QueryExecutor,
    ResultFormat,
    FederatedQuery,
    execute_query,
    execute_federated_query,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_execution():
    """Demonstrate basic query execution."""
    print("\n" + "=" * 80)
    print("Example 1: Basic Query Execution")
    print("=" * 80)

    # Create executor
    executor = QueryExecutor(timeout=30, enable_metrics=True)

    # Define endpoint
    endpoint = EndpointInfo(
        url="https://sparql.uniprot.org/sparql",
        name="UniProt",
        timeout=30
    )

    # Simple query
    query = """
    PREFIX up: <http://purl.uniprot.org/core/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?protein ?name
    WHERE {
      ?protein a up:Protein ;
               up:organism <http://purl.uniprot.org/taxonomy/9606> ;
               up:recommendedName ?recommendedName .
      ?recommendedName up:fullName ?name .
    }
    LIMIT 5
    """

    try:
        result = executor.execute(query, endpoint)

        print(f"\nQuery Status: {result.status.value}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print(f"Results Found: {result.row_count}")
        print(f"Variables: {', '.join(result.variables)}")

        print("\nResults:")
        for i, binding in enumerate(result.bindings[:5], 1):
            print(f"{i}. {binding}")

        # Show metrics
        if result.metadata.get("metrics"):
            print("\nPerformance Metrics:")
            metrics = result.metadata["metrics"]
            print(f"  Network Time: {metrics.get('network_time', 0):.2f}s")
            print(f"  Parse Time: {metrics.get('parse_time', 0):.2f}s")

    except Exception as e:
        logger.error(f"Query execution failed: {e}")

    finally:
        executor.close()


def example_different_formats():
    """Demonstrate different result formats."""
    print("\n" + "=" * 80)
    print("Example 2: Different Result Formats")
    print("=" * 80)

    executor = QueryExecutor()

    endpoint = EndpointInfo(
        url="https://query.wikidata.org/sparql",
        name="Wikidata"
    )

    query = """
    SELECT ?item ?itemLabel ?birthDate
    WHERE {
      ?item wdt:P31 wd:Q5 ;         # instance of human
            wdt:P569 ?birthDate .     # birth date
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    LIMIT 3
    """

    # Try JSON format
    try:
        print("\nFormat: JSON")
        result = executor.execute(query, endpoint, format=ResultFormat.JSON)
        print(f"  Results: {result.row_count}")
        print(f"  First result: {result.bindings[0] if result.bindings else 'None'}")
    except Exception as e:
        logger.error(f"JSON format failed: {e}")

    # Try XML format
    try:
        print("\nFormat: XML")
        result = executor.execute(query, endpoint, format=ResultFormat.XML)
        print(f"  Results: {result.row_count}")
    except Exception as e:
        logger.error(f"XML format failed: {e}")

    executor.close()


def example_streaming_results():
    """Demonstrate streaming large result sets."""
    print("\n" + "=" * 80)
    print("Example 3: Streaming Results")
    print("=" * 80)

    executor = QueryExecutor(enable_streaming=True)

    endpoint = EndpointInfo(
        url="https://sparql.uniprot.org/sparql",
        name="UniProt"
    )

    query = """
    PREFIX up: <http://purl.uniprot.org/core/>

    SELECT ?protein ?taxon
    WHERE {
      ?protein a up:Protein ;
               up:organism ?taxon .
    }
    LIMIT 100
    """

    try:
        print("\nExecuting query with streaming...")
        result = executor.execute(query, endpoint, stream=True)

        print(f"Status: {result.status.value}")
        print(f"Results: {result.row_count}")
        print(f"Streaming: {result.metadata.get('streaming', False)}")

        # Process first few results
        print("\nFirst 3 results:")
        for i, binding in enumerate(result.bindings[:3], 1):
            print(f"{i}. {binding}")

    except Exception as e:
        logger.error(f"Streaming query failed: {e}")

    finally:
        executor.close()


def example_federated_query():
    """Demonstrate federated query across multiple endpoints."""
    print("\n" + "=" * 80)
    print("Example 4: Federated Query Execution")
    print("=" * 80)

    executor = QueryExecutor(timeout=60)

    # Define multiple endpoints
    endpoints = [
        EndpointInfo(
            url="https://sparql.uniprot.org/sparql",
            name="UniProt"
        ),
        EndpointInfo(
            url="https://www.ebi.ac.uk/rdf/services/reactome/sparql",
            name="Reactome"
        ),
    ]

    # Simple query that should work on multiple endpoints
    query = """
    SELECT ?s ?p ?o
    WHERE {
      ?s ?p ?o .
    }
    LIMIT 5
    """

    config = FederatedQuery(
        endpoints=endpoints,
        merge_strategy="union",
        parallel=True,
        fail_on_error=False  # Don't fail if one endpoint fails
    )

    try:
        print(f"\nExecuting federated query across {len(endpoints)} endpoints...")
        result = executor.execute_federated(query, config)

        print(f"\nStatus: {result.status.value}")
        print(f"Total Results: {result.row_count}")
        print(f"Execution Time: {result.execution_time:.2f}s")

        if result.metadata.get("endpoints_count"):
            print(f"Successful Endpoints: {result.metadata['endpoints_count']}")

        if result.metadata.get("errors"):
            print(f"\nErrors encountered:")
            for endpoint, error in result.metadata["errors"]:
                print(f"  - {endpoint.name}: {error}")

        print("\nSample Results:")
        for i, binding in enumerate(result.bindings[:5], 1):
            print(f"{i}. {binding}")

    except Exception as e:
        logger.error(f"Federated query failed: {e}")

    finally:
        executor.close()


def example_performance_monitoring():
    """Demonstrate performance monitoring and metrics."""
    print("\n" + "=" * 80)
    print("Example 5: Performance Monitoring")
    print("=" * 80)

    executor = QueryExecutor(enable_metrics=True)

    endpoint = EndpointInfo(
        url="https://sparql.uniprot.org/sparql",
        name="UniProt"
    )

    queries = [
        "SELECT * WHERE { ?s ?p ?o } LIMIT 10",
        "SELECT ?s WHERE { ?s a ?type } LIMIT 20",
        "SELECT ?label WHERE { ?s rdfs:label ?label } LIMIT 15",
    ]

    print("\nExecuting multiple queries...")

    for i, query in enumerate(queries, 1):
        try:
            result = executor.execute(query, endpoint, timeout=30)
            print(f"\nQuery {i}:")
            print(f"  Status: {result.status.value}")
            print(f"  Time: {result.execution_time:.2f}s")
            print(f"  Results: {result.row_count}")
        except Exception as e:
            logger.error(f"Query {i} failed: {e}")

    # Show overall statistics
    print("\n" + "-" * 40)
    print("Overall Statistics:")
    print("-" * 40)
    stats = executor.get_statistics()

    print(f"Total Queries: {stats['total_queries']}")
    print(f"Successful: {stats['successful_queries']}")
    print(f"Failed: {stats['failed_queries']}")
    print(f"Total Results: {stats['total_results']}")
    print(f"Average Execution Time: {stats['average_execution_time']:.2f}s")

    print("\nQueries by Endpoint:")
    for endpoint_url, count in stats['queries_by_endpoint'].items():
        print(f"  {endpoint_url}: {count}")

    if stats['errors_by_type']:
        print("\nErrors by Type:")
        for error_type, count in stats['errors_by_type'].items():
            print(f"  {error_type}: {count}")

    print("\nConnection Pool Stats:")
    pool_stats = stats['pool_stats']
    print(f"  Connections Created: {pool_stats['connections_created']}")
    print(f"  Connections Reused: {pool_stats['connections_reused']}")
    print(f"  Requests Sent: {pool_stats['requests_sent']}")
    print(f"  Requests Failed: {pool_stats['requests_failed']}")

    executor.close()


def example_error_handling():
    """Demonstrate error handling and recovery."""
    print("\n" + "=" * 80)
    print("Example 6: Error Handling")
    print("=" * 80)

    executor = QueryExecutor(max_retries=3, timeout=10)

    # Test with invalid endpoint
    print("\n1. Invalid endpoint:")
    invalid_endpoint = EndpointInfo(url="https://invalid.endpoint.example.com/sparql")
    query = "SELECT * WHERE { ?s ?p ?o } LIMIT 1"

    result = executor.execute(query, invalid_endpoint)
    print(f"  Status: {result.status.value}")
    print(f"  Error: {result.error_message}")

    # Test with timeout
    print("\n2. Query timeout:")
    endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql")
    complex_query = """
    SELECT *
    WHERE {
      ?s ?p ?o .
      ?o ?p2 ?o2 .
      ?o2 ?p3 ?o3 .
    }
    LIMIT 1000000
    """

    result = executor.execute(complex_query, endpoint, timeout=1)
    print(f"  Status: {result.status.value}")
    print(f"  Error: {result.error_message}")

    # Test with syntax error
    print("\n3. Syntax error:")
    invalid_query = "INVALID SPARQL QUERY"

    result = executor.execute(invalid_query, endpoint)
    print(f"  Status: {result.status.value}")
    print(f"  Error: {result.error_message}")

    executor.close()


def example_context_manager():
    """Demonstrate context manager usage."""
    print("\n" + "=" * 80)
    print("Example 7: Context Manager Usage")
    print("=" * 80)

    endpoint = EndpointInfo(
        url="https://sparql.uniprot.org/sparql",
        name="UniProt"
    )

    query = "SELECT * WHERE { ?s ?p ?o } LIMIT 5"

    # Use context manager for automatic cleanup
    with QueryExecutor() as executor:
        print("\nExecuting query with context manager...")
        result = executor.execute(query, endpoint)

        print(f"Status: {result.status.value}")
        print(f"Results: {result.row_count}")

    print("Executor automatically closed after context exit")


def example_quick_utilities():
    """Demonstrate quick utility functions."""
    print("\n" + "=" * 80)
    print("Example 8: Quick Utility Functions")
    print("=" * 80)

    # Quick single query execution
    print("\n1. Quick execute_query():")
    query = "SELECT * WHERE { ?s ?p ?o } LIMIT 3"
    endpoint = "https://sparql.uniprot.org/sparql"

    try:
        result = execute_query(query, endpoint, timeout=30)
        print(f"  Status: {result.status.value}")
        print(f"  Results: {result.row_count}")
    except Exception as e:
        logger.error(f"Quick query failed: {e}")

    # Quick federated query
    print("\n2. Quick execute_federated_query():")
    endpoints = [
        "https://sparql.uniprot.org/sparql",
        "https://www.ebi.ac.uk/rdf/services/reactome/sparql",
    ]

    try:
        result = execute_federated_query(query, endpoints, parallel=True)
        print(f"  Status: {result.status.value}")
        print(f"  Results: {result.row_count}")
    except Exception as e:
        logger.error(f"Federated query failed: {e}")


def run_all_examples():
    """Run all examples."""
    examples = [
        ("Basic Execution", example_basic_execution),
        ("Different Formats", example_different_formats),
        ("Streaming Results", example_streaming_results),
        ("Federated Query", example_federated_query),
        ("Performance Monitoring", example_performance_monitoring),
        ("Error Handling", example_error_handling),
        ("Context Manager", example_context_manager),
        ("Quick Utilities", example_quick_utilities),
    ]

    print("\n" + "=" * 80)
    print("SPARQL Query Executor Examples")
    print("=" * 80)
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")

    print("\n" + "=" * 80)

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            logger.error(f"Example '{name}' failed: {e}")

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    # Run all examples
    run_all_examples()

    # Or run individual examples:
    # example_basic_execution()
    # example_federated_query()
    # example_performance_monitoring()
