# Integration Tests

Comprehensive integration test suite for SPARQL Agent with real SPARQL endpoints and ontology services.

## Overview

This test suite validates the complete functionality of SPARQL Agent by executing real queries against public SPARQL endpoints and ontology services. Tests are organized by endpoint and functionality, with extensive use of pytest markers for flexible test selection.

## Test Structure

```
tests/integration/
├── __init__.py                          # Test configuration constants
├── conftest.py                          # Shared fixtures and utilities
├── pytest.ini                           # Pytest configuration
├── README.md                            # This file
│
├── test_uniprot_integration.py          # UniProt endpoint tests
├── test_rdfportal_integration.py        # RDFPortal endpoint tests
├── test_clinvar_integration.py          # ClinVar endpoint tests
├── test_ols4_integration.py             # OLS4 API integration tests
│
├── test_nl_to_sparql_workflow.py        # Natural language → SPARQL workflows
├── test_federated_queries.py            # Multi-endpoint federated queries
├── test_ontology_guided_workflow.py     # Ontology-guided query generation
└── test_error_recovery.py               # Error handling and resilience
```

## Test Endpoints

### SPARQL Endpoints

- **UniProt**: https://sparql.uniprot.org/sparql
  - Comprehensive protein data
  - Well-maintained and stable
  - Rich annotations and cross-references

- **RDFPortal**: https://rdfportal.org/sparql
  - Biomedical research datasets
  - Dataset discovery and metadata

- **ClinVar**: https://sparql.omics.ai/blazegraph/namespace/clinvar/sparql
  - Clinical variant data
  - May not always be available

### REST APIs

- **OLS4**: https://www.ebi.ac.uk/ols4/api
  - Ontology Lookup Service
  - Term search and hierarchy navigation
  - High availability

## Test Categories

### By Marker

Tests are categorized using pytest markers:

- **@pytest.mark.integration**: All integration tests
- **@pytest.mark.network**: Requires internet connectivity
- **@pytest.mark.endpoint**: Endpoint-specific tests
- **@pytest.mark.smoke**: Basic connectivity tests
- **@pytest.mark.functional**: Complete feature tests
- **@pytest.mark.regression**: Known good query tests
- **@pytest.mark.performance**: Response time monitoring
- **@pytest.mark.slow**: Long-running tests (>5 seconds)

### By Test Type

1. **Smoke Tests**: Basic connectivity validation
   - Endpoint availability
   - Simple queries
   - Health checks

2. **Functional Tests**: Complete feature workflows
   - Protein queries
   - Annotation retrieval
   - Cross-reference lookups
   - Ontology integration

3. **Regression Tests**: Known good queries
   - Specific protein lookups
   - Expected result validation
   - Data consistency checks

4. **Performance Tests**: Response time monitoring
   - Query execution time
   - Result set size handling
   - Timeout behavior

5. **Error Recovery Tests**: Resilience validation
   - Network failures
   - Invalid queries
   - Endpoint downtime
   - Rate limiting

## Running Tests

### Prerequisites

```bash
# Install dependencies
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Run all integration tests
uv run pytest tests/integration/ -m integration

# Run specific endpoint tests
uv run pytest tests/integration/test_uniprot_integration.py

# Run only smoke tests
uv run pytest tests/integration/ -m smoke

# Run functional tests (excluding slow)
uv run pytest tests/integration/ -m "functional and not slow"
```

### Advanced Usage

```bash
# Run with verbose output
uv run pytest tests/integration/ -v -m integration

# Run with detailed logging
uv run pytest tests/integration/ -v --log-cli-level=DEBUG

# Run specific test class
uv run pytest tests/integration/test_uniprot_integration.py::TestUniProtProteinQueries

# Run specific test method
uv run pytest tests/integration/test_uniprot_integration.py::TestUniProtProteinQueries::test_get_protein_by_accession

# Run with coverage
uv run pytest tests/integration/ -m integration --cov=sparql_agent --cov-report=html

# Run in parallel (requires pytest-xdist)
uv run pytest tests/integration/ -m integration -n auto

# Skip network tests
uv run pytest tests/integration/ -m "integration and not network"

# Skip slow tests
uv run pytest tests/integration/ -m "integration and not slow"
```

### Using Markers

```bash
# Combine markers
uv run pytest tests/integration/ -m "endpoint and not slow"

# Run only performance tests
uv run pytest tests/integration/ -m performance

# Run regression tests only
uv run pytest tests/integration/ -m regression

# Exclude specific markers
uv run pytest tests/integration/ -m "not slow and not performance"
```

## Environment Variables

Configure test behavior using environment variables:

```bash
# Skip all network tests
export SKIP_NETWORK_TESTS=true

# Skip slow tests
export SKIP_SLOW_TESTS=true

# Set query timeout (seconds)
export TEST_TIMEOUT=60

# Set maximum retries for failed queries
export MAX_RETRIES=3
```

Example:

```bash
# Run tests without network or slow tests
SKIP_NETWORK_TESTS=true SKIP_SLOW_TESTS=true uv run pytest tests/integration/
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync --dev

      - name: Run smoke tests
        run: uv run pytest tests/integration/ -m smoke

      - name: Run fast integration tests
        run: uv run pytest tests/integration/ -m "integration and not slow"
        continue-on-error: true

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results/
```

### GitLab CI Example

```yaml
integration-tests:
  stage: test
  image: python:3.11

  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
    - uv sync --dev

  script:
    - uv run pytest tests/integration/ -m "integration and not slow" --junit-xml=test-results/junit.xml

  artifacts:
    when: always
    reports:
      junit: test-results/junit.xml
```

## Fixtures and Utilities

### Available Fixtures

- **endpoint_checker**: Check if endpoints are available
- **check_endpoint_available**: Skip test if endpoint unavailable
- **sparql_wrapper_factory**: Create configured SPARQLWrapper instances
- **sparql_query_executor**: Execute queries with retry logic
- **cached_query_executor**: Execute with response caching
- **timed_query_executor**: Execute with timing measurement
- **performance_monitor**: Track query performance
- **response_cache**: Cache responses to avoid rate limiting
- **sample_protein_ids**: Sample UniProt protein IDs
- **sample_go_terms**: Sample Gene Ontology terms
- **sample_taxonomy_ids**: Sample NCBI taxonomy IDs

### Example Usage

```python
def test_my_integration(cached_query_executor, sample_protein_ids):
    """Example integration test."""
    protein_id = sample_protein_ids[0]

    query = f"""
    PREFIX up: <http://purl.uniprot.org/core/>
    SELECT ?protein WHERE {{
        BIND(<http://purl.uniprot.org/uniprot/{protein_id}> AS ?protein)
        ?protein a up:Protein .
    }}
    """

    result = cached_query_executor(UNIPROT_ENDPOINT, query)
    assert len(result["results"]["bindings"]) > 0
```

## Performance Monitoring

Tests automatically track performance metrics. After a test session, a performance summary is displayed:

```
======================================================================
PERFORMANCE SUMMARY
======================================================================

simple_protein_query:
  Count: 3
  Mean:  2.345s
  Min:   1.234s
  Max:   3.456s

complex_multi_constraint:
  Count: 2
  Mean:  15.678s
  Min:   14.234s
  Max:   17.122s
======================================================================
```

## Best Practices

### Writing Integration Tests

1. **Use markers appropriately**:
   ```python
   @pytest.mark.integration
   @pytest.mark.network
   @pytest.mark.functional
   def test_my_feature(cached_query_executor):
       ...
   ```

2. **Check endpoint availability**:
   ```python
   def test_endpoint_feature(check_endpoint_available, cached_query_executor):
       check_endpoint_available(UNIPROT_ENDPOINT)
       # Test continues only if endpoint is available
   ```

3. **Use caching to avoid rate limiting**:
   ```python
   # Use cached_query_executor instead of sparql_query_executor
   result = cached_query_executor(UNIPROT_ENDPOINT, query)
   ```

4. **Mark slow tests**:
   ```python
   @pytest.mark.slow
   def test_long_running_query(cached_query_executor):
       ...
   ```

5. **Handle errors gracefully**:
   ```python
   try:
       result = query_executor(ENDPOINT, query)
   except Exception as e:
       pytest.skip(f"Endpoint unavailable: {e}")
   ```

### Avoiding Rate Limiting

1. Use `cached_query_executor` for repeated queries
2. Add delays between requests in loops
3. Use `LIMIT` clauses to reduce result size
4. Mark tests appropriately to avoid running all at once
5. Consider using `pytest-xdist` carefully (can trigger rate limits)

### Debugging Failures

```bash
# Run with verbose output and logging
uv run pytest tests/integration/test_uniprot_integration.py -v -s --log-cli-level=DEBUG

# Run single test with full traceback
uv run pytest tests/integration/test_uniprot_integration.py::TestClass::test_method -vv --tb=long

# Drop into debugger on failure
uv run pytest tests/integration/ --pdb

# Show local variables on failure
uv run pytest tests/integration/ -l
```

## Troubleshooting

### Common Issues

1. **Endpoint unavailable**: Tests will skip automatically if endpoint is down
2. **Timeout errors**: Increase `TEST_TIMEOUT` environment variable
3. **Rate limiting**: Use cached executor and add delays
4. **Network errors**: Set `SKIP_NETWORK_TESTS=true` for offline development

### Known Limitations

- Some endpoints may not support federated queries (SERVICE keyword)
- ClinVar endpoint availability may vary
- Performance tests depend on network conditions
- Some queries may fail during endpoint maintenance

## Contributing

When adding new integration tests:

1. Follow existing test structure and naming conventions
2. Add appropriate pytest markers
3. Use provided fixtures for consistency
4. Document any new test endpoints or APIs
5. Update this README with new test categories
6. Ensure tests can handle endpoint unavailability
7. Add caching for frequently used queries

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [UniProt SPARQL Documentation](https://sparql.uniprot.org/)
- [OLS4 API Documentation](https://www.ebi.ac.uk/ols4/help)
- [SPARQLWrapper Documentation](https://sparqlwrapper.readthedocs.io/)
