# SPARQL Agent Batch Processing Implementation

## Overview

This document describes the comprehensive batch processing CLI tools implemented for the SPARQL Agent. The implementation provides powerful, production-ready capabilities for processing multiple SPARQL queries, endpoints, and related operations at scale.

## Implementation Summary

### File Structure
- **Main Implementation**: `/src/sparql_agent/cli/batch.py` (2,450 lines)
- **Test Suite**: `/src/sparql_agent/cli/test_batch.py`
- **Examples**: `/src/sparql_agent/cli/batch_examples.md`
- **Documentation**: This file

## Core Components

### 1. Data Classes and Enums

#### InputFormat
Supported input formats for batch processing:
- TEXT - One query per line
- JSON - Structured data with metadata
- YAML - Configuration-style input
- CSV - Tabular data format

#### OutputMode
Output modes for results:
- INDIVIDUAL - Separate file per result
- CONSOLIDATED - Single combined file
- BOTH - Both individual and consolidated

#### ProcessingStatus
Status tracking for batch items:
- PENDING - Not yet started
- PROCESSING - Currently being processed
- SUCCESS - Successfully completed
- FAILED - Failed with error
- SKIPPED - Skipped (e.g., already processed)

#### BatchItem
Represents a single item in a batch with:
- Unique identifier
- Input data
- Metadata
- Status tracking
- Result storage
- Error handling
- Performance metrics (attempts, execution time)

#### BatchJobConfig
Comprehensive configuration including:
- Input/output settings
- Parallel processing options
- Retry logic
- Error handling
- **Advanced features**:
  - Rate limiting per endpoint
  - Result deduplication
  - Endpoint health monitoring
  - Checkpoint/resume support
  - Query optimization suggestions

#### BatchJobResult
Complete results with:
- Summary statistics
- Individual item results
- Performance metrics
- Success/failure rates
- Execution times

### 2. Input Parsers

**InputParser** class supports:
- Plain text files (one query per line)
- JSON with metadata
- YAML configurations
- CSV with column mapping
- Automatic format detection
- Comment handling
- Validation

### 3. Advanced Features

#### RateLimiter
- Per-endpoint rate limiting
- Configurable requests per second
- Automatic request pacing
- Prevents overwhelming endpoints

#### ResultDeduplicator
- Content-based deduplication
- SHA256 hash comparison
- Statistics tracking
- Memory-efficient implementation

#### EndpointHealthMonitor
- Real-time health monitoring
- Success/failure rate tracking
- Response time analysis
- Error aggregation
- Health status determination (healthy/degraded/unhealthy)

#### QueryOptimizer
- Static query analysis
- Performance optimization suggestions
- Best practice recommendations
- Severity levels (warning/info)

### 4. Batch Processor

**BatchProcessor** class features:
- Parallel and sequential execution modes
- Configurable worker pool
- Progress tracking with rich progress bars
- Automatic retry logic with exponential backoff
- Error handling and recovery
- Checkpoint/resume support
- Integration with all advanced features

Key methods:
- `load_items()` - Load and parse input with checkpoint support
- `process_item()` - Process single item with retries and features
- `process_parallel()` - Parallel execution with ThreadPoolExecutor
- `process_sequential()` - Sequential execution with progress tracking
- `save_results()` - Save results with statistics and reports

## CLI Commands

### 1. batch-query
Execute multiple SPARQL queries in batch mode.

**Features**:
- Multiple input formats (text, JSON, YAML, CSV)
- Parallel/sequential execution
- Natural language and SPARQL support
- Multiple generation strategies
- Configurable workers and timeout
- Progress reporting
- Error handling and retry

**Usage**:
```bash
sparql-agent batch batch-query queries.txt \
    --endpoint https://sparql.uniprot.org/sparql \
    --parallel --workers 4 \
    --retry 2 --timeout 60
```

### 2. bulk-discover
Discover capabilities of multiple SPARQL endpoints.

**Features**:
- Parallel endpoint discovery
- Capability detection
- Namespace extraction
- Statistics gathering
- Multiple output formats

**Usage**:
```bash
sparql-agent batch bulk-discover endpoints.yaml \
    --output discovery-results/ \
    --parallel --workers 4
```

### 3. generate-examples
Generate query examples from schema files.

**Features**:
- Schema-based generation
- Multiple query patterns
- Configurable count
- Various output formats

**Usage**:
```bash
sparql-agent batch generate-examples schema.ttl \
    --count 100 \
    --patterns "basic,filter,aggregate" \
    --output examples.json
```

### 4. benchmark
Benchmark queries across multiple endpoints.

**Features**:
- Multiple iterations with warmup
- Statistical analysis (mean, median, stdev)
- Performance comparison
- HTML/JSON/CSV reports
- Visualization-ready output

**Usage**:
```bash
sparql-agent batch benchmark queries.json endpoints.yaml \
    --iterations 5 --warmup 2 \
    --report-format html \
    --output benchmark-results/
```

### 5. migrate-queries
Migrate and adapt queries for different endpoints.

**Features**:
- Query validation
- Prefix updates
- Cross-endpoint testing
- Diff generation
- Compatibility checking

**Usage**:
```bash
sparql-agent batch migrate-queries old-queries.sparql new-queries.sparql \
    --source-endpoint https://old.endpoint/sparql \
    --target-endpoint https://new.endpoint/sparql \
    --test-execution --validate --diff
```

## Advanced Features Usage

### Rate Limiting
```bash
--rate-limit 10.0  # Max 10 requests per second per endpoint
```

### Result Deduplication
```bash
--deduplicate  # Remove duplicate results
```

### Health Monitoring
```bash
--monitor-health  # Generate endpoint health reports
```

### Query Optimization
```bash
--optimize-queries  # Get optimization suggestions
```

### Checkpoint/Resume
```bash
--resume --checkpoint-interval 10  # Save progress every 10 items
```

## Output Structure

After batch processing:

```
output-directory/
├── checkpoint.json              # Resume checkpoint (if enabled)
├── results.json                 # Consolidated results
├── errors.json                  # Failed items (if any)
├── endpoint_health.json         # Health monitoring (if enabled)
├── query_optimizations.json     # Optimization suggestions (if enabled)
├── batch.log                    # Detailed logs (if verbose)
└── individual/                  # Individual results (if enabled)
    ├── item_1.json
    ├── item_2.json
    └── ...
```

## Integration Points

### With Main CLI
Batch commands are automatically registered with the main CLI:
```python
from .batch import batch_cli
cli.add_command(batch_cli, name='batch')
```

### With Job Queue System
Results can be consumed by external job queue systems through:
- Structured JSON output
- Progress file updates
- Checkpoint files
- Status tracking

### With Other Modules
- **Query Generator**: For natural language processing
- **Query Executor**: For SPARQL execution
- **Query Validator**: For query validation
- **Capabilities Detector**: For endpoint discovery
- **Formatters**: For result formatting

## Performance Characteristics

### Scalability
- Handles thousands of queries efficiently
- Configurable parallelism (1-100+ workers)
- Memory-efficient streaming where possible
- Checkpoint support for very large batches

### Reliability
- Automatic retry with exponential backoff
- Error isolation (continue on error)
- Checkpoint/resume for recovery
- Health monitoring for endpoint issues

### Flexibility
- Multiple input/output formats
- Pluggable processor functions
- Configurable processing strategies
- Extensible architecture

## Testing

Comprehensive test suite in `test_batch.py`:
- Input parser tests (all formats)
- BatchItem lifecycle tests
- BatchProcessor functionality tests
- Integration tests
- Performance tests
- Error handling tests

## Future Enhancements

Potential improvements:
1. **Enhanced Schema-based Generation**: Implement full schema parsing for example generation
2. **Advanced Migration**: Add semantic query translation
3. **Distributed Processing**: Support for distributed batch processing
4. **Real-time Streaming**: Stream results as they complete
5. **Machine Learning**: Query optimization using ML models
6. **Caching**: Result caching for repeated queries
7. **Monitoring Dashboard**: Web-based monitoring interface
8. **Query Templates**: Template-based query generation

## Best Practices

1. **Start Small**: Test with small batches before scaling up
2. **Use Checkpoints**: Enable for any batch > 100 items
3. **Monitor Health**: Track endpoint status during processing
4. **Optimize First**: Review optimization suggestions before large batches
5. **Rate Limit**: Be respectful of public endpoints
6. **Error Analysis**: Always review errors.json after completion
7. **Parallel Tuning**: Match workers to endpoint capacity
8. **Deduplicate**: Enable for potentially redundant queries
9. **Verbose Logging**: Use for debugging and auditing
10. **Backup**: Keep original input files and checkpoints

## Examples

See `batch_examples.md` for comprehensive usage examples covering:
- All batch commands
- Various input formats
- Advanced features
- Integration patterns
- Performance tuning
- Error handling

## Support and Documentation

- **CLI Help**: `sparql-agent batch --help`
- **Command Help**: `sparql-agent batch COMMAND --help`
- **Examples**: `batch_examples.md`
- **Tests**: `test_batch.py`
- **API Docs**: See docstrings in `batch.py`

## Version

- **Initial Implementation**: 2024
- **Major Version**: 1.0
- **Status**: Production Ready

## License

Same as sparql-agent project license.
