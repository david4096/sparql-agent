"""
Example usage of structured output formatters.

This module demonstrates how to use the JSON, CSV, TSV, and DataFrame
formatters to convert SPARQL query results into various output formats.
"""

from ..core.types import QueryResult, QueryStatus, EndpointInfo
from .structured import (
    JSONFormatter,
    CSVFormatter,
    TSVFormatter,
    DataFrameFormatter,
    FormatterConfig,
    MultiValueStrategy,
    FormatDetector,
    format_as_json,
    format_as_csv,
    format_as_dataframe,
    auto_format,
)


def create_sample_result() -> QueryResult:
    """
    Create a sample SPARQL query result for demonstration.

    Returns:
        Sample QueryResult with person data
    """
    return QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                "person": "http://example.org/person/alice",
                "name": "Alice Johnson",
                "age": "30",
                "city": "New York",
                "email": "alice@example.org",
            },
            {
                "person": "http://example.org/person/bob",
                "name": "Bob Smith",
                "age": "25",
                "city": "London",
                "email": "bob@example.org",
            },
            {
                "person": "http://example.org/person/charlie",
                "name": "Charlie Brown",
                "age": "35",
                "city": "Paris",
                "email": "charlie@example.org",
            },
            {
                "person": "http://example.org/person/diana",
                "name": "Diana Prince",
                "age": "28",
                "city": "Berlin",
                "email": "diana@example.org",
            },
        ],
        variables=["person", "name", "age", "city", "email"],
        row_count=4,
        execution_time=0.234,
        query="""
            SELECT ?person ?name ?age ?city ?email
            WHERE {
                ?person a foaf:Person ;
                    foaf:name ?name ;
                    foaf:age ?age ;
                    ex:city ?city ;
                    foaf:mbox ?email .
            }
        """,
        metadata={
            "endpoint": "http://example.org/sparql",
            "format": "json",
        }
    )


def create_complex_result() -> QueryResult:
    """
    Create a complex SPARQL query result with typed bindings.

    Returns:
        Sample QueryResult with typed binding information
    """
    return QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                "person": {
                    "type": "uri",
                    "value": "http://example.org/person/1"
                },
                "name": {
                    "type": "literal",
                    "value": "Alice Johnson",
                    "xml:lang": "en"
                },
                "age": {
                    "type": "typed-literal",
                    "value": "30",
                    "datatype": "http://www.w3.org/2001/XMLSchema#integer"
                },
                "birthDate": {
                    "type": "typed-literal",
                    "value": "1994-03-15",
                    "datatype": "http://www.w3.org/2001/XMLSchema#date"
                },
            },
            {
                "person": {
                    "type": "uri",
                    "value": "http://example.org/person/2"
                },
                "name": {
                    "type": "literal",
                    "value": "Bob Smith",
                    "xml:lang": "en"
                },
                "age": {
                    "type": "typed-literal",
                    "value": "25",
                    "datatype": "http://www.w3.org/2001/XMLSchema#integer"
                },
                "birthDate": {
                    "type": "typed-literal",
                    "value": "1999-07-22",
                    "datatype": "http://www.w3.org/2001/XMLSchema#date"
                },
            },
        ],
        variables=["person", "name", "age", "birthDate"],
        row_count=2,
        execution_time=0.156,
    )


def example_json_formatter():
    """
    Demonstrate JSON formatter usage.
    """
    print("=" * 80)
    print("JSON Formatter Examples")
    print("=" * 80)

    result = create_sample_result()

    # Example 1: Basic JSON formatting
    print("\n1. Basic JSON Formatting")
    print("-" * 80)
    formatter = JSONFormatter()
    output = formatter.format(result)
    print(output[:500] + "...")  # Print first 500 chars

    # Example 2: Pretty-printed JSON
    print("\n2. Pretty-Printed JSON")
    print("-" * 80)
    formatter = JSONFormatter(pretty=True, indent=2)
    output = formatter.format(result)
    print(output[:500] + "...")

    # Example 3: JSON with metadata
    print("\n3. JSON with Metadata")
    print("-" * 80)
    config = FormatterConfig(include_metadata=True)
    formatter = JSONFormatter(pretty=True, config=config)
    output = formatter.format(result)
    print(output[:600] + "...")

    # Example 4: JSON as dictionary
    print("\n4. Format as Dictionary")
    print("-" * 80)
    formatter = JSONFormatter()
    data_dict = formatter.format_dict(result)
    print(f"Type: {type(data_dict)}")
    print(f"Keys: {list(data_dict.keys())}")
    print(f"Variables: {data_dict['head']['vars']}")
    print(f"Result count: {len(data_dict['results']['bindings'])}")

    # Example 5: Convenience function
    print("\n5. Convenience Function")
    print("-" * 80)
    output = format_as_json(result, pretty=True, include_metadata=True)
    print(output[:400] + "...")


def example_csv_formatter():
    """
    Demonstrate CSV formatter usage.
    """
    print("\n" + "=" * 80)
    print("CSV Formatter Examples")
    print("=" * 80)

    result = create_sample_result()

    # Example 1: Basic CSV formatting
    print("\n1. Basic CSV Formatting")
    print("-" * 80)
    formatter = CSVFormatter()
    output = formatter.format(result)
    print(output)

    # Example 2: Custom delimiter (pipe-separated)
    print("\n2. Pipe-Separated Values")
    print("-" * 80)
    formatter = CSVFormatter(delimiter="|")
    output = formatter.format(result)
    print(output)

    # Example 3: Excel-compatible CSV
    print("\n3. Excel-Compatible CSV")
    print("-" * 80)
    formatter = CSVFormatter(excel_compatible=True)
    output = formatter.format(result)
    print(output)

    # Example 4: CSV without header
    print("\n4. CSV Without Header")
    print("-" * 80)
    formatter = CSVFormatter(include_header=False)
    output = formatter.format(result)
    print(output)

    # Example 5: CSV with custom null value
    print("\n5. CSV with Custom NULL Value")
    print("-" * 80)
    config = FormatterConfig(null_value="N/A")
    formatter = CSVFormatter(config=config)
    output = formatter.format(result)
    print(output)

    # Example 6: Convenience function
    print("\n6. Convenience Function")
    print("-" * 80)
    output = format_as_csv(result, delimiter=",", excel_compatible=True)
    print(output)


def example_tsv_formatter():
    """
    Demonstrate TSV formatter usage.
    """
    print("\n" + "=" * 80)
    print("TSV Formatter Examples")
    print("=" * 80)

    result = create_sample_result()

    # Example 1: Basic TSV formatting
    print("\n1. Basic TSV Formatting")
    print("-" * 80)
    formatter = TSVFormatter()
    output = formatter.format(result)
    print(output)

    # Example 2: TSV without header
    print("\n2. TSV Without Header")
    print("-" * 80)
    formatter = TSVFormatter(include_header=False)
    output = formatter.format(result)
    print(output)


def example_dataframe_formatter():
    """
    Demonstrate DataFrame formatter usage.
    """
    print("\n" + "=" * 80)
    print("DataFrame Formatter Examples")
    print("=" * 80)

    try:
        import pandas as pd
    except ImportError:
        print("pandas is not installed. Skipping DataFrame examples.")
        print("Install with: pip install pandas")
        return

    result = create_sample_result()

    # Example 1: Basic DataFrame formatting
    print("\n1. Basic DataFrame Formatting")
    print("-" * 80)
    formatter = DataFrameFormatter()
    df = formatter.format(result)
    print(df)
    print(f"\nDataFrame shape: {df.shape}")
    print(f"Column types:\n{df.dtypes}")

    # Example 2: DataFrame with type inference
    print("\n2. DataFrame with Type Inference")
    print("-" * 80)
    formatter = DataFrameFormatter(infer_types=True)
    df = formatter.format(result)
    print(df)
    print(f"\nColumn types after inference:\n{df.dtypes}")

    # Example 3: DataFrame with custom index
    print("\n3. DataFrame with Custom Index")
    print("-" * 80)
    formatter = DataFrameFormatter(index_column="name")
    df = formatter.format(result)
    print(df)

    # Example 4: DataFrame with metadata
    print("\n4. DataFrame with Metadata")
    print("-" * 80)
    formatter = DataFrameFormatter()
    df, metadata = formatter.format_with_metadata(result)
    print("DataFrame:")
    print(df.head())
    print("\nMetadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    # Example 5: Basic data analysis
    print("\n5. Basic Data Analysis")
    print("-" * 80)
    formatter = DataFrameFormatter(infer_types=True)
    df = formatter.format(result)

    print("Summary statistics:")
    print(df.describe(include='all'))

    # Example 6: Convenience function
    print("\n6. Convenience Function")
    print("-" * 80)
    df = format_as_dataframe(result, infer_types=True)
    print(df.head())


def example_format_detection():
    """
    Demonstrate automatic format detection.
    """
    print("\n" + "=" * 80)
    print("Format Detection Examples")
    print("=" * 80)

    # Example 1: Simple result
    print("\n1. Simple Tabular Result")
    print("-" * 80)
    result = create_sample_result()
    detected_format = FormatDetector.detect_format(result)
    print(f"Detected format: {detected_format.value}")

    # Example 2: Empty result
    print("\n2. Empty Result")
    print("-" * 80)
    empty_result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[],
        variables=["x", "y"],
        row_count=0,
    )
    detected_format = FormatDetector.detect_format(empty_result)
    print(f"Detected format: {detected_format.value}")

    # Example 3: Large result
    print("\n3. Large Result Set")
    print("-" * 80)
    large_bindings = [
        {"x": f"value_{i}", "y": f"data_{i}"}
        for i in range(2000)
    ]
    large_result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=large_bindings,
        variables=["x", "y"],
        row_count=2000,
    )
    detected_format = FormatDetector.detect_format(large_result)
    print(f"Detected format: {detected_format.value}")

    # Example 4: Auto-format
    print("\n4. Auto-Format with Detection")
    print("-" * 80)
    result = create_sample_result()
    output = auto_format(result)
    print(f"Output type: {type(output)}")
    print("First 300 characters:")
    print(str(output)[:300])


def example_advanced_configurations():
    """
    Demonstrate advanced formatter configurations.
    """
    print("\n" + "=" * 80)
    print("Advanced Configuration Examples")
    print("=" * 80)

    result = create_sample_result()

    # Example 1: Custom multi-value handling
    print("\n1. Multi-Value Field Handling")
    print("-" * 80)

    # Create result with multi-valued field
    multi_value_result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {"name": "Alice", "skills": ["Python", "Java", "SQL"]},
            {"name": "Bob", "skills": ["JavaScript", "React"]},
        ],
        variables=["name", "skills"],
        row_count=2,
    )

    # JOIN strategy
    config = FormatterConfig(
        multi_value_strategy=MultiValueStrategy.JOIN,
        multi_value_separator=" | "
    )
    formatter = CSVFormatter(config=config)
    print("JOIN strategy:")
    # Note: This would work if bindings actually had list values
    # print(formatter.format(multi_value_result))

    # Example 2: Type information in JSON
    print("\n2. Include Type Information in JSON")
    print("-" * 80)
    config = FormatterConfig(include_types=True)
    formatter = JSONFormatter(pretty=True, config=config)
    output = formatter.format(result)
    print(output[:400] + "...")

    # Example 3: Column width limiting
    print("\n3. Column Width Limiting")
    print("-" * 80)
    config = FormatterConfig(max_column_width=20)
    formatter = CSVFormatter(config=config)

    # Create result with long text
    long_text_result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                "name": "Alice",
                "description": "This is a very long description that exceeds the maximum column width"
            },
        ],
        variables=["name", "description"],
        row_count=1,
    )
    output = formatter.format(long_text_result)
    print(output)


def example_real_world_workflow():
    """
    Demonstrate a real-world data analysis workflow.
    """
    print("\n" + "=" * 80)
    print("Real-World Workflow Example")
    print("=" * 80)

    try:
        import pandas as pd
    except ImportError:
        print("pandas is not installed. Skipping workflow example.")
        return

    # Step 1: Execute query and get results
    print("\n1. Execute Query")
    print("-" * 80)
    result = create_sample_result()
    print(f"Retrieved {result.row_count} results in {result.execution_time}s")

    # Step 2: Convert to DataFrame for analysis
    print("\n2. Convert to DataFrame")
    print("-" * 80)
    formatter = DataFrameFormatter(infer_types=True)
    df = formatter.format(result)
    print(df)

    # Step 3: Perform analysis
    print("\n3. Data Analysis")
    print("-" * 80)
    print(f"Total people: {len(df)}")
    print(f"Cities represented: {df['city'].nunique()}")

    # Step 4: Export to CSV for sharing
    print("\n4. Export to CSV")
    print("-" * 80)
    csv_formatter = CSVFormatter(excel_compatible=True)
    csv_output = csv_formatter.format(result)
    print("CSV output (first 300 chars):")
    print(csv_output[:300])

    # Step 5: Export to JSON for web API
    print("\n5. Export to JSON for API")
    print("-" * 80)
    json_output = format_as_json(result, pretty=True, include_metadata=True)
    print("JSON output (first 400 chars):")
    print(json_output[:400])


def example_error_handling():
    """
    Demonstrate error handling in formatters.
    """
    print("\n" + "=" * 80)
    print("Error Handling Examples")
    print("=" * 80)

    from ..core.exceptions import FormattingError

    # Example 1: Failed query result
    print("\n1. Failed Query Result")
    print("-" * 80)
    failed_result = QueryResult(
        status=QueryStatus.FAILED,
        error_message="Query execution failed",
        row_count=0,
    )

    try:
        formatter = JSONFormatter()
        output = formatter.format(failed_result)
    except FormattingError as e:
        print(f"Caught FormattingError: {e}")

    # Example 2: Empty result handling
    print("\n2. Empty Result Handling")
    print("-" * 80)
    empty_result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[],
        variables=["x", "y", "z"],
        row_count=0,
    )

    formatter = CSVFormatter()
    output = formatter.format(empty_result)
    print("Empty result CSV:")
    print(output)
    print("(Contains header only)")


def main():
    """
    Run all examples.
    """
    print("\n")
    print("#" * 80)
    print("# SPARQL Result Structured Output Formatters - Example Usage")
    print("#" * 80)

    example_json_formatter()
    example_csv_formatter()
    example_tsv_formatter()
    example_dataframe_formatter()
    example_format_detection()
    example_advanced_configurations()
    example_real_world_workflow()
    example_error_handling()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
