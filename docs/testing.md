# Testing Guide

Comprehensive guide to testing SPARQL Agent.

## Test Structure

```
tests/
├── unit/              # Unit tests (fast, isolated)
├── integration/       # Integration tests (multiple modules)
├── e2e/               # End-to-end tests (full workflows)
├── performance/       # Performance benchmarks
├── data/              # Test data files
└── conftest.py        # Shared fixtures
```

## Running Tests

### Basic Usage

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific file
uv run pytest tests/test_query.py

# Run specific test
uv run pytest tests/test_query.py::test_generate_query
```

### With Coverage

```bash
# Generate coverage report
uv run pytest --cov=sparql_agent --cov-report=html

# View report
open htmlcov/index.html
```

### Parallel Execution

```bash
# Run tests in parallel
uv run pytest -n auto
```

## Test Categories

### Unit Tests

```python
# tests/unit/test_query_generator.py
import pytest
from sparql_agent.query import QueryGenerator

def test_query_generation():
    """Test basic query generation."""
    generator = QueryGenerator()
    sparql = generator.generate("Find proteins")

    assert "SELECT" in sparql
    assert "Protein" in sparql.lower()

def test_with_limit():
    """Test query with limit."""
    generator = QueryGenerator()
    sparql = generator.generate("Find proteins", limit=10)

    assert "LIMIT 10" in sparql
```

### Integration Tests

```python
# tests/integration/test_agent_workflow.py
import pytest
from sparql_agent import SPARQLAgent

@pytest.mark.integration
def test_full_workflow(test_endpoint):
    """Test complete query workflow."""
    agent = SPARQLAgent(endpoint=test_endpoint)
    results = agent.query("Find 5 proteins")

    assert len(results) <= 5
    assert all('protein' in r for r in results)

@pytest.mark.integration
@pytest.mark.network
def test_real_endpoint():
    """Test with real UniProt endpoint."""
    agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
    results = agent.query("Find 5 human proteins")

    assert len(results) > 0
```

### End-to-End Tests

```python
# tests/e2e/test_cli.py
import subprocess

def test_cli_query():
    """Test CLI query command."""
    result = subprocess.run(
        ["sparql-agent", "query", "Find proteins", "--limit", "5"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "protein" in result.stdout.lower()
```

## Fixtures

### Common Fixtures

```python
# tests/conftest.py
import pytest
from sparql_agent import SPARQLAgent

@pytest.fixture
def test_endpoint():
    """Test SPARQL endpoint URL."""
    return "http://localhost:3030/test/sparql"

@pytest.fixture
def agent(test_endpoint):
    """SPARQLAgent instance for testing."""
    return SPARQLAgent(endpoint=test_endpoint)

@pytest.fixture
def mock_llm(mocker):
    """Mocked LLM provider."""
    return mocker.patch('sparql_agent.llm.AnthropicClient')

@pytest.fixture
def sample_results():
    """Sample query results."""
    return [
        {"protein": "P00533", "name": "EGFR"},
        {"protein": "P04637", "name": "TP53"}
    ]
```

### Parametrized Fixtures

```python
@pytest.fixture(params=["anthropic", "openai"])
def llm_provider(request):
    """Test with multiple LLM providers."""
    return request.param

def test_with_different_providers(llm_provider):
    agent = SPARQLAgent(llm_provider=llm_provider)
    # Test logic
```

## Mocking

### Mock External APIs

```python
from unittest.mock import Mock, patch

@patch('sparql_agent.llm.AnthropicClient.generate')
def test_query_with_mocked_llm(mock_generate):
    """Test with mocked LLM."""
    mock_generate.return_value = "SELECT * WHERE { ?s ?p ?o }"

    agent = SPARQLAgent(llm_provider="anthropic")
    results = agent.query("test")

    mock_generate.assert_called_once()

### Mock SPARQL Endpoints

```python
@pytest.fixture
def mock_endpoint(requests_mock):
    """Mock SPARQL endpoint."""
    requests_mock.post(
        "http://test.endpoint/sparql",
        json={
            "results": {
                "bindings": [
                    {"protein": {"value": "P00533"}}
                ]
            }
        }
    )
    return "http://test.endpoint/sparql"

def test_with_mock_endpoint(mock_endpoint):
    agent = SPARQLAgent(endpoint=mock_endpoint)
    results = agent.execute_sparql("SELECT * WHERE { ?s ?p ?o }")
    assert len(results) == 1
```

## Test Markers

### Using Markers

```python
@pytest.mark.slow
def test_long_running():
    """Test that takes > 5 seconds."""
    pass

@pytest.mark.integration
def test_integration():
    """Integration test."""
    pass

@pytest.mark.network
def test_requires_network():
    """Test requiring internet."""
    pass
```

### Running Specific Markers

```bash
# Run only integration tests
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"

# Run multiple markers
uv run pytest -m "integration and not network"
```

## Performance Testing

### Benchmarks

```python
import pytest

def test_query_performance(benchmark):
    """Benchmark query generation."""
    generator = QueryGenerator()

    result = benchmark(generator.generate, "Find proteins")

    assert result is not None

def test_execution_performance(benchmark, agent):
    """Benchmark query execution."""
    sparql = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

    result = benchmark(agent.execute_sparql, sparql)

    assert len(result) > 0
```

### Load Testing

```python
# tests/performance/test_load.py
from locust import HttpUser, task, between

class SPARQLAgentUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def query_endpoint(self):
        self.client.post("/api/query", json={
            "query": "Find proteins",
            "endpoint": "https://sparql.uniprot.org/sparql"
        })
```

Run load test:

```bash
locust -f tests/performance/test_load.py --host=http://localhost:8000
```

## Coverage

### Target Coverage

- Overall: 80%+
- Core modules: 90%+
- Critical paths: 100%

### Generate Coverage Report

```bash
# Terminal report
uv run pytest --cov=sparql_agent

# HTML report
uv run pytest --cov=sparql_agent --cov-report=html

# XML report (for CI)
uv run pytest --cov=sparql_agent --cov-report=xml
```

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

## Continuous Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Run tests
        run: uv run pytest --cov=sparql_agent --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Best Practices

1. **Write Tests First**: TDD approach
2. **Keep Tests Fast**: Unit tests < 1s
3. **Independent Tests**: No shared state
4. **Clear Names**: Descriptive test names
5. **One Assert**: Test one thing
6. **Use Fixtures**: Reduce duplication
7. **Mock External**: Mock APIs, endpoints
8. **Test Edge Cases**: Null, empty, large inputs
9. **Document Tests**: Clear docstrings
10. **Clean Up**: Use fixtures for teardown

## Troubleshooting

### Flaky Tests

```python
@pytest.mark.flaky(reruns=3)
def test_may_fail():
    """Test that sometimes fails."""
    pass
```

### Debugging Tests

```bash
# Run with debugging
uv run pytest --pdb

# Stop on first failure
uv run pytest -x

# Show local variables on failure
uv run pytest -l
```

### Timeout Tests

```python
@pytest.mark.timeout(10)
def test_with_timeout():
    """Test must complete in 10 seconds."""
    pass
```

## Next Steps

- [Contributing Guide](contributing.md)
- [Development Setup](architecture.md)
- [CI/CD Pipeline](deployment.md)
