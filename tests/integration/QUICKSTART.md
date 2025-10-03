# Integration Tests Quick Start Guide

Get started with SPARQL Agent integration tests in 5 minutes.

## 1. Installation

```bash
# Install with UV (recommended)
cd /Users/david/git/sparql-agent
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

## 2. Run Your First Tests

```bash
# Quick smoke tests (30 seconds)
cd tests/integration
./run_tests.sh smoke

# Or using pytest directly
uv run pytest . -m smoke -v
```

Expected output:
```
tests/integration/test_uniprot_integration.py::TestUniProtSmoke::test_endpoint_available PASSED
tests/integration/test_uniprot_integration.py::TestUniProtSmoke::test_simple_ask_query PASSED
...
```

## 3. Common Test Commands

### By Speed
```bash
./run_tests.sh fast           # Fast tests only (~2-3 minutes)
./run_tests.sh all            # All tests (~10-15 minutes)
```

### By Endpoint
```bash
./run_tests.sh uniprot        # UniProt tests only
./run_tests.sh ols4           # OLS4 API tests only
./run_tests.sh endpoints      # All endpoint tests
```

### By Function
```bash
./run_tests.sh functional     # Feature tests
./run_tests.sh workflows      # End-to-end workflows
./run_tests.sh error          # Error handling
```

### For CI/CD
```bash
./run_tests.sh ci             # Quick CI suite (~1-2 minutes)
```

## 4. Understanding Test Results

### Success
```
✓ Tests completed successfully!
```

### Skipped Tests
```
SKIPPED [1] Endpoint not available
```
This is normal - tests skip if endpoints are down.

### Performance Summary
```
======================================================================
PERFORMANCE SUMMARY
======================================================================

simple_protein_query:
  Count: 3
  Mean:  2.345s
  Min:   1.234s
  Max:   3.456s
```

## 5. Writing Your First Test

Create `test_my_feature.py`:

```python
"""My integration test."""

import pytest
from . import UNIPROT_ENDPOINT


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.functional
class TestMyFeature:
    """Test my feature."""

    def test_basic_query(self, cached_query_executor):
        """Test a basic query."""
        query = """
        PREFIX up: <http://purl.uniprot.org/core/>

        SELECT ?protein ?mnemonic
        WHERE {
            ?protein a up:Protein ;
                     up:mnemonic ?mnemonic .
        }
        LIMIT 5
        """

        result = cached_query_executor(UNIPROT_ENDPOINT, query)
        bindings = result["results"]["bindings"]

        assert len(bindings) == 5
        assert "mnemonic" in bindings[0]
```

Run it:
```bash
uv run pytest test_my_feature.py -v
```

## 6. Common Issues

### Issue: Tests timeout
**Solution**: Increase timeout
```bash
TEST_TIMEOUT=60 ./run_tests.sh fast
```

### Issue: Rate limiting
**Solution**: Use caching and delays
```python
# Always use cached_query_executor for repeated queries
result = cached_query_executor(endpoint, query)
```

### Issue: Endpoint unavailable
**Solution**: Tests auto-skip when endpoints are down
```
SKIPPED - Endpoint not available
```

### Issue: Network required
**Solution**: Skip network tests
```bash
SKIP_NETWORK_TESTS=true ./run_tests.sh
```

## 7. Debugging

### Verbose output
```bash
uv run pytest test_file.py -vv
```

### With logging
```bash
uv run pytest test_file.py -v --log-cli-level=DEBUG
```

### Single test
```bash
uv run pytest test_file.py::TestClass::test_method -v
```

### Drop into debugger
```bash
uv run pytest test_file.py --pdb
```

## 8. Coverage Reports

```bash
./run_tests.sh coverage
# Opens htmlcov/index.html
```

## 9. Test Markers

Filter tests by marker:

```bash
# Only smoke tests
uv run pytest . -m smoke

# Functional but not slow
uv run pytest . -m "functional and not slow"

# Performance tests only
uv run pytest . -m performance

# Exclude network tests
uv run pytest . -m "integration and not network"
```

Available markers:
- `integration` - All integration tests
- `network` - Requires internet
- `endpoint` - Endpoint-specific
- `smoke` - Quick connectivity tests
- `functional` - Feature tests
- `regression` - Known good queries
- `performance` - Timing tests
- `slow` - Long-running (>5s)

## 10. Next Steps

1. Read the full [README.md](README.md)
2. Explore test files for examples
3. Check [conftest.py](conftest.py) for available fixtures
4. Run `./run_tests.sh help` for all options

## Quick Reference Card

```bash
# Essential Commands
./run_tests.sh help          # Show all options
./run_tests.sh smoke         # Quick validation
./run_tests.sh fast          # Fast tests
./run_tests.sh ci            # CI pipeline tests
./run_tests.sh coverage      # With coverage

# By Endpoint
./run_tests.sh uniprot       # UniProt
./run_tests.sh ols4          # OLS4
./run_tests.sh endpoints     # All endpoints

# By Type
./run_tests.sh functional    # Features
./run_tests.sh workflows     # E2E workflows
./run_tests.sh regression    # Known queries
./run_tests.sh performance   # Timing

# Debugging
uv run pytest test.py -v     # Verbose
uv run pytest test.py -vv    # Very verbose
uv run pytest test.py --pdb  # Debugger
uv run pytest test.py -k "test_name"  # By name

# Environment
TEST_TIMEOUT=60 ./run_tests.sh       # Set timeout
SKIP_SLOW_TESTS=true ./run_tests.sh  # Skip slow
SKIP_NETWORK_TESTS=true ./run_tests.sh  # Skip network
```

## Support

- Questions? Check [README.md](README.md)
- Issues? See [Troubleshooting](README.md#troubleshooting)
- Contributing? See [Contributing](README.md#contributing)

Happy testing! 🧪
