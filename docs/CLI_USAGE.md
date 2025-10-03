# SPARQL Agent CLI Documentation

Complete command-line interface for SPARQL Agent with natural language query generation, ontology integration, and endpoint discovery.

## Installation

```bash
pip install -e .
```

After installation, the `sparql-agent` command will be available in your PATH.

## Quick Start

```bash
# Generate and execute a natural language query
sparql-agent query "Find all proteins from human" --endpoint https://rdf.uniprot.org/sparql

# Discover endpoint capabilities
sparql-agent discover https://query.wikidata.org/sparql

# Validate a SPARQL query
sparql-agent validate query.sparql

# Search ontologies
sparql-agent ontology search "diabetes"

# Start the API server
sparql-agent serve --port 8000
```

## Commands

### Main Commands

#### `query` - Generate and Execute SPARQL Queries

Generate SPARQL queries from natural language and optionally execute them.

**Usage:**
```bash
sparql-agent query "NATURAL_LANGUAGE_QUERY" [OPTIONS]
```

**Options:**
- `--endpoint, -e` - SPARQL endpoint URL
- `--ontology, -o` - Ontology to use for mapping (e.g., efo, mondo, hp)
- `--format, -f` - Output format: json, csv, tsv, table, sparql (default: json)
- `--limit, -l` - Maximum number of results
- `--timeout, -t` - Query timeout in seconds
- `--execute/--no-execute` - Execute the generated query (default: True)
- `--show-sparql` - Display the generated SPARQL query
- `--strategy` - Generation strategy: auto, template, llm, hybrid (default: auto)

**Examples:**
```bash
# Basic query
sparql-agent query "Find all proteins from human"

# With specific endpoint
sparql-agent query "Show diseases related to diabetes" \
  --endpoint https://rdf.uniprot.org/sparql

# With ontology mapping
sparql-agent query "List genes with GO term DNA binding" \
  --ontology go --format csv

# Just generate SPARQL without executing
sparql-agent query "Find all proteins" \
  --no-execute --show-sparql

# Using LLM strategy with limit
sparql-agent query "Find proteins related to cancer" \
  --strategy llm --limit 100 --format table

# Output as CSV
sparql-agent query "List all human genes" \
  --endpoint https://rdf.uniprot.org/sparql \
  --format csv > genes.csv
```

#### `discover` - Discover Endpoint Capabilities

Analyze a SPARQL endpoint to discover its capabilities, namespaces, and statistics.

**Usage:**
```bash
sparql-agent discover ENDPOINT_URL [OPTIONS]
```

**Options:**
- `--timeout, -t` - Discovery timeout in seconds (default: 30)
- `--output, -o` - Save discovery results to file
- `--format, -f` - Output format: json, yaml, text (default: json)

**Examples:**
```bash
# Discover Wikidata endpoint
sparql-agent discover https://query.wikidata.org/sparql

# Save results to file
sparql-agent discover https://rdf.uniprot.org/sparql \
  --output uniprot-info.json

# Human-readable text format
sparql-agent discover http://localhost:3030/dataset \
  --format text
```

#### `validate` - Validate SPARQL Queries

Validate SPARQL query syntax and check for best practices.

**Usage:**
```bash
sparql-agent validate QUERY_FILE [OPTIONS]
```

**Options:**
- `--strict` - Enable strict validation mode with additional checks
- `--format, -f` - Output format: text, json (default: text)

**Examples:**
```bash
# Validate a query file
sparql-agent validate query.sparql

# Strict validation with JSON output
sparql-agent validate query.rq --strict --format json

# Validate and save report
sparql-agent validate query.sparql --format json > validation-report.json
```

**Validation Checks:**
- Syntax errors
- Missing prefix declarations
- Variable consistency
- URI and literal validation
- Balanced brackets and quotes
- Best practice recommendations
- Performance suggestions

#### `format` - Format Query Results

Convert SPARQL query results between different formats.

**Usage:**
```bash
sparql-agent format RESULTS_FILE [OPTIONS]
```

**Options:**
- `--output-format, -f` - Output format: json, csv, tsv, table, html (default: json)
- `--output, -o` - Output file (default: stdout)
- `--pretty` - Pretty-print output (for JSON)

**Examples:**
```bash
# Convert JSON results to CSV
sparql-agent format results.json --output-format csv -o results.csv

# Display as table
sparql-agent format results.json --output-format table

# Pretty-print JSON
sparql-agent format results.json -f json --pretty
```

### Ontology Commands

Work with biomedical ontologies using the EBI Ontology Lookup Service.

#### `ontology search` - Search Ontology Terms

Search for terms across biomedical ontologies.

**Usage:**
```bash
sparql-agent ontology search TERM [OPTIONS]
```

**Options:**
- `--ontology, -o` - Filter by specific ontology (e.g., efo, mondo, hp)
- `--exact` - Require exact match
- `--limit, -l` - Maximum number of results (default: 10)
- `--format, -f` - Output format: text, json, csv (default: text)

**Examples:**
```bash
# Search all ontologies
sparql-agent ontology search "diabetes"

# Search specific ontology
sparql-agent ontology search "DNA binding" --ontology go --limit 5

# Exact match with JSON output
sparql-agent ontology search "heart" --exact --format json

# Export to CSV
sparql-agent ontology search "cancer" --format csv > terms.csv
```

#### `ontology list` - List Available Ontologies

Show commonly used biomedical ontologies.

**Usage:**
```bash
sparql-agent ontology list [OPTIONS]
```

**Options:**
- `--limit, -l` - Maximum number of ontologies to list (default: 20)
- `--format, -f` - Output format: text, json (default: text)

**Examples:**
```bash
# List common ontologies
sparql-agent ontology list

# List all with JSON output
sparql-agent ontology list --limit 100 --format json
```

#### `ontology info` - Get Ontology Information

Get detailed information about a specific ontology.

**Usage:**
```bash
sparql-agent ontology info ONTOLOGY_ID [OPTIONS]
```

**Options:**
- `--format, -f` - Output format: text, json (default: text)

**Examples:**
```bash
# Get info about EFO
sparql-agent ontology info efo

# Get info as JSON
sparql-agent ontology info mondo --format json
```

**Common Ontologies:**
- `go` - Gene Ontology
- `chebi` - Chemical Entities of Biological Interest
- `pr` - Protein Ontology
- `hp` - Human Phenotype Ontology
- `mondo` - Monarch Disease Ontology
- `uberon` - Uber Anatomy Ontology
- `cl` - Cell Ontology
- `so` - Sequence Ontology
- `efo` - Experimental Factor Ontology
- `doid` - Human Disease Ontology

### Server Command

#### `serve` - Start API Server

Run the SPARQL Agent REST API server.

**Usage:**
```bash
sparql-agent serve [OPTIONS]
```

**Options:**
- `--port, -p` - Port to run the server on (default: 8000)
- `--host, -h` - Host to bind to (default: 127.0.0.1)
- `--reload` - Enable auto-reload on code changes (development mode)

**Examples:**
```bash
# Start server on default port
sparql-agent serve

# Start on custom port
sparql-agent serve --port 8080

# Start with public access
sparql-agent serve --host 0.0.0.0 --port 8000

# Development mode with auto-reload
sparql-agent serve --reload
```

**API Endpoints:**
- `GET /` - API documentation
- `POST /query` - Generate and execute queries
- `POST /generate` - Generate SPARQL from natural language
- `POST /validate` - Validate SPARQL queries
- `GET /discover/{endpoint}` - Discover endpoint capabilities
- `GET /ontology/search` - Search ontology terms
- `GET /ontology/list` - List ontologies

### Configuration Commands

#### `config show` - Show Configuration

Display current SPARQL Agent configuration.

**Usage:**
```bash
sparql-agent config show [OPTIONS]
```

**Options:**
- `--format, -f` - Output format: text, json, yaml (default: text)

**Examples:**
```bash
# Show configuration
sparql-agent config show

# Show as JSON
sparql-agent config show --format json

# Show as YAML
sparql-agent config show --format yaml
```

#### `config list-endpoints` - List Configured Endpoints

List all configured SPARQL endpoints.

**Usage:**
```bash
sparql-agent config list-endpoints
```

**Example:**
```bash
sparql-agent config list-endpoints
```

## Global Options

These options can be used with any command:

- `--config` - Path to configuration file
- `--verbose, -v` - Enable verbose output
- `--debug` - Enable debug mode
- `--help` - Show help message

**Examples:**
```bash
# Verbose output
sparql-agent -v query "Find proteins"

# Debug mode
sparql-agent --debug query "List genes"

# Custom config file
sparql-agent --config my-config.yaml query "Find all"
```

## Environment Variables

Configure SPARQL Agent using environment variables:

### General
- `SPARQL_AGENT_DEBUG` - Enable debug mode (true/false)

### Ontology Settings
- `SPARQL_AGENT_ONTOLOGY_OLS_API_BASE_URL` - OLS API base URL
- `SPARQL_AGENT_ONTOLOGY_CACHE_ENABLED` - Enable ontology caching (true/false)
- `SPARQL_AGENT_ONTOLOGY_CACHE_DIR` - Cache directory path
- `SPARQL_AGENT_ONTOLOGY_CACHE_TTL` - Cache TTL in seconds
- `SPARQL_AGENT_ONTOLOGY_DEFAULT_ONTOLOGIES` - Comma-separated list of default ontologies

### Endpoint Settings
- `SPARQL_AGENT_ENDPOINT_DEFAULT_TIMEOUT` - Default query timeout in seconds
- `SPARQL_AGENT_ENDPOINT_MAX_RETRIES` - Maximum number of retries
- `SPARQL_AGENT_ENDPOINT_RATE_LIMIT_ENABLED` - Enable rate limiting (true/false)
- `SPARQL_AGENT_ENDPOINT_RATE_LIMIT_CALLS` - Max calls per period
- `SPARQL_AGENT_ENDPOINT_RATE_LIMIT_PERIOD` - Rate limit period in seconds

### LLM Settings
- `SPARQL_AGENT_LLM_MODEL_NAME` - LLM model name
- `SPARQL_AGENT_LLM_TEMPERATURE` - Temperature for generation (0.0-2.0)
- `SPARQL_AGENT_LLM_MAX_TOKENS` - Maximum tokens for response
- `SPARQL_AGENT_LLM_API_KEY` - API key for LLM service
- `SPARQL_AGENT_LLM_API_BASE_URL` - Base URL for LLM API

### Logging Settings
- `SPARQL_AGENT_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `SPARQL_AGENT_LOG_JSON_ENABLED` - Enable JSON logging (true/false)
- `SPARQL_AGENT_LOG_FILE_ENABLED` - Enable file logging (true/false)
- `SPARQL_AGENT_LOG_FILE_PATH` - Log file path

**Example:**
```bash
# Set environment variables
export SPARQL_AGENT_ENDPOINT_DEFAULT_TIMEOUT=120
export SPARQL_AGENT_LLM_MODEL_NAME=gpt-4
export SPARQL_AGENT_LLM_API_KEY=sk-...
export SPARQL_AGENT_LOG_LEVEL=DEBUG

# Run with environment configuration
sparql-agent query "Find all proteins"
```

## Configuration Files

SPARQL Agent loads configuration from YAML files in the config directory:

### endpoints.yaml

Configure SPARQL endpoints:

```yaml
endpoints:
  uniprot:
    url: https://rdf.uniprot.org/sparql
    description: UniProt SPARQL endpoint
    timeout: 60

  wikidata:
    url: https://query.wikidata.org/sparql
    description: Wikidata Query Service
    timeout: 30

  local:
    url: http://localhost:3030/dataset
    description: Local Fuseki server
    timeout: 30
```

### ontologies.yaml

Configure ontology mappings:

```yaml
ontologies:
  go:
    id: go
    name: Gene Ontology
    url: http://purl.obolibrary.org/obo/go.owl

  efo:
    id: efo
    name: Experimental Factor Ontology
    url: https://www.ebi.ac.uk/efo/efo.owl
```

### prompts.yaml

Configure prompt templates:

```yaml
prompts:
  basic_query:
    template: |
      Generate a SPARQL query for: {query}

      Available prefixes:
      {prefixes}

      Schema information:
      {schema}
```

## Output Formats

### JSON
```json
{
  "results": {
    "bindings": [
      {
        "protein": {
          "type": "uri",
          "value": "http://purl.uniprot.org/uniprot/P12345"
        },
        "label": {
          "type": "literal",
          "value": "Example protein"
        }
      }
    ]
  },
  "metadata": {
    "execution_time": 0.234,
    "result_count": 1
  }
}
```

### CSV
```csv
protein,label
http://purl.uniprot.org/uniprot/P12345,Example protein
```

### Table (requires pandas)
```
                                 protein          label
0  http://purl.uniprot.org/uniprot/P12345  Example protein
```

## Error Handling

The CLI provides detailed error messages:

```bash
# Query generation error
sparql-agent query "invalid query concept"
# Error: Could not generate query from natural language

# Endpoint error
sparql-agent query "find proteins" --endpoint http://invalid-url
# Error: Failed to connect to endpoint

# Validation error
sparql-agent validate broken-query.sparql
# Error: Syntax error at line 5: Missing closing brace
```

Use `--verbose` for more details and `--debug` for full stack traces.

## Tips and Best Practices

1. **Use ontology mapping** for domain-specific queries:
   ```bash
   sparql-agent query "genes related to cancer" --ontology mondo
   ```

2. **Always set limits** for large datasets:
   ```bash
   sparql-agent query "list all proteins" --limit 1000
   ```

3. **Validate queries** before execution:
   ```bash
   sparql-agent validate query.sparql && sparql-agent query ...
   ```

4. **Save discovery results** for reuse:
   ```bash
   sparql-agent discover $ENDPOINT -o endpoint-info.json
   ```

5. **Use CSV output** for data analysis:
   ```bash
   sparql-agent query "find proteins" --format csv > data.csv
   ```

6. **Chain commands** with Unix pipes:
   ```bash
   sparql-agent query "list genes" --format json | jq '.results.bindings'
   ```

## Troubleshooting

### Command not found

```bash
# Install in development mode
pip install -e .

# Or ensure the package is installed
pip install sparql-agent
```

### Import errors

```bash
# Install all dependencies
pip install -r requirements.txt

# Install optional dependencies for specific features
pip install pandas  # For table format
pip install pyyaml  # For YAML format
```

### Timeout errors

```bash
# Increase timeout
sparql-agent query "complex query" --timeout 300

# Or configure globally
export SPARQL_AGENT_ENDPOINT_DEFAULT_TIMEOUT=300
```

## Advanced Usage

### Scripting

```bash
#!/bin/bash

# Batch query processing
for concept in "protein" "gene" "disease"; do
  sparql-agent query "find all $concept" \
    --endpoint $ENDPOINT \
    --format csv \
    -o "${concept}_results.csv"
done
```

### Integration with other tools

```bash
# Use with jq for JSON processing
sparql-agent query "find proteins" --format json | \
  jq '.results.bindings[] | .protein.value'

# Use with csvkit for CSV analysis
sparql-agent query "list genes" --format csv | \
  csvstat

# Pipe to database
sparql-agent query "get data" --format csv | \
  psql -c "COPY my_table FROM STDIN WITH CSV HEADER"
```

## See Also

- [Configuration Guide](./CONFIGURATION.md)
- [API Documentation](./API.md)
- [Ontology Integration](./ONTOLOGY.md)
- [Examples](../examples/)
