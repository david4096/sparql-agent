# Testing Guide for SPARQL Agent

Complete guide for running and understanding the SPARQL agent test suite.

## Quick Start

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=sparql_agent --cov-report=term-missing

# Run specific test module
uv run pytest tests/test_core.py -v
```

## Test Suite Overview

The test suite contains **206+ test functions** across **42 test classes**, with **3500+ lines** of test code providing comprehensive coverage of all core modules.

### Test Files

#### Core Tests (`test_core.py`)
- **TestBaseAbstractClasses**: Tests for abstract base class hierarchy
- **TestEnums**: QueryStatus, OWLPropertyType, OWLRestrictionType enums
- **TestOWLClass**: OWL class creation, labels, and hierarchy
- **TestOWLProperty**: OWL property functionality and constraints
- **TestOntologyInfo**: Ontology information management
- **TestQueryResult**: Query result handling and status
- **TestSchemaInfo**: Schema discovery and statistics
- **TestLLMResponse**: LLM response parsing and metadata
- **TestGeneratedQuery**: Generated query validation
- **TestExceptionHierarchy**: Exception inheritance and handling
- **TestTypeValidation**: Type constraints and validation
- **TestTypeIntegration**: Integration of multiple types

#### Discovery Tests (`test_discovery.py`)
- **TestEndpointHealth**: Health check results and status
- **TestConnectionConfig**: Connection configuration management
- **TestRateLimiter**: Rate limiting (async and sync)
- **TestEndpointPinger**: Endpoint connectivity testing
  - Synchronous and asynchronous pinging
  - Timeout handling
  - Authentication detection
  - Server information extraction
  - Health history and uptime tracking
- **TestCapabilitiesDetector**: SPARQL capability detection
  - Version detection (1.0 vs 1.1)
  - Named graph discovery
  - Function support detection
  - Feature detection
- **TestPrefixExtractor**: Namespace and prefix management
  - Common prefix initialization
  - Conflict resolution
  - Query extraction
  - URI shortening/expansion
  - Mapping merging
- **TestDiscoveryIntegration**: End-to-end discovery workflows

#### Schema Tests (`test_schema.py`)
- **TestVoIDParser**: VoID (Vocabulary of Interlinked Datasets) parsing
- **TestShExParser**: ShEx (Shape Expressions) validation
- **TestMetadataInference**: RDF metadata inference
  - Class discovery
  - Property discovery
  - Domain/range inference
  - Cardinality constraints
  - Namespace discovery
- **TestOntologyMapper**: Ontology alignment and mapping
  - Vocabulary mapping
  - Equivalent class detection
  - Subclass relationships
  - Term suggestions
- **TestSchemaIntegration**: Complete schema workflows
- **TestSchemaPerformance**: Large graph performance tests

#### Query Tests (`test_query.py`)
- **TestPromptEngine**: LLM prompt construction
  - System prompt building
  - Query generation prompts
  - Schema context inclusion
  - Example formatting
- **TestIntentParser**: Natural language understanding
  - Simple query parsing
  - Filter condition extraction
  - Aggregation detection
  - Relationship queries
  - Ambiguity detection
  - Entity extraction
  - Query type identification
- **TestQueryGenerator**: SPARQL generation
  - Basic SELECT queries
  - Ontology-guided generation
  - Filtered queries
  - Aggregation queries
  - Multiple alternatives
  - Error handling
- **TestOntologyGenerator**: Ontology-aware generation
  - Class usage
  - Property constraints
  - Domain/range respect
  - Subclass reasoning
- **TestQueryIntegration**: End-to-end query workflows

#### Execution Tests (`test_execution.py`)
- **TestQueryValidator**: SPARQL validation
  - Syntax validation
  - Variable binding checks
  - Query form validation (SELECT, ASK, etc.)
  - FILTER, OPTIONAL, UNION validation
- **TestQueryExecutor**: Query execution
  - SELECT query execution
  - ASK query execution
  - Timeout handling
  - Execution time measurement
  - Empty and large result handling
- **TestErrorHandler**: Error recovery
  - Syntax error handling
  - Timeout recovery
  - Endpoint error handling
  - Query optimization suggestions
  - Retry with backoff
  - Query simplification
  - Complexity scoring
- **TestExecutionIntegration**: Complete execution workflows
- **TestExecutionPerformance**: Performance benchmarks

#### LLM Tests (`test_llm.py`)
- **TestLLMProvider**: Provider abstraction
  - Initialization
  - Response generation
  - System prompts
  - JSON schema support
  - Token counting
  - Cost estimation
  - Model information
  - Connection testing
- **TestAnthropicProvider**: Claude integration
  - Provider initialization
  - Response generation
  - Rate limit handling
  - Authentication errors
  - Token counting
- **TestOpenAIProvider**: GPT integration
  - Provider initialization
  - Response generation
  - JSON mode
  - Rate limit handling
  - Token counting
- **TestProviderFallback**: Multi-provider logic
  - Provider selection
  - Fallback chains
  - Health checking
  - Cost-based selection
- **TestResponseParsing**: Response handling
  - SPARQL extraction
  - JSON parsing
  - Malformed response handling
  - Code block extraction
- **TestLLMIntegration**: Complete LLM workflows
- **TestLLMPerformance**: Performance benchmarks

### Test Data (`tests/data/`)

#### sample_queries.sparql
- 10 different SPARQL query patterns
- SELECT, ASK, CONSTRUCT, DESCRIBE examples
- FILTER, OPTIONAL, UNION patterns
- Property paths and aggregations
- Complex multi-pattern queries

#### sample_ontology.ttl
- Complete OWL ontology with:
  - 10 classes (Agent, Person, Organization, etc.)
  - 8 object properties (worksFor, collaboratesWith, etc.)
  - 13 data properties (name, email, age, etc.)
  - Sample instances for testing
  - Symmetric and transitive properties
  - Domain/range constraints

## Test Markers

Tests are categorized using pytest markers:

### Standard Markers
- `@pytest.mark.unit` - Fast, isolated unit tests (no external dependencies)
- `@pytest.mark.integration` - Integration tests (may use mocked endpoints)
- `@pytest.mark.slow` - Slow-running tests (>5 seconds)
- `@pytest.mark.requires_api_key` - Requires API keys (skipped by default)
- `@pytest.mark.requires_network` - Requires internet connection

### Running by Marker
```bash
# Fast unit tests only
uv run pytest -m unit

# Integration tests
uv run pytest -m integration

# Exclude slow tests
uv run pytest -m "not slow"

# Multiple markers
uv run pytest -m "unit and not slow"
```

## Coverage Goals

**Target: >90% code coverage**

### Current Coverage by Module
```bash
# Check coverage for all modules
uv run pytest --cov=sparql_agent --cov-report=term-missing

# Check specific module
uv run pytest --cov=sparql_agent.core --cov-report=term-missing
uv run pytest --cov=sparql_agent.discovery --cov-report=term-missing
uv run pytest --cov=sparql_agent.schema --cov-report=term-missing
uv run pytest --cov=sparql_agent.query --cov-report=term-missing
uv run pytest --cov=sparql_agent.execution --cov-report=term-missing
uv run pytest --cov=sparql_agent.llm --cov-report=term-missing
```

### Generate HTML Coverage Report
```bash
uv run pytest --cov=sparql_agent --cov-report=html
open htmlcov/index.html
```

## Test Fixtures

### Shared Fixtures (conftest.py)

#### Data Fixtures
- `test_data_dir` - Temporary test data directory
- `sample_rdf_file` - Sample RDF/Turtle file
- `sample_owl_file` - Sample OWL ontology
- `sample_void_file` - VoID description
- `sample_sparql_queries` - Collection of SPARQL queries

#### Type Fixtures
- `sample_endpoint_info` - EndpointInfo instance
- `sample_owl_class` - OWLClass instance
- `sample_owl_property` - OWLProperty instance
- `sample_ontology_info` - Complete ontology
- `sample_schema_info` - Schema information
- `sample_query_result` - Query result
- `sample_llm_response` - LLM response
- `sample_generated_query` - Generated query

#### Mock Fixtures
- `mock_sparql_endpoint` - Mocked SPARQL endpoint
- `mock_ontology_provider` - Mocked ontology provider
- `mock_llm_provider` - Mocked LLM provider
- `mock_schema_discoverer` - Mocked schema discoverer
- `mock_http_response` - Mocked HTTP response
- `create_mock_response` - Factory for custom responses

#### RDFLib Fixtures
- `sample_rdf_graph` - Pre-populated RDF graph
- `sample_owl_graph` - Pre-populated OWL ontology graph

## Advanced Testing

### Parallel Execution
```bash
# Install pytest-xdist
uv pip install pytest-xdist

# Run tests in parallel
uv run pytest -n auto
```

### Watch Mode
```bash
# Install pytest-watch
uv pip install pytest-watch

# Run tests on file changes
uv run ptw tests/
```

### Debug Mode
```bash
# Verbose output with print statements
uv run pytest -s -v

# Drop into debugger on failure
uv run pytest --pdb

# Drop into debugger at start
uv run pytest --trace
```

### Performance Profiling
```bash
# Profile test execution time
uv run pytest --durations=10

# Show slowest tests
uv run pytest --durations=0
```

## Continuous Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Scheduled nightly builds

CI Matrix:
- Python versions: 3.9, 3.10, 3.11, 3.12
- Operating systems: Ubuntu, macOS, Windows
- Coverage threshold: 90%

## Common Issues

### Import Errors
```bash
# Install package in development mode
uv pip install -e .
```

### Missing Dependencies
```bash
# Install all test dependencies
uv pip install -e ".[dev]"
```

### API Key Tests Failing
```bash
# Skip tests requiring API keys
uv run pytest -m "not requires_api_key"

# Or set environment variables
export ANTHROPIC_API_KEY=your_key
export OPENAI_API_KEY=your_key
```

### Network Tests Failing
```bash
# Skip tests requiring network
uv run pytest -m "not requires_network"
```

## Best Practices

### Writing Tests

1. **Use descriptive names**: `test_validate_valid_select_query` not `test_1`
2. **One assertion per test**: Test one thing at a time
3. **Use fixtures**: Don't repeat setup code
4. **Mock external calls**: Never make real API calls in unit tests
5. **Test edge cases**: Empty inputs, invalid data, boundary conditions
6. **Add docstrings**: Explain what the test verifies

### Example Test Structure
```python
class TestQueryValidator:
    \"\"\"Tests for SPARQL query validation.\"\"\"

    def test_validate_valid_select_query(self):
        \"\"\"Test validating a syntactically correct SELECT query.\"\"\"
        # Arrange
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"

        # Act
        errors = validate_query(query)

        # Assert
        assert len(errors) == 0
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

## Getting Help

If you encounter issues:

1. Check this documentation
2. Review existing tests for examples
3. Check GitHub issues
4. Ask in team chat/discussions

## Contributing Tests

When adding new features:

1. Write tests first (TDD)
2. Ensure >90% coverage
3. Add appropriate markers
4. Update this documentation
5. Run full test suite before committing

```bash
# Run everything before committing
uv run pytest --cov=sparql_agent --cov-report=term-missing
```
