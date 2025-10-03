"""
Interactive SPARQL Query Builder CLI.

This module provides a rich, interactive terminal interface for building and executing
SPARQL queries with features like auto-completion, syntax highlighting, history
management, and beautiful output formatting.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, WordCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.lexers import PygmentsLexer
    from prompt_toolkit.styles import Style
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.formatted_text import HTML
    from pygments.lexers.rdf import SparqlLexer
except ImportError:
    print("Error: prompt_toolkit is required for interactive mode.")
    print("Install with: pip install prompt-toolkit")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
except ImportError:
    print("Error: rich is required for interactive mode.")
    print("Install with: pip install rich")
    sys.exit(1)

from ..execution.executor import QueryExecutor as SPARQLExecutor
from ..core.types import EndpointInfo, QueryResult
from ..schema.schema_inference import SchemaInferencer
from ..ontology.ols_client import OLSClient, list_common_ontologies
from ..discovery.capabilities import CapabilitiesDetector
from ..core.exceptions import SPARQLAgentError


# SPARQL Keywords for auto-completion
SPARQL_KEYWORDS = [
    "SELECT", "DISTINCT", "REDUCED", "CONSTRUCT", "DESCRIBE", "ASK",
    "FROM", "FROM NAMED", "WHERE", "ORDER BY", "GROUP BY", "HAVING",
    "LIMIT", "OFFSET", "VALUES", "OPTIONAL", "UNION", "MINUS",
    "GRAPH", "SERVICE", "BIND", "FILTER", "EXISTS", "NOT EXISTS",
    "AS", "a", "PREFIX", "BASE",
    # Functions
    "COUNT", "SUM", "MIN", "MAX", "AVG", "SAMPLE", "GROUP_CONCAT",
    "STR", "LANG", "LANGMATCHES", "DATATYPE", "BOUND", "IRI", "URI",
    "BNODE", "RAND", "ABS", "CEIL", "FLOOR", "ROUND", "STRLEN",
    "SUBSTR", "UCASE", "LCASE", "STRSTARTS", "STRENDS", "CONTAINS",
    "STRBEFORE", "STRAFTER", "ENCODE_FOR_URI", "CONCAT", "REPLACE",
    "REGEX", "IF", "COALESCE", "IN", "NOT IN",
    # Operators
    "AND", "OR", "NOT", "true", "false",
]


@dataclass
class SessionState:
    """State management for interactive session."""
    current_endpoint: Optional[str] = None
    current_ontology: Optional[str] = None
    query_history: List[Tuple[str, QueryResult]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    last_result: Optional[QueryResult] = None
    schema_cache: Dict[str, Any] = field(default_factory=dict)
    endpoint_capabilities: Dict[str, Any] = field(default_factory=dict)


class SPARQLCompleter(Completer):
    """Smart auto-completer for SPARQL queries."""

    def __init__(self, session_state: SessionState):
        self.session_state = session_state
        self.keyword_completer = WordCompleter(
            SPARQL_KEYWORDS,
            ignore_case=True,
            sentence=True
        )

    def get_completions(self, document, complete_event):
        """Generate completions based on context."""
        text = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)

        # Keyword completion
        if word and word[0].isupper():
            for completion in self.keyword_completer.get_completions(document, complete_event):
                yield completion

        # Variable completion (starts with ?)
        elif word.startswith('?'):
            variables = self._extract_variables(text)
            for var in variables:
                if var.startswith(word):
                    yield Completion(var, start_position=-len(word))

        # Prefix completion
        elif ':' in word:
            # Could suggest known prefixes/URIs
            pass


    def _extract_variables(self, text: str) -> Set[str]:
        """Extract all variables from query text."""
        import re
        return set(re.findall(r'\?[a-zA-Z0-9_]+', text))


class InteractiveShell:
    """
    Interactive SPARQL query builder shell with rich terminal UI.

    Features:
    - Rich terminal interface with syntax highlighting
    - Auto-completion for SPARQL keywords
    - Multi-line query editing
    - History management
    - Query result paging
    - Quick endpoint switching
    - Save/load sessions

    Example:
        >>> shell = InteractiveShell()
        >>> shell.run()
    """

    def __init__(
        self,
        history_file: Optional[Path] = None,
        config_dir: Optional[Path] = None
    ):
        """
        Initialize interactive shell.

        Args:
            history_file: Path to history file (default: ~/.sparql_agent_history)
            config_dir: Configuration directory (default: ~/.sparql_agent)
        """
        self.console = Console()
        self.state = SessionState()

        # Setup paths
        home = Path.home()
        self.config_dir = config_dir or home / ".sparql_agent"
        self.config_dir.mkdir(exist_ok=True)

        self.history_file = history_file or self.config_dir / "history.txt"
        self.session_file = self.config_dir / "last_session.json"

        # Initialize prompt session
        self.session = PromptSession(
            history=FileHistory(str(self.history_file)),
            completer=SPARQLCompleter(self.state),
            lexer=PygmentsLexer(SparqlLexer),
            style=self._create_style(),
            multiline=True,
            enable_history_search=True,
        )

        # Initialize clients
        self.executor: Optional[SPARQLExecutor] = None
        self.ols_client = OLSClient()

        # Command registry
        self.commands = {
            '.connect': self._cmd_connect,
            '.schema': self._cmd_schema,
            '.examples': self._cmd_examples,
            '.ontology': self._cmd_ontology,
            '.help': self._cmd_help,
            '.quit': self._cmd_quit,
            '.exit': self._cmd_quit,
            '.clear': self._cmd_clear,
            '.history': self._cmd_history,
            '.save': self._cmd_save,
            '.load': self._cmd_load,
            '.endpoints': self._cmd_endpoints,
            '.capabilities': self._cmd_capabilities,
            '.info': self._cmd_info,
            '.export': self._cmd_export,
            '.set': self._cmd_set,
        }

    def _create_style(self) -> Style:
        """Create prompt_toolkit style."""
        return Style.from_dict({
            'prompt': '#00aa00 bold',
            'continuation': '#00aa00',
        })

    def run(self):
        """Start the interactive shell."""
        self._print_banner()

        # Try to load last session
        if self.session_file.exists():
            try:
                self._load_session(str(self.session_file))
                self.console.print("[dim]Loaded previous session[/dim]\n")
            except:
                pass

        # Main loop
        while True:
            try:
                # Get input
                text = self.session.prompt(
                    HTML('<prompt>sparql></prompt> '),
                    multiline=True,
                )

                if not text.strip():
                    continue

                # Process input
                self._process_input(text.strip())

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")

        # Save session on exit
        self._save_session(str(self.session_file))
        self._print_goodbye()

    def _print_banner(self):
        """Print welcome banner."""
        banner = """
[bold cyan]SPARQL Agent - Interactive Query Builder[/bold cyan]
[dim]Version 0.1.0[/dim]

Type [yellow].help[/yellow] for available commands
Type [yellow].quit[/yellow] or press Ctrl+D to exit
Use [yellow].connect <endpoint>[/yellow] to connect to a SPARQL endpoint
"""
        self.console.print(Panel(banner.strip(), border_style="cyan"))
        self.console.print()

    def _print_goodbye(self):
        """Print goodbye message."""
        self.console.print("\n[cyan]Goodbye![/cyan]")

    def _process_input(self, text: str):
        """Process user input."""
        # Check if it's a command
        if text.startswith('.'):
            parts = text.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if command in self.commands:
                self.commands[command](args)
            else:
                self.console.print(f"[red]Unknown command: {command}[/red]")
                self.console.print("Type [yellow].help[/yellow] for available commands")
        else:
            # Execute as SPARQL query
            self._execute_query(text)

    # ========================================================================
    # Commands
    # ========================================================================

    def _cmd_connect(self, args: str):
        """Connect to a SPARQL endpoint."""
        if not args:
            self.console.print("[yellow]Usage: .connect <endpoint_url>[/yellow]")
            self.console.print("Example: .connect https://query.wikidata.org/sparql")
            return

        endpoint = args.strip()

        with self.console.status(f"[cyan]Connecting to {endpoint}...[/cyan]"):
            try:
                # Test connection
                self.executor = SPARQLExecutor(timeout=30)
                test_result = self.executor.execute(
                    "SELECT * WHERE { ?s ?p ?o } LIMIT 1",
                    EndpointInfo(url=endpoint)
                )

                if test_result.is_success:
                    self.state.current_endpoint = endpoint
                    self.console.print(f"[green]Connected to: {endpoint}[/green]")

                    # Discover capabilities
                    self._discover_capabilities(endpoint)
                else:
                    self.console.print(f"[red]Connection failed: {test_result.error_message}[/red]")
            except Exception as e:
                self.console.print(f"[red]Connection failed: {e}[/red]")

    def _cmd_schema(self, args: str):
        """Display schema information."""
        if not self.state.current_endpoint:
            self.console.print("[yellow]No endpoint connected. Use .connect first[/yellow]")
            return

        parts = args.split() if args else []
        schema_type = parts[0] if parts else None
        search_term = parts[1] if len(parts) > 1 else None

        if not schema_type:
            # Show available schema info
            self._show_schema_summary()
        elif schema_type == "class" or schema_type == "classes":
            self._show_classes(search_term)
        elif schema_type == "property" or schema_type == "properties":
            self._show_properties(search_term)
        else:
            self.console.print(f"[yellow]Usage: .schema [class|property] [search_term][/yellow]")

    def _cmd_examples(self, args: str):
        """Show example queries."""
        topic = args.strip() if args else None

        examples = self._get_example_queries(topic)

        if not examples:
            self.console.print("[yellow]No examples available for this topic[/yellow]")
            return

        table = Table(title="Example Queries", box=box.ROUNDED)
        table.add_column("Topic", style="cyan")
        table.add_column("Query", style="white")
        table.add_column("Description", style="dim")

        for ex in examples:
            table.add_row(ex['topic'], ex['query'], ex['description'])

        self.console.print(table)

    def _cmd_ontology(self, args: str):
        """Search ontologies."""
        if not args:
            # List common ontologies
            self._list_ontologies()
            return

        search_term = args.strip()

        with self.console.status(f"[cyan]Searching ontologies for '{search_term}'...[/cyan]"):
            try:
                results = self.ols_client.search(search_term, limit=10)

                if not results:
                    self.console.print(f"[yellow]No results found for '{search_term}'[/yellow]")
                    return

                table = Table(title=f"Ontology Search Results: '{search_term}'", box=box.ROUNDED)
                table.add_column("ID", style="cyan")
                table.add_column("Label", style="white")
                table.add_column("Ontology", style="yellow")
                table.add_column("Description", style="dim", max_width=50)

                for result in results:
                    table.add_row(
                        result.get('id', 'N/A'),
                        result.get('label', 'N/A'),
                        result.get('ontology', 'N/A'),
                        (result.get('description', '')[:100] + '...') if result.get('description') else 'N/A'
                    )

                self.console.print(table)

            except Exception as e:
                self.console.print(f"[red]Search failed: {e}[/red]")

    def _cmd_help(self, args: str):
        """Show help information."""
        if args:
            # Show help for specific command
            command = f".{args}" if not args.startswith('.') else args
            if command in self.commands:
                self._show_command_help(command)
            else:
                self.console.print(f"[red]Unknown command: {command}[/red]")
            return

        # Show all commands
        help_text = """
[bold cyan]Available Commands:[/bold cyan]

[yellow]Connection:[/yellow]
  .connect <url>          - Connect to a SPARQL endpoint
  .endpoints              - List configured endpoints
  .capabilities           - Show endpoint capabilities

[yellow]Schema & Discovery:[/yellow]
  .schema [type] [term]   - Display schema information
                            Types: class, property
  .examples [topic]       - Show example queries
  .ontology [term]        - Search ontologies (NEW)

[yellow]Query Execution:[/yellow]
  Write SPARQL query and press Enter (multi-line supported)
  Use Ctrl+J for new line without executing

[yellow]Session Management:[/yellow]
  .history                - Show query history
  .save [file]            - Save current session
  .load [file]            - Load saved session
  .clear                  - Clear screen
  .set <var> <value>      - Set session variable

[yellow]Results & Export:[/yellow]
  .export <format> [file] - Export last results (json, csv, table)
  .info                   - Show session information

[yellow]General:[/yellow]
  .help [command]         - Show help (for specific command)
  .quit / .exit           - Exit the shell

[bold cyan]Tips:[/bold cyan]
- Use TAB for auto-completion of SPARQL keywords
- Use UP/DOWN arrows to navigate history
- Multi-line queries: Press Enter on empty line to execute
"""
        self.console.print(Panel(help_text.strip(), border_style="cyan"))

    def _cmd_quit(self, args: str):
        """Exit the shell."""
        raise EOFError()

    def _cmd_clear(self, args: str):
        """Clear the screen."""
        self.console.clear()

    def _cmd_history(self, args: str):
        """Show query history."""
        if not self.state.query_history:
            self.console.print("[yellow]No query history yet[/yellow]")
            return

        table = Table(title="Query History", box=box.ROUNDED)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Query", style="white", max_width=60)
        table.add_column("Status", style="white", width=10)
        table.add_column("Results", style="yellow", width=8)

        for i, (query, result) in enumerate(self.state.query_history[-20:], 1):
            status = "[green]OK[/green]" if result.is_success else "[red]FAIL[/red]"
            table.add_row(
                str(i),
                query[:60] + "..." if len(query) > 60 else query,
                status,
                str(result.row_count) if result.is_success else "0"
            )

        self.console.print(table)

    def _cmd_save(self, args: str):
        """Save current session."""
        filename = args.strip() or str(self.session_file)
        try:
            self._save_session(filename)
            self.console.print(f"[green]Session saved to: {filename}[/green]")
        except Exception as e:
            self.console.print(f"[red]Failed to save session: {e}[/red]")

    def _cmd_load(self, args: str):
        """Load saved session."""
        filename = args.strip() or str(self.session_file)
        try:
            self._load_session(filename)
            self.console.print(f"[green]Session loaded from: {filename}[/green]")
        except Exception as e:
            self.console.print(f"[red]Failed to load session: {e}[/red]")

    def _cmd_endpoints(self, args: str):
        """List configured endpoints."""
        # Show common endpoints
        endpoints = {
            "Wikidata": "https://query.wikidata.org/sparql",
            "DBpedia": "https://dbpedia.org/sparql",
            "UniProt": "https://sparql.uniprot.org/sparql",
            "EBI RDF Platform": "https://www.ebi.ac.uk/rdf/services/sparql",
        }

        table = Table(title="Common SPARQL Endpoints", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("URL", style="white")
        table.add_column("Status", style="yellow")

        for name, url in endpoints.items():
            status = "[green]Connected[/green]" if url == self.state.current_endpoint else ""
            table.add_row(name, url, status)

        self.console.print(table)

    def _cmd_capabilities(self, args: str):
        """Show endpoint capabilities."""
        if not self.state.current_endpoint:
            self.console.print("[yellow]No endpoint connected. Use .connect first[/yellow]")
            return

        if self.state.current_endpoint in self.state.endpoint_capabilities:
            caps = self.state.endpoint_capabilities[self.state.current_endpoint]
            self._display_capabilities(caps)
        else:
            self._discover_capabilities(self.state.current_endpoint)

    def _cmd_info(self, args: str):
        """Show session information."""
        info = f"""
[bold cyan]Session Information[/bold cyan]

[yellow]Endpoint:[/yellow] {self.state.current_endpoint or 'Not connected'}
[yellow]Ontology:[/yellow] {self.state.current_ontology or 'None'}
[yellow]Queries executed:[/yellow] {len(self.state.query_history)}
[yellow]Last result:[/yellow] {self.state.last_result.row_count if self.state.last_result else 0} rows
[yellow]Config directory:[/yellow] {self.config_dir}
[yellow]History file:[/yellow] {self.history_file}
"""
        self.console.print(Panel(info.strip(), border_style="cyan"))

    def _cmd_export(self, args: str):
        """Export last results."""
        if not self.state.last_result or not self.state.last_result.is_success:
            self.console.print("[yellow]No results to export[/yellow]")
            return

        parts = args.split()
        format_type = parts[0] if parts else "json"
        filename = parts[1] if len(parts) > 1 else None

        try:
            output = self._format_results(self.state.last_result, format_type)

            if filename:
                Path(filename).write_text(output)
                self.console.print(f"[green]Results exported to: {filename}[/green]")
            else:
                self.console.print(output)
        except Exception as e:
            self.console.print(f"[red]Export failed: {e}[/red]")

    def _cmd_set(self, args: str):
        """Set session variable."""
        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            self.console.print("[yellow]Usage: .set <variable> <value>[/yellow]")
            return

        var_name, value = parts
        self.state.variables[var_name] = value
        self.console.print(f"[green]Set {var_name} = {value}[/green]")

    # ========================================================================
    # Query Execution
    # ========================================================================

    def _execute_query(self, query: str):
        """Execute a SPARQL query."""
        if not self.state.current_endpoint:
            self.console.print("[yellow]No endpoint connected. Use .connect <url> first[/yellow]")
            return

        # Show query with syntax highlighting
        syntax = Syntax(query, "sparql", theme="monokai", line_numbers=False)
        self.console.print(Panel(syntax, title="[cyan]Executing Query[/cyan]", border_style="cyan"))

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]{task.description}[/cyan]"),
                console=self.console
            ) as progress:
                task = progress.add_task("Executing query...", total=None)

                result = self.executor.execute(
                    query,
                    EndpointInfo(url=self.state.current_endpoint)
                )

                progress.update(task, completed=True)

            # Store in history
            self.state.query_history.append((query, result))
            self.state.last_result = result

            # Display results
            if result.is_success:
                self._display_results(result)
            else:
                self.console.print(f"[red]Query failed: {result.error_message}[/red]")

        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def _display_results(self, result: QueryResult):
        """Display query results in a table."""
        if result.row_count == 0:
            self.console.print("[yellow]No results found[/yellow]")
            return

        # Create result table
        table = Table(
            title=f"Query Results ({result.row_count} rows in {result.execution_time:.2f}s)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )

        # Add columns
        for var in result.variables:
            table.add_column(var, style="white", max_width=50)

        # Add rows (limit to 50 for display)
        display_limit = 50
        for i, binding in enumerate(result.bindings[:display_limit]):
            row = [str(binding.get(var, ''))[:100] for var in result.variables]
            table.add_row(*row)

        if result.row_count > display_limit:
            table.add_row(
                *["..." for _ in result.variables]
            )
            self.console.print(f"[dim]Showing {display_limit} of {result.row_count} results[/dim]")

        self.console.print(table)
        self.console.print(f"\n[dim]Execution time: {result.execution_time:.3f}s[/dim]")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _discover_capabilities(self, endpoint: str):
        """Discover endpoint capabilities."""
        try:
            detector = CapabilitiesDetector(endpoint, timeout=30)
            caps = detector.detect_all_capabilities()
            self.state.endpoint_capabilities[endpoint] = caps
            self._display_capabilities(caps)
        except Exception as e:
            self.console.print(f"[dim]Could not discover capabilities: {e}[/dim]")

    def _display_capabilities(self, caps: Dict[str, Any]):
        """Display endpoint capabilities."""
        table = Table(title="Endpoint Capabilities", box=box.ROUNDED)
        table.add_column("Feature", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("SPARQL Version", caps.get('sparql_version', 'Unknown'))
        table.add_row("Named Graphs", str(len(caps.get('named_graphs', []))))
        table.add_row("Namespaces", str(len(caps.get('namespaces', {}))))

        if caps.get('features'):
            features = caps['features']
            table.add_row(
                "Supported Features",
                ", ".join([k for k, v in features.items() if v][:5])
            )

        self.console.print(table)

    def _show_schema_summary(self):
        """Show schema summary."""
        if not self.state.current_endpoint:
            return

        # Query for classes and properties count
        try:
            # Count classes
            class_query = """
            SELECT (COUNT(DISTINCT ?class) as ?count)
            WHERE {
                ?class a ?type .
                FILTER(isIRI(?class))
            }
            LIMIT 1
            """

            with self.console.status("[cyan]Analyzing schema...[/cyan]"):
                result = self.executor.execute(
                    class_query,
                    EndpointInfo(url=self.state.current_endpoint)
                )

                if result.is_success and result.bindings:
                    class_count = result.bindings[0].get('count', 'Unknown')
                else:
                    class_count = 'Unknown'

            info = f"""
[bold cyan]Schema Summary[/bold cyan]

[yellow]Classes:[/yellow] {class_count}
[yellow]Endpoint:[/yellow] {self.state.current_endpoint}

Use [cyan].schema classes[/cyan] to list classes
Use [cyan].schema properties[/cyan] to list properties
"""
            self.console.print(Panel(info.strip(), border_style="cyan"))
        except Exception as e:
            self.console.print(f"[red]Failed to analyze schema: {e}[/red]")

    def _show_classes(self, search_term: Optional[str]):
        """Show classes from endpoint."""
        query = """
        SELECT DISTINCT ?class (COUNT(?instance) as ?count)
        WHERE {
            ?instance a ?class .
        }
        GROUP BY ?class
        ORDER BY DESC(?count)
        LIMIT 20
        """

        try:
            with self.console.status("[cyan]Querying classes...[/cyan]"):
                result = self.executor.execute(
                    query,
                    EndpointInfo(url=self.state.current_endpoint)
                )

            if result.is_success and result.bindings:
                table = Table(title="Classes", box=box.ROUNDED)
                table.add_column("Class", style="cyan")
                table.add_column("Instances", style="yellow")

                for binding in result.bindings:
                    class_uri = binding.get('class', '')
                    count = binding.get('count', '0')
                    table.add_row(class_uri, str(count))

                self.console.print(table)
            else:
                self.console.print("[yellow]No classes found[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Query failed: {e}[/red]")

    def _show_properties(self, search_term: Optional[str]):
        """Show properties from endpoint."""
        query = """
        SELECT DISTINCT ?property (COUNT(*) as ?count)
        WHERE {
            ?s ?property ?o .
        }
        GROUP BY ?property
        ORDER BY DESC(?count)
        LIMIT 20
        """

        try:
            with self.console.status("[cyan]Querying properties...[/cyan]"):
                result = self.executor.execute(
                    query,
                    EndpointInfo(url=self.state.current_endpoint)
                )

            if result.is_success and result.bindings:
                table = Table(title="Properties", box=box.ROUNDED)
                table.add_column("Property", style="cyan")
                table.add_column("Usage Count", style="yellow")

                for binding in result.bindings:
                    prop_uri = binding.get('property', '')
                    count = binding.get('count', '0')
                    table.add_row(prop_uri, str(count))

                self.console.print(table)
            else:
                self.console.print("[yellow]No properties found[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Query failed: {e}[/red]")

    def _list_ontologies(self):
        """List common ontologies."""
        ontologies = list_common_ontologies()

        table = Table(title="Common Biomedical Ontologies", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Description", style="dim", max_width=60)

        for onto in ontologies[:15]:
            table.add_row(
                onto['id'].upper(),
                onto['name'],
                onto['description'][:100] + "..." if len(onto['description']) > 100 else onto['description']
            )

        self.console.print(table)
        self.console.print("\n[dim]Use .ontology <search_term> to search for specific terms[/dim]")

    def _get_example_queries(self, topic: Optional[str]) -> List[Dict[str, str]]:
        """Get example queries."""
        examples = [
            {
                'topic': 'basic',
                'query': 'SELECT * WHERE { ?s ?p ?o } LIMIT 10',
                'description': 'Get first 10 triples'
            },
            {
                'topic': 'basic',
                'query': 'SELECT DISTINCT ?type WHERE { ?s a ?type } LIMIT 20',
                'description': 'List entity types'
            },
            {
                'topic': 'aggregation',
                'query': 'SELECT ?type (COUNT(?s) as ?count) WHERE { ?s a ?type } GROUP BY ?type ORDER BY DESC(?count) LIMIT 10',
                'description': 'Count instances by type'
            },
            {
                'topic': 'filtering',
                'query': 'SELECT ?s ?label WHERE { ?s rdfs:label ?label . FILTER(LANG(?label) = "en") } LIMIT 20',
                'description': 'Filter by language'
            },
            {
                'topic': 'optional',
                'query': 'SELECT ?s ?label ?comment WHERE { ?s rdfs:label ?label . OPTIONAL { ?s rdfs:comment ?comment } } LIMIT 10',
                'description': 'Using OPTIONAL'
            },
        ]

        if topic:
            return [ex for ex in examples if ex['topic'] == topic]
        return examples

    def _format_results(self, result: QueryResult, format_type: str) -> str:
        """Format query results."""
        if format_type == "json":
            return json.dumps({
                'variables': result.variables,
                'bindings': result.bindings,
                'row_count': result.row_count,
                'execution_time': result.execution_time
            }, indent=2)

        elif format_type == "csv":
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=result.variables)
            writer.writeheader()
            for binding in result.bindings:
                writer.writerow(binding)
            return output.getvalue()

        elif format_type == "table":
            # Return as formatted table string
            return str(result.bindings)

        else:
            raise ValueError(f"Unknown format: {format_type}")

    def _save_session(self, filename: str):
        """Save session state to file."""
        state_dict = {
            'endpoint': self.state.current_endpoint,
            'ontology': self.state.current_ontology,
            'variables': self.state.variables,
            'timestamp': datetime.now().isoformat()
        }

        with open(filename, 'w') as f:
            json.dump(state_dict, f, indent=2)

    def _load_session(self, filename: str):
        """Load session state from file."""
        with open(filename, 'r') as f:
            state_dict = json.load(f)

        if state_dict.get('endpoint'):
            self.state.current_endpoint = state_dict['endpoint']
            self.executor = SPARQLExecutor(timeout=30)

        self.state.current_ontology = state_dict.get('ontology')
        self.state.variables = state_dict.get('variables', {})

    def _show_command_help(self, command: str):
        """Show help for specific command."""
        help_texts = {
            '.connect': 'Connect to a SPARQL endpoint\nUsage: .connect <endpoint_url>',
            '.schema': 'Display schema information\nUsage: .schema [class|property] [search_term]',
            '.examples': 'Show example queries\nUsage: .examples [topic]',
            '.ontology': 'Search ontologies\nUsage: .ontology <search_term>',
            '.help': 'Show help information\nUsage: .help [command]',
            '.history': 'Show query history\nUsage: .history',
            '.save': 'Save current session\nUsage: .save [filename]',
            '.load': 'Load saved session\nUsage: .load [filename]',
            '.export': 'Export last results\nUsage: .export <format> [filename]',
        }

        help_text = help_texts.get(command, 'No help available for this command')
        self.console.print(Panel(help_text, title=f"[cyan]{command}[/cyan]", border_style="cyan"))


def main():
    """Entry point for interactive shell."""
    shell = InteractiveShell()
    try:
        shell.run()
    except KeyboardInterrupt:
        shell._print_goodbye()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
