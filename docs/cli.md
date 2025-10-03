# SPARQL Agent CLI Reference

Complete command-line interface reference for SPARQL Agent.

## Table of Contents

- [Installation](#installation)
- [Global Options](#global-options)
- [Commands](#commands)
  - [query](#query) - Execute SPARQL queries
  - [discover](#discover) - Discover endpoint capabilities
  - [validate](#validate) - Validate SPARQL queries
  - [format](#format) - Format query results
  - [ontology](#ontology) - Ontology operations
  - [serve](#serve) - Start API server
  - [interactive](#interactive) - Interactive shell
  - [config](#config) - Configuration management
  - [batch](#batch) - Batch processing
  - [version](#version) - Version information
- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Examples](#examples)

## Installation

Using UV (recommended):

```bash
# Install dependencies
uv sync

# Run commands
uv run sparql-agent --help
```

Using pip:

```bash
pip install -e .
sparql-agent --help
```

## Global Options

These options are available for all commands:

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to configuration file |
| `--verbose, -v` | Enable verbose output (-v: INFO, -vv: DEBUG) |
| `--debug` | Enable debug mode with stack traces |
| `--profile NAME` | Configuration profile to use |
| `--help` | Show help message and exit |

Environment variables:
- `SPARQL_AGENT_CONFIG` - Configuration file path
- `SPARQL_AGENT_PROFILE` - Profile name

## Commands

### query

Generate and execute SPARQL queries from natural language.

```bash
uv run sparql-agent query [OPTIONS] QUERY
```

**Arguments:**
- `QUERY` - Natural language query or SPARQL query string

**Options:**
- `--endpoint, -e URL` - SPARQL endpoint URL (env: `SPARQL_AGENT_ENDPOINT`)
- `--ontology, -o ID` - Ontology for term mapping (e.g., efo, mondo, hp)
- `--format, -f FORMAT` - Output format: json, csv, tsv, table, sparql (default: table)
- `--output PATH` - Save output to file
- `--limit, -l N` - Maximum number of results
- `--timeout, -t SECONDS` - Query timeout
- `--execute/--no-execute` - Execute the query (default: execute)
- `--show-sparql` - Display generated SPARQL query
- `--strategy TYPE` - Generation strategy: auto, template, llm, hybrid (default: auto)
- `--llm-provider PROVIDER` - LLM provider: anthropic, openai, local

**Examples:**

```bash
# Natural language query with table output
uv run sparql-agent query "Find all proteins from human"

# Query with specific endpoint
uv run sparql-agent query "Show diseases related to diabetes" \
  --endpoint https://rdf.uniprot.org/sparql

# Query with ontology mapping and CSV output
uv run sparql-agent query "List genes with GO term DNA binding" \
  --ontology go --format csv --output results.csv

# Generate SPARQL without execution
uv run sparql-agent query "Find all classes" \
  --no-execute --show-sparql

# Direct SPARQL query
uv run sparql-agent query "SELECT * WHERE { ?s ?p ?o } LIMIT 10" \
  --endpoint https://query.wikidata.org/sparql
```

### discover

Discover capabilities and metadata of SPARQL endpoints.

```bash
uv run sparql-agent discover [OPTIONS] ENDPOINT
```

**Arguments:**
- `ENDPOINT` - SPARQL endpoint URL

**Options:**
- `--timeout, -t SECONDS` - Discovery timeout (default: 30)
- `--output, -o PATH` - Save results to file
- `--format, -f FORMAT` - Output format: json, yaml, text (default: text)
- `--analyze-schema` - Perform deep schema analysis (slower)

**Examples:**

```bash
# Discover endpoint
uv run sparql-agent discover https://query.wikidata.org/sparql

# Save to file
uv run sparql-agent discover https://rdf.uniprot.org/sparql \
  --output uniprot-info.json --format json

# Deep analysis
uv run sparql-agent discover https://sparql.uniprot.org/sparql \
  --analyze-schema --timeout 120
```

### validate

Validate SPARQL query syntax and best practices.

```bash
uv run sparql-agent validate [OPTIONS] QUERY_FILE
```

**Arguments:**
- `QUERY_FILE` - Path to SPARQL query file

**Options:**
- `--strict` - Enable strict validation mode
- `--format, -f FORMAT` - Output format: text, json (default: text)

**Examples:**

```bash
# Validate query
uv run sparql-agent validate query.sparql

# Strict validation with JSON output
uv run sparql-agent validate query.rq --strict --format json
```

### format

Format SPARQL query results into various output formats.

```bash
uv run sparql-agent format [OPTIONS] RESULTS_FILE
```

**Arguments:**
- `RESULTS_FILE` - Path to SPARQL JSON results file

**Options:**
- `--output-format, -f FORMAT` - Output format: json, csv, tsv, table, html (default: json)
- `--output, -o PATH` - Output file (default: stdout)
- `--pretty` - Pretty-print JSON output

**Examples:**

```bash
# Convert to CSV
uv run sparql-agent format results.json \
  --output-format csv --output results.csv

# Pretty-print JSON
uv run sparql-agent format results.json --pretty

# Generate HTML table
uv run sparql-agent format results.json \
  --output-format html --output results.html
```

### ontology

Ontology search and management commands.

#### ontology search

Search for ontology terms.

```bash
uv run sparql-agent ontology search [OPTIONS] TERM
```

**Arguments:**
- `TERM` - Search term

**Options:**
- `--ontology, -o ID` - Filter by ontology (e.g., efo, mondo)
- `--exact` - Require exact match
- `--limit, -l N` - Maximum results (default: 10)
- `--format, -f FORMAT` - Output format: text, json, csv (default: text)

**Examples:**

```bash
# Search for term
uv run sparql-agent ontology search "diabetes"

# Search in specific ontology
uv run sparql-agent ontology search "DNA binding" \
  --ontology go --limit 5

# Exact match with JSON output
uv run sparql-agent ontology search "heart" \
  --exact --format json
```

#### ontology list

List available ontologies.

```bash
uv run sparql-agent ontology list [OPTIONS]
```

**Options:**
- `--limit, -l N` - Maximum ontologies (default: 20)
- `--format, -f FORMAT` - Output format: text, json

**Examples:**

```bash
# List common ontologies
uv run sparql-agent ontology list

# Get all as JSON
uv run sparql-agent ontology list --limit 100 --format json
```

#### ontology info

Get information about a specific ontology.

```bash
uv run sparql-agent ontology info [OPTIONS] ONTOLOGY_ID
```

**Arguments:**
- `ONTOLOGY_ID` - Ontology identifier (e.g., efo, mondo)

**Options:**
- `--format, -f FORMAT` - Output format: text, json

**Examples:**

```bash
# Get ontology info
uv run sparql-agent ontology info efo

# JSON output
uv run sparql-agent ontology info mondo --format json
```

### serve

Start the SPARQL Agent API server.

```bash
uv run sparql-agent serve [OPTIONS]
```

**Options:**
- `--port, -p PORT` - Server port (default: 8000)
- `--host, -h HOST` - Host to bind (default: 127.0.0.1)
- `--reload` - Enable auto-reload on code changes

**Examples:**

```bash
# Start server
uv run sparql-agent serve

# Custom port
uv run sparql-agent serve --port 8080

# Development mode with reload
uv run sparql-agent serve --reload --host 0.0.0.0
```

### interactive

Start interactive query builder shell.

```bash
uv run sparql-agent interactive [OPTIONS]
```

**Features:**
- Syntax highlighting
- Auto-completion
- Query history
- Schema exploration
- Ontology search

**Examples:**

```bash
# Start interactive shell
uv run sparql-agent interactive

# In the shell:
sparql> .connect https://query.wikidata.org/sparql
sparql> SELECT * WHERE { ?s ?p ?o } LIMIT 10
sparql> .ontology diabetes
sparql> .help
sparql> .exit
```

### config

Configuration management commands.

#### config show

Show current configuration.

```bash
uv run sparql-agent config show [OPTIONS]
```

**Options:**
- `--format, -f FORMAT` - Output format: text, json, yaml

**Examples:**

```bash
# Show config
uv run sparql-agent config show

# JSON output
uv run sparql-agent config show --format json
```

#### config list-endpoints

List configured SPARQL endpoints.

```bash
uv run sparql-agent config list-endpoints
```

### batch

Batch processing commands for large-scale operations.

#### batch batch-query

Execute multiple queries in batch mode.

```bash
uv run sparql-agent batch batch-query [OPTIONS] INPUT_FILE
```

**Arguments:**
- `INPUT_FILE` - File containing queries

**Options:**
- `--endpoint, -e URL` - SPARQL endpoint (required)
- `--format, -f FORMAT` - Input format: text, json, yaml, csv (default: text)
- `--output, -o DIR` - Output directory (default: batch-results)
- `--output-mode MODE` - Output mode: individual, consolidated, both (default: both)
- `--execute/--no-execute` - Execute queries (default: execute)
- `--parallel/--sequential` - Processing mode (default: parallel)
- `--workers, -w N` - Number of parallel workers (default: 4)
- `--timeout, -t SECONDS` - Timeout per query (default: 60)
- `--retry, -r N` - Retry attempts (default: 2)
- `--strategy TYPE` - Generation strategy: auto, template, llm, hybrid

**Examples:**

```bash
# Process queries from text file
uv run sparql-agent batch batch-query queries.txt \
  --endpoint https://sparql.uniprot.org/sparql

# Parallel processing with JSON input
uv run sparql-agent batch batch-query queries.json \
  --format json --parallel --workers 8

# Generate without execution
uv run sparql-agent batch batch-query nl-queries.txt \
  --no-execute --output sparql-queries/
```

#### batch bulk-discover

Discover capabilities of multiple endpoints.

```bash
uv run sparql-agent batch bulk-discover [OPTIONS] INPUT_FILE
```

**Arguments:**
- `INPUT_FILE` - File containing endpoint URLs

**Options:**
- `--format, -f FORMAT` - Input format: text, json, yaml, csv
- `--output, -o DIR` - Output directory (default: discovery-results)
- `--parallel/--sequential` - Processing mode
- `--workers, -w N` - Number of workers
- `--timeout, -t SECONDS` - Timeout per endpoint (default: 30)

**Examples:**

```bash
# Discover multiple endpoints
uv run sparql-agent batch bulk-discover endpoints.txt \
  --output discovery/

# With YAML config
uv run sparql-agent batch bulk-discover endpoints.yaml \
  --format yaml --parallel --workers 4
```

### version

Show version information.

```bash
uv run sparql-agent version [OPTIONS]
```

**Options:**
- `--verbose, -v` - Show detailed information

**Examples:**

```bash
# Show version
uv run sparql-agent version

# Detailed info
uv run sparql-agent version --verbose
```

## Environment Variables

Configure SPARQL Agent using environment variables:

### General

- `SPARQL_AGENT_CONFIG` - Configuration file path
- `SPARQL_AGENT_PROFILE` - Configuration profile name
- `SPARQL_AGENT_DEBUG` - Enable debug mode (true/false)
- `SPARQL_AGENT_ENDPOINT` - Default SPARQL endpoint URL

### LLM Configuration

- `SPARQL_AGENT_LLM__MODEL_NAME` - LLM model name
- `SPARQL_AGENT_LLM__API_KEY` - API key for LLM service
- `SPARQL_AGENT_LLM__API_BASE_URL` - Custom API base URL
- `SPARQL_AGENT_LLM__TEMPERATURE` - Temperature (0.0-2.0)
- `SPARQL_AGENT_LLM__MAX_TOKENS` - Maximum tokens

### Ontology Configuration

- `SPARQL_AGENT_ONTOLOGY__OLS_API_BASE_URL` - OLS API URL
- `SPARQL_AGENT_ONTOLOGY__CACHE_ENABLED` - Enable caching
- `SPARQL_AGENT_ONTOLOGY__CACHE_DIR` - Cache directory

### Endpoint Configuration

- `SPARQL_AGENT_ENDPOINT__DEFAULT_TIMEOUT` - Default timeout
- `SPARQL_AGENT_ENDPOINT__MAX_RETRIES` - Maximum retries
- `SPARQL_AGENT_ENDPOINT__RATE_LIMIT_ENABLED` - Enable rate limiting

### Logging

- `SPARQL_AGENT_LOG__LEVEL` - Log level (DEBUG, INFO, WARNING, ERROR)
- `SPARQL_AGENT_LOG__FILE_ENABLED` - Enable file logging
- `SPARQL_AGENT_LOG__FILE_PATH` - Log file path

## Configuration Files

SPARQL Agent uses YAML configuration files located in the config directory.

### Main Configuration (settings.yaml)

Not required but loaded if present in config directory.

### Endpoints Configuration (endpoints.yaml)

Define SPARQL endpoints:

```yaml
endpoints:
  uniprot:
    url: https://sparql.uniprot.org/sparql
    description: UniProt protein database
    timeout: 60

  wikidata:
    url: https://query.wikidata.org/sparql
    description: Wikidata knowledge base
    rate_limit: 10

  local:
    url: http://localhost:3030/dataset
    description: Local Jena Fuseki endpoint
```

### Ontologies Configuration (ontologies.yaml)

Configure ontologies:

```yaml
ontologies:
  efo:
    name: Experimental Factor Ontology
    url: https://www.ebi.ac.uk/efo/
    prefix: http://www.ebi.ac.uk/efo/

  mondo:
    name: Mondo Disease Ontology
    url: http://purl.obolibrary.org/obo/mondo.owl
    prefix: http://purl.obolibrary.org/obo/MONDO_
```

### Prompts Configuration (prompts.yaml)

Custom prompt templates:

```yaml
prompts:
  basic_query:
    template: |
      Generate a SPARQL query for: {query}
      Consider the following ontology terms: {ontology_terms}

  complex_query:
    template: |
      Generate a complex SPARQL query that:
      - Uses the following patterns: {patterns}
      - Maps to these ontologies: {ontologies}
      - Returns: {expected_output}
```

## Examples

### Complete Workflow Example

```bash
# 1. Discover endpoint capabilities
uv run sparql-agent discover https://sparql.uniprot.org/sparql \
  --output uniprot-capabilities.json

# 2. Search for relevant ontology terms
uv run sparql-agent ontology search "insulin" \
  --ontology efo --format json --output insulin-terms.json

# 3. Generate and execute query
uv run sparql-agent query "Find proteins related to insulin" \
  --endpoint https://sparql.uniprot.org/sparql \
  --ontology efo \
  --format csv \
  --output insulin-proteins.csv \
  --show-sparql \
  -v

# 4. Validate the generated query
uv run sparql-agent validate generated-query.sparql --strict

# 5. Run batch queries
uv run sparql-agent batch batch-query protein-queries.txt \
  --endpoint https://sparql.uniprot.org/sparql \
  --parallel --workers 8 \
  --output batch-results/
```

### Interactive Session Example

```bash
# Start interactive shell
uv run sparql-agent interactive

# Interactive commands:
sparql> .connect https://query.wikidata.org/sparql
Connected to https://query.wikidata.org/sparql

sparql> .ontology search diabetes
Found 15 results:
1. Diabetes mellitus [MONDO:0005015]
2. Type 1 diabetes [MONDO:0005147]
...

sparql> SELECT ?disease ?label WHERE {
      >   ?disease a <http://purl.obolibrary.org/obo/MONDO_0005015> .
      >   ?disease rdfs:label ?label .
      > } LIMIT 10

Executing query...
Results:
+------------------------+---------------------------+
| disease                | label                     |
+------------------------+---------------------------+
| ...                    | ...                       |
+------------------------+---------------------------+

sparql> .export results.csv csv
Exported to results.csv

sparql> .history
1. SELECT ?disease ?label WHERE { ... }

sparql> .exit
Goodbye!
```

### Configuration Management Example

```bash
# Show current configuration
uv run sparql-agent config show

# List configured endpoints
uv run sparql-agent config list-endpoints

# Use specific configuration file
uv run sparql-agent --config /path/to/config.yaml query "Find proteins"

# Use environment-specific profile
uv run sparql-agent --profile production serve --port 8080
```

### Batch Processing Example

```bash
# Create queries file (queries.txt)
cat > queries.txt << EOF
Find proteins from human
Show diseases related to diabetes
List genes with GO term DNA binding
EOF

# Process in batch
uv run sparql-agent batch batch-query queries.txt \
  --endpoint https://sparql.uniprot.org/sparql \
  --output batch-results/ \
  --parallel \
  --workers 4 \
  -v

# Results:
# - batch-results/individual/ (one file per query)
# - batch-results/results.json (consolidated)
# - batch-results/errors.json (failed queries)
# - batch-results/batch.log (processing log)
```

## Tips and Best Practices

1. **Use environment variables** for sensitive data like API keys
2. **Enable verbose mode** (`-v`) for debugging
3. **Use batch commands** for processing multiple queries efficiently
4. **Configure default endpoint** in environment to avoid repeating `--endpoint`
5. **Save results to files** for large result sets
6. **Use the interactive shell** for exploration and testing
7. **Validate queries** before executing on production endpoints
8. **Monitor timeout settings** for slow endpoints
9. **Leverage ontology search** for better query generation
10. **Use configuration files** for team collaboration

## Getting Help

```bash
# General help
uv run sparql-agent --help

# Command-specific help
uv run sparql-agent query --help
uv run sparql-agent discover --help

# Show version and dependencies
uv run sparql-agent version --verbose
```

For issues and feature requests, visit:
https://github.com/david4096/sparql-agent/issues
