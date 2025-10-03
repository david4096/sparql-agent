# Quick Start: Interactive SPARQL Query Builder

## Installation

```bash
# Navigate to the project
cd /Users/david/git/sparql-agent

# Install the package with dependencies
pip install -e .

# Or install just the required libraries
pip install rich prompt-toolkit pygments
```

## Launch the Interactive Shell

```bash
sparql-agent interactive
```

## 5-Minute Tutorial

### 1. Connect to Wikidata (10 seconds)

```bash
sparql> .connect https://query.wikidata.org/sparql
```

You'll see:
- ✓ Connection success message
- Endpoint capabilities summary

### 2. Search for Ontology Terms (NEW - 20 seconds)

```bash
# List common ontologies
sparql> .ontology

# Search for a specific term
sparql> .ontology diabetes
```

You'll see a beautiful table with:
- Term IDs (e.g., MONDO:0005015)
- Labels (e.g., "diabetes mellitus")
- Source ontologies (MONDO, DOID, EFO, HP)
- Descriptions

### 3. Explore the Schema (30 seconds)

```bash
# View schema overview
sparql> .schema

# See top classes
sparql> .schema classes

# See top properties
sparql> .schema properties
```

### 4. View Example Queries (20 seconds)

```bash
sparql> .examples
```

You'll see example queries for:
- Basic queries
- Aggregation
- Filtering
- Optional patterns

### 5. Execute Your First Query (60 seconds)

```bash
sparql> SELECT ?type (COUNT(?s) as ?count)
....... WHERE { ?s a ?type }
....... GROUP BY ?type
....... ORDER BY DESC(?count)
....... LIMIT 5
.......
```

(Press Enter on empty line to execute)

You'll see:
- Syntax-highlighted query in a panel
- Progress spinner during execution
- Beautiful table with results
- Execution time

### 6. Export Results (20 seconds)

```bash
sparql> .export csv my_results.csv
```

### 7. Save Your Session (10 seconds)

```bash
sparql> .save my_session.json
```

### 8. Exit

```bash
sparql> .quit
```

## Common Commands Cheat Sheet

```bash
# Connection
.connect <url>              # Connect to endpoint
.endpoints                  # List common endpoints

# Ontology (NEW)
.ontology                   # List common ontologies
.ontology <term>            # Search for term across ontologies

# Schema
.schema                     # Show overview
.schema classes             # List classes
.schema properties          # List properties

# Queries
<write SPARQL>              # Execute query (multi-line)
.examples                   # Show examples
.history                    # View query history

# Results
.export json [file]         # Export as JSON
.export csv [file]          # Export as CSV

# Session
.save [file]                # Save session
.load [file]                # Load session
.info                       # Show session info

# Help
.help                       # Show all commands
.help <command>             # Help for specific command
.quit                       # Exit
```

## Keyboard Shortcuts

- **TAB**: Auto-complete SPARQL keywords
- **UP/DOWN**: Navigate history
- **Ctrl+R**: Search history
- **Ctrl+D**: Exit
- **Ctrl+C**: Cancel input
- **Enter (empty line)**: Execute multi-line query

## Example Workflows

### Workflow 1: Explore a New Endpoint

```bash
sparql> .connect https://sparql.uniprot.org/sparql
sparql> .capabilities
sparql> .schema classes
sparql> .schema properties
sparql> .examples
```

### Workflow 2: Find and Query Ontology Terms

```bash
sparql> .ontology cancer
# Copy term ID from results
sparql> SELECT ?gene ?name WHERE {
....... ?gene a up:Gene .
....... ?gene up:annotation ?annotation .
....... ?annotation up:disease <term-id> .
....... ?gene up:name ?name .
....... } LIMIT 10
.......
```

### Workflow 3: Data Analysis Pipeline

```bash
sparql> .connect https://query.wikidata.org/sparql
sparql> SELECT ?person ?personLabel ?birth
....... WHERE {
....... ?person wdt:P31 wd:Q5 .
....... ?person wdt:P106 wd:Q169470 .
....... ?person wdt:P569 ?birth .
....... SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
....... } LIMIT 100
.......
sparql> .export csv physicists.csv
sparql> .save physics_analysis.json
```

## Tips for Success

1. **Start with .connect**: Always connect to an endpoint first
2. **Use .schema**: Explore the schema before writing queries
3. **Check .examples**: Learn query patterns from examples
4. **Search .ontology**: Find relevant ontology terms quickly (NEW)
5. **Save often**: Use .save to preserve your work
6. **Export results**: Save results in different formats
7. **Use TAB**: Let auto-completion help you
8. **Read errors**: Error messages are helpful and actionable

## Next Steps

1. Read the full documentation: `src/sparql_agent/cli/INTERACTIVE_README.md`
2. Try the examples: `src/sparql_agent/cli/interactive_example.py`
3. Connect to different endpoints: .endpoints
4. Build complex queries with multi-line support
5. Search ontologies for domain-specific terms
6. Export your findings to CSV or JSON

## Getting Help

```bash
# In the shell
sparql> .help
sparql> .help connect
sparql> .help ontology

# Documentation files
- INTERACTIVE_README.md (detailed guide)
- INTERACTIVE_CLI_SUMMARY.md (implementation details)
- interactive_example.py (code examples)
```

## Troubleshooting

**Problem**: "Module not found: rich"
**Solution**: `pip install rich prompt-toolkit pygments`

**Problem**: Connection timeout
**Solution**: Check endpoint URL, increase timeout in executor

**Problem**: No results
**Solution**: Check query syntax, try .examples for working queries

**Problem**: Can't find ontology term
**Solution**: Try different search terms, use .ontology without args to see available ontologies

## Features Highlight

✅ Beautiful terminal UI with colors and tables
✅ Syntax highlighting for SPARQL
✅ Auto-completion (TAB key)
✅ Multi-line query editing
✅ Persistent history across sessions
✅ Schema exploration tools
✅ **Ontology search across GO, CHEBI, MONDO, HPO, etc. (NEW)**
✅ Result export (JSON, CSV, table)
✅ Session save/restore
✅ Comprehensive help system
✅ Progress indicators
✅ Error handling with helpful messages

**Enjoy exploring SPARQL endpoints with style!** 🎉
