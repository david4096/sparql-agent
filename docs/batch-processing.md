# Batch Processing CLI Tools

## Overview

The SPARQL Agent batch processing module provides production-ready tools for executing multiple SPARQL queries, discovering endpoints, and generating query examples at scale. Built with parallel processing, comprehensive error handling, and rich progress reporting.

## Architecture

### Core Components

```
sparql_agent/cli/batch.py
├── BatchProcessor           # Core processing engine
├── InputParser             # Multi-format input parsing
├── BatchItem              # Individual item tracking
├── BatchJobConfig         # Job configuration
├── BatchJobResult         # Result aggregation
└── CLI Commands           # Click command interface
```

### Key Features

1. **Parallel Processing**
   - ThreadPoolExecutor for concurrent execution
   - Configurable worker pool size
   - Automatic load balancing
   - Resource-efficient execution

2. **Multiple Input Formats**
   - TEXT: Simple line-by-line format
   - JSON: Structured data with metadata
   - YAML: Hierarchical configurations
   - CSV: Tabular data processing

3. **Progress Reporting**
   - Real-time progress bars (Rich library)
   - Time elapsed and remaining
   - Success/failure tracking
   - Detailed statistics

4. **Error Handling**
   - Automatic retry with exponential backoff
   - Continue-on-error mode
   - Comprehensive error logging
   - Error categorization and analysis

5. **Output Options**
   - Individual result files
   - Consolidated reports
   - Progress tracking files
   - Detailed error logs

## Commands

### 1. batch-query

Execute multiple SPARQL queries from a file.

**Syntax:**
```bash
sparql-agent batch batch-query INPUT_FILE \
  --endpoint ENDPOINT_URL \
  [OPTIONS]
```

**Options:**
- `--endpoint, -e`: SPARQL endpoint URL (required)
- `--format, -f`: Input format (text, json, yaml, csv)
- `--output, -o`: Output directory (default: batch-results)
- `--output-mode`: individual, consolidated, or both
- `--execute/--no-execute`: Execute or just generate queries
- `--parallel/--sequential`: Processing mode
- `--workers, -w`: Number of parallel workers (default: 4)
- `--timeout, -t`: Timeout per query in seconds (default: 60)
- `--retry, -r`: Retry attempts (default: 2)
- `--strategy`: Query generation strategy (auto, template, llm, hybrid)
- `--verbose, -v`: Enable verbose output

**Examples:**

```bash
# Basic batch processing
sparql-agent batch batch-query queries.txt \
  --endpoint https://sparql.uniprot.org/sparql

# High-throughput parallel processing
sparql-agent batch batch-query queries.json \
  --format json \
  --parallel \
  --workers 16 \
  --timeout 300 \
  --output production-results/

# Generate SPARQL without execution
sparql-agent batch batch-query nl-queries.txt \
  --no-execute \
  --output sparql-queries/
```

**Input File Examples:**

TEXT format (queries.txt):
```text
# Comment lines start with #
SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10
Find all proteins from human
Show diseases related to diabetes
```

JSON format (queries.json):
```json
[
  {
    "id": "query_001",
    "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
    "metadata": {
      "description": "Basic triple pattern",
      "expected_results": 10
    }
  }
]
```

**Output Structure:**
```
batch-results/
├── individual/
│   ├── query_001.json
│   ├── query_002.json
│   └── ...
├── results.json         # Consolidated results
├── errors.json          # Failed queries
└── batch.log           # Processing log (if --verbose)
```

### 2. bulk-discover

Discover capabilities of multiple SPARQL endpoints.

**Syntax:**
```bash
sparql-agent batch bulk-discover INPUT_FILE \
  [OPTIONS]
```

**Options:**
- `--format, -f`: Input format (text, json, yaml, csv)
- `--output, -o`: Output directory (default: discovery-results)
- `--parallel/--sequential`: Processing mode
- `--workers, -w`: Number of parallel workers (default: 4)
- `--timeout, -t`: Discovery timeout per endpoint (default: 30)
- `--verbose, -v`: Enable verbose output

**Examples:**

```bash
# Discover from list of URLs
sparql-agent batch bulk-discover endpoints.txt \
  --output discovery-results/

# With YAML configuration
sparql-agent batch bulk-discover endpoints.yaml \
  --format yaml \
  --parallel \
  --workers 8

# Sequential with extended timeout
sparql-agent batch bulk-discover endpoints.txt \
  --sequential \
  --timeout 60 \
  --verbose
```

**Input File Examples:**

TEXT format (endpoints.txt):
```text
https://sparql.uniprot.org/sparql
https://query.wikidata.org/sparql
http://dbpedia.org/sparql
```

YAML format (endpoints.yaml):
```yaml
- id: uniprot
  endpoint: https://sparql.uniprot.org/sparql
  metadata:
    name: UniProt SPARQL
    domain: proteins

- id: wikidata
  endpoint: https://query.wikidata.org/sparql
  metadata:
    name: Wikidata Query Service
    domain: general
```

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

### 3. generate-examples

Generate query examples from schema files.

**Syntax:**
```bash
sparql-agent batch generate-examples SCHEMA_FILE \
  [OPTIONS]
```

**Options:**
- `--count, -c`: Number of examples to generate (default: 100)
- `--output, -o`: Output file (default: examples.json)
- `--format, -f`: Output format (json, text, sparql)
- `--patterns`: Comma-separated query patterns
- `--verbose, -v`: Enable verbose output

**Examples:**

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
  --output queries/
```

## Data Classes

### BatchItem

Represents a single processing item with status tracking:

```python
@dataclass
class BatchItem:
    id: str
    input_data: Any
    metadata: Dict[str, Any]
    status: ProcessingStatus
    result: Optional[Any]
    error: Optional[str]
    attempts: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    execution_time: float
```

### BatchJobConfig

Configuration for batch jobs:

```python
@dataclass
class BatchJobConfig:
    input_file: Path
    input_format: InputFormat
    output_dir: Path
    output_mode: OutputMode
    output_format: str
    parallel: bool
    max_workers: int
    timeout: int
    retry_attempts: int
    retry_delay: float
    continue_on_error: bool
    save_errors: bool
    progress_file: Optional[Path]
    log_file: Optional[Path]
```

### BatchJobResult

Aggregated results from batch processing:

```python
@dataclass
class BatchJobResult:
    total_items: int
    successful_items: int
    failed_items: int
    skipped_items: int
    items: List[BatchItem]
    start_time: datetime
    end_time: datetime
    total_time: float
    statistics: Dict[str, Any]
```

## Usage Patterns

### Pattern 1: High-Throughput Processing

For maximum throughput with robust error handling:

```bash
sparql-agent batch batch-query queries.json \
  --endpoint https://endpoint/sparql \
  --parallel \
  --workers 16 \
  --timeout 300 \
  --retry 3 \
  --output-mode both \
  --output results/
```

**Best For:**
- Production workloads
- Large query sets (1000+)
- Time-critical processing
- High-availability endpoints

### Pattern 2: Careful Sequential Processing

For careful, sequential processing with maximum logging:

```bash
sparql-agent batch batch-query queries.txt \
  --endpoint https://endpoint/sparql \
  --sequential \
  --timeout 120 \
  --retry 5 \
  --output-mode both \
  --output results/ \
  --verbose
```

**Best For:**
- Debugging query issues
- Rate-limited endpoints
- Complex queries
- Development/testing

### Pattern 3: Endpoint Monitoring

For continuous endpoint monitoring:

```bash
#!/bin/bash
# monitor-endpoints.sh

DATE=$(date +%Y%m%d-%H%M)
sparql-agent batch bulk-discover endpoints.yaml \
  --format yaml \
  --parallel \
  --workers 8 \
  --output "monitoring/$DATE/"
```

**Best For:**
- Continuous monitoring
- Health checks
- Capability tracking
- Infrastructure management

### Pattern 4: Test Suite Execution

For running comprehensive test suites:

```bash
sparql-agent batch batch-query test-queries.json \
  --endpoint https://test.endpoint/sparql \
  --parallel \
  --workers 8 \
  --timeout 60 \
  --output test-results/ \
  --verbose
```

**Best For:**
- CI/CD integration
- Regression testing
- Performance testing
- Quality assurance

## Performance Optimization

### Worker Configuration

Choose worker count based on:

```python
# Light load (1-4 workers)
# - Small query sets (< 100)
# - Limited resources
# - Rate-limited endpoints

# Medium load (4-8 workers)
# - Medium query sets (100-1000)
# - Standard servers
# - Normal endpoints

# Heavy load (8-16+ workers)
# - Large query sets (1000+)
# - High-performance servers
# - Robust endpoints
```

### Timeout Strategy

Set timeouts appropriately:

```python
# Fast queries: 30s
# - Simple patterns
# - Small result sets
# - Local endpoints

# Standard queries: 60s
# - Moderate complexity
# - Medium result sets
# - Public endpoints

# Complex queries: 300s+
# - Complex aggregations
# - Large result sets
# - Federation queries
```

### Retry Configuration

Configure retries based on reliability:

```python
# No retries (0)
# - Fast-fail needed
# - Development testing
# - Debugging

# Standard retries (2-3)
# - Production use
# - Stable endpoints
# - Normal errors

# Aggressive retries (5+)
# - Unreliable endpoints
# - Critical queries
# - Network issues
```

## Error Handling

### Error Categories

1. **Query Errors**
   - Syntax errors
   - Validation failures
   - Generation failures

2. **Execution Errors**
   - Timeout errors
   - Connection failures
   - Authentication issues

3. **Endpoint Errors**
   - Unavailable endpoints
   - Rate limiting
   - Server errors

### Error Recovery

Automatic retry with exponential backoff:

```python
retry_delay = base_delay * (2 ** attempt)
# Attempt 1: 1s
# Attempt 2: 2s
# Attempt 3: 4s
```

### Error Reporting

Comprehensive error logs in `errors.json`:

```json
{
  "id": "query_042",
  "input_data": {...},
  "status": "failed",
  "error": "Query timeout after 60s",
  "attempts": 3,
  "start_time": "2025-10-02T10:30:00",
  "end_time": "2025-10-02T10:33:00",
  "execution_time": 180.0
}
```

## Integration

### CI/CD Integration

GitHub Actions example:

```yaml
name: SPARQL Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install SPARQL Agent
        run: pip install sparql-agent

      - name: Run Batch Queries
        run: |
          sparql-agent batch batch-query tests/queries.json \
            --endpoint ${{ secrets.SPARQL_ENDPOINT }} \
            --parallel \
            --workers 4 \
            --output test-results/

      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test-results/
```

### Monitoring Integration

Prometheus metrics example:

```python
#!/usr/bin/env python3
"""Export batch processing metrics to Prometheus."""

import json
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Load results
with open('results/results.json') as f:
    results = json.load(f)

# Create metrics
registry = CollectorRegistry()
success_rate = Gauge('sparql_batch_success_rate',
                     'Batch processing success rate',
                     registry=registry)
avg_time = Gauge('sparql_batch_avg_time',
                'Average query execution time',
                registry=registry)

# Set values
summary = results['summary']
success_rate.set(float(summary['success_rate'].rstrip('%')))
avg_time.set(float(summary['average_time'].rstrip('s')))

# Push to gateway
push_to_gateway('localhost:9091', job='sparql_batch', registry=registry)
```

### Data Pipeline Integration

Apache Airflow DAG example:

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-team',
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    'sparql_batch_processing',
    default_args=default_args,
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1)
) as dag:

    batch_query = BashOperator(
        task_id='execute_batch_queries',
        bash_command='''
            sparql-agent batch batch-query \
              /data/queries/daily-queries.json \
              --endpoint https://sparql.endpoint/query \
              --parallel \
              --workers 8 \
              --output /data/results/{{ ds }}/
        '''
    )
```

## Best Practices

1. **Start Small**
   - Test with 5-10 queries first
   - Verify output format
   - Check error handling
   - Then scale up

2. **Use Metadata**
   - Add descriptions to queries
   - Track expected results
   - Include priority levels
   - Document assumptions

3. **Monitor Progress**
   - Watch success rates
   - Track execution times
   - Analyze error patterns
   - Adjust configuration

4. **Save Results**
   - Use `--output-mode both`
   - Keep error logs
   - Archive results
   - Version control inputs

5. **Optimize Performance**
   - Match workers to resources
   - Set appropriate timeouts
   - Enable parallel processing
   - Use local endpoints when possible

6. **Handle Errors**
   - Enable retries
   - Continue on error
   - Log everything
   - Review failures

7. **Document Configuration**
   - Save job configs
   - Track changes
   - Share best practices
   - Document lessons learned

## Troubleshooting

### Problem: High Failure Rate

**Symptoms:**
- Success rate < 80%
- Many timeout errors
- Connection failures

**Solutions:**
```bash
# Increase timeout
--timeout 180

# Reduce parallelism
--workers 2

# Add more retries
--retry 5

# Sequential processing
--sequential
```

### Problem: Slow Processing

**Symptoms:**
- Long execution times
- Low throughput
- Resource underutilization

**Solutions:**
```bash
# Increase parallelism
--workers 16

# Reduce timeout
--timeout 30

# Use parallel mode
--parallel
```

### Problem: Memory Issues

**Symptoms:**
- Out of memory errors
- System slowdown
- Process crashes

**Solutions:**
```bash
# Reduce workers
--workers 2

# Sequential processing
--sequential

# Split into smaller batches
# Process in chunks
```

### Problem: Rate Limiting

**Symptoms:**
- 429 errors
- Consistent failures
- Slow responses

**Solutions:**
```bash
# Sequential processing
--sequential

# Longer timeouts
--timeout 120

# Fewer workers
--workers 2
```

## Advanced Topics

### Custom Processing Functions

Extend batch processing with custom logic:

```python
from sparql_agent.cli.batch import BatchProcessor, BatchItem

def custom_processor(item: BatchItem, **kwargs) -> dict:
    """Custom processing function."""
    # Extract data
    query = item.input_data['query']

    # Custom logic
    result = {
        'query': query,
        'processed': True,
        'custom_field': 'value'
    }

    return result

# Use custom processor
processor = BatchProcessor(config)
processor.load_items()
result = processor.process(custom_processor, custom_param='value')
```

### Result Post-Processing

Process results after batch completion:

```python
import json
from pathlib import Path

def analyze_results(results_file: Path):
    """Analyze batch results."""
    with open(results_file) as f:
        results = json.load(f)

    # Extract metrics
    items = results['items']
    execution_times = [item['execution_time']
                      for item in items
                      if item['status'] == 'success']

    # Calculate statistics
    avg_time = sum(execution_times) / len(execution_times)
    max_time = max(execution_times)
    min_time = min(execution_times)

    print(f"Average: {avg_time:.2f}s")
    print(f"Max: {max_time:.2f}s")
    print(f"Min: {min_time:.2f}s")

# Analyze
analyze_results(Path('results/results.json'))
```

## API Reference

See the inline documentation in `sparql_agent/cli/batch.py` for complete API reference.

## Examples

Complete examples are available in `/examples/batch/`:
- `queries.txt` - Text format examples
- `queries.json` - JSON format examples
- `queries.csv` - CSV format examples
- `endpoints.yaml` - YAML format examples
- `usage_example.py` - Programmatic usage
- `README.md` - Detailed examples

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/david4096/sparql-agent/issues
- Documentation: https://sparql-agent.readthedocs.io
- Examples: `/examples/batch/`
