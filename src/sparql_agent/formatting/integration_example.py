"""
Integration Example: SPARQL Query Execution with Structured Formatting

This example demonstrates end-to-end integration of query execution
with structured output formatting for real-world use cases.
"""

from ..core.types import QueryResult, QueryStatus, EndpointInfo
from ..execution.executor import QueryExecutor
from .structured import (
    JSONFormatter,
    CSVFormatter,
    DataFrameFormatter,
    FormatterConfig,
    MultiValueStrategy,
    auto_format,
)


def example_uniprot_query():
    """
    Example: Query UniProt SPARQL endpoint and format results.

    This demonstrates a real query against a public SPARQL endpoint.
    """
    print("=" * 80)
    print("UniProt Query Example")
    print("=" * 80)

    # Setup endpoint
    endpoint = EndpointInfo(
        url="https://sparql.uniprot.org/sparql",
        name="UniProt",
        timeout=30,
    )

    # Define query
    query = """
    PREFIX up: <http://purl.uniprot.org/core/>
    PREFIX taxon: <http://purl.uniprot.org/taxonomy/>

    SELECT ?protein ?name ?organism
    WHERE {
        ?protein a up:Protein ;
            up:organism taxon:9606 ;
            up:recommendedName ?recName .
        ?recName up:fullName ?name .
        ?protein up:organism ?organism .
    }
    LIMIT 10
    """

    # Execute query
    print("\nExecuting query...")
    executor = QueryExecutor(timeout=30, enable_metrics=True)
    result = executor.execute(query, endpoint)

    if not result.is_success:
        print(f"Query failed: {result.error_message}")
        return

    print(f"✓ Query successful: {result.row_count} results in {result.execution_time:.2f}s")

    # Format as JSON
    print("\n1. JSON Output:")
    print("-" * 80)
    json_formatter = JSONFormatter(pretty=True, indent=2)
    json_output = json_formatter.format(result)
    print(json_output[:500] + "...")

    # Format as CSV
    print("\n2. CSV Output:")
    print("-" * 80)
    csv_formatter = CSVFormatter(excel_compatible=True)
    csv_output = csv_formatter.format(result)
    print(csv_output[:500] + "...")

    # Format as DataFrame (if pandas available)
    print("\n3. DataFrame Output:")
    print("-" * 80)
    try:
        df_formatter = DataFrameFormatter(infer_types=True)
        df = df_formatter.format(result)
        print(df.head())
        print(f"\nDataFrame shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
    except ImportError:
        print("pandas not installed - skipping DataFrame example")


def example_wikidata_query():
    """
    Example: Query Wikidata for Nobel Prize winners.
    """
    print("\n" + "=" * 80)
    print("Wikidata Query Example - Nobel Prize Winners")
    print("=" * 80)

    endpoint = EndpointInfo(
        url="https://query.wikidata.org/sparql",
        name="Wikidata",
        timeout=30,
    )

    query = """
    SELECT ?person ?personLabel ?prize ?prizeLabel ?year
    WHERE {
        ?person wdt:P166 ?prize .
        ?prize wdt:P279* wd:Q7191 .
        ?person wdt:P166 ?prize .
        OPTIONAL { ?person wdt:P166 ?prize . ?prize wdt:P585 ?year }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    LIMIT 20
    """

    print("\nExecuting query...")
    executor = QueryExecutor(timeout=30)
    result = executor.execute(query, endpoint)

    if not result.is_success:
        print(f"Query failed: {result.error_message}")
        return

    print(f"✓ Retrieved {result.row_count} results")

    # Auto-format based on result structure
    print("\nAuto-formatted output:")
    print("-" * 80)
    output = auto_format(result)
    print(str(output)[:600] + "...")


def example_custom_formatting_pipeline():
    """
    Example: Custom data processing pipeline with multiple output formats.
    """
    print("\n" + "=" * 80)
    print("Custom Formatting Pipeline Example")
    print("=" * 80)

    # Simulate query result
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                "project": "Project Alpha",
                "budget": "1000000",
                "status": "Active",
                "start_date": "2024-01-15",
            },
            {
                "project": "Project Beta",
                "budget": "750000",
                "status": "Completed",
                "start_date": "2023-06-01",
            },
            {
                "project": "Project Gamma",
                "budget": "500000",
                "status": "Planning",
                "start_date": "2024-03-01",
            },
        ],
        variables=["project", "budget", "status", "start_date"],
        row_count=3,
        execution_time=0.145,
    )

    print(f"\nProcessing {result.row_count} project records...")

    # Pipeline Step 1: JSON for API response
    print("\n1. JSON for API:")
    print("-" * 80)
    config_api = FormatterConfig(include_metadata=True)
    json_formatter = JSONFormatter(pretty=False, config=config_api)
    api_response = json_formatter.format(result)
    print(f"Generated JSON response: {len(api_response)} bytes")
    print(api_response[:200] + "...")

    # Pipeline Step 2: CSV for Excel export
    print("\n2. CSV for Excel:")
    print("-" * 80)
    csv_formatter = CSVFormatter(excel_compatible=True)
    csv_output = csv_formatter.format(result)
    print("CSV output:")
    print(csv_output)

    # Pipeline Step 3: DataFrame for analysis
    print("\n3. DataFrame for Analysis:")
    print("-" * 80)
    try:
        import pandas as pd

        df_formatter = DataFrameFormatter(
            infer_types=True,
            parse_dates=["start_date"],
        )
        df = df_formatter.format(result)

        print("Data summary:")
        print(df)
        print(f"\nTotal budget: ${df['budget'].astype(int).sum():,}")
        print(f"Status distribution:\n{df['status'].value_counts()}")

    except ImportError:
        print("pandas not installed - skipping analysis")

    # Pipeline Step 4: TSV for data exchange
    print("\n4. TSV for Data Exchange:")
    print("-" * 80)
    from .structured import TSVFormatter
    tsv_formatter = TSVFormatter()
    tsv_output = tsv_formatter.format(result)
    print("TSV output:")
    print(tsv_output)


def example_multi_value_handling():
    """
    Example: Handling multi-valued fields in different formats.
    """
    print("\n" + "=" * 80)
    print("Multi-Value Field Handling Example")
    print("=" * 80)

    # Simulate result with multi-valued fields
    # Note: In practice, multi-valued fields would come from query results
    # with multiple bindings for the same entity
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                "person": "Alice",
                "skills": "Python, Java, SQL",  # Simulated multi-value
                "years_exp": "5",
            },
            {
                "person": "Bob",
                "skills": "JavaScript, React, Node.js",
                "years_exp": "3",
            },
            {
                "person": "Charlie",
                "skills": "C++, Rust",
                "years_exp": "8",
            },
        ],
        variables=["person", "skills", "years_exp"],
        row_count=3,
    )

    print("\n1. JOIN Strategy (semicolon-separated):")
    print("-" * 80)
    config = FormatterConfig(
        multi_value_strategy=MultiValueStrategy.JOIN,
        multi_value_separator="; "
    )
    formatter = CSVFormatter(config=config)
    print(formatter.format(result))

    print("\n2. Default Strategy (FIRST value):")
    print("-" * 80)
    config = FormatterConfig(multi_value_strategy=MultiValueStrategy.FIRST)
    formatter = CSVFormatter(config=config)
    print(formatter.format(result))


def example_error_handling_and_validation():
    """
    Example: Proper error handling in formatting pipeline.
    """
    print("\n" + "=" * 80)
    print("Error Handling Example")
    print("=" * 80)

    from ..core.exceptions import FormattingError

    # Example 1: Handle failed query
    print("\n1. Failed Query Result:")
    print("-" * 80)
    failed_result = QueryResult(
        status=QueryStatus.FAILED,
        error_message="Connection timeout",
        row_count=0,
    )

    try:
        formatter = JSONFormatter()
        output = formatter.format(failed_result)
    except FormattingError as e:
        print(f"✓ Caught expected error: {e}")
        print(f"  Details: {e.details}")

    # Example 2: Handle empty results gracefully
    print("\n2. Empty Result Set:")
    print("-" * 80)
    empty_result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[],
        variables=["x", "y", "z"],
        row_count=0,
    )

    formatter = CSVFormatter()
    output = formatter.format(empty_result)
    print("CSV output for empty result:")
    print(output)
    print("✓ Empty result handled gracefully (header only)")

    # Example 3: Validate before processing
    print("\n3. Pre-validation:")
    print("-" * 80)
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[{"x": "1"}],
        variables=["x"],
        row_count=1,
    )

    formatter = JSONFormatter()
    try:
        formatter._validate_result(result)
        print("✓ Validation passed")
        output = formatter.format(result)
        print(f"✓ Formatted successfully: {len(output)} bytes")
    except FormattingError as e:
        print(f"✗ Validation failed: {e}")


def example_performance_comparison():
    """
    Example: Compare performance of different formatters.
    """
    print("\n" + "=" * 80)
    print("Performance Comparison Example")
    print("=" * 80)

    import time

    # Create a moderately large result set
    bindings = [
        {
            "id": f"id_{i}",
            "name": f"Item {i}",
            "value": str(i * 100),
            "category": f"Category {i % 10}",
        }
        for i in range(1000)
    ]

    result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=bindings,
        variables=["id", "name", "value", "category"],
        row_count=1000,
    )

    print(f"\nFormatting {result.row_count} rows...")

    # Test JSON formatter
    start = time.time()
    json_formatter = JSONFormatter()
    json_output = json_formatter.format(result)
    json_time = time.time() - start
    print(f"\n1. JSON: {json_time:.4f}s ({len(json_output):,} bytes)")

    # Test CSV formatter
    start = time.time()
    csv_formatter = CSVFormatter()
    csv_output = csv_formatter.format(result)
    csv_time = time.time() - start
    print(f"2. CSV: {csv_time:.4f}s ({len(csv_output):,} bytes)")

    # Test DataFrame formatter (if available)
    try:
        start = time.time()
        df_formatter = DataFrameFormatter()
        df = df_formatter.format(result)
        df_time = time.time() - start
        print(f"3. DataFrame: {df_time:.4f}s ({df.memory_usage(deep=True).sum():,} bytes)")
    except ImportError:
        print("3. DataFrame: pandas not installed")

    print("\nPerformance summary:")
    print(f"  - JSON is suitable for APIs and web responses")
    print(f"  - CSV is efficient for file exports")
    print(f"  - DataFrame is best for data analysis workflows")


def main():
    """
    Run all integration examples.
    """
    print("\n")
    print("#" * 80)
    print("# SPARQL Formatting Integration Examples")
    print("#" * 80)

    # Note: Actual endpoint queries are commented out to avoid
    # making real network requests during testing

    # Uncomment to run real queries:
    # example_uniprot_query()
    # example_wikidata_query()

    # Run local examples
    example_custom_formatting_pipeline()
    example_multi_value_handling()
    example_error_handling_and_validation()
    example_performance_comparison()

    print("\n" + "=" * 80)
    print("Integration examples completed!")
    print("=" * 80 + "\n")

    print("\nTo run queries against real SPARQL endpoints, uncomment:")
    print("  - example_uniprot_query()")
    print("  - example_wikidata_query()")


if __name__ == "__main__":
    main()
