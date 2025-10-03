"""
Examples demonstrating the ErrorHandler module.

This module shows how to use error handling and query optimization features.
"""

from sparql_agent.execution.error_handler import (
    ErrorHandler,
    ErrorCategory,
    ErrorContext,
    RetryStrategy,
    OptimizationLevel,
    handle_query_error,
    get_error_suggestions,
    optimize_query,
)
from sparql_agent.core.exceptions import (
    QueryTimeoutError,
    QuerySyntaxError,
    EndpointConnectionError,
    EndpointRateLimitError,
)
from sparql_agent.core.types import EndpointInfo


def example_1_categorize_errors():
    """Example 1: Categorize different types of errors."""
    print("=" * 70)
    print("Example 1: Error Categorization")
    print("=" * 70)

    handler = ErrorHandler()

    # Example errors
    errors = [
        (QuerySyntaxError("Syntax error at line 5"), "SELECT * WHERE ?s ?p ?o }"),
        (QueryTimeoutError("Query timed out after 30s"), "SELECT * WHERE { ?s ?p ?o }"),
        (EndpointConnectionError("Connection refused"), "SELECT * WHERE { ?s ?p ?o }"),
        (EndpointRateLimitError("Rate limit exceeded: 429"), "SELECT * WHERE { ?s ?p ?o }"),
    ]

    for error, query in errors:
        print(f"\nError: {error}")
        context = handler.categorize_error(error, query)
        print(f"Category: {context.category.value}")
        print(f"Severity: {context.severity}/10")
        print(f"Message: {context.message}")
        print(f"Recoverable: {context.is_recoverable}")
        print(f"Retry Strategy: {context.retry_strategy.value}")
        print(f"Suggestions ({len(context.suggestions)}):")
        for i, suggestion in enumerate(context.suggestions[:3], 1):
            print(f"  {i}. {suggestion}")


def example_2_timeout_handling():
    """Example 2: Handle timeout errors with suggestions."""
    print("\n" + "=" * 70)
    print("Example 2: Timeout Error Handling")
    print("=" * 70)

    handler = ErrorHandler()

    # Query that times out
    slow_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT *
    WHERE {
        ?s ?p ?o .
        OPTIONAL { ?s rdfs:label ?label }
        OPTIONAL { ?s rdfs:comment ?comment }
        OPTIONAL { ?o rdfs:label ?oLabel }
    }
    """

    error = QueryTimeoutError("Query execution time exceeded 30s")
    endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql", timeout=30)

    context = handler.categorize_error(error, slow_query, endpoint)

    print(f"\nQuery caused timeout:")
    print(slow_query[:100] + "...")
    print(f"\nError: {context.message}")
    print(f"\nSuggestions:")
    for i, suggestion in enumerate(context.suggestions, 1):
        print(f"  {i}. {suggestion}")

    # Show optimization suggestions
    print(f"\nQuery optimizations detected:")
    optimizations = handler.suggest_optimizations(slow_query)
    for opt in optimizations:
        print(f"  - {opt.issue} (Impact: {opt.impact})")
        print(f"    {opt.suggestion}")


def example_3_query_optimization():
    """Example 3: Query optimization analysis."""
    print("\n" + "=" * 70)
    print("Example 3: Query Optimization")
    print("=" * 70)

    handler = ErrorHandler()

    # Inefficient query
    inefficient_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT DISTINCT *
    WHERE {
        ?s ?p ?o .
        OPTIONAL { ?s rdfs:label ?label1 }
        OPTIONAL { ?s rdfs:comment ?comment1 }
        OPTIONAL { ?o rdfs:label ?label2 }
        OPTIONAL { ?o rdfs:comment ?comment2 }
        OPTIONAL { ?s rdf:type ?type1 }
        OPTIONAL { ?o rdf:type ?type2 }
        FILTER(regex(str(?s), "protein", "i"))
    }
    ORDER BY ?s
    """

    print("Analyzing query for optimization opportunities...")
    print(f"\nOriginal query:")
    print(inefficient_query)

    optimizations = handler.suggest_optimizations(inefficient_query)

    print(f"\nFound {len(optimizations)} optimization opportunities:")
    for i, opt in enumerate(optimizations, 1):
        print(f"\n{i}. {opt.issue}")
        print(f"   Level: {opt.level.value}")
        print(f"   Impact: {opt.impact}")
        print(f"   Category: {opt.category}")
        print(f"   Suggestion: {opt.suggestion}")
        if opt.estimated_improvement:
            print(f"   Estimated improvement: {opt.estimated_improvement}%")

    # Auto-optimize
    print("\n" + "-" * 70)
    print("Auto-optimized query (MEDIUM level):")
    print("-" * 70)
    optimized = handler.optimize_query(inefficient_query, OptimizationLevel.MEDIUM)
    print(optimized)


def example_4_error_recovery():
    """Example 4: Error recovery with retry strategies."""
    print("\n" + "=" * 70)
    print("Example 4: Error Recovery Simulation")
    print("=" * 70)

    handler = ErrorHandler(max_retries=3, retry_delay=0.1, enable_fallback=True)

    query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
    endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql")

    # Simulate different error scenarios
    scenarios = [
        ("Transient Network Error", EndpointConnectionError("Connection temporarily failed")),
        ("Rate Limited", EndpointRateLimitError("Too many requests")),
        ("Syntax Error", QuerySyntaxError("Malformed query")),
    ]

    for scenario_name, error in scenarios:
        print(f"\nScenario: {scenario_name}")
        print(f"Error: {error}")

        context = handler.categorize_error(error, query, endpoint)

        print(f"Category: {context.category.value}")
        print(f"Recoverable: {context.is_recoverable}")
        print(f"Retry Strategy: {context.retry_strategy.value}")
        print(f"Top Suggestions:")
        for suggestion in context.suggestions[:2]:
            print(f"  - {suggestion}")


def example_5_user_friendly_reports():
    """Example 5: Generate user-friendly error reports."""
    print("\n" + "=" * 70)
    print("Example 5: User-Friendly Error Reports")
    print("=" * 70)

    handler = ErrorHandler()

    # Complex error scenario
    query = """
    SELECT *
    WHERE {
        ?protein a <http://purl.uniprot.org/core/Protein> .
        ?protein rdfs:label ?label .
        ?protein <http://purl.uniprot.org/core/organism> ?organism .
    }
    """

    error = QueryTimeoutError(
        "Query execution exceeded timeout of 30 seconds",
        details={"timeout": 30, "elapsed": 35}
    )

    endpoint = EndpointInfo(
        url="https://sparql.uniprot.org/sparql",
        timeout=30
    )

    context = handler.categorize_error(error, query, endpoint)

    # Generate formatted report
    report = handler.format_error_report(context)
    print(report)


def example_6_convenience_functions():
    """Example 6: Using convenience functions."""
    print("\n" + "=" * 70)
    print("Example 6: Convenience Functions")
    print("=" * 70)

    # Quick error handling
    query = "SELECT * WHERE { ?s ?p ?o }"
    error = QueryTimeoutError("Timeout after 30s")

    print("Using handle_query_error():")
    context = handle_query_error(error, query)
    print(f"Category: {context.category.value}")
    print(f"Message: {context.message}")

    print("\nUsing get_error_suggestions():")
    suggestions = get_error_suggestions(error, query)
    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"{i}. {suggestion}")

    print("\nUsing optimize_query():")
    optimized, optimizations = optimize_query(query)
    print(f"Original: {query}")
    print(f"Optimized: {optimized}")
    print(f"Found {len(optimizations)} optimization(s)")


def example_7_statistics():
    """Example 7: Error handler statistics."""
    print("\n" + "=" * 70)
    print("Example 7: Error Handler Statistics")
    print("=" * 70)

    handler = ErrorHandler()

    # Simulate multiple errors
    test_queries = [
        ("SELECT * WHERE { ?s ?p ?o }", QueryTimeoutError("timeout")),
        ("INVALID QUERY", QuerySyntaxError("syntax error")),
        ("SELECT * WHERE { ?s ?p ?o }", EndpointConnectionError("connection failed")),
        ("SELECT * WHERE { ?s ?p ?o }", QueryTimeoutError("timeout")),
        ("SELECT * WHERE { ?s ?p ?o }", EndpointRateLimitError("rate limit")),
    ]

    for query, error in test_queries:
        handler.categorize_error(error, query)

    stats = handler.get_statistics()

    print("\nError Handler Statistics:")
    print(f"Total errors processed: {stats['total_errors']}")
    print(f"\nErrors by category:")
    for category, count in stats['errors_by_category'].items():
        print(f"  {category}: {count}")


def example_8_memory_error_handling():
    """Example 8: Handle memory/result size errors."""
    print("\n" + "=" * 70)
    print("Example 8: Memory Error Handling")
    print("=" * 70)

    handler = ErrorHandler()

    # Query without LIMIT that causes memory issues
    large_query = """
    PREFIX up: <http://purl.uniprot.org/core/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?protein ?label ?organism
    WHERE {
        ?protein a up:Protein .
        ?protein rdfs:label ?label .
        ?protein up:organism ?organism .
        ?organism rdfs:label ?orgLabel .
    }
    """

    error = Exception("Result set too large: out of memory")

    context = handler.categorize_error(error, large_query)

    print(f"Query without LIMIT:")
    print(large_query)
    print(f"\nError Category: {context.category.value}")
    print(f"Message: {context.message}")
    print(f"Severity: {context.severity}/10")
    print(f"\nCritical suggestions:")
    for i, suggestion in enumerate(context.suggestions[:5], 1):
        print(f"{i}. {suggestion}")

    if "critical_fix" in context.metadata:
        print(f"\nCritical Fix Required: {context.metadata['critical_fix']}")
        print(f"Suggested LIMIT: {context.metadata.get('suggested_limit', 'N/A')}")


def example_9_complex_query_optimization():
    """Example 9: Optimize complex queries."""
    print("\n" + "=" * 70)
    print("Example 9: Complex Query Optimization")
    print("=" * 70)

    handler = ErrorHandler(enable_optimization_suggestions=True)

    complex_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX up: <http://purl.uniprot.org/core/>

    SELECT DISTINCT *
    WHERE {
        {
            SELECT ?s WHERE {
                ?s rdf:type up:Protein .
                ?s up:organism ?org .
            }
        }
        ?s ?p ?o .
        OPTIONAL { ?s rdfs:label ?l1 }
        OPTIONAL { ?s rdfs:comment ?c1 }
        OPTIONAL { ?o rdfs:label ?l2 }
        OPTIONAL { ?o rdfs:comment ?c2 }
        OPTIONAL { ?s up:enzyme ?e }
        OPTIONAL { ?s up:sequence ?seq }
        FILTER(regex(str(?o), "human", "i"))
    }
    ORDER BY ?s ?p
    """

    print("Complex query with multiple issues:")
    print(complex_query)

    # Analyze
    optimizations = handler.suggest_optimizations(complex_query)

    print(f"\n{len(optimizations)} optimization opportunities found:\n")

    # Group by impact
    by_impact = {"high": [], "medium": [], "low": []}
    for opt in optimizations:
        by_impact[opt.impact].append(opt)

    for impact in ["high", "medium", "low"]:
        if by_impact[impact]:
            print(f"{impact.upper()} IMPACT:")
            for opt in by_impact[impact]:
                print(f"  - {opt.issue}")
                print(f"    Solution: {opt.suggestion}")
            print()

    # Show different optimization levels
    print("\nOptimization at different levels:")
    for level in [OptimizationLevel.LOW, OptimizationLevel.MEDIUM, OptimizationLevel.HIGH]:
        optimized = handler.optimize_query(complex_query, level)
        print(f"\n{level.value.upper()} level optimization:")
        print(f"Length: {len(complex_query)} -> {len(optimized)} chars")


def example_10_integrated_error_workflow():
    """Example 10: Complete error handling workflow."""
    print("\n" + "=" * 70)
    print("Example 10: Integrated Error Handling Workflow")
    print("=" * 70)

    handler = ErrorHandler(
        max_retries=3,
        retry_delay=0.5,
        enable_fallback=True,
        enable_optimization_suggestions=True
    )

    query = """
    PREFIX up: <http://purl.uniprot.org/core/>
    SELECT *
    WHERE {
        ?protein a up:Protein .
        ?protein up:organism ?org .
    }
    """

    endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql", timeout=30)

    print("Step 1: Execute query and encounter error")
    error = QueryTimeoutError("Query timed out after 30 seconds")

    print(f"\nStep 2: Categorize error")
    context = handler.categorize_error(error, query, endpoint)
    print(f"  Category: {context.category.value}")
    print(f"  Severity: {context.severity}/10")
    print(f"  Recoverable: {context.is_recoverable}")

    print(f"\nStep 3: Get suggestions")
    for i, suggestion in enumerate(context.suggestions[:3], 1):
        print(f"  {i}. {suggestion}")

    print(f"\nStep 4: Analyze query for optimization")
    optimizations = handler.suggest_optimizations(query)
    print(f"  Found {len(optimizations)} optimization opportunities")
    for opt in optimizations[:2]:
        print(f"    - {opt.issue} ({opt.impact} impact)")

    print(f"\nStep 5: Auto-optimize query")
    optimized = handler.optimize_query(query, OptimizationLevel.MEDIUM)
    print(f"  Original length: {len(query)} chars")
    print(f"  Optimized length: {len(optimized)} chars")
    print(f"  Optimized query: ...{optimized[-100:]}")

    print(f"\nStep 6: Retry strategy")
    print(f"  Recommended: {context.retry_strategy.value}")

    print(f"\nStep 7: Review statistics")
    stats = handler.get_statistics()
    print(f"  Total errors: {stats['total_errors']}")
    print(f"  Errors by category: {stats['errors_by_category']}")


def main():
    """Run all examples."""
    examples = [
        example_1_categorize_errors,
        example_2_timeout_handling,
        example_3_query_optimization,
        example_4_error_recovery,
        example_5_user_friendly_reports,
        example_6_convenience_functions,
        example_7_statistics,
        example_8_memory_error_handling,
        example_9_complex_query_optimization,
        example_10_integrated_error_workflow,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n[ERROR in {example.__name__}]: {e}")

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
