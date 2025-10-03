"""
Integration example showing text formatters in action.

Demonstrates practical use cases for the TextFormatter, MarkdownFormatter,
and PlainTextFormatter in real-world scenarios.
"""

import sys
from typing import Optional

from sparql_agent.core.types import QueryResult, QueryStatus
from sparql_agent.formatting.text import (
    ANSI,
    MarkdownFormatter,
    PlainTextFormatter,
    TextFormatter,
    VerbosityLevel,
    smart_format,
)


def create_realistic_dbpedia_result() -> QueryResult:
    """Create a realistic result from a DBpedia query."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                'scientist': {'type': 'uri', 'value': 'http://dbpedia.org/resource/Albert_Einstein'},
                'name': {'type': 'literal', 'value': 'Albert Einstein'},
                'birthDate': {'type': 'literal', 'value': '1879-03-14', 'datatype': 'http://www.w3.org/2001/XMLSchema#date'},
                'field': {'type': 'literal', 'value': 'Theoretical Physics'},
                'nobelPrize': {'type': 'literal', 'value': '1921'},
            },
            {
                'scientist': {'type': 'uri', 'value': 'http://dbpedia.org/resource/Marie_Curie'},
                'name': {'type': 'literal', 'value': 'Marie Curie'},
                'birthDate': {'type': 'literal', 'value': '1867-11-07', 'datatype': 'http://www.w3.org/2001/XMLSchema#date'},
                'field': {'type': 'literal', 'value': 'Physics and Chemistry'},
                'nobelPrize': {'type': 'literal', 'value': '1903, 1911'},
            },
            {
                'scientist': {'type': 'uri', 'value': 'http://dbpedia.org/resource/Richard_Feynman'},
                'name': {'type': 'literal', 'value': 'Richard Feynman'},
                'birthDate': {'type': 'literal', 'value': '1918-05-11', 'datatype': 'http://www.w3.org/2001/XMLSchema#date'},
                'field': {'type': 'literal', 'value': 'Theoretical Physics'},
                'nobelPrize': {'type': 'literal', 'value': '1965'},
            },
        ],
        variables=['scientist', 'name', 'birthDate', 'field', 'nobelPrize'],
        row_count=3,
        execution_time=0.456,
        query="""
SELECT ?scientist ?name ?birthDate ?field ?nobelPrize
WHERE {
  ?scientist a dbo:Scientist ;
             rdfs:label ?name ;
             dbo:birthDate ?birthDate ;
             dbo:field ?field ;
             dbo:nobelPrize ?nobelPrize .
  FILTER (lang(?name) = 'en')
}
LIMIT 3
        """.strip(),
        metadata={
            'endpoint': 'https://dbpedia.org/sparql',
            'graph': 'default',
        }
    )


def scenario_1_cli_output():
    """Scenario 1: Command-line tool output for end users."""
    print("=" * 80)
    print("SCENARIO 1: CLI Output for End Users")
    print("=" * 80)
    print("\nUse Case: Interactive terminal tool showing query results to users\n")

    result = create_realistic_dbpedia_result()

    # Use smart format with color support
    print("Using smart_format() with automatic detection:\n")
    output = smart_format(result, force_color=True)
    print(output)

    print("\n" + "-" * 80)
    print("Alternative: PlainTextFormatter with explicit settings:\n")

    formatter = PlainTextFormatter(
        use_color=True,
        table_style='grid',
        max_col_width=40,
        show_row_numbers=False,
        fit_terminal=True,
    )
    print(formatter.format(result))


def scenario_2_documentation_generation():
    """Scenario 2: Generate documentation with query examples."""
    print("\n" + "=" * 80)
    print("SCENARIO 2: Documentation Generation")
    print("=" * 80)
    print("\nUse Case: Generate markdown documentation with query examples\n")

    result = create_realistic_dbpedia_result()

    formatter = MarkdownFormatter(
        include_metadata=True,
        generate_links=True,
        code_blocks_for_uris=True,
    )

    markdown = formatter.format(result)
    print(markdown)

    # Save to file (simulated)
    print("\n# This markdown can be saved to a .md file for documentation")


def scenario_3_api_response():
    """Scenario 3: Human-readable API response."""
    print("\n" + "=" * 80)
    print("SCENARIO 3: Human-Readable API Response")
    print("=" * 80)
    print("\nUse Case: API that returns human-friendly text alongside structured data\n")

    result = create_realistic_dbpedia_result()

    # Compact text format for API
    formatter = TextFormatter(verbosity=VerbosityLevel.NORMAL)
    description = formatter.format(result)

    print("API Response:")
    print("-" * 40)
    print(description)
    print("-" * 40)


def scenario_4_logging():
    """Scenario 4: Structured logging output."""
    print("\n" + "=" * 80)
    print("SCENARIO 4: Structured Logging")
    print("=" * 80)
    print("\nUse Case: Log query results for debugging and monitoring\n")

    result = create_realistic_dbpedia_result()

    # Detailed format with metadata for logs
    formatter = TextFormatter(verbosity=VerbosityLevel.DEBUG)
    log_output = formatter.format(result)

    print("Log Entry:")
    print("-" * 40)
    print(log_output)
    print("-" * 40)


def scenario_5_email_report():
    """Scenario 5: Email report generation."""
    print("\n" + "=" * 80)
    print("SCENARIO 5: Email Report Generation")
    print("=" * 80)
    print("\nUse Case: Generate readable text for email reports\n")

    result = create_realistic_dbpedia_result()

    # Clean text without colors for email
    formatter = TextFormatter(verbosity=VerbosityLevel.DETAILED)
    report = formatter.format(result)

    print("Email Body:")
    print("-" * 40)
    print("Subject: Weekly SPARQL Query Report")
    print()
    print(report)
    print()
    print("Report generated automatically.")
    print("-" * 40)


def scenario_6_jupyter_notebook():
    """Scenario 6: Jupyter notebook display."""
    print("\n" + "=" * 80)
    print("SCENARIO 6: Jupyter Notebook Display")
    print("=" * 80)
    print("\nUse Case: Display results in Jupyter notebook with markdown\n")

    result = create_realistic_dbpedia_result()

    # Rich markdown for notebooks
    formatter = MarkdownFormatter(
        generate_links=True,
        code_blocks_for_uris=True,
        include_metadata=False,  # Usually shown separately in notebooks
    )

    markdown = formatter.format(result)
    print("Markdown for Jupyter:")
    print("-" * 40)
    print(markdown)
    print("-" * 40)
    print("\n# Use IPython.display.Markdown(markdown) to render in notebook")


def scenario_7_github_readme():
    """Scenario 7: Generate README.md examples."""
    print("\n" + "=" * 80)
    print("SCENARIO 7: GitHub README Examples")
    print("=" * 80)
    print("\nUse Case: Create example output for project README\n")

    result = create_realistic_dbpedia_result()

    markdown = f"""## Example Query: Nobel Prize Winners

### Query
```sparql
{result.query}
```

### Results
"""

    formatter = MarkdownFormatter(
        generate_links=True,
        code_blocks_for_uris=True,
        include_metadata=False,
    )

    markdown += formatter.format(result)

    print(markdown)


def scenario_8_error_reporting():
    """Scenario 8: User-friendly error messages."""
    print("\n" + "=" * 80)
    print("SCENARIO 8: Error Reporting")
    print("=" * 80)
    print("\nUse Case: Display query errors in a user-friendly way\n")

    # Create a failed query result
    failed_result = QueryResult(
        status=QueryStatus.FAILED,
        bindings=[],
        variables=[],
        row_count=0,
        error_message="Endpoint connection timeout after 30 seconds",
        query="SELECT * WHERE { ?s ?p ?o }",
        execution_time=30.1,
    )

    formatter = TextFormatter(verbosity=VerbosityLevel.NORMAL)
    error_output = formatter.format(failed_result)

    print("Error Display:")
    print("-" * 40)
    if ANSI.supports_color():
        print(f"{ANSI.RED}{error_output}{ANSI.RESET}")
    else:
        print(error_output)
    print("-" * 40)


def scenario_9_comparison_view():
    """Scenario 9: Side-by-side format comparison."""
    print("\n" + "=" * 80)
    print("SCENARIO 9: Format Comparison")
    print("=" * 80)
    print("\nUse Case: Show same data in different formats\n")

    # Create simpler result for comparison
    simple_result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {'country': {'value': 'Germany'}, 'capital': {'value': 'Berlin'}},
            {'country': {'value': 'France'}, 'capital': {'value': 'Paris'}},
        ],
        variables=['country', 'capital'],
        row_count=2,
        execution_time=0.05,
    )

    print("1. Natural Language (TextFormatter):")
    print("-" * 40)
    text_formatter = TextFormatter(verbosity=VerbosityLevel.MINIMAL)
    print(text_formatter.format(simple_result))

    print("\n2. Markdown Table (MarkdownFormatter):")
    print("-" * 40)
    md_formatter = MarkdownFormatter(include_metadata=False)
    print(md_formatter.format(simple_result))

    print("\n3. ASCII Table (PlainTextFormatter):")
    print("-" * 40)
    plain_formatter = PlainTextFormatter(use_color=False, table_style='grid')
    print(plain_formatter.format(simple_result))


def scenario_10_progress_tracking():
    """Scenario 10: Long-running query progress."""
    print("\n" + "=" * 80)
    print("SCENARIO 10: Progress Tracking")
    print("=" * 80)
    print("\nUse Case: Show progress during query execution\n")

    formatter = PlainTextFormatter(use_color=True)

    print("Simulating query execution with progress updates:\n")

    stages = [
        (10, "Connecting to endpoint"),
        (30, "Parsing query"),
        (50, "Executing query"),
        (75, "Fetching results"),
        (100, "Complete"),
    ]

    for progress, stage in stages:
        bar = formatter.format_progress(progress, 100, prefix=stage)
        print(bar)

    # Show final result
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[{'count': {'value': '1523'}}],
        variables=['count'],
        row_count=1,
        execution_time=2.345,
    )

    print("\n" + "-" * 40)
    print("Final Result:")
    print("-" * 40)
    text_formatter = TextFormatter()
    print(text_formatter.format(result))


def run_all_scenarios():
    """Run all integration scenarios."""
    scenario_1_cli_output()
    scenario_2_documentation_generation()
    scenario_3_api_response()
    scenario_4_logging()
    scenario_5_email_report()
    scenario_6_jupyter_notebook()
    scenario_7_github_readme()
    scenario_8_error_reporting()
    scenario_9_comparison_view()
    scenario_10_progress_tracking()

    print("\n" + "=" * 80)
    print("All integration scenarios completed!")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario_num = sys.argv[1]
        scenario_func = f"scenario_{scenario_num}"

        if scenario_func in globals():
            globals()[scenario_func]()
        else:
            print(f"Unknown scenario: {scenario_num}")
            print("Available scenarios:")
            for i in range(1, 11):
                print(f"  {i} - {globals()[f'scenario_{i}'].__doc__.split(':')[1].strip()}")
    else:
        run_all_scenarios()
