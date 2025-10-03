"""
SPARQL Agent Test Suite

Comprehensive test coverage for the SPARQL agent system including:
- Core types and exceptions
- Discovery modules (connectivity, capabilities, statistics)
- Schema modules (VoID, ShEx, metadata inference, ontology mapping)
- Query modules (prompt engineering, intent parsing, generation)
- Execution modules (validation, execution, error handling)
- LLM providers (Anthropic, OpenAI, provider abstraction)

Run tests with:
    uv run pytest
    uv run pytest -v  # Verbose output
    uv run pytest --cov=sparql_agent  # With coverage
    uv run pytest -m unit  # Only unit tests
    uv run pytest -m integration  # Only integration tests
"""

__version__ = "0.1.0"
