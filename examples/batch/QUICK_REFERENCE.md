# Batch Processing Quick Reference

## Commands at a Glance

### batch-query
Execute multiple SPARQL queries
```bash
sparql-agent batch batch-query FILE --endpoint URL [OPTIONS]
```

### bulk-discover
Discover endpoint capabilities
```bash
sparql-agent batch bulk-discover FILE [OPTIONS]
```

### generate-examples
Generate query examples
```bash
sparql-agent batch generate-examples SCHEMA [OPTIONS]
```

## Common Options

| Option | Short | Values | Default | Description |
|--------|-------|--------|---------|-------------|
| `--format` | `-f` | text/json/yaml/csv | text | Input format |
| `--output` | `-o` | path | batch-results | Output directory |
| `--parallel` | - | flag | enabled | Parallel processing |
| `--workers` | `-w` | 1-32 | 4 | Worker threads |
| `--timeout` | `-t` | seconds | 60 | Timeout per item |
| `--retry` | `-r` | 0-10 | 2 | Retry attempts |
| `--verbose` | `-v` | flag | disabled | Verbose output |

## Quick Examples

### Process Text File
```bash
sparql-agent batch batch-query queries.txt \
  --endpoint https://sparql.uniprot.org/sparql
```

### Process JSON with Metadata
```bash
sparql-agent batch batch-query queries.json \
  --format json \
  --parallel \
  --workers 8
```

### Discover Endpoints
```bash
sparql-agent batch bulk-discover endpoints.txt \
  --output discovery/
```

### High-Performance Processing
```bash
sparql-agent batch batch-query queries.json \
  --parallel \
  --workers 16 \
  --timeout 300 \
  --retry 3
```

## Input Formats

### TEXT
One item per line, `#` for comments
```text
SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10
Find all proteins
```

### JSON
Array of objects with metadata
```json
[
  {
    "id": "q1",
    "query": "SELECT * WHERE { ?s ?p ?o }",
    "metadata": {"type": "basic"}
  }
]
```

### YAML
Hierarchical configuration
```yaml
- id: q1
  query: SELECT * WHERE { ?s ?p ?o }
  metadata:
    type: basic
```

### CSV
Tabular data
```csv
id,query,description
q1,SELECT * WHERE { ?s ?p ?o },Basic query
```

## Output Structure

```
output-dir/
├── individual/          # Individual results
│   ├── item_001.json
│   └── ...
├── results.json         # Consolidated results
├── errors.json          # Error details
└── batch.log           # Process log
```

## Performance Tuning

### Light Load (< 100 items)
```bash
--workers 2 --timeout 30
```

### Medium Load (100-1000 items)
```bash
--workers 8 --timeout 60
```

### Heavy Load (1000+ items)
```bash
--workers 16 --timeout 300
```

## Error Handling

### Continue on Errors
```bash
# Default behavior - continues processing
```

### Fail Fast
```bash
# Custom implementation needed
```

### Retry Configuration
```bash
--retry 3  # Retry failed items 3 times
```

## Common Patterns

### Production Workflow
```bash
sparql-agent batch batch-query queries.json \
  --endpoint https://prod.endpoint/sparql \
  --parallel --workers 16 --timeout 300 --retry 3 \
  --output-mode both --output results/ --verbose
```

### Development Testing
```bash
sparql-agent batch batch-query queries.txt \
  --endpoint https://test.endpoint/sparql \
  --sequential --timeout 60 --verbose
```

### Endpoint Monitoring
```bash
sparql-agent batch bulk-discover endpoints.yaml \
  --format yaml --parallel --workers 8 \
  --output monitoring/$(date +%Y%m%d)/
```

## Troubleshooting

### High Failure Rate
```bash
--timeout 180 --retry 5 --workers 2
```

### Slow Processing
```bash
--parallel --workers 16 --timeout 30
```

### Memory Issues
```bash
--sequential --workers 2
```

### Rate Limiting
```bash
--sequential --timeout 120
```

## Help Commands

```bash
# Main help
sparql-agent batch --help

# Command help
sparql-agent batch batch-query --help
sparql-agent batch bulk-discover --help
sparql-agent batch generate-examples --help
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 130 | Interrupted (Ctrl+C) |

## Environment Variables

```bash
# Set default endpoint
export SPARQL_ENDPOINT="https://sparql.uniprot.org/sparql"

# Increase verbosity
export SPARQL_AGENT_VERBOSE=1

# Set output directory
export SPARQL_AGENT_OUTPUT="./results"
```

## Tips & Tricks

1. **Start small**: Test with 5-10 items first
2. **Use metadata**: Add descriptions and priorities
3. **Monitor progress**: Enable verbose mode during development
4. **Save both**: Use `--output-mode both` for flexibility
5. **Check errors**: Always review `errors.json`
6. **Adjust workers**: Match to your system resources
7. **Set timeouts**: Account for query complexity
8. **Enable retries**: Handle transient failures

## Integration

### With Shell Scripts
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
sparql-agent batch batch-query queries.json \
  --endpoint "$ENDPOINT" \
  --output "results/$DATE/"
```

### With Python
```python
import subprocess
result = subprocess.run([
    'sparql-agent', 'batch', 'batch-query',
    'queries.json',
    '--endpoint', 'https://endpoint/sparql',
    '--output', 'results/'
])
```

### With CI/CD
```yaml
- name: Run SPARQL Tests
  run: |
    sparql-agent batch batch-query tests/queries.json \
      --endpoint ${{ secrets.SPARQL_ENDPOINT }} \
      --output test-results/
```

## Resources

- Full Documentation: `/docs/batch-processing.md`
- Examples: `/examples/batch/`
- Tests: `/src/sparql_agent/cli/test_batch.py`
- Implementation: `/src/sparql_agent/cli/batch.py`

## Support

For issues or questions:
- GitHub Issues
- Documentation
- Example files
