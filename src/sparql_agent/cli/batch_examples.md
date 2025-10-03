# Batch Processing CLI Examples

This document provides comprehensive examples for using the SPARQL Agent batch processing commands.

## Table of Contents

- [Batch Query Processing](#batch-query-processing)
- [Bulk Endpoint Discovery](#bulk-endpoint-discovery)
- [Example Generation](#example-generation)
- [Benchmarking](#benchmarking)
- [Query Migration](#query-migration)
- [Advanced Features](#advanced-features)

## Batch Query Processing

### Basic Batch Query Execution

Execute multiple queries from a text file:

```bash
# queries.txt contains one query per line
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --parallel --workers 4
```

### JSON Input Format

Process queries with metadata from JSON:

```json
// queries.json
[
  {
    "id": "query_1",
    "query": "SELECT ?protein WHERE { ?protein a <http://purl.uniprot.org/core/Protein> } LIMIT 10",
    "metadata": {
      "category": "proteins",
      "expected_results": ">= 10"
    }
  },
  {
    "id": "query_2",
    "query": "Find all human proteins",
    "metadata": {
      "type": "natural_language"
    }
  }
]
```

```bash
sparql-agent batch batch-query queries.json \
    --endpoint https://sparql.uniprot.org/sparql \
    --format json \
    --output batch-results/
```

### CSV Input Format

Process queries from CSV with additional columns:

```csv
id,query,description,timeout
q1,SELECT ?s WHERE { ?s ?p ?o } LIMIT 10,Basic query,30
q2,SELECT ?class WHERE { ?s a ?class } LIMIT 20,Find all classes,45
```

```bash
sparql-agent batch batch-query queries.csv \
    --endpoint https://query.wikidata.org/sparql \
    --format csv \
    --timeout 60
```

### Advanced Processing Options

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --parallel --workers 8 \
    --retry 3 \
    --timeout 120 \
    --output-mode both \
    --strategy hybrid \
    --verbose
```

## Bulk Endpoint Discovery

### Discover Multiple Endpoints

```bash
# endpoints.txt
https://sparql.uniprot.org/sparql
https://query.wikidata.org/sparql
https://dbpedia.org/sparql
```

```bash
sparql-agent batch bulk-discover endpoints.txt \
    --output discovery-results/ \
    --parallel --workers 4
```

### YAML Configuration Format

```yaml
# endpoints.yaml
- id: uniprot
  endpoint: https://sparql.uniprot.org/sparql
  description: UniProt SPARQL endpoint
- id: wikidata
  endpoint: https://query.wikidata.org/sparql
  description: Wikidata query service
- id: dbpedia
  endpoint: https://dbpedia.org/sparql
  description: DBpedia SPARQL endpoint
```

```bash
sparql-agent batch bulk-discover endpoints.yaml \
    --format yaml \
    --timeout 60 \
    --output discovery/
```

## Example Generation

### Generate Query Examples from Schema

```bash
sparql-agent batch generate-examples schema.ttl \
    --count 100 \
    --output examples.json \
    --format json
```

### Generate Specific Query Patterns

```bash
sparql-agent batch generate-examples schema.ttl \
    --count 50 \
    --patterns "basic,filter,aggregate,optional" \
    --output examples/ \
    --format sparql
```

## Benchmarking

### Benchmark Queries Across Endpoints

Create queries file:
```json
// benchmark_queries.json
[
  {"id": "q1", "query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 100"},
  {"id": "q2", "query": "SELECT DISTINCT ?type WHERE { ?s a ?type } LIMIT 50"}
]
```

Create endpoints file:
```yaml
# endpoints.yaml
- id: endpoint1
  endpoint: https://sparql.uniprot.org/sparql
- id: endpoint2
  endpoint: https://dbpedia.org/sparql
```

Run benchmark:
```bash
sparql-agent batch benchmark \
    benchmark_queries.json \
    endpoints.yaml \
    --iterations 5 \
    --warmup 2 \
    --timeout 60 \
    --report-format html \
    --output benchmark-results/
```

### Quick Performance Comparison

```bash
sparql-agent batch benchmark queries.txt endpoints.txt \
    --iterations 3 \
    --report-format csv \
    --output perf-results/
```

## Query Migration

### Basic Migration

```bash
sparql-agent batch migrate-queries \
    old-queries.sparql \
    new-queries.sparql \
    --validate
```

### Migration with Testing

```bash
sparql-agent batch migrate-queries \
    queries.json \
    migrated-queries.json \
    --source-endpoint https://old.endpoint/sparql \
    --target-endpoint https://new.endpoint/sparql \
    --test-execution \
    --update-prefixes \
    --diff
```

### Migration Output

The migration will produce:
- `migrated-queries.json` - Migrated queries
- `migrated-queries_diff.txt` - Side-by-side comparison
- `migration.log` - Detailed migration log

## Advanced Features

### Rate Limiting

Limit requests to avoid overwhelming endpoints:

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://api.example.com/sparql \
    --rate-limit 5.0 \
    --parallel --workers 2
```

### Result Deduplication

Remove duplicate results:

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --deduplicate
```

### Endpoint Health Monitoring

Monitor endpoint health during batch processing:

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --monitor-health \
    --output results/

# Health report saved to: results/endpoint_health.json
```

### Query Optimization Suggestions

Get optimization suggestions for queries:

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --optimize-queries \
    --output results/

# Suggestions saved to: results/query_optimizations.json
```

### Resume from Checkpoint

Resume interrupted batch jobs:

```bash
# Start a batch job
sparql-agent batch batch-query large-batch.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --resume \
    --checkpoint-interval 10 \
    --output results/

# If interrupted, resume with the same command:
sparql-agent batch batch-query large-batch.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --resume \
    --checkpoint-interval 10 \
    --output results/
```

### All Advanced Features Combined

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --parallel --workers 4 \
    --rate-limit 10.0 \
    --deduplicate \
    --monitor-health \
    --optimize-queries \
    --resume \
    --checkpoint-interval 20 \
    --retry 3 \
    --output-mode both \
    --output results/ \
    --verbose
```

## Integration with Job Queue

### Export to Job Queue Format

Process results and integrate with external systems:

```bash
# Process batch and export results
sparql-agent batch batch-query queries.json \
    --endpoint https://sparql.uniprot.org/sparql \
    --output-mode consolidated \
    --format json \
    --output job-queue/

# Results can be consumed by job queue systems
```

## Output File Structure

After running batch commands, you'll get:

```
output-directory/
├── checkpoint.json              # Resume checkpoint
├── results.json                 # Consolidated results
├── errors.json                  # Failed items
├── endpoint_health.json         # Health monitoring data
├── query_optimizations.json     # Optimization suggestions
├── batch.log                    # Detailed logs
└── individual/                  # Individual result files
    ├── query_1.json
    ├── query_2.json
    └── ...
```

## Error Handling Examples

### Continue on Error

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --continue-on-error \
    --save-errors \
    --output results/
```

### Strict Mode (Stop on First Error)

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --no-continue-on-error
```

## Performance Tuning

### High Throughput Configuration

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --parallel --workers 16 \
    --timeout 30 \
    --retry 1 \
    --output results/
```

### Conservative Configuration (Reliable)

```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --sequential \
    --timeout 120 \
    --retry 5 \
    --rate-limit 2.0 \
    --output results/
```

## Tips and Best Practices

1. **Start Small**: Test with a small subset before processing large batches
2. **Use Checkpoints**: Enable checkpoints for long-running jobs
3. **Monitor Health**: Use health monitoring to detect endpoint issues early
4. **Optimize Queries**: Review optimization suggestions to improve performance
5. **Rate Limiting**: Use rate limiting for public endpoints to be respectful
6. **Parallel Processing**: Adjust worker count based on endpoint capacity
7. **Result Deduplication**: Enable for queries that might return duplicates
8. **Error Handling**: Always review errors.json after batch completion
9. **Verbose Logging**: Use --verbose for debugging and troubleshooting
10. **Output Formats**: Choose appropriate output format for downstream processing
