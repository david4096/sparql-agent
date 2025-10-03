"""
Examples demonstrating the text formatting module.

This module provides comprehensive examples of using the TextFormatter,
MarkdownFormatter, and PlainTextFormatter classes to create human-readable
output from SPARQL query results.
"""

import sys
from typing import List

from sparql_agent.core.types import QueryResult, QueryStatus
from sparql_agent.formatting.text import (
    ANSI,
    ColorScheme,
    MarkdownFormatter,
    PlainTextFormatter,
    TextFormatter,
    TextFormatterConfig,
    VerbosityLevel,
    format_as_markdown,
    format_as_table,
    format_as_text,
    smart_format,
)


def create_sample_results() -> List[QueryResult]:
    """Create various sample query results for testing."""
    results = []

    # 1. Simple list result
    results.append(QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {'label': {'type': 'literal', 'value': 'Apple'}},
            {'label': {'type': 'literal', 'value': 'Banana'}},
            {'label': {'type': 'literal', 'value': 'Cherry'}},
            {'label': {'type': 'literal', 'value': 'Date'}},
        ],
        variables=['label'],
        row_count=4,
        execution_time=0.045,
        query="SELECT ?label WHERE { ?fruit rdfs:label ?label . }",
    ))

    # 2. Count result
    results.append(QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {'count': {'type': 'literal', 'value': '1523'}},
        ],
        variables=['count'],
        row_count=1,
        execution_time=0.892,
    ))

    # 3. Multi-column tabular result
    results.append(QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                'name': {'type': 'literal', 'value': 'Albert Einstein'},
                'born': {'type': 'literal', 'value': '1879'},
                'field': {'type': 'literal', 'value': 'Physics'},
                'uri': {'type': 'uri', 'value': 'http://dbpedia.org/resource/Albert_Einstein'},
            },
            {
                'name': {'type': 'literal', 'value': 'Marie Curie'},
                'born': {'type': 'literal', 'value': '1867'},
                'field': {'type': 'literal', 'value': 'Chemistry'},
                'uri': {'type': 'uri', 'value': 'http://dbpedia.org/resource/Marie_Curie'},
            },
            {
                'name': {'type': 'literal', 'value': 'Isaac Newton'},
                'born': {'type': 'literal', 'value': '1643'},
                'field': {'type': 'literal', 'value': 'Physics'},
                'uri': {'type': 'uri', 'value': 'http://dbpedia.org/resource/Isaac_Newton'},
            },
        ],
        variables=['name', 'born', 'field', 'uri'],
        row_count=3,
        execution_time=0.234,
        metadata={'endpoint': 'DBpedia', 'graph': 'default'},
    ))

    # 4. Empty result
    results.append(QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[],
        variables=['subject', 'predicate', 'object'],
        row_count=0,
        execution_time=0.012,
    ))

    # 5. Large result (truncation test)
    large_bindings = []
    for i in range(150):
        large_bindings.append({
            'id': {'type': 'literal', 'value': f'item_{i:03d}'},
            'value': {'type': 'literal', 'value': str(i * 100)},
        })

    results.append(QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=large_bindings,
        variables=['id', 'value'],
        row_count=150,
        execution_time=1.456,
    ))

    return results


def example_text_formatter_basic():
    """Basic TextFormatter usage with different verbosity levels."""
    print("=" * 80)
    print("EXAMPLE 1: TextFormatter - Basic Usage")
    print("=" * 80)

    results = create_sample_results()
    result = results[2]  # Multi-column result

    print("\n--- Verbosity: MINIMAL ---")
    formatter = TextFormatter(verbosity=VerbosityLevel.MINIMAL)
    print(formatter.format(result))

    print("\n--- Verbosity: NORMAL (default) ---")
    formatter = TextFormatter(verbosity=VerbosityLevel.NORMAL)
    print(formatter.format(result))

    print("\n--- Verbosity: DETAILED ---")
    formatter = TextFormatter(verbosity=VerbosityLevel.DETAILED)
    print(formatter.format(result))

    print("\n--- Verbosity: DEBUG ---")
    formatter = TextFormatter(verbosity=VerbosityLevel.DEBUG)
    print(formatter.format(result))


def example_text_formatter_query_types():
    """Demonstrate context-aware formatting for different query types."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: TextFormatter - Query Type Detection")
    print("=" * 80)

    results = create_sample_results()
    formatter = TextFormatter(verbosity=VerbosityLevel.NORMAL)

    print("\n--- List Query (single column) ---")
    print(formatter.format(results[0]))

    print("\n--- Count Query ---")
    print(formatter.format(results[1]))

    print("\n--- Tabular Query (multi-column) ---")
    print(formatter.format(results[2]))

    print("\n--- Empty Result ---")
    print(formatter.format(results[3]))


def example_text_formatter_configuration():
    """Advanced configuration options."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: TextFormatter - Configuration Options")
    print("=" * 80)

    result = create_sample_results()[2]

    # Custom configuration
    config = TextFormatterConfig(
        verbosity=VerbosityLevel.NORMAL,
        show_metadata=True,
        human_numbers=True,
        truncate_uris=True,
        uri_display="short",
    )

    formatter = TextFormatter(config=config)

    print("\n--- With Custom Configuration ---")
    print(formatter.format(result))

    # Change URI display mode
    print("\n--- URI Display: Full ---")
    config.uri_display = "full"
    formatter = TextFormatter(config=config)
    print(formatter.format(result))

    print("\n--- URI Display: Label ---")
    config.uri_display = "label"
    formatter = TextFormatter(config=config)
    print(formatter.format(result))


def example_markdown_formatter():
    """MarkdownFormatter examples."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: MarkdownFormatter - GitHub-Compatible Output")
    print("=" * 80)

    results = create_sample_results()

    print("\n--- Basic Markdown Table ---")
    formatter = MarkdownFormatter()
    print(formatter.format(results[2]))

    print("\n--- Markdown with Row Limit ---")
    formatter = MarkdownFormatter(max_rows=2, include_metadata=False)
    print(formatter.format(results[4]))

    print("\n--- Markdown with Links and Code Blocks ---")
    formatter = MarkdownFormatter(
        generate_links=True,
        code_blocks_for_uris=True,
    )
    print(formatter.format(results[2]))

    print("\n--- Markdown without Links ---")
    formatter = MarkdownFormatter(
        generate_links=False,
        code_blocks_for_uris=True,
    )
    print(formatter.format(results[2]))


def example_plain_text_formatter():
    """PlainTextFormatter examples with different styles."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: PlainTextFormatter - ASCII Tables")
    print("=" * 80)

    result = create_sample_results()[2]

    print("\n--- Table Style: Grid (default) ---")
    formatter = PlainTextFormatter(
        use_color=False,
        table_style="grid"
    )
    print(formatter.format(result))

    print("\n--- Table Style: Simple ---")
    formatter = PlainTextFormatter(
        use_color=False,
        table_style="simple"
    )
    print(formatter.format(result))

    print("\n--- Table Style: Minimal ---")
    formatter = PlainTextFormatter(
        use_color=False,
        table_style="minimal"
    )
    print(formatter.format(result))

    print("\n--- With Row Numbers ---")
    formatter = PlainTextFormatter(
        use_color=False,
        table_style="grid",
        show_row_numbers=True
    )
    print(formatter.format(result))


def example_plain_text_with_color():
    """PlainTextFormatter with color support."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: PlainTextFormatter - Color Support")
    print("=" * 80)

    result = create_sample_results()[2]

    if ANSI.supports_color():
        print("\n--- With ANSI Colors ---")
        formatter = PlainTextFormatter(
            use_color=True,
            color_scheme=ColorScheme.BASIC,
            table_style="grid"
        )
        print(formatter.format(result))
    else:
        print("\nTerminal does not support ANSI colors.")
        print("Color output is automatically disabled.")

        formatter = PlainTextFormatter(
            use_color=False,
            table_style="grid"
        )
        print(formatter.format(result))


def example_progress_indicator():
    """Progress indicator demonstration."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: PlainTextFormatter - Progress Indicators")
    print("=" * 80)

    formatter = PlainTextFormatter()

    print("\n--- Progress Examples ---")
    for i in [0, 25, 50, 75, 100]:
        print(formatter.format_progress(i, 100, prefix="Processing"))

    print("\n--- With Custom Prefix ---")
    print(formatter.format_progress(42, 100, prefix="Download"))
    print(formatter.format_progress(87, 100, prefix="Upload"))


def example_convenience_functions():
    """Convenience function examples."""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Convenience Functions")
    print("=" * 80)

    result = create_sample_results()[2]

    print("\n--- format_as_text() ---")
    text = format_as_text(result, verbosity="normal", show_metadata=True)
    print(text)

    print("\n--- format_as_markdown() ---")
    markdown = format_as_markdown(result, max_rows=5, include_metadata=False)
    print(markdown)

    print("\n--- format_as_table() ---")
    table = format_as_table(result, use_color=False, table_style="grid")
    print(table)


def example_smart_format():
    """Smart formatting that adapts to content."""
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Smart Format (Auto-Detection)")
    print("=" * 80)

    results = create_sample_results()

    print("\n--- Small Result (uses natural language) ---")
    print(smart_format(results[1]))

    print("\n--- Medium Result (uses table) ---")
    print(smart_format(results[2]))

    print("\n--- Large Result (adaptive) ---")
    output = smart_format(results[4])
    print(output[:500] + "...\n[Output truncated for display]")


def example_error_handling():
    """Error and edge case handling."""
    print("\n" + "=" * 80)
    print("EXAMPLE 10: Error Handling and Edge Cases")
    print("=" * 80)

    # Failed query
    print("\n--- Failed Query ---")
    failed_result = QueryResult(
        status=QueryStatus.FAILED,
        bindings=[],
        variables=[],
        row_count=0,
        error_message="Connection timeout to endpoint"
    )

    formatter = TextFormatter()
    print(formatter.format(failed_result))

    # Empty result
    print("\n--- Empty Result ---")
    empty_result = create_sample_results()[3]
    print(formatter.format(empty_result))

    # Result with missing values
    print("\n--- Result with Missing Values ---")
    sparse_result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {'a': {'type': 'literal', 'value': '1'}, 'b': {'type': 'literal', 'value': 'x'}},
            {'a': {'type': 'literal', 'value': '2'}},  # Missing 'b'
            {'b': {'type': 'literal', 'value': 'z'}},  # Missing 'a'
        ],
        variables=['a', 'b'],
        row_count=3,
        execution_time=0.05
    )

    plain_formatter = PlainTextFormatter(use_color=False)
    print(plain_formatter.format(sparse_result))


def example_column_width_handling():
    """Column width and truncation handling."""
    print("\n" + "=" * 80)
    print("EXAMPLE 11: Column Width and Truncation")
    print("=" * 80)

    # Long values
    long_result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                'short': {'type': 'literal', 'value': 'ABC'},
                'long': {'type': 'literal', 'value': 'This is a very long text value that should be truncated when displayed in a table format'},
                'uri': {'type': 'uri', 'value': 'http://example.org/resource/with/a/very/long/path/that/goes/on/and/on'},
            },
        ],
        variables=['short', 'long', 'uri'],
        row_count=1,
        execution_time=0.01
    )

    print("\n--- Default Column Width ---")
    formatter = PlainTextFormatter(use_color=False, table_style="grid")
    print(formatter.format(long_result))

    print("\n--- Custom Max Column Width ---")
    formatter = PlainTextFormatter(
        use_color=False,
        table_style="grid",
        max_col_width=30
    )
    print(formatter.format(long_result))


def example_comparison():
    """Side-by-side comparison of all formatters."""
    print("\n" + "=" * 80)
    print("EXAMPLE 12: Formatter Comparison")
    print("=" * 80)

    result = create_sample_results()[2]

    print("\n--- TextFormatter (Natural Language) ---")
    text_formatter = TextFormatter(verbosity=VerbosityLevel.NORMAL)
    print(text_formatter.format(result))

    print("\n--- MarkdownFormatter (GitHub-Compatible) ---")
    md_formatter = MarkdownFormatter(include_metadata=False)
    print(md_formatter.format(result))

    print("\n--- PlainTextFormatter (Terminal Table) ---")
    plain_formatter = PlainTextFormatter(use_color=False, table_style="grid")
    print(plain_formatter.format(result))


def run_all_examples():
    """Run all examples."""
    example_text_formatter_basic()
    example_text_formatter_query_types()
    example_text_formatter_configuration()
    example_markdown_formatter()
    example_plain_text_formatter()
    example_plain_text_with_color()
    example_progress_indicator()
    example_convenience_functions()
    example_smart_format()
    example_error_handling()
    example_column_width_handling()
    example_comparison()

    print("\n" + "=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        example_func = f"example_{example_num}"

        if example_func in globals():
            globals()[example_func]()
        else:
            print(f"Unknown example: {example_num}")
            print("Available examples:")
            print("  text_formatter_basic")
            print("  text_formatter_query_types")
            print("  text_formatter_configuration")
            print("  markdown_formatter")
            print("  plain_text_formatter")
            print("  plain_text_with_color")
            print("  progress_indicator")
            print("  convenience_functions")
            print("  smart_format")
            print("  error_handling")
            print("  column_width_handling")
            print("  comparison")
    else:
        run_all_examples()
