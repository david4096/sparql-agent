#!/bin/bash
#
# SPARQL Agent CLI Examples
#
# This script demonstrates various CLI commands and workflows.
# Uncomment and run the examples you want to try.

# ============================================================================
# Setup
# ============================================================================

# Set common variables
UNIPROT_ENDPOINT="https://rdf.uniprot.org/sparql"
WIKIDATA_ENDPOINT="https://query.wikidata.org/sparql"

# ============================================================================
# Basic Query Examples
# ============================================================================

echo "=== Basic Query Examples ==="

# Simple query
# sparql-agent query "Find all proteins from human" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --limit 10

# Query with ontology mapping
# sparql-agent query "Show diseases related to diabetes" \
#   --endpoint $WIKIDATA_ENDPOINT \
#   --ontology mondo \
#   --format table

# Just generate SPARQL without executing
# sparql-agent query "List genes with GO term DNA binding" \
#   --ontology go \
#   --no-execute \
#   --show-sparql

# Query with CSV output
# sparql-agent query "Find human proteins involved in metabolism" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --format csv \
#   --limit 100 > proteins.csv

# ============================================================================
# Discovery Examples
# ============================================================================

echo "=== Endpoint Discovery Examples ==="

# Discover Wikidata endpoint
# sparql-agent discover $WIKIDATA_ENDPOINT \
#   --format text

# Save discovery results
# sparql-agent discover $UNIPROT_ENDPOINT \
#   --output uniprot-discovery.json

# Discover local endpoint
# sparql-agent discover http://localhost:3030/dataset \
#   --timeout 60 \
#   --format yaml

# ============================================================================
# Validation Examples
# ============================================================================

echo "=== Query Validation Examples ==="

# Create a sample query file
cat > sample_query.sparql << 'EOF'
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?protein ?label
WHERE {
  ?protein a <http://purl.uniprot.org/core/Protein> .
  ?protein rdfs:label ?label .
  FILTER(CONTAINS(?label, "kinase"))
}
LIMIT 100
EOF

# Validate the query
# sparql-agent validate sample_query.sparql

# Strict validation with JSON output
# sparql-agent validate sample_query.sparql \
#   --strict \
#   --format json > validation_report.json

# Clean up
rm -f sample_query.sparql

# ============================================================================
# Ontology Search Examples
# ============================================================================

echo "=== Ontology Search Examples ==="

# Search for diabetes across all ontologies
# sparql-agent ontology search "diabetes" \
#   --limit 10

# Search Gene Ontology for DNA binding
# sparql-agent ontology search "DNA binding" \
#   --ontology go \
#   --limit 5

# Exact match with JSON output
# sparql-agent ontology search "Homo sapiens" \
#   --exact \
#   --format json

# Export search results to CSV
# sparql-agent ontology search "cancer" \
#   --ontology mondo \
#   --format csv \
#   --limit 50 > disease_terms.csv

# List available ontologies
# sparql-agent ontology list

# Get information about specific ontology
# sparql-agent ontology info efo
# sparql-agent ontology info mondo --format json

# ============================================================================
# Formatting Examples
# ============================================================================

echo "=== Result Formatting Examples ==="

# First, execute a query and save results
# sparql-agent query "Find proteins" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --limit 10 \
#   --format json > results.json

# Convert JSON to CSV
# sparql-agent format results.json \
#   --output-format csv \
#   -o results.csv

# Display as table
# sparql-agent format results.json \
#   --output-format table

# Convert to HTML
# sparql-agent format results.json \
#   --output-format html \
#   -o results.html

# Pretty-print JSON
# sparql-agent format results.json \
#   --output-format json \
#   --pretty

# Clean up
rm -f results.json results.csv results.html

# ============================================================================
# Configuration Examples
# ============================================================================

echo "=== Configuration Examples ==="

# Show current configuration
# sparql-agent config show

# Show configuration as JSON
# sparql-agent config show --format json

# List configured endpoints
# sparql-agent config list-endpoints

# ============================================================================
# Advanced Workflows
# ============================================================================

echo "=== Advanced Workflow Examples ==="

# Workflow 1: Discover, Generate, Execute, Format
# 1. Discover endpoint capabilities
# sparql-agent discover $UNIPROT_ENDPOINT -o endpoint_info.json

# 2. Generate query with ontology
# sparql-agent query "proteins related to cancer" \
#   --ontology mondo \
#   --no-execute \
#   --show-sparql > generated_query.sparql

# 3. Validate the query
# sparql-agent validate generated_query.sparql

# 4. Execute and format
# sparql-agent query "proteins related to cancer" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --ontology mondo \
#   --format csv > cancer_proteins.csv

# Workflow 2: Batch Processing
# Create a list of search terms
cat > terms.txt << 'EOF'
diabetes
cancer
alzheimer
parkinson
EOF

# Process each term
# while read -r term; do
#   echo "Processing: $term"
#   sparql-agent ontology search "$term" \
#     --format json > "${term}_ontology.json"
#
#   sparql-agent query "Find genes related to $term" \
#     --endpoint $UNIPROT_ENDPOINT \
#     --format csv > "${term}_genes.csv"
# done < terms.txt

# Clean up
rm -f terms.txt

# Workflow 3: Pipeline with jq
# sparql-agent query "find proteins" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --format json | \
#   jq '.results.bindings[] | {
#     protein: .protein.value,
#     label: .label.value
#   }'

# ============================================================================
# Server Examples
# ============================================================================

echo "=== Server Examples ==="

# Start server on default port (8000)
# sparql-agent serve

# Start server on custom port
# sparql-agent serve --port 8080

# Start with public access
# sparql-agent serve --host 0.0.0.0 --port 8000

# Development mode with auto-reload
# sparql-agent serve --reload

# Test the server with curl
# curl -X POST http://localhost:8000/query \
#   -H "Content-Type: application/json" \
#   -d '{
#     "query": "Find all proteins",
#     "endpoint": "https://rdf.uniprot.org/sparql",
#     "format": "json"
#   }'

# ============================================================================
# Using Environment Variables
# ============================================================================

echo "=== Environment Variable Examples ==="

# Set configuration via environment
# export SPARQL_AGENT_ENDPOINT_DEFAULT_TIMEOUT=120
# export SPARQL_AGENT_LLM_MODEL_NAME=gpt-4
# export SPARQL_AGENT_LOG_LEVEL=DEBUG

# Run with environment configuration
# sparql-agent query "complex query" --endpoint $UNIPROT_ENDPOINT

# ============================================================================
# Integration Examples
# ============================================================================

echo "=== Integration Examples ==="

# With csvkit (requires csvkit: pip install csvkit)
# sparql-agent query "list genes" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --format csv | \
#   csvstat

# With pandas (requires pandas: pip install pandas)
# sparql-agent query "get proteins" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --format csv | \
#   python -c "import pandas as pd; df = pd.read_csv('/dev/stdin'); print(df.describe())"

# Pipe to database (PostgreSQL)
# sparql-agent query "get data" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --format csv | \
#   psql -c "COPY my_table FROM STDIN WITH CSV HEADER"

# Save to SQLite
# sparql-agent query "get proteins" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --format csv | \
#   sqlite3 proteins.db ".import /dev/stdin proteins"

# ============================================================================
# Error Handling Examples
# ============================================================================

echo "=== Error Handling Examples ==="

# Handle invalid queries gracefully
# sparql-agent query "this is probably not going to work" || \
#   echo "Query generation failed, falling back to default"

# Retry with timeout on failure
# sparql-agent query "complex query" \
#   --endpoint $UNIPROT_ENDPOINT \
#   --timeout 60 || \
#   sparql-agent query "complex query" \
#     --endpoint $UNIPROT_ENDPOINT \
#     --timeout 120

# Validate before executing
# if sparql-agent validate query.sparql; then
#   echo "Query is valid, executing..."
#   # Execute the query
# else
#   echo "Query validation failed"
#   exit 1
# fi

# ============================================================================
# Verbose and Debug Examples
# ============================================================================

echo "=== Verbose and Debug Examples ==="

# Verbose output
# sparql-agent -v query "find proteins" \
#   --endpoint $UNIPROT_ENDPOINT

# Debug mode (includes stack traces)
# sparql-agent --debug query "find proteins" \
#   --endpoint $UNIPROT_ENDPOINT

# ============================================================================
# End
# ============================================================================

echo ""
echo "Examples completed!"
echo ""
echo "To run an example, uncomment it in this script and execute:"
echo "  bash cli_examples.sh"
echo ""
echo "Or copy individual commands to your terminal."
