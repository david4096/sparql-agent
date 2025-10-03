# SPARQL Agent Test Suite

Comprehensive test suite for the SPARQL agent system with >90% code coverage.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── __init__.py              # Test suite initialization
├── test_core.py             # Core types, base classes, exceptions
├── test_discovery.py        # Endpoint discovery and connectivity
├── test_schema.py           # Schema discovery and validation
├── test_query.py            # Query generation and intent parsing
├── test_execution.py        # Query execution and validation
├── test_llm.py              # LLM provider integration
└── data/                    # Test data files
    ├── sample_queries.sparql
    ├── sample_ontology.ttl
    └── README.md
```

## Running Tests

### Run all tests
```bash
uv run pytest
```

### Run with verbose output
```bash
uv run pytest -v
```

### Run with coverage report
```bash
uv run pytest --cov=sparql_agent --cov-report=term-missing
```

### Run specific test file
```bash
uv run pytest tests/test_core.py
```

### Run specific test class
```bash
uv run pytest tests/test_core.py::TestOWLClass
```

### Run specific test method
```bash
uv run pytest tests/test_core.py::TestOWLClass::test_owl_class_creation
```

## Test Categories

### By Marker

```bash
# Unit tests only (fast, no external dependencies)
uv run pytest -m unit

# Integration tests (may require endpoints/APIs)
uv run pytest -m integration

# Slow tests (performance, large datasets)
uv run pytest -m slow

# Tests requiring API keys
uv run pytest -m requires_api_key

# Tests requiring network access
uv run pytest -m requires_network
```

### By Module

```bash
# Core module tests
uv run pytest tests/test_core.py -v

# Discovery tests
uv run pytest tests/test_discovery.py -v

# Schema tests
uv run pytest tests/test_schema.py -v

# Query generation tests
uv run pytest tests/test_query.py -v

# Execution tests
uv run pytest tests/test_execution.py -v

# LLM provider tests
uv run pytest tests/test_llm.py -v
```

## Test Coverage

Target: >90% code coverage across all modules

### Generate HTML coverage report
```bash
uv run pytest --cov=sparql_agent --cov-report=html
open htmlcov/index.html
```

### Check coverage for specific module
```bash
uv run pytest --cov=sparql_agent.core --cov-report=term-missing
```

## Test Fixtures

Common fixtures are defined in `conftest.py`:

### Data Fixtures
- `test_data_dir` - Temporary directory for test data
- `sample_rdf_file` - Sample RDF/Turtle file
- `sample_owl_file` - Sample OWL ontology file
- `sample_void_file` - Sample VoID description file

### Type Fixtures
- `sample_endpoint_info` - EndpointInfo instance
- `sample_owl_class` - OWLClass instance
- `sample_owl_property` - OWLProperty instance
- `sample_ontology_info` - OntologyInfo instance
- `sample_schema_info` - SchemaInfo instance
- `sample_query_result` - QueryResult instance
- `sample_llm_response` - LLMResponse instance
- `sample_generated_query` - GeneratedQuery instance

### Mock Fixtures
- `mock_sparql_endpoint` - Mock SPARQL endpoint
- `mock_ontology_provider` - Mock ontology provider
- `mock_llm_provider` - Mock LLM provider
- `mock_schema_discoverer` - Mock schema discoverer
- `mock_http_response` - Mock HTTP response

### RDFLib Fixtures
- `sample_rdf_graph` - Sample RDF graph using rdflib
- `sample_owl_graph` - Sample OWL ontology graph

### Query Fixtures
- `sample_sparql_queries` - Collection of sample SPARQL queries

## Writing New Tests

### Test Structure

```python
import pytest
from sparql_agent.core.types import QueryResult

class TestMyFeature:
    \"\"\"Tests for MyFeature functionality.\"\"\"

    def test_basic_functionality(self):
        \"\"\"Test basic feature operation.\"\"\"
        result = my_function()
        assert result is not None

    @pytest.mark.unit
    def test_unit_behavior(self):
        \"\"\"Test isolated unit behavior.\"\"\"
        # Test logic here
        pass

    @pytest.mark.integration
    def test_integration_behavior(self, mock_sparql_endpoint):
        \"\"\"Test integration with other components.\"\"\"
        # Test logic here
        pass

    @pytest.mark.slow
    def test_performance(self):
        \"\"\"Test performance characteristics.\"\"\"
        # Performance test logic
        pass
```

### Using Fixtures

```python
def test_with_fixtures(
    sample_schema_info,
    mock_llm_provider,
    sample_sparql_queries
):
    \"\"\"Test using multiple fixtures.\"\"\"
    query = sample_sparql_queries["select_all"]
    # Use fixtures in test
    pass
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_multiple_cases(input, expected):
    \"\"\"Test multiple input/output pairs.\"\"\"
    result = my_function(input)
    assert result == expected
```

## Test Data

Test data files are located in `tests/data/`:

- `sample_queries.sparql` - Various SPARQL query patterns
- `sample_ontology.ttl` - Complete OWL ontology with sample instances

See `tests/data/README.md` for details.

## Continuous Integration

Tests are automatically run in CI on:
- Push to main branch
- Pull requests
- Scheduled nightly builds

CI configuration includes:
- Multiple Python versions (3.9, 3.10, 3.11, 3.12)
- Coverage reporting
- Code quality checks

## Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Test names should describe what they test
3. **Speed**: Unit tests should be fast (<1s each)
4. **Coverage**: Aim for >90% coverage
5. **Fixtures**: Use fixtures for common test data
6. **Mocking**: Mock external dependencies (APIs, endpoints)
7. **Markers**: Use markers to categorize tests
8. **Documentation**: Add docstrings to test classes and methods

## Troubleshooting

### Tests fail with import errors
```bash
# Ensure package is installed in development mode
uv pip install -e .
```

### Tests fail with missing dependencies
```bash
# Install test dependencies
uv pip install -e ".[dev]"
```

### Slow test execution
```bash
# Run only fast unit tests
uv run pytest -m "not slow"

# Run tests in parallel
uv run pytest -n auto
```

### Coverage not showing
```bash
# Ensure coverage is installed
uv pip install pytest-cov

# Run with coverage
uv run pytest --cov=sparql_agent
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure >90% coverage for new code
3. Add appropriate markers
4. Update this README if needed
5. Run full test suite before committing

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Testing best practices](https://docs.python-guide.org/writing/tests/)
