# SPARQL Agent CLI - Quick Reference Card

## Installation

```bash
uv sync                              # Install dependencies
uv run sparql-agent --help           # Show help
```

## Common Commands

### Query SPARQL Endpoints

```bash
# Natural language query
uv run sparql-agent query "Find all proteins from human"

# With specific endpoint
uv run sparql-agent query "Show diseases" -e https://sparql.uniprot.org/sparql

# Save to file
uv run sparql-agent query "List genes" --output results.csv --format csv

# Show generated SPARQL
uv run sparql-agent query "Find classes" --show-sparql --no-execute

# Use ontology
uv run sparql-agent query "DNA binding" --ontology go
```

### Discover Endpoints

```bash
# Discover capabilities
uv run sparql-agent discover https://query.wikidata.org/sparql

# Save discovery results
uv run sparql-agent discover URL --output info.json

# Deep schema analysis
uv run sparql-agent discover URL --analyze-schema
```

### Validate Queries

```bash
# Validate SPARQL file
uv run sparql-agent validate query.sparql

# Strict validation
uv run sparql-agent validate query.rq --strict
```

### Ontology Search

```bash
# Search for terms
uv run sparql-agent ontology search "diabetes"

# Search in specific ontology
uv run sparql-agent ontology search "DNA" --ontology go

# List ontologies
uv run sparql-agent ontology list

# Get ontology info
uv run sparql-agent ontology info efo
```

### Batch Processing

```bash
# Batch queries
uv run sparql-agent batch batch-query queries.txt -e URL

# Multiple endpoints discovery
uv run sparql-agent batch bulk-discover endpoints.txt

# Benchmark queries
uv run sparql-agent batch benchmark queries.json endpoints.yaml
```

### Configuration

```bash
# Show configuration
uv run sparql-agent config show

# List endpoints
uv run sparql-agent config list-endpoints

# Use custom config
uv run sparql-agent --config /path/to/config.yaml COMMAND
```

### Server & Interactive

```bash
# Start API server
uv run sparql-agent serve

# Custom port
uv run sparql-agent serve --port 8080

# Interactive shell
uv run sparql-agent interactive
```

## Global Options

```bash
-v, --verbose              # Verbose output (-v: INFO, -vv: DEBUG)
--debug                    # Debug mode with stack traces
--config FILE              # Configuration file
--profile NAME             # Configuration profile
```

## Output Formats

```bash
--format json              # JSON output (default for most)
--format csv               # CSV output
--format tsv               # TSV output
--format table             # Pretty table (default for query)
--format sparql            # SPARQL query only
```

## Environment Variables

```bash
export SPARQL_AGENT_ENDPOINT="https://sparql.uniprot.org/sparql"
export SPARQL_AGENT_LLM__API_KEY="your-api-key"
export SPARQL_AGENT_LLM__MODEL_NAME="gpt-4"
export SPARQL_AGENT_CONFIG="/path/to/config.yaml"
```

## Interactive Shell Commands

```
.connect URL               # Connect to endpoint
.disconnect                # Disconnect from endpoint
.ontology search TERM      # Search ontology
.export FILE FORMAT        # Export results
.history                   # Show history
.clear                     # Clear screen
.help                      # Show help
.exit                      # Exit shell
```

## Quick Examples

### Complete Workflow

```bash
# 1. Discover endpoint
uv run sparql-agent discover https://sparql.uniprot.org/sparql \
  --output uniprot-info.json

# 2. Search ontology
uv run sparql-agent ontology search "insulin" --ontology efo

# 3. Execute query
uv run sparql-agent query "Find proteins related to insulin" \
  -e https://sparql.uniprot.org/sparql \
  --format csv \
  --output results.csv \
  -v

# 4. Validate and format
uv run sparql-agent validate query.sparql
uv run sparql-agent format results.json --output-format html
```

### Batch Processing

```bash
# Create queries file
cat > queries.txt << EOF
Find proteins from human
Show diseases related to diabetes
List genes with GO term DNA binding
EOF

# Process in batch
uv run sparql-agent batch batch-query queries.txt \
  -e https://sparql.uniprot.org/sparql \
  --parallel --workers 8 \
  --output batch-results/

# Results in:
# - batch-results/individual/
# - batch-results/results.json
# - batch-results/errors.json
```

### Configuration

```yaml
# config/endpoints.yaml
endpoints:
  uniprot:
    url: https://sparql.uniprot.org/sparql
    timeout: 60
  wikidata:
    url: https://query.wikidata.org/sparql
    rate_limit: 10
```

## Tips

1. **Use verbose mode** for debugging: `-v` or `-vv`
2. **Set default endpoint** in environment: `SPARQL_AGENT_ENDPOINT`
3. **Save frequently used configs** in `config/` directory
4. **Use batch commands** for multiple operations
5. **Check endpoint first** with `discover` command
6. **Validate queries** before execution on production
7. **Use interactive mode** for exploration
8. **Save results to files** for large datasets

## Getting Help

```bash
sparql-agent --help                    # General help
sparql-agent COMMAND --help            # Command help
sparql-agent batch SUBCOMMAND --help   # Sub-command help
```

## Documentation

- Full Reference: `docs/CLI_REFERENCE.md`
- Implementation: `CLI_IMPLEMENTATION_COMPLETE.md`
- Project README: `README.md`

## Common Issues

**Module not found**: Run `uv sync` to install dependencies

**No endpoint specified**: Use `--endpoint URL` or set `SPARQL_AGENT_ENDPOINT`

**Permission denied**: Check file permissions and paths

**Timeout errors**: Increase with `--timeout SECONDS`

**Import errors**: Ensure all dependencies installed with `uv sync`

## More Information

- GitHub: https://github.com/david4096/sparql-agent
- Issues: https://github.com/david4096/sparql-agent/issues
- Version: `uv run sparql-agent version`
