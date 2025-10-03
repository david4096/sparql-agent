# Quick Start: Discovery with Timeout Fixes

## TL;DR

Discovery now works on large endpoints like Wikidata! Use `--fast` mode:

```bash
sparql-agent discover https://query.wikidata.org/sparql --fast
```

## Common Use Cases

### 1. Wikidata (Large, Public)
```bash
# Fast discovery (recommended)
sparql-agent discover https://query.wikidata.org/sparql --fast --timeout 30 -v

# Save results
sparql-agent discover https://query.wikidata.org/sparql --fast -o wikidata.json
```

### 2. DBpedia (Large, Public)
```bash
sparql-agent discover https://dbpedia.org/sparql --fast --timeout 20
```

### 3. UniProt (Medium, Public)
```bash
# Full discovery (no fast mode needed)
sparql-agent discover https://sparql.uniprot.org/sparql --timeout 60
```

### 4. Local Endpoint (Small, Private)
```bash
# Full discovery with higher limits
sparql-agent discover http://localhost:3030/dataset \
    --timeout 120 \
    --max-samples 5000
```

### 5. Unknown Endpoint (Test First)
```bash
# Start with fast mode to test
sparql-agent discover <endpoint> --fast --timeout 30 -v

# If it works well, try full mode
sparql-agent discover <endpoint> --timeout 60 --max-samples 2000
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--timeout N` | 30 | Overall timeout in seconds |
| `--fast` | False | Skip expensive queries |
| `--no-progressive-timeout` | False | Disable phased timeouts |
| `--max-samples N` | 1000 | Limit sampling queries |
| `-v` / `--verbose` | False | Show progress |
| `-o FILE` | stdout | Output file |
| `--format` | text | Output format (text/json/yaml) |

## Python API

### Basic Usage
```python
from sparql_agent.discovery.capabilities import CapabilitiesDetector

# Create detector
detector = CapabilitiesDetector(
    "https://query.wikidata.org/sparql",
    timeout=30,
    fast_mode=True
)

# Run discovery
capabilities = detector.detect_all_capabilities()

# Use results
print(f"SPARQL Version: {capabilities['sparql_version']}")
print(f"Namespaces: {len(capabilities['namespaces'])}")
print(f"Features: {sum(capabilities['features'].values())} supported")
```

### With Progress Tracking
```python
def show_progress(current, total, message):
    print(f"Progress: {current}/{total} - {message}")

capabilities = detector.detect_all_capabilities(
    progress_callback=show_progress
)
```

### Check for Errors
```python
capabilities = detector.detect_all_capabilities()

# Check metadata
metadata = capabilities.get('_metadata', {})

if metadata.get('timed_out_queries'):
    print(f"Warning: Some queries timed out: {metadata['timed_out_queries']}")

if metadata.get('failed_queries'):
    print(f"Error: Some queries failed: {metadata['failed_queries']}")

# Check individual results
if capabilities['statistics'] is None:
    error = capabilities.get('statistics_error', 'Unknown error')
    print(f"Statistics unavailable: {error}")
```

## Decision Tree

```
Is the endpoint large (>1M triples)?
├─ Yes → Use --fast mode
│   └─ Still timing out?
│       ├─ Yes → Reduce --timeout and --max-samples
│       └─ No → Good! Save results
│
└─ No → Use full mode
    └─ Getting good results in <60s?
        ├─ Yes → Perfect! Use as is
        └─ No → Consider --fast mode
```

## Troubleshooting

### Problem: Everything times out
```bash
# Solution: Use fast mode with low timeout
sparql-agent discover <endpoint> --fast --timeout 15 --max-samples 300
```

### Problem: Not enough information
```bash
# Solution: Increase timeout and samples
sparql-agent discover <endpoint> --timeout 120 --max-samples 3000
```

### Problem: Want to see what's happening
```bash
# Solution: Add verbose flag
sparql-agent discover <endpoint> -v
```

### Problem: Need results for debugging
```bash
# Solution: Save as JSON
sparql-agent discover <endpoint> --fast -o results.json --format json
```

## Understanding Output

### Text Format
```
SPARQL Endpoint Discovery Results
============================================================

Endpoint: https://query.wikidata.org/sparql
Discovery Mode: fast                    ← Shows fast/full mode
SPARQL Version: 1.1                     ← Basic info

Named Graphs: 0                         ← Structural info
Namespaces (45):                        ← Discovered vocabularies
  - http://www.w3.org/1999/02/22-rdf-syntax-ns#
  ...

Supported Features:                     ← SPARQL capabilities
  ✓ BIND
  ✓ EXISTS
  ✗ SERVICE                            ← Not supported

Dataset Statistics:                     ← Size info
  distinct_predicates: 7543
  Note: Endpoint has >100K triples...  ← Important notes

Discovery Issues:                       ← What failed
  Timed out: statistics                ← Expected on large endpoints
```

### JSON Format
```json
{
  "endpoint_url": "https://query.wikidata.org/sparql",
  "discovery_mode": "fast",
  "sparql_version": "1.1",
  "namespaces": [...],
  "features": {...},
  "statistics": {...},
  "_metadata": {
    "timed_out_queries": ["statistics"],
    "failed_queries": [],
    "fast_mode": true,
    "max_samples": 1000
  }
}
```

## Best Practices

1. **Start with fast mode** for unknown endpoints
2. **Use verbose mode** (`-v`) to see progress
3. **Save results** to avoid re-running discovery
4. **Check metadata** for failed/timed-out queries
5. **Adjust timeout** based on endpoint size
6. **Use appropriate samples** (500-1000 for large, 2000-5000 for small)

## Performance Tips

| Endpoint Size | Timeout | Fast Mode | Max Samples | Expected Time |
|---------------|---------|-----------|-------------|---------------|
| Small (<10K) | 30s | No | 5000 | 10-20s |
| Medium (10K-1M) | 60s | No | 2000 | 20-40s |
| Large (1M-100M) | 30s | Yes | 1000 | 15-30s |
| Huge (>100M) | 20s | Yes | 500 | 10-20s |

## Examples by Endpoint

### Public SPARQL Endpoints

```bash
# Wikidata
sparql-agent discover https://query.wikidata.org/sparql --fast -v

# DBpedia
sparql-agent discover https://dbpedia.org/sparql --fast

# UniProt
sparql-agent discover https://sparql.uniprot.org/sparql --timeout 60

# Bio2RDF
sparql-agent discover http://bio2rdf.org/sparql --fast --timeout 45

# EBI RDF Platform
sparql-agent discover https://www.ebi.ac.uk/rdf/services/sparql --timeout 60
```

### Local Endpoints

```bash
# Apache Jena Fuseki
sparql-agent discover http://localhost:3030/dataset --timeout 60

# Virtuoso
sparql-agent discover http://localhost:8890/sparql --timeout 60

# GraphDB
sparql-agent discover http://localhost:7200/repositories/repo --timeout 60
```

## Need Help?

1. Check verbose output: `sparql-agent discover <endpoint> -v`
2. Review `DISCOVERY_IMPROVEMENTS.md` for details
3. Check metadata in results for specific errors
4. Try fast mode if full mode times out
5. Reduce timeout and samples for very large endpoints

## Migration from Old Version

Old code still works! No changes needed.

To use new features:
```bash
# Old (still works)
sparql-agent discover <endpoint>

# New (with improvements)
sparql-agent discover <endpoint> --fast -v
```

## What's New?

- ✓ Works on large endpoints (Wikidata, DBpedia)
- ✓ Progressive timeouts (faster for quick queries)
- ✓ Graceful degradation (partial results better than nothing)
- ✓ Progress tracking (see what's happening)
- ✓ Better error messages (know what failed and why)
- ✓ Fast mode (skip expensive queries)
- ✓ Configurable sampling (adjust for endpoint size)

## Support

- Documentation: `DISCOVERY_IMPROVEMENTS.md`
- Changes: `CHANGES_SUMMARY.md`
- Tests: `test_discovery_improvements.py`
