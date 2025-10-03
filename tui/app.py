#!/usr/bin/env python3
"""
SPARQL Agent TUI (Terminal User Interface)

A rich terminal-based interface for the SPARQL Agent system that provides:
- Natural language query input
- SPARQL generation and execution
- Result visualization in terminal
- Multiple endpoint management
- Session history
- Performance metrics
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    from rich.columns import Columns
    from rich.markdown import Markdown
    from rich import print as rprint
    from prompt_toolkit import Application
    from prompt_toolkit.layout.containers import HSplit, VSplit
    from prompt_toolkit.layout.layout import Layout as PTKLayout
    from prompt_toolkit.widgets import TextArea, Frame, Button, Label
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.shortcuts import message_dialog, input_dialog

    from sparql_agent.llm import create_anthropic_provider
    from sparql_agent.query import quick_generate
    from sparql_agent.execution import execute_query
    from sparql_agent.discovery import EndpointPinger, EndpointStatus
    from sparql_agent.formatting.visualizer import VisualizationSelector

except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure all dependencies are installed:")
    print("uv add rich prompt-toolkit")
    sys.exit(1)


class SPARQLAgentTUI:
    """Terminal User Interface for SPARQL Agent"""

    def __init__(self):
        self.console = Console()
        self.session_history = []
        self.current_results = None
        self.performance_metrics = {
            "queries_executed": 0,
            "total_llm_time": 0.0,
            "total_sparql_time": 0.0,
            "total_tokens_used": 0,
            "endpoints_used": set()
        }

        # Common endpoints
        self.endpoints = {
            "1": ("Wikidata", "https://query.wikidata.org/sparql"),
            "2": ("DBpedia", "https://dbpedia.org/sparql"),
            "3": ("EBI OLS4", "https://www.ebi.ac.uk/ols4/api/sparql"),
            "4": ("UniProt", "https://sparql.uniprot.org/sparql"),
            "5": ("RDF Portal (FAIR)", "https://rdfportal.org/sparql"),
            "6": ("RDF Portal (Biomedical)", "https://rdfportal.org/biomedical/sparql"),
            "7": ("Custom", "")
        }

        self.current_endpoint = self.endpoints["1"]

        # Check API key
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            self.console.print("[red]⚠️  ANTHROPIC_API_KEY not set![/red]")
            self.console.print("Please set your API key: export ANTHROPIC_API_KEY='your-key-here'")
            sys.exit(1)

    def show_welcome(self):
        """Display welcome screen"""
        welcome_text = """
# 🔍 SPARQL Agent TUI

Welcome to the SPARQL Agent Terminal User Interface!

## Features
- 🗣️  Natural language to SPARQL query generation
- ⚡ Multiple SPARQL endpoint support
- 📊 Results visualization in terminal
- 🔄 Bidirectional translation (Query ↔ English)
- 📈 Performance metrics and monitoring
- 💾 Session history and caching

## Quick Start
1. Select an endpoint (or press Enter for Wikidata)
2. Type your question in plain English
3. View generated SPARQL and results
4. Get natural language explanations

Press any key to continue...
"""

        panel = Panel(
            Markdown(welcome_text),
            title="🚀 SPARQL Agent",
            border_style="blue"
        )
        self.console.print(panel)
        self.console.input()

    def select_endpoint(self) -> tuple[str, str]:
        """Interactive endpoint selection"""
        self.console.print("\n[bold cyan]📡 Select SPARQL Endpoint:[/bold cyan]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", style="dim", width=6)
        table.add_column("Endpoint", style="cyan")
        table.add_column("URL", style="dim")

        for key, (name, url) in self.endpoints.items():
            if key == "7":  # Custom option
                table.add_row(key, name, "Enter your own URL")
            else:
                table.add_row(key, name, url[:50] + "..." if len(url) > 50 else url)

        self.console.print(table)

        choice = Prompt.ask(
            "Select endpoint",
            choices=list(self.endpoints.keys()),
            default="1"
        )

        if choice == "7":  # Custom endpoint
            custom_url = Prompt.ask("Enter SPARQL endpoint URL")
            return ("Custom", custom_url)
        else:
            return self.endpoints[choice]

    def test_endpoint(self, endpoint_url: str) -> bool:
        """Test endpoint connectivity"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Testing {endpoint_url}...", total=None)

            try:
                pinger = EndpointPinger()
                health = pinger.ping_sync(endpoint_url)

                if health.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]:
                    self.console.print(f"[green]✅ Connected ({health.response_time_ms:.1f}ms)[/green]")
                    return True
                else:
                    self.console.print(f"[red]❌ Failed: {health.error_message}[/red]")
                    return False

            except Exception as e:
                self.console.print(f"[red]❌ Error: {e}[/red]")
                return False

    def generate_sparql_query(self, natural_language: str) -> tuple[str, dict]:
        """Generate SPARQL from natural language with metrics"""
        metrics = {"llm_time": 0, "tokens": 0}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Generating SPARQL query...", total=None)

            start_time = time.time()
            try:
                provider = create_anthropic_provider(api_key=self.api_key)
                sparql_query = quick_generate(
                    natural_language=natural_language,
                    llm_client=provider
                )

                end_time = time.time()
                metrics["llm_time"] = end_time - start_time

                # Try to get token usage if available
                if hasattr(provider, 'last_usage'):
                    metrics["tokens"] = getattr(provider.last_usage, 'total_tokens', 0)

                return sparql_query, metrics

            except Exception as e:
                self.console.print(f"[red]❌ SPARQL Generation Error: {e}[/red]")
                return None, metrics

    def execute_sparql_query(self, sparql_query: str, endpoint_url: str) -> tuple[Any, dict]:
        """Execute SPARQL query with metrics"""
        metrics = {"sparql_time": 0, "result_count": 0}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Executing SPARQL query...", total=None)

            start_time = time.time()
            try:
                result = execute_query(sparql_query, endpoint_url)
                end_time = time.time()

                metrics["sparql_time"] = end_time - start_time
                metrics["result_count"] = len(result.bindings) if hasattr(result, 'bindings') else 0

                return result, metrics

            except Exception as e:
                self.console.print(f"[red]❌ SPARQL Execution Error: {e}[/red]")
                return None, metrics

    def display_sparql_query(self, sparql_query: str):
        """Display formatted SPARQL query"""
        syntax = Syntax(sparql_query, "sparql", theme="monokai", line_numbers=True)
        panel = Panel(syntax, title="🔧 Generated SPARQL Query", border_style="green")
        self.console.print(panel)

    def display_results(self, result: Any, limit: int = 20):
        """Display query results in a table"""
        if not result or not hasattr(result, 'bindings') or not result.bindings:
            self.console.print("[yellow]No results found.[/yellow]")
            return

        bindings = result.bindings[:limit]  # Limit displayed results

        # Get all unique keys
        all_keys = set()
        for binding in bindings:
            all_keys.update(binding.keys())
        columns = sorted(list(all_keys))

        if not columns:
            self.console.print("[yellow]No data columns found.[/yellow]")
            return

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        for col in columns:
            table.add_column(col, style="cyan", max_width=40, overflow="ellipsis")

        # Add rows
        for binding in bindings:
            row = []
            for col in columns:
                value = binding.get(col, "")
                # Handle different value types
                if hasattr(value, 'value'):
                    row.append(str(value.value))
                else:
                    row.append(str(value))
            table.add_row(*row)

        panel = Panel(table, title=f"📊 Results ({len(bindings)} of {len(result.bindings)})", border_style="blue")
        self.console.print(panel)

    def generate_explanation(self, query: str, sparql_query: str, results: Any) -> str:
        """Generate natural language explanation of results"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Generating explanation...", total=None)

            try:
                provider = create_anthropic_provider(api_key=self.api_key)

                # Prepare results sample for explanation
                result_sample = []
                if hasattr(results, 'bindings') and results.bindings:
                    for binding in results.bindings[:3]:  # First 3 results
                        sample = {}
                        for key, value in binding.items():
                            if hasattr(value, 'value'):
                                sample[key] = str(value.value)
                            else:
                                sample[key] = str(value)
                        result_sample.append(sample)

                explanation_prompt = f"""
Given the original question: "{query}"
And the SPARQL query: {sparql_query}
And the results showing {len(results.bindings) if hasattr(results, 'bindings') else 0} items:

{json.dumps(result_sample, indent=2) if result_sample else "No results"}

Please provide a clear, concise explanation in plain English of what was found and what it means.
Focus on answering the original question and summarizing the key insights from the data.
"""

                response = provider.generate(explanation_prompt)
                if response and hasattr(response, 'content'):
                    return response.content.strip()
                else:
                    return "Could not generate explanation."

            except Exception as e:
                return f"Error generating explanation: {e}"

    def display_explanation(self, explanation: str):
        """Display natural language explanation"""
        panel = Panel(
            Markdown(explanation),
            title="🧠 Natural Language Explanation",
            border_style="yellow"
        )
        self.console.print(panel)

    def display_metrics(self):
        """Display performance metrics"""
        metrics = self.performance_metrics

        table = Table(title="📈 Performance Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Queries Executed", str(metrics["queries_executed"]))
        table.add_row("Total LLM Time", f"{metrics['total_llm_time']:.2f}s")
        table.add_row("Total SPARQL Time", f"{metrics['total_sparql_time']:.2f}s")
        table.add_row("Total Tokens Used", str(metrics["total_tokens_used"]))
        table.add_row("Endpoints Used", str(len(metrics["endpoints_used"])))

        self.console.print(table)

    def display_session_history(self):
        """Display session query history"""
        if not self.session_history:
            self.console.print("[yellow]No queries in session history.[/yellow]")
            return

        table = Table(title="📜 Session History")
        table.add_column("Time", style="dim")
        table.add_column("Query", style="cyan", max_width=50)
        table.add_column("Results", style="magenta")
        table.add_column("Endpoint", style="dim")

        for entry in self.session_history[-10:]:  # Show last 10
            table.add_row(
                entry["timestamp"],
                entry["query"][:50] + "..." if len(entry["query"]) > 50 else entry["query"],
                str(entry["result_count"]),
                entry["endpoint_name"]
            )

        self.console.print(table)

    def main_menu(self):
        """Display main menu options"""
        options = {
            "1": "🔍 Execute Query",
            "2": "📡 Change Endpoint",
            "3": "📊 View Results",
            "4": "🧠 Get Explanation",
            "5": "📈 Show Metrics",
            "6": "📜 Session History",
            "7": "❓ Help",
            "8": "🚪 Exit"
        }

        table = Table(show_header=False)
        table.add_column("Option", style="bold cyan", width=8)
        table.add_column("Action", style="white")

        for key, desc in options.items():
            table.add_row(key, desc)

        panel = Panel(table, title="🎯 Main Menu", border_style="cyan")
        self.console.print(panel)

        choice = Prompt.ask(
            "Select option",
            choices=list(options.keys()),
            default="1"
        )

        return choice

    def show_help(self):
        """Display help information"""
        help_text = """
# 🆘 SPARQL Agent TUI Help

## Commands
- **1**: Execute a new natural language query
- **2**: Change SPARQL endpoint
- **3**: View last query results in detail
- **4**: Get natural language explanation of results
- **5**: Show performance metrics
- **6**: View session query history
- **7**: Show this help
- **8**: Exit the application

## Tips
- Be specific in your queries (e.g., "Find 10 people born in Paris")
- Include limits in your questions to avoid large result sets
- Use endpoint testing to verify connectivity
- Check metrics to monitor token usage and performance

## Keyboard Shortcuts
- **Ctrl+C**: Exit at any time
- **Enter**: Accept default options
- **Up/Down**: Navigate through history (when available)

## Environment
- **API Key**: Set via ANTHROPIC_API_KEY environment variable
- **Config**: Can be customized via ~/.sparql-agent/config.yaml
"""

        panel = Panel(
            Markdown(help_text),
            title="📚 Help Documentation",
            border_style="green"
        )
        self.console.print(panel)

    def run(self):
        """Main application loop"""
        # Show welcome screen
        self.show_welcome()

        # Select initial endpoint
        self.console.print(f"[bold green]Current endpoint:[/bold green] {self.current_endpoint[0]} - {self.current_endpoint[1]}")

        # Test endpoint
        if not self.test_endpoint(self.current_endpoint[1]):
            if not Confirm.ask("Endpoint test failed. Continue anyway?"):
                return

        # Main loop
        while True:
            try:
                self.console.print("\n" + "="*80)
                choice = self.main_menu()

                if choice == "1":  # Execute Query
                    query = Prompt.ask("\n[bold cyan]Enter your natural language query[/bold cyan]")

                    if not query.strip():
                        continue

                    # Generate SPARQL
                    sparql_query, llm_metrics = self.generate_sparql_query(query)
                    if not sparql_query:
                        continue

                    # Display generated SPARQL
                    self.display_sparql_query(sparql_query)

                    # Ask if user wants to execute
                    if not Confirm.ask("Execute this SPARQL query?", default=True):
                        continue

                    # Execute SPARQL
                    result, sparql_metrics = self.execute_sparql_query(sparql_query, self.current_endpoint[1])
                    if result is None:
                        continue

                    # Store results
                    self.current_results = result

                    # Display results
                    self.display_results(result)

                    # Generate and display explanation
                    explanation = self.generate_explanation(query, sparql_query, result)
                    self.display_explanation(explanation)

                    # Update metrics
                    self.performance_metrics["queries_executed"] += 1
                    self.performance_metrics["total_llm_time"] += llm_metrics["llm_time"]
                    self.performance_metrics["total_sparql_time"] += sparql_metrics["sparql_time"]
                    self.performance_metrics["total_tokens_used"] += llm_metrics["tokens"]
                    self.performance_metrics["endpoints_used"].add(self.current_endpoint[1])

                    # Add to session history
                    self.session_history.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "query": query,
                        "sparql_query": sparql_query,
                        "result_count": sparql_metrics["result_count"],
                        "endpoint_name": self.current_endpoint[0]
                    })

                elif choice == "2":  # Change Endpoint
                    new_endpoint = self.select_endpoint()
                    if self.test_endpoint(new_endpoint[1]):
                        self.current_endpoint = new_endpoint
                        self.console.print(f"[green]✅ Switched to {new_endpoint[0]}[/green]")
                    else:
                        if Confirm.ask("Use this endpoint anyway?"):
                            self.current_endpoint = new_endpoint

                elif choice == "3":  # View Results
                    if self.current_results:
                        limit = Prompt.ask("How many results to display?", default="20")
                        try:
                            self.display_results(self.current_results, int(limit))
                        except ValueError:
                            self.display_results(self.current_results)
                    else:
                        self.console.print("[yellow]No results available. Execute a query first.[/yellow]")

                elif choice == "4":  # Get Explanation
                    if self.current_results and self.session_history:
                        last_query = self.session_history[-1]
                        explanation = self.generate_explanation(
                            last_query["query"],
                            last_query["sparql_query"],
                            self.current_results
                        )
                        self.display_explanation(explanation)
                    else:
                        self.console.print("[yellow]No results available. Execute a query first.[/yellow]")

                elif choice == "5":  # Show Metrics
                    self.display_metrics()

                elif choice == "6":  # Session History
                    self.display_session_history()

                elif choice == "7":  # Help
                    self.show_help()

                elif choice == "8":  # Exit
                    self.console.print("[bold green]👋 Thank you for using SPARQL Agent TUI![/bold green]")
                    if self.performance_metrics["queries_executed"] > 0:
                        self.display_metrics()
                    break

            except KeyboardInterrupt:
                self.console.print("\n[bold red]👋 Goodbye![/bold red]")
                break
            except Exception as e:
                self.console.print(f"[red]Unexpected error: {e}[/red]")
                continue


def main():
    """Entry point for the TUI application"""
    tui = SPARQLAgentTUI()
    tui.run()


if __name__ == "__main__":
    main()