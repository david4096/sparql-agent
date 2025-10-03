# Contributing Guide

Thank you for considering contributing to SPARQL Agent! This guide will help you get started.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Follow Python and open source best practices

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then clone
git clone https://github.com/YOUR-USERNAME/sparql-agent.git
cd sparql-agent

# Add upstream remote
git remote add upstream https://github.com/david4096/sparql-agent.git
```

### 2. Set Up Development Environment

```bash
# Install UV (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Activate environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

### 3. Create a Branch

```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/my-bug-fix
```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=sparql_agent --cov-report=html

# Run specific test file
uv run pytest tests/test_query.py

# Run specific test
uv run pytest tests/test_query.py::test_query_generation
```

### Code Quality

#### Format Code

```bash
# Format with black
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/
```

#### Lint Code

```bash
# Run ruff
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check --fix src/ tests/
```

#### Type Checking

```bash
# Run mypy
uv run mypy src/
```

#### Pre-commit Hook

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

### Writing Tests

#### Unit Tests

```python
# tests/unit/test_query_generator.py
import pytest
from sparql_agent.query import QueryGenerator

def test_query_generation():
    generator = QueryGenerator()
    sparql = generator.generate("Find proteins")

    assert "SELECT" in sparql
    assert "Protein" in sparql

def test_invalid_input():
    generator = QueryGenerator()

    with pytest.raises(ValueError):
        generator.generate("")
```

#### Integration Tests

```python
# tests/integration/test_full_workflow.py
import pytest
from sparql_agent import SPARQLAgent

@pytest.mark.integration
def test_full_query_workflow():
    agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
    results = agent.query("Find 5 proteins from human")

    assert len(results) <= 5
    assert all('protein' in r for r in results)
```

#### Mock External Services

```python
from unittest.mock import Mock, patch

@patch('sparql_agent.llm.AnthropicClient')
def test_with_mocked_llm(mock_llm):
    mock_llm.return_value.generate.return_value = "SELECT * WHERE { ?s ?p ?o }"

    agent = SPARQLAgent(llm_provider="anthropic")
    results = agent.query("test")

    mock_llm.return_value.generate.assert_called_once()
```

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints for all functions
- Maximum line length: 100 characters
- Use docstrings (Google style)

### Example Function

```python
def query_endpoint(
    endpoint: str,
    sparql: str,
    timeout: int = 30
) -> List[Dict[str, Any]]:
    """Execute a SPARQL query against an endpoint.

    Args:
        endpoint: SPARQL endpoint URL
        sparql: SPARQL query string
        timeout: Query timeout in seconds

    Returns:
        List of result dictionaries

    Raises:
        EndpointError: If endpoint is unreachable
        TimeoutError: If query exceeds timeout

    Example:
        >>> results = query_endpoint(
        ...     "https://sparql.uniprot.org/sparql",
        ...     "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
        ... )
    """
    # Implementation
    pass
```

### Docstring Guidelines

```python
class SPARQLAgent:
    """An intelligent SPARQL query agent.

    This class provides natural language to SPARQL translation,
    schema discovery, and query execution capabilities.

    Attributes:
        endpoint: SPARQL endpoint URL
        llm_provider: LLM provider name
        cache: Query result cache

    Example:
        >>> agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
        >>> results = agent.query("Find proteins")
    """
```

## Contribution Types

### 1. Bug Fixes

```bash
# Create issue first, then branch
git checkout -b fix/issue-123-endpoint-timeout

# Make changes
# Add tests
# Run tests
uv run pytest

# Commit
git commit -m "Fix: Handle endpoint timeout properly (fixes #123)"
```

### 2. New Features

```bash
# Discuss in issue first
git checkout -b feature/add-graphql-support

# Implement feature
# Add tests (aim for 80%+ coverage)
# Update documentation
# Add examples

# Commit
git commit -m "Feature: Add GraphQL API support (#124)"
```

### 3. Documentation

```bash
git checkout -b docs/improve-installation-guide

# Update documentation
# Build and test locally
mkdocs serve

# Commit
git commit -m "Docs: Improve installation guide with UV examples"
```

### 4. Tests

```bash
git checkout -b test/increase-coverage

# Add missing tests
# Run coverage
uv run pytest --cov

# Commit
git commit -m "Test: Increase query module coverage to 90%"
```

## Pull Request Process

### 1. Before Submitting

Checklist:
- [ ] Tests pass (`uv run pytest`)
- [ ] Code formatted (`uv run black src/ tests/`)
- [ ] Linting passes (`uv run ruff check src/`)
- [ ] Type checking passes (`uv run mypy src/`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Commits follow conventional commits

### 2. Create Pull Request

```bash
# Push to your fork
git push origin feature/my-feature

# Create PR on GitHub
```

### 3. PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass
- [ ] No new warnings

## Related Issues
Fixes #123
Related to #456
```

### 4. Review Process

1. Automated checks run (CI/CD)
2. Maintainer reviews code
3. Address feedback
4. Approval and merge

## Commit Message Guidelines

### Conventional Commits

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

### Examples

```bash
feat(query): Add support for federated queries

Implement federated query generation and execution
across multiple SPARQL endpoints.

Closes #123

fix(llm): Handle API rate limiting properly

Add exponential backoff for LLM API calls when
rate limited.

Fixes #456

docs(tutorial): Add ontology integration tutorial

test(discovery): Add tests for VoID parsing
```

## Project Structure

```
sparql-agent/
├── src/sparql_agent/    # Source code
│   ├── core/            # Core abstractions
│   ├── query/           # Query generation
│   ├── discovery/       # Schema discovery
│   ├── ontology/        # Ontology support
│   ├── llm/             # LLM integration
│   ├── execution/       # Query execution
│   ├── formatting/      # Result formatting
│   ├── cli/             # CLI interface
│   ├── web/             # Web API
│   └── mcp/             # MCP server
├── tests/               # Tests
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/             # End-to-end tests
├── docs/                # Documentation
├── examples/            # Examples
└── pyproject.toml       # Project configuration
```

## Adding a New Module

### 1. Create Module Structure

```bash
mkdir src/sparql_agent/mymodule
touch src/sparql_agent/mymodule/__init__.py
touch src/sparql_agent/mymodule/core.py
touch tests/test_mymodule.py
```

### 2. Implement Module

```python
# src/sparql_agent/mymodule/core.py
from typing import List, Dict, Any

class MyFeature:
    """New feature implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def process(self, data: List[Dict]) -> List[Dict]:
        """Process data."""
        # Implementation
        pass
```

### 3. Add Tests

```python
# tests/test_mymodule.py
import pytest
from sparql_agent.mymodule import MyFeature

def test_my_feature():
    feature = MyFeature(config={})
    result = feature.process([{"test": "data"}])
    assert len(result) == 1
```

### 4. Update Documentation

```markdown
# docs/mymodule.md

# My Module

Description of the module...

## Usage

\```python
from sparql_agent.mymodule import MyFeature

feature = MyFeature()
result = feature.process(data)
\```
```

### 5. Add Examples

```python
# examples/mymodule_example.py
from sparql_agent.mymodule import MyFeature

# Example usage
feature = MyFeature(config={"option": "value"})
result = feature.process(data)
print(result)
```

## Adding a New LLM Provider

```python
# src/sparql_agent/llm/mymodel_provider.py
from sparql_agent.llm.client import LLMProvider

class MyModelClient(LLMProvider):
    """My custom LLM provider."""

    def __init__(self, api_key: str, model: str = "default"):
        self.api_key = api_key
        self.model = model

    def generate_query(
        self,
        natural_query: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate SPARQL from natural language."""
        # Implementation
        pass
```

## Performance Considerations

- Profile code before optimizing
- Use `pytest-benchmark` for benchmarks
- Cache expensive operations
- Use async I/O where appropriate
- Consider memory usage

## Documentation Standards

### Markdown Files

- Use clear headings
- Include code examples
- Add diagrams where helpful
- Keep line length reasonable
- Link to related docs

### API Documentation

- Use Google-style docstrings
- Include type hints
- Provide examples
- Document exceptions
- Link to related functions

## Getting Help

- GitHub Issues: Report bugs or request features
- Discussions: Ask questions or share ideas
- Email: maintainer@example.com
- Discord: [Join our community](#)

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md
- Release notes
- Documentation credits

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Your contributions make SPARQL Agent better for everyone.
