# Interactive SPARQL Query Builder

A rich, interactive terminal interface for building and executing SPARQL queries with advanced features.

## Features

### 🎨 Beautiful Terminal UI
- **Syntax highlighting** for SPARQL queries using Pygments
- **Rich tables** for displaying query results
- **Colored output** with status indicators
- **Panels and borders** for organized information display
- **Progress indicators** for long-running operations

### ⌨️ Smart Query Editing
- **Auto-completion** for SPARQL keywords (press TAB)
- **Multi-line editing** with proper indentation
- **Variable completion** based on query context
- **History search** with Ctrl+R
- **UP/DOWN arrow keys** to navigate command history

### 🔍 Schema Discovery
- **`.schema classes`** - List all classes with instance counts
- **`.schema properties`** - Show properties with usage statistics
- **`.schema [type] [search]`** - Search specific schema elements
- **Automatic caching** of schema information

### 🧬 Ontology Integration
- **`.ontology [term]`** - Search biomedical ontologies via OLS
- **List common ontologies** (GO, CHEBI, MONDO, HPO, etc.)
- **Term details** with descriptions and metadata
- **Cross-ontology search** across multiple sources

### 📊 Query Execution
- **Real-time query execution** with progress indicators
- **Formatted results** in beautiful tables
- **Automatic paging** for large result sets (50 rows displayed)
- **Execution time** tracking
- **Row count** information

### 💾 Session Management
- **`.save [file]`** - Save current session state
- **`.load [file]`** - Restore previous session
- **Auto-save** on exit to `~/.sparql_agent/last_session.json`
- **Persistent history** across sessions
- **Variable storage** for reusable values

### 📜 Query History
- **`.history`** - View last 20 queries with status
- **Persistent history** saved to `~/.sparql_agent/history.txt`
- **History search** with Ctrl+R
- **Query replay** with UP/DOWN arrows

### 📤 Export Results
- **`.export json [file]`** - Export as JSON
- **`.export csv [file]`** - Export as CSV
- **`.export table`** - Display as formatted table
- **File or stdout** output options

### 🔌 Endpoint Management
- **`.connect <url>`** - Connect to any SPARQL endpoint
- **`.endpoints`** - List common public endpoints
- **`.capabilities`** - Show endpoint features and statistics
- **Connection testing** before committing

## Installation

### Required Dependencies

```bash
pip install rich prompt-toolkit pygments
```

Or install the full package with all dependencies:

```bash
pip install -e .
```

### Optional Dependencies

All required dependencies are listed in `pyproject.toml`:
- `rich>=13.7.0` - Terminal formatting and tables
- `prompt-toolkit>=3.0.43` - Interactive prompts and completion
- `pygments>=2.17.0` - Syntax highlighting

## Usage

### Starting the Shell

```bash
# From command line
sparql-agent interactive

# Or programmatically
from sparql_agent.cli.interactive import InteractiveShell
shell = InteractiveShell()
shell.run()
```

### Basic Workflow

```bash
# 1. Connect to an endpoint
sparql> .connect https://query.wikidata.org/sparql

# 2. Explore the schema
sparql> .schema classes

# 3. View example queries
sparql> .examples

# 4. Execute a query
sparql> SELECT * WHERE { ?s ?p ?o } LIMIT 10

# 5. Search ontologies
sparql> .ontology diabetes

# 6. Export results
sparql> .export csv results.csv

# 7. Save session
sparql> .save my_session.json
```

## Available Commands

### Connection Commands
- **`.connect <url>`** - Connect to a SPARQL endpoint
- **`.endpoints`** - List configured/common endpoints
- **`.capabilities`** - Show endpoint capabilities and statistics

### Query Commands
- **Write SPARQL directly** - Multi-line queries supported
- **`.examples [topic]`** - Show example queries by topic
- **`.history`** - View query execution history

### Schema Commands
- **`.schema`** - Show schema summary
- **`.schema classes [search]`** - List classes (optionally filtered)
- **`.schema properties [search]`** - List properties (optionally filtered)

### Ontology Commands (NEW)
- **`.ontology`** - List common biomedical ontologies
- **`.ontology <term>`** - Search for ontology terms
  - Searches across GO, MONDO, HPO, CHEBI, and more
  - Returns term IDs, labels, and descriptions
  - Shows ontology source for each result

### Session Commands
- **`.save [file]`** - Save current session to file
- **`.load [file]`** - Load session from file
- **`.set <var> <value>`** - Set session variable
- **`.info`** - Show session information

### Export Commands
- **`.export json [file]`** - Export results as JSON
- **`.export csv [file]`** - Export results as CSV
- **`.export table`** - Display results as table

### Utility Commands
- **`.help [command]`** - Show help information
- **`.clear`** - Clear the screen
- **`.quit`** / **`.exit`** - Exit the shell

## Keyboard Shortcuts

- **TAB** - Auto-complete SPARQL keywords
- **UP/DOWN** - Navigate command history
- **Ctrl+R** - Search command history
- **Ctrl+C** - Cancel current input
- **Ctrl+D** - Exit shell
- **Ctrl+J** - New line in multi-line mode
- **Enter (on empty line)** - Execute multi-line query

## Example Session

```bash
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
✓ Connected to: https://query.wikidata.org/sparql

sparql> SELECT ?type (COUNT(?s) as ?count)
....... WHERE { ?s a ?type }
....... GROUP BY ?type
....... ORDER BY DESC(?count)
....... LIMIT 5

╭─────────────────────────────────────────────────────────────╮
│ Executing Query                                            │
├─────────────────────────────────────────────────────────────┤
│ SELECT ?type (COUNT(?s) as ?count)                        │
│ WHERE { ?s a ?type }                                       │
│ GROUP BY ?type                                             │
│ ORDER BY DESC(?count)                                      │
│ LIMIT 5                                                    │
╰─────────────────────────────────────────────────────────────╯

⠋ Executing query...

╭─────────────────────────────────────────────────────────────╮
│ Query Results (5 rows in 0.52s)                            │
├─────────────────────────────┬───────────────────────────────┤
│ type                        │ count                         │
├─────────────────────────────┼───────────────────────────────┤
│ http://www.wikidata.org/... │ 8526543                       │
│ http://www.wikidata.org/... │ 2847291                       │
│ http://www.wikidata.org/... │ 1932847                       │
│ http://www.wikidata.org/... │ 1284756                       │
│ http://www.wikidata.org/... │ 923847                        │
╰─────────────────────────────┴───────────────────────────────╯

Execution time: 0.524s

sparql> .ontology diabetes

⠋ Searching ontologies for 'diabetes'...

╭─────────────────────────────────────────────────────────────╮
│ Ontology Search Results: 'diabetes'                        │
├────────────┬─────────────────┬──────────┬─────────────────┤
│ ID         │ Label           │ Ontology │ Description     │
├────────────┼─────────────────┼──────────┼─────────────────┤
│ MONDO:0... │ diabetes melli..│ mondo    │ A metabolic ... │
│ DOID:9351  │ diabetes melli..│ doid     │ A glucose me... │
│ EFO:0001...│ type 1 diabetes │ efo      │ A chronic au... │
│ HP:0000819 │ diabetes melli..│ hp       │ A group of a... │
╰────────────┴─────────────────┴──────────┴─────────────────╯

sparql> .export csv diabetes_results.csv
✓ Results exported to: diabetes_results.csv

sparql> .quit
Goodbye!
```

## Configuration

### Default Paths

- **Config directory**: `~/.sparql_agent/`
- **History file**: `~/.sparql_agent/history.txt`
- **Session file**: `~/.sparql_agent/last_session.json`

### Custom Configuration

```python
from pathlib import Path
from sparql_agent.cli.interactive import InteractiveShell

# Custom paths
shell = InteractiveShell(
    history_file=Path("~/.my_history").expanduser(),
    config_dir=Path("~/.my_config").expanduser()
)
shell.run()
```

## Advanced Features

### Multi-line Queries

Press Enter on an empty line to execute:

```sparql
sparql> SELECT ?person ?name ?email
....... WHERE {
....... ?person a foaf:Person .
....... ?person foaf:name ?name .
....... OPTIONAL { ?person foaf:mbox ?email }
....... }
....... LIMIT 100
.......
```

### Query History Navigation

- Use **UP/DOWN** arrows to cycle through history
- Press **Ctrl+R** to search history interactively
- History is saved across sessions

### Schema Exploration

```bash
# Get overview
sparql> .schema

# List classes
sparql> .schema classes

# Search for specific class
sparql> .schema class Person

# List properties
sparql> .schema properties

# Search for specific property
sparql> .schema property name
```

### Ontology Search

```bash
# List common ontologies
sparql> .ontology

# Search for a term
sparql> .ontology cancer

# Search specific ontology
sparql> .ontology protein GO
```

### Session Variables

```bash
sparql> .set endpoint https://query.wikidata.org/sparql
sparql> .set limit 100
sparql> .info
```

## Tips & Tricks

1. **Auto-completion**: Type first few letters of a SPARQL keyword and press TAB
2. **Query templates**: Use `.examples` to see common query patterns
3. **Result paging**: Only first 50 rows are displayed; use LIMIT in query for more control
4. **Save sessions**: Use `.save` before complex operations to preserve state
5. **Quick exit**: Press Ctrl+D twice to exit immediately
6. **Error recovery**: Failed queries don't interrupt the session
7. **Endpoint testing**: `.connect` tests the connection before committing

## Troubleshooting

### Import Errors

If you see import errors for `rich` or `prompt_toolkit`:

```bash
pip install rich prompt-toolkit pygments
```

### Connection Timeouts

Increase timeout when connecting:

```python
shell = InteractiveShell()
# Timeout is set on the executor
shell.executor = SPARQLExecutor(timeout=120)  # 2 minutes
```

### Large Result Sets

For queries returning many results:

1. Use LIMIT in your query
2. Export to file: `.export csv large_results.csv`
3. Only first 50 rows displayed in terminal

### History Not Saving

Check permissions on:
- `~/.sparql_agent/` directory
- `~/.sparql_agent/history.txt` file

## Architecture

### Components

1. **InteractiveShell**: Main shell class managing state and UI
2. **SPARQLCompleter**: Auto-completion engine for SPARQL keywords
3. **SessionState**: State management for sessions and variables
4. **SPARQLExecutor**: Query execution engine
5. **OLSClient**: Ontology Lookup Service integration

### Integration Points

- **Execution Module**: `sparql_agent.execution.executor`
- **Ontology Module**: `sparql_agent.ontology.ols_client`
- **Schema Module**: `sparql_agent.schema.schema_inference`
- **Discovery Module**: `sparql_agent.discovery.capabilities`

## Development

### Adding New Commands

```python
class InteractiveShell:
    def __init__(self):
        # Register new command
        self.commands['.mycommand'] = self._cmd_mycommand

    def _cmd_mycommand(self, args: str):
        """Handle .mycommand"""
        self.console.print("[cyan]My command output[/cyan]")
```

### Custom Completers

```python
class CustomCompleter(Completer):
    def get_completions(self, document, complete_event):
        # Yield Completion objects
        yield Completion("my_completion", start_position=0)
```

## Future Enhancements

Planned features:
- Query validation before execution
- Visual query builder
- Result visualization (charts, graphs)
- Query optimization suggestions
- Federation support
- Authentication management
- Custom themes
- Plugin system

## Support

For issues, questions, or contributions:
- GitHub: https://github.com/david4096/sparql-agent
- Documentation: https://sparql-agent.readthedocs.io

## License

MIT License - See LICENSE file for details
