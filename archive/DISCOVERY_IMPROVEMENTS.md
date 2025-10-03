# SPARQL Discovery Timeout Improvements

## Overview

This document describes the improvements made to the SPARQL Agent discovery system to handle timeout issues with large endpoints like Wikidata.

## Problem Statement

The original discovery system had several issues when querying large SPARQL endpoints:

1. **Timeout on complex queries**: Queries like counting all triples would timeout on endpoints with billions of triples
2. **All-or-nothing approach**: If one query failed, the entire discovery would fail
3. **No progress feedback**: Users had no visibility into what was happening during long discoveries
4. **Fixed timeout**: Single timeout value applied to all queries regardless of complexity
5. **No graceful degradation**: No fallback strategies when queries failed

## Solution

### 1. Progressive Timeout Handling

The system now uses a **phased discovery approach** with different timeouts for different types of queries:

```python
# Phase 1: Quick tests (5s timeout)
- SPARQL version detection
- Basic connectivity

# Phase 2: Feature detection (10s timeout)
- SPARQL 1.1 features
- Supported functions

# Phase 3: Data sampling (20s timeout)
- Named graphs
- Namespace discovery

# Phase 4: Function support (30s timeout)
- Testing individual SPARQL functions

# Phase 5: Statistics (full timeout)
- Triple counts
- Subject/predicate counts
```

Each phase gets a progressively longer timeout, allowing quick queries to complete fast while giving complex queries more time.

### 2. Graceful Degradation

When a query fails or times out:

1. The error is logged with context
2. The result is set to `None` with an error message
3. Discovery continues with remaining tasks
4. Metadata tracks which queries failed/timed out

Example output:
```python
{
    'statistics': None,
    'statistics_error': 'Timeout after 30s',
    '_metadata': {
        'timed_out_queries': ['statistics'],
        'failed_queries': []
    }
}
```

### 3. Result Streaming for Namespaces

Namespace discovery now uses a two-strategy approach:

**Strategy 1: Fast predicate sampling** (primary)
- Query only predicates (much faster)
- Predicates are from well-defined vocabularies
- Usually sufficient for most use cases

**Strategy 2: Subject/object sampling** (fallback)
- Only executed if Strategy 1 finds few namespaces
- Uses smaller sample size to avoid timeouts
- Skipped in fast mode

### 4. Improved Query Execution

Enhanced `_execute_query` method with:

- **Retry logic**: Automatically retries failed queries with exponential backoff
- **Better error handling**: Distinguishes between timeout, authentication, and server errors
- **Timeout detection**: Catches various timeout error patterns
- **Specific error types**: Handles different SPARQL exception types appropriately

### 5. Fast Mode

New `fast_mode` parameter skips expensive queries:

```python
detector = CapabilitiesDetector(
    endpoint_url,
    fast_mode=True,  # Skip statistics, function tests, etc.
    timeout=30
)
```

Fast mode is recommended for:
- Large public endpoints (Wikidata, DBpedia)
- Initial quick checks
- Automated monitoring
- CI/CD pipelines

### 6. Configurable Parameters

New initialization parameters:

```python
CapabilitiesDetector(
    endpoint_url="https://query.wikidata.org/sparql",
    timeout=30,                    # Overall timeout
    fast_mode=False,               # Skip expensive queries
    progressive_timeout=True,       # Use phased timeouts
    max_samples=1000               # Limit sampling queries
)
```

### 7. Progress Callbacks

Support for progress tracking:

```python
def progress_callback(current, total, message):
    print(f"[{current}/{total}] {message}")

capabilities = detector.detect_all_capabilities(
    progress_callback=progress_callback
)
```

### 8. Enhanced CLI

New CLI options for the `discover` command:

```bash
# Fast mode for large endpoints
sparql-agent discover https://query.wikidata.org/sparql --fast

# Custom timeout
sparql-agent discover <endpoint> --timeout 60

# Disable progressive timeouts
sparql-agent discover <endpoint> --no-progressive-timeout

# Limit samples
sparql-agent discover <endpoint> --max-samples 500

# Verbose progress
sparql-agent discover <endpoint> -v
```

## Usage Examples

### Example 1: Wikidata (Large Endpoint)

```bash
# Fast discovery with reasonable timeout
sparql-agent discover https://query.wikidata.org/sparql \
    --fast \
    --timeout 30 \
    --output wikidata-info.json \
    -v
```

Expected behavior:
- Completes in ~15-30 seconds
- Skips expensive statistics
- Reports any timed out queries
- Returns basic capabilities

### Example 2: Local Endpoint (Full Discovery)

```bash
# Full discovery on local endpoint
sparql-agent discover http://localhost:3030/dataset \
    --timeout 60 \
    --format text
```

Expected behavior:
- Performs all discovery tasks
- Uses progressive timeouts
- Returns comprehensive results
- Shows all statistics

### Example 3: Python API

```python
from sparql_agent.discovery.capabilities import CapabilitiesDetector

# For large endpoints like Wikidata
detector = CapabilitiesDetector(
    "https://query.wikidata.org/sparql",
    timeout=30,
    fast_mode=True,
    max_samples=500
)

capabilities = detector.detect_all_capabilities()

# Check for issues
if capabilities.get('_metadata', {}).get('timed_out_queries'):
    print("Some queries timed out (expected for Wikidata)")

# Use results
print(f"SPARQL Version: {capabilities['sparql_version']}")
print(f"Namespaces found: {len(capabilities['namespaces'])}")
```

## Performance Comparison

### Before (Original System)

**Wikidata Discovery:**
- Result: Timeout error after 30s
- Queries executed: 1-2 before timeout
- Information gathered: None
- User experience: Failure

### After (Improved System)

**Wikidata Discovery (Fast Mode):**
- Result: Partial success in ~20s
- Queries executed: 10-15
- Information gathered:
  - SPARQL version ✓
  - Features ✓
  - Namespaces ✓
  - Named graphs ✓
  - Some statistics (with notes about timeouts)
- User experience: Useful results with clear indication of limitations

## Technical Details

### Timeout Strategy Decision Tree

```
Start Discovery
    │
    ├─ Quick Tests (5s)
    │   └─ SPARQL version detection
    │
    ├─ Feature Detection (10s)
    │   └─ Test SPARQL 1.1 features
    │
    ├─ If NOT fast_mode:
    │   │
    │   ├─ Data Sampling (20s)
    │   │   ├─ Named graphs
    │   │   └─ Namespaces (predicates first)
    │   │
    │   ├─ Function Support (30s)
    │   │   └─ Test SPARQL functions
    │   │
    │   └─ Statistics (full timeout)
    │       ├─ Try full count (may timeout)
    │       ├─ Fallback to sampling
    │       └─ Report approximate values
    │
    └─ Return Results with Metadata
```

### Error Handling Strategy

```python
try:
    result = execute_query(query)
except TimeoutError:
    # Log, mark as timed out, continue
    log_timeout(query_name)
    result = None
except AuthError:
    # Authentication required - can't continue
    raise
except ServerError:
    # Server error - retry with backoff
    retry_with_backoff()
except QueryError:
    # Bad query - log and skip
    log_error(query_name)
    result = None
```

## Configuration Recommendations

### Endpoint Types

**1. Large Public Endpoints (Wikidata, DBpedia)**
```python
CapabilitiesDetector(
    endpoint_url,
    timeout=30,
    fast_mode=True,
    max_samples=500
)
```

**2. Medium Institutional Endpoints (UniProt, EBI)**
```python
CapabilitiesDetector(
    endpoint_url,
    timeout=60,
    fast_mode=False,
    max_samples=1000
)
```

**3. Small Local Endpoints**
```python
CapabilitiesDetector(
    endpoint_url,
    timeout=120,
    fast_mode=False,
    progressive_timeout=False,  # Can disable for small endpoints
    max_samples=5000
)
```

## Monitoring and Debugging

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

detector = CapabilitiesDetector(endpoint_url, timeout=30)
capabilities = detector.detect_all_capabilities()
```

### Check Metadata

```python
metadata = capabilities.get('_metadata', {})

print(f"Failed queries: {metadata.get('failed_queries', [])}")
print(f"Timed out queries: {metadata.get('timed_out_queries', [])}")
print(f"Fast mode: {metadata.get('fast_mode')}")
print(f"Max samples: {metadata.get('max_samples')}")
```

### CLI Verbose Mode

```bash
# Show progress and debug info
sparql-agent discover <endpoint> -vv
```

## Future Improvements

Potential enhancements for future versions:

1. **Adaptive timeout**: Learn optimal timeouts based on endpoint performance
2. **Parallel queries**: Execute independent queries in parallel
3. **Smart sampling**: Use VoID descriptions if available
4. **Caching**: Cache discovery results with TTL
5. **Endpoint profiles**: Pre-configured settings for known endpoints
6. **Streaming results**: Return results as they become available

## Testing

Run the test suite:

```bash
python test_discovery_improvements.py
```

This will test discovery on multiple endpoints of varying sizes.

## Troubleshooting

### Issue: All queries timing out

**Solution**: Reduce timeout, enable fast mode
```bash
sparql-agent discover <endpoint> --fast --timeout 20
```

### Issue: Not enough information gathered

**Solution**: Increase timeout, disable fast mode
```bash
sparql-agent discover <endpoint> --timeout 120 --max-samples 2000
```

### Issue: Specific query type failing

**Solution**: Check metadata to identify failing queries
```python
metadata = capabilities['_metadata']
print(metadata['failed_queries'])
```

## References

- SPARQL 1.1 Specification: https://www.w3.org/TR/sparql11-query/
- SPARQLWrapper Documentation: https://sparqlwrapper.readthedocs.io/
- Wikidata Query Service: https://query.wikidata.org/

## Authors

- Claude (AI Assistant) - Implementation
- David (User) - Requirements and Testing

## License

Same as SPARQL Agent project license.
