"""
Example usage of the Interactive SPARQL Query Builder.

This module demonstrates how to use the interactive shell programmatically
and provides usage examples.
"""

from pathlib import Path
from .interactive import InteractiveShell


def example_basic_usage():
    """
    Basic usage example of the interactive shell.

    Example:
        >>> from sparql_agent.cli.interactive_example import example_basic_usage
        >>> example_basic_usage()
    """
    # Create shell instance
    shell = InteractiveShell()

    # Start interactive session
    shell.run()


def example_with_custom_config():
    """
    Example with custom configuration.

    Example:
        >>> from sparql_agent.cli.interactive_example import example_with_custom_config
        >>> example_with_custom_config()
    """
    # Set up custom paths
    config_dir = Path.home() / ".my_sparql_agent"
    history_file = config_dir / "my_history.txt"

    # Create shell with custom config
    shell = InteractiveShell(
        history_file=history_file,
        config_dir=config_dir
    )

    # Start session
    shell.run()


def example_commands():
    """
    Example interactive commands and their outputs.

    This function demonstrates the available commands without actually
    running the interactive shell.
    """
    examples = """
    Interactive SPARQL Query Builder - Command Examples
    ====================================================

    1. Connect to Wikidata:
       sparql> .connect https://query.wikidata.org/sparql

    2. Run a simple query:
       sparql> SELECT * WHERE { ?s ?p ?o } LIMIT 10

    3. Search for ontology terms:
       sparql> .ontology diabetes

       Results will show:
       - Term IDs (e.g., MONDO:0005015)
       - Labels (e.g., "diabetes mellitus")
       - Ontology sources (e.g., MONDO, EFO)
       - Descriptions

    4. View schema information:
       sparql> .schema classes

       Shows the most common classes in the endpoint with instance counts.

    5. List properties:
       sparql> .schema properties

       Shows the most frequently used properties.

    6. View example queries:
       sparql> .examples

       Displays:
       - Basic queries
       - Aggregation examples
       - Filtering patterns
       - OPTIONAL clause usage

    7. Check query history:
       sparql> .history

       Shows last 20 queries with:
       - Query text
       - Status (OK/FAIL)
       - Number of results

    8. Export results:
       sparql> .export json results.json
       sparql> .export csv results.csv
       sparql> .export table

    9. View endpoint capabilities:
       sparql> .capabilities

       Shows:
       - SPARQL version
       - Number of named graphs
       - Available namespaces
       - Supported features

    10. List common endpoints:
        sparql> .endpoints

        Shows configured endpoints:
        - Wikidata
        - DBpedia
        - UniProt
        - EBI RDF Platform

    11. Save session:
        sparql> .save my_session.json

    12. Load session:
        sparql> .load my_session.json

    13. Set variables:
        sparql> .set limit 100

    14. View session info:
        sparql> .info

        Shows:
        - Current endpoint
        - Current ontology
        - Number of queries executed
        - Last result count
        - Config directories

    15. Multi-line query:
        sparql> SELECT ?person ?name ?birth
        ....... WHERE {
        ....... ?person a dbo:Person .
        ....... ?person foaf:name ?name .
        ....... OPTIONAL { ?person dbo:birthDate ?birth }
        ....... }
        ....... LIMIT 10
        (Press Enter on empty line to execute)

    16. Get help:
        sparql> .help
        sparql> .help connect

    17. Clear screen:
        sparql> .clear

    18. Exit:
        sparql> .quit
        or press Ctrl+D


    Features:
    =========

    ✓ Syntax Highlighting
      - SPARQL keywords in color
      - Variables highlighted
      - URIs and literals formatted

    ✓ Auto-completion
      - Press TAB for SPARQL keyword completion
      - Variable completion for defined variables

    ✓ Query History
      - Press UP/DOWN to navigate history
      - History persisted across sessions
      - Search history with Ctrl+R

    ✓ Beautiful Output
      - Results displayed in formatted tables
      - Execution time shown
      - Row counts displayed
      - Paging for large result sets

    ✓ Error Handling
      - Clear error messages
      - Helpful suggestions
      - Query validation

    ✓ Session Management
      - Save/load sessions
      - Persistent configuration
      - Variable storage


    Example Session:
    ================

    $ sparql-agent interactive

    ╭─────────────────────────────────────────────────────────────╮
    │ SPARQL Agent - Interactive Query Builder                   │
    │ Version 0.1.0                                              │
    │                                                            │
    │ Type .help for available commands                          │
    │ Type .quit or press Ctrl+D to exit                        │
    │ Use .connect <endpoint> to connect to a SPARQL endpoint   │
    ╰─────────────────────────────────────────────────────────────╯

    sparql> .connect https://query.wikidata.org/sparql
    ⠋ Connecting to https://query.wikidata.org/sparql...
    ✓ Connected to: https://query.wikidata.org/sparql

    ╭─────────────────────────────────────────────────────────────╮
    │ Endpoint Capabilities                                       │
    ├─────────────────────────────────────────────────────────────┤
    │ SPARQL Version    │ 1.1                                    │
    │ Named Graphs      │ 15                                      │
    │ Namespaces        │ 42                                      │
    │ Supported Features│ UNION, OPTIONAL, FILTER, BIND, SERVICE │
    ╰─────────────────────────────────────────────────────────────╯

    sparql> SELECT ?person ?personLabel WHERE {
    ....... ?person wdt:P31 wd:Q5 .
    ....... ?person wdt:P106 wd:Q82955 .
    ....... SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    ....... } LIMIT 10

    ╭─────────────────────────────────────────────────────────────╮
    │ Executing Query                                            │
    ├─────────────────────────────────────────────────────────────┤
    │ SELECT ?person ?personLabel WHERE {                        │
    │   ?person wdt:P31 wd:Q5 .                                 │
    │   ?person wdt:P106 wd:Q82955 .                            │
    │   SERVICE wikibase:label {                                 │
    │     bd:serviceParam wikibase:language "en".               │
    │   }                                                        │
    │ } LIMIT 10                                                 │
    ╰─────────────────────────────────────────────────────────────╯

    ⠋ Executing query...

    ╭─────────────────────────────────────────────────────────────╮
    │ Query Results (10 rows in 0.34s)                           │
    ├─────────────────────────┬───────────────────────────────────┤
    │ person                  │ personLabel                       │
    ├─────────────────────────┼───────────────────────────────────┤
    │ http://www.wikidata.o...│ Marie Curie                       │
    │ http://www.wikidata.o...│ Albert Einstein                   │
    │ http://www.wikidata.o...│ Isaac Newton                      │
    │ ...                     │ ...                               │
    ╰─────────────────────────┴───────────────────────────────────╯

    Execution time: 0.342s

    sparql> .ontology cancer
    ⠋ Searching ontologies for 'cancer'...

    ╭─────────────────────────────────────────────────────────────╮
    │ Ontology Search Results: 'cancer'                          │
    ├──────────┬──────────────┬──────────┬──────────────────────┤
    │ ID       │ Label        │ Ontology │ Description          │
    ├──────────┼──────────────┼──────────┼──────────────────────┤
    │ MONDO:...│ malignant... │ mondo    │ A tumor composed ... │
    │ DOID:... │ cancer       │ doid     │ A disease of cell... │
    │ EFO:...  │ cancer       │ efo      │ A tumor character... │
    ╰──────────┴──────────────┴──────────┴──────────────────────╯

    sparql> .quit

    Goodbye!
    """

    print(examples)


if __name__ == '__main__':
    # Run the examples
    example_commands()
