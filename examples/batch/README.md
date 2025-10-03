# Batch Processing Examples

This directory contains examples for using SPARQL Agent's batch processing capabilities.

## Overview

The batch processing module provides three main commands:

1. **batch-query**: Execute multiple SPARQL queries in parallel
2. **bulk-discover**: Discover capabilities of multiple endpoints
3. **generate-examples**: Generate query examples from schemas

## Input Formats

All batch commands support multiple input formats:

### TEXT Format
One item per line, comments with `#`:

```text
# queries.txt
SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10
Find all proteins from human
Show diseases related to diabetes
```

### JSON Format
Structured data with metadata:

```json
[
  {
    "id": "query_001",
    "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
    "metadata": {
      "description": "Basic triple pattern"
    }
  }
]
```

### YAML Format
Hierarchical configuration:

```yaml
- id: uniprot
  endpoint: https://sparql.uniprot.org/sparql
  metadata:
    name: UniProt SPARQL
    domain: proteins
```

### CSV Format
Tabular data:

```csv
id,query,description
query_001,SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10,Basic pattern
```

## Commands

### Batch Query Execution

Execute multiple queries from a file:

```bash
# Basic usage
sparql-agent batch batch-query queries.txt \
  --endpoint https://sparql.uniprot.org/sparql

# With JSON input and parallel processing
sparql-agent batch batch-query queries.json \
  --format json \
  --parallel \
  --workers 8 \
  --output results/

# Generate SPARQL without execution
sparql-agent batch batch-query nl-queries.txt \
  --no-execute \
  --output sparql-queries/

# With retry logic and error handling
sparql-agent batch batch-query queries.txt \
  --endpoint https://sparql.uniprot.org/sparql \
  --retry 3 \
  --timeout 120 \
  --output-mode both
```

**Options:**
- `--endpoint, -e`: SPARQL endpoint URL (required)
- `--format, -f`: Input format (text, json, yaml, csv)
- `--output, -o`: Output directory
- `--output-mode`: individual, consolidated, or both
- `--execute/--no-execute`: Execute queries or just generate
- `--parallel/--sequential`: Processing mode
- `--workers, -w`: Number of parallel workers
- `--timeout, -t`: Timeout per query (seconds)
- `--retry, -r`: Retry attempts
- `--strategy`: Query generation strategy (auto, template, llm, hybrid)

**Output Structure:**
```
batch-results/
├── individual/          # Individual result files
│   ├── query_001.json
│   ├── query_002.json
│   └── ...
├── results.json         # Consolidated results
├── errors.json          # Failed queries
└── batch.log            # Processing log
```

### Bulk Endpoint Discovery

Discover capabilities of multiple endpoints:

```bash
# Basic discovery
sparql-agent batch bulk-discover endpoints.txt \
  --output discovery-results/

# With YAML configuration
sparql-agent batch bulk-discover endpoints.yaml \
  --format yaml \
  --parallel \
  --workers 4

# Sequential with extended timeout
sparql-agent batch bulk-discover endpoints.txt \
  --sequential \
  --timeout 60 \
  --verbose
```

**Options:**
- `--format, -f`: Input format (text, json, yaml, csv)
- `--output, -o`: Output directory
- `--parallel/--sequential`: Processing mode
- `--workers, -w`: Number of parallel workers
- `--timeout, -t`: Discovery timeout per endpoint

**Output Structure:**
```
discovery-results/
├── individual/
│   ├── uniprot.json
│   ├── wikidata.json
│   └── ...
├── results.json         # All discoveries
├── errors.json          # Failed endpoints
└── discovery.log
```

### Generate Query Examples

Generate example queries from schemas:

```bash
# Generate 100 examples
sparql-agent batch generate-examples schema.ttl \
  --count 100 \
  --output examples.json

# Generate specific patterns
sparql-agent batch generate-examples schema.ttl \
  --patterns "basic,filter,aggregate,optional,union" \
  --count 50

# Output as SPARQL files
sparql-agent batch generate-examples schema.ttl \
  --format sparql \
  --output queries/ \
  --verbose
```

**Options:**
- `--count, -c`: Number of examples to generate
- `--output, -o`: Output file/directory
- `--format, -f`: Output format (json, text, sparql)
- `--patterns`: Query patterns to generate

## Examples

### Example 1: Process Mixed Queries

```bash
# queries.txt contains both SPARQL and natural language
sparql-agent batch batch-query queries.txt \
  --endpoint https://sparql.uniprot.org/sparql \
  --parallel \
  --workers 4 \
  --output mixed-results/
```

### Example 2: Discover Multiple Endpoints

```bash
# Discover capabilities in parallel
sparql-agent batch bulk-discover endpoints.yaml \
  --format yaml \
  --parallel \
  --workers 8 \
  --output endpoint-capabilities/
```

### Example 3: Generate Test Queries

```bash
# Generate diverse examples for testing
sparql-agent batch generate-examples schema.ttl \
  --count 200 \
  --patterns "basic,filter,aggregate,optional,union,subquery" \
  --output test-queries.json
```

### Example 4: Production Batch Processing

```bash
# Process production queries with error handling
sparql-agent batch batch-query production-queries.json \
  --format json \
  --endpoint https://production.sparql.endpoint/query \
  --parallel \
  --workers 16 \
  --timeout 300 \
  --retry 3 \
  --output-mode both \
  --output production-results/ \
  --verbose
```

## Performance Tuning

### Parallel Processing

Adjust workers based on your system:

```bash
# Light load (4 workers)
--workers 4

# Medium load (8 workers)
--workers 8

# Heavy load (16 workers)
--workers 16
```

### Timeout Configuration

Set appropriate timeouts:

```bash
# Fast queries
--timeout 30

# Standard queries
--timeout 60

# Complex queries
--timeout 300
```

### Retry Strategy

Configure retry behavior:

```bash
# No retries (fail fast)
--retry 0

# Standard retries
--retry 2

# Aggressive retries
--retry 5
```

## Output Formats

### Consolidated Results (results.json)

```json
{
  "summary": {
    "total_items": 100,
    "successful_items": 95,
    "failed_items": 5,
    "success_rate": "95.00%",
    "total_time": "123.45s",
    "average_time": "1.23s"
  },
  "items": [
    {
      "id": "query_001",
      "status": "success",
      "result": {...},
      "execution_time": 1.23
    }
  ]
}
```

### Error Log (errors.json)

```json
[
  {
    "id": "query_042",
    "input_data": {...},
    "status": "failed",
    "error": "Query timeout after 60s",
    "attempts": 3
  }
]
```

## Advanced Usage

### Custom Input Processing

Create custom input files with metadata:

```json
{
  "id": "complex_query",
  "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o }",
  "metadata": {
    "priority": "high",
    "expected_results": 1000,
    "timeout": 120,
    "tags": ["production", "monitoring"]
  }
}
```

### Filtered Processing

Use metadata to filter or prioritize:

```yaml
- id: high_priority_query
  query: "..."
  metadata:
    priority: high
    execute_first: true
```

### Result Aggregation

Results include detailed metrics:

```json
{
  "execution": {
    "status": "success",
    "row_count": 1234,
    "execution_time": 2.34,
    "variables": ["s", "p", "o"],
    "bindings": [...]
  }
}
```

## Monitoring and Logging

### Progress Tracking

Real-time progress bars show:
- Current item being processed
- Percentage complete
- Time elapsed
- Estimated time remaining

### Log Files

Detailed logs include:
- Timestamp for each operation
- Success/failure status
- Error messages with stack traces
- Performance metrics

### Statistics

Summary statistics provide:
- Total processing time
- Average time per item
- Success rate percentage
- Failure analysis

## Best Practices

1. **Start Small**: Test with a few items before scaling up
2. **Use Appropriate Workers**: Match worker count to system resources
3. **Set Realistic Timeouts**: Account for query complexity
4. **Enable Retries**: Handle transient failures gracefully
5. **Monitor Logs**: Watch for patterns in failures
6. **Save Both Modes**: Use `--output-mode both` for flexibility
7. **Version Input Files**: Track changes to query sets
8. **Document Metadata**: Use metadata fields for context

## Troubleshooting

### High Failure Rate

- Increase timeout: `--timeout 120`
- Reduce workers: `--workers 2`
- Add retries: `--retry 3`
- Check endpoint availability

### Slow Processing

- Increase workers: `--workers 8`
- Use parallel mode: `--parallel`
- Optimize queries
- Check network connectivity

### Memory Issues

- Reduce workers: `--workers 4`
- Process sequentially: `--sequential`
- Split input file into smaller batches
- Use consolidated output only

## Integration

### CI/CD Pipeline

```yaml
# .github/workflows/sparql-tests.yml
- name: Run SPARQL Tests
  run: |
    sparql-agent batch batch-query tests/queries.json \
      --endpoint ${{ secrets.SPARQL_ENDPOINT }} \
      --parallel \
      --workers 4 \
      --output test-results/
```

### Automated Monitoring

```bash
#!/bin/bash
# monitor-endpoints.sh

sparql-agent batch bulk-discover endpoints.txt \
  --output monitoring/$(date +%Y%m%d) \
  --parallel \
  --workers 8
```

### Data Pipeline

```python
# pipeline.py
import subprocess
import json

# Execute batch queries
subprocess.run([
    "sparql-agent", "batch", "batch-query",
    "queries.json",
    "--endpoint", "https://sparql.endpoint/query",
    "--output", "results/"
])

# Process results
with open("results/results.json") as f:
    results = json.load(f)
    # ... process results
```

## Support

For issues or questions:
- Check logs in output directory
- Enable verbose mode: `--verbose`
- Review error details in errors.json
- Consult main documentation
